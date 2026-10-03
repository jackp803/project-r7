import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from registry.models import StrategyIdentity
from registry.operational_authority import CurrentRuntimePermission, ReleaseBinding


class ProductDispatchV02Tests(unittest.TestCase):
    def setUp(self):
        from storage.product_dispatch import open_product_dispatch_journal
        self.open = open_product_dispatch_journal
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'dispatch.sqlite'
        self.now = datetime(2026, 10, 3, tzinfo=timezone.utc)
        self.owner = self.permission()

    def permission(self):
        hashed = 'sha256:' + '1' * 64
        release = ReleaseBinding('FIXTURE', hashed, '1' * 40, hashed, hashed, 1, hashed, hashed,
                                 'OKX_FIXTURE', 'sanitized-account', hashed, 1, 1, 'FIXTURE')
        return CurrentRuntimePermission(StrategyIdentity('strategy', '1.0.0'), hashed, 7, 'NEW_EXPOSURE',
                    'FIXTURE', release, 'approval', hashed, 'activation', hashed,
                    self.now.isoformat().replace('+00:00', 'Z'), 'SIMULATED_MECHANICS')

    def request(self, client='r7abc'):
        return dict(role='ENTRY', path='/api/v5/trade/order', native_client_id=client,
                    body=dict(instId='BTC-USDT-SWAP', tdMode='isolated', posSide='net', side='buy',
                              ordType='market', sz='10', clOrdId=client),
                    canonical_request_hash='sha256:' + '2' * 64, authority_hash='sha256:' + '3' * 64)

    def initialized(self):
        journal = self.open(self.path)
        self.addCleanup(journal.close)
        journal.ensure_run('run', self.owner, now=self.now)
        lease = journal.begin_process('run', 'pid:1', expected_generation=0, now=self.now)
        return journal, lease

    def test_dispatch_claim_survives_crash_and_never_grants_a_second_post(self):
        journal, lease = self.initialized()
        journal.prepare('run', 'operation', self.request(), lease=lease, now=self.now)
        self.assertEqual('PREPARED', journal.operation('run', 'operation').status)
        self.assertTrue(journal.claim_dispatch('run', 'operation', lease=lease, now=self.now))
        self.assertFalse(journal.claim_dispatch('run', 'operation', lease=lease, now=self.now))
        journal.close()
        with self.open(self.path) as recovered:
            new_lease = recovered.begin_process('run', 'pid:2', expected_generation=1, now=self.now + timedelta(seconds=1))
            operation = recovered.operation('run', 'operation')
            self.assertEqual('DISPATCHING', operation.status)
            self.assertEqual('READBACK_REQUIRED', operation.recovery_disposition)
            self.assertFalse(recovered.claim_dispatch('run', 'operation', lease=new_lease, now=self.now + timedelta(seconds=1)))
            self.assertEqual(('operation',), recovered.recover('run').ambiguous_operations)

    def test_two_actual_connections_can_claim_a_dispatch_only_once(self):
        journal, lease = self.initialized()
        journal.prepare('run', 'operation', self.request(), lease=lease, now=self.now)
        barrier = Barrier(2)
        def claim():
            with self.open(self.path) as writer:
                barrier.wait(timeout=10)
                return writer.claim_dispatch('run', 'operation', lease=lease, now=self.now)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: claim(), range(2)))
        self.assertEqual(1, sum(results))

    def test_new_process_fences_old_writer_and_copied_receipts_are_data_only(self):
        journal, lease = self.initialized()
        journal.prepare('run', 'operation', self.request(), lease=lease, now=self.now)
        journal.begin_process('run', 'pid:2', expected_generation=1, now=self.now + timedelta(seconds=1))
        with self.assertRaises(ValueError):
            journal.claim_dispatch('run', 'operation', lease=lease, now=self.now + timedelta(seconds=1))
        with self.assertRaises(ValueError):
            journal.begin_process('run', 'pid:1', expected_generation=2, now=self.now + timedelta(seconds=2))
        with self.assertRaises(ValueError):
            journal.claim_dispatch('run', 'operation', lease={'generation': 2}, now=self.now + timedelta(seconds=2))

    def test_observation_is_immutable_and_ack_or_ambiguity_is_not_terminal_truth(self):
        journal, lease = self.initialized()
        journal.prepare('run', 'operation', self.request(), lease=lease, now=self.now)
        journal.claim_dispatch('run', 'operation', lease=lease, now=self.now)
        ack = dict(status='ACK_PENDING', provider_id='123', reason_code='PROVIDER_ACK_PENDING')
        journal.observe('run', 'operation', ack, lease=lease, now=self.now)
        self.assertEqual('READBACK_REQUIRED', journal.operation('run', 'operation').recovery_disposition)
        self.assertFalse(journal.claim_dispatch('run', 'operation', lease=lease, now=self.now))
        journal.observe('run', 'operation', ack, lease=lease, now=self.now)
        with self.assertRaises(ValueError):
            journal.observe('run', 'operation', dict(ack, status='CLOSED'), lease=lease, now=self.now)

    def test_changed_request_historical_client_reuse_and_secret_payload_fail_closed(self):
        journal, lease = self.initialized()
        journal.prepare('run', 'operation', self.request(), lease=lease, now=self.now)
        for request in (dict(self.request(), body=dict(self.request()['body'], sz='11')),
                        dict(self.request(), api_key='fake secret')):
            with self.assertRaises(ValueError):
                journal.prepare('run', 'operation', request, lease=lease, now=self.now)
        with self.assertRaises(ValueError):
            journal.prepare('run', 'other-operation', self.request(), lease=lease, now=self.now)
        journal.ensure_run('other-run', self.owner, now=self.now)
        other_lease = journal.begin_process('other-run', 'pid:3', expected_generation=0, now=self.now)
        with self.assertRaises(ValueError):
            journal.prepare('other-run', 'operation', self.request(), lease=other_lease, now=self.now)

    def test_binding_drift_and_namespace_mix_cannot_reopen_a_run(self):
        journal, _ = self.initialized()
        with self.assertRaises(ValueError):
            journal.ensure_run('run', replace(self.owner, approval_record_id='other'), now=self.now)
        real_release = replace(self.owner.release, namespace='LOCAL_RESEARCH', release_kind='SOURCE_QUALIFIED')
        real = replace(self.owner, namespace='LOCAL_RESEARCH', release=real_release, execution='ACTUAL_OWNER')
        with self.assertRaises(ValueError):
            journal.ensure_run('real-run', real, now=self.now)

    def test_account_ambiguity_inventory_includes_other_runs_but_not_unclaimed_or_other_accounts(self):
        journal, lease = self.initialized()
        journal.prepare('run', 'unclaimed', self.request('unclaimed'), lease=lease, now=self.now)
        journal.ensure_run('same-account-run', self.owner, now=self.now)
        other_lease = journal.begin_process('same-account-run', 'pid:2', expected_generation=0, now=self.now)
        journal.prepare('same-account-run', 'claimed', self.request('sameaccount'), lease=other_lease, now=self.now)
        journal.claim_dispatch('same-account-run', 'claimed', lease=other_lease, now=self.now)
        other_owner = replace(self.owner, release=replace(self.owner.release, account_ref='another-account'))
        journal.ensure_run('another-account-run', other_owner, now=self.now)
        another_lease = journal.begin_process('another-account-run', 'pid:3', expected_generation=0, now=self.now)
        journal.prepare('another-account-run', 'another-claimed', self.request('anotheraccount'), lease=another_lease, now=self.now)
        journal.claim_dispatch('another-account-run', 'another-claimed', lease=another_lease, now=self.now)
        self.assertEqual([('same-account-run', 'claimed')],
            [(item.run_id, item.operation_id) for item in journal.claimed_entries_for_account('run')])

    def test_malformed_body_roles_and_credential_headers_never_reach_claim(self):
        journal, lease = self.initialized()
        for request in (dict(self.request(), body=[]), dict(self.request(), body=None),
                        dict(self.request(), role=[]), dict(self.request(), body=dict(self.request()['body'], credentials='fake'))):
            with self.subTest(request=request), self.assertRaises(ValueError):
                journal.prepare('run', 'operation', request, lease=lease, now=self.now)
        self.assertIsNone(journal.operation('run', 'operation'))


if __name__ == '__main__':
    unittest.main()
