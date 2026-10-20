"""Original genuine protected close, one durable fake stop-cancel phase."""
from dataclasses import replace
from datetime import timedelta
import json
import unittest
from unittest.mock import patch

import tests.product.test_trading_protected_close_v02 as fixtures
import tests.product.test_trading_inventory_v02 as inventory_fixtures


class TradingStopCleanupV02Tests(unittest.TestCase):
    def setUp(self):
        self.flow=fixtures.GenuineProtectedCloseContext(self).protect()
        self.fixture=self.flow.fixture;self.service=self.flow.service;self.provider=self.flow.provider

    def algo(self,**changes):
        now=self.fixture.clock[0]
        row=dict(self.flow.stop.materialization.body,instType='SWAP',algoId='2345',state='live',
            ordIdList=[],actualSz='0',failCode='',cTime=str(int(self.flow.stop.canonical_request.created_at.timestamp()*1000)),
            uTime=str(int(now.timestamp()*1000)))
        row.update(changes);return row

    def flat(self):
        self.flow.close_readback(flat=False);self.flow.close_readback(flat=True)
        self.fixture.clock[0]+=timedelta(seconds=1)

    def reads(self,*,net='0',extra=False,empty=False,stop_changes=None):
        algo=self.algo(**(stop_changes or {}))
        self.flow.append(dict(code='0',data=[algo]),self.flow.position.response(pos=net,posId='5678',avgPx='0' if net=='0' else '60000'))
        stop=self.service.read_fixture_cleanup_stop(self.flow.stop.canonical_request.order_request_id,
            expected_revision=self.fixture.revision)
        metadata,proof=self.flow.fresh()
        native=self.service.read_position(metadata=metadata,proof=proof,expected_revision=self.fixture.revision,
            expected_provider_position_id='5678')
        rows=[] if empty else [algo]
        if extra:rows.append(dict(algo,algoId='9999',algoClOrdId='UNOWNEDSTOP'))
        self.flow.append(*inventory_fixtures.TradingInventoryV02Tests(methodName='runTest').scans(rows))
        inventory=self.service.read_algo_inventory(metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        return stop,native,inventory,metadata,proof

    def prepare(self,reads):
        stop,native,inventory,metadata,proof=reads
        return self.service.prepare_fixture_stop_cleanup(self.flow.stop.canonical_request.order_request_id,
            stop,native,inventory,metadata=metadata,proof=proof,expected_revision=self.fixture.revision)

    def execute(self,prepared):
        return self.service.execute_fixture_stop_cleanup(prepared,expected_revision=self.fixture.revision)

    def cancel_calls(self):return [c for c in self.provider.calls if c['path']=='/api/v5/trade/cancel-algos']

    def test_one_exact_target_cancel_ack_leaves_original_stop_unsettled_and_duplicate_never_resends(self):
        self.flat();reads=self.reads();before=self.flow.recover();prepared=self.prepare(reads)
        self.assertEqual(self.flow.recover(),before);self.assertEqual(self.cancel_calls(),[])
        self.flow.append(dict(code='0',data=[dict(algoId='2345',sCode='0')]))
        outcome=self.execute(prepared)
        self.assertEqual(outcome.status,'CLEANUP_READBACK_REQUIRED')
        self.assertEqual(self.execute(prepared),outcome)
        self.assertEqual(self.execute(self.prepare(self.reads())),outcome)
        calls=self.cancel_calls();self.assertEqual(len(calls),1)
        self.assertEqual(calls[0]['method'],'POST');self.assertEqual(calls[0]['body'],[dict(instId='BTC-USDT-SWAP',algoId='2345')])
        after=self.flow.recover();self.assertEqual(after,before)
        self.assertIsNone(after.trade_result);self.assertEqual(after.current_position_projection.payload['lifecycle_state'],'EXIT_REQUESTED')

    def test_before_original_flat_cleanup_refuses_without_cancel(self):
        with self.assertRaises(ValueError):self.prepare(self.reads(net='10'))
        self.assertEqual(self.cancel_calls(),[])

    def test_reads_expiring_during_actual_post_guard_preserve_claim_without_cancel(self):
        import application.trading.stop_cleanup as cleanup
        self.flat();prepared=self.prepare(self.reads())
        self.fixture.clock[0]+=timedelta(seconds=4.9)
        self.flow.append(dict(code='0',data=[dict(algoId='2345',sCode='0')]))
        original_request=self.provider.request;original_context=cleanup._context
        inside_post=[False];advanced=[False]
        def request(method,path,**kwargs):
            inside_post[0]=method=='POST' and path=='/api/v5/trade/cancel-algos'
            try:return original_request(method,path,**kwargs)
            finally:inside_post[0]=False
        def context(*args,**kwargs):
            value=original_context(*args,**kwargs)
            if inside_post[0] and not advanced[0]:
                self.fixture.clock[0]+=timedelta(seconds=0.2);advanced[0]=True
            return value
        denied=None
        with patch.object(self.provider,'request',side_effect=request),patch.object(cleanup,'_context',side_effect=context):
            try:self.execute(prepared)
            except ValueError as error:denied=error
        self.assertTrue(advanced[0],'Cross the boundary inside the actual provider final guard')
        self.assertIsNotNone(self.service.dispatch.stop_cleanup_claim(self.service.run_id,prepared.stop_operation_id))
        self.assertEqual(self.cancel_calls(),[])
        self.assertIsNotNone(denied)

    def append_unknown_entry(self):
        from storage.product_dispatch import open_product_dispatch_journal
        decision=self.service.admission.evaluate(self.service.identity,expected_revision=self.fixture.revision,
            permission='MANAGE_EXISTING',execution=self.service.execution)
        self.assertTrue(decision.allowed)
        with open_product_dispatch_journal(self.fixture.root/'dispatch.sqlite') as writer:
            writer.ensure_run('other-cleanup',decision.owner_permission,now=self.fixture.clock[0])
            lease=writer.begin_process('other-cleanup','other-cleanup:1',expected_generation=0,now=self.fixture.clock[0])
            unknown=dict(role='ENTRY',path='/api/v5/trade/order',native_client_id='OTHERCLEANUP',
                body=dict(instId='BTC-USDT-SWAP',tdMode='isolated',posSide='net',side='buy',ordType='market',sz='10',clOrdId='OTHERCLEANUP'),
                canonical_request_hash='sha256:'+'1'*64,authority_hash='sha256:'+'2'*64)
            writer.prepare('other-cleanup','other-cleanup-op',unknown,lease=lease,now=self.fixture.clock[0])
            writer.claim_dispatch('other-cleanup','other-cleanup-op',lease=lease,now=self.fixture.clock[0])

    def test_actual_second_connection_append_at_claim_writer_blocks_claim_and_cancel(self):
        self.flat();prepared=self.prepare(self.reads());original=self.service.dispatch.claim_stop_cleanup
        def append_then_claim(*args,**kwargs):
            self.append_unknown_entry();return original(*args,**kwargs)
        with patch.object(self.service.dispatch,'claim_stop_cleanup',side_effect=append_then_claim):
            with self.assertRaises(ValueError):self.execute(prepared)
        self.assertIsNone(self.service.dispatch.stop_cleanup_claim(self.service.run_id,prepared.stop_operation_id))
        self.assertEqual(self.cancel_calls(),[])

    def test_actual_second_connection_append_after_claim_blocks_final_provider_guard(self):
        self.flat();prepared=self.prepare(self.reads());original=self.service.dispatch.claim_stop_cleanup
        def claim_then_append(*args,**kwargs):
            claimed=original(*args,**kwargs);self.append_unknown_entry();return claimed
        with patch.object(self.service.dispatch,'claim_stop_cleanup',side_effect=claim_then_append):
            with self.assertRaises(ValueError):self.execute(prepared)
        self.assertIsNotNone(self.service.dispatch.stop_cleanup_claim(self.service.run_id,prepared.stop_operation_id))
        self.assertEqual(self.cancel_calls(),[])

    def test_cleanup_claim_is_immutable_even_when_recursive_delete_triggers_are_disabled(self):
        import sqlite3
        self.flat();prepared=self.prepare(self.reads());self.flow.append('LOST_ACK');self.execute(prepared)
        connection=self.service.dispatch._db;connection.execute('PRAGMA recursive_triggers=OFF')
        original=connection.execute('SELECT * FROM product_dispatch_stop_cleanup_claims').fetchone()
        operations=[('UPDATE product_dispatch_stop_cleanup_claims SET source_hash=?',('changed',)),
            ('DELETE FROM product_dispatch_stop_cleanup_claims',()),
            ('INSERT OR REPLACE INTO product_dispatch_stop_cleanup_claims VALUES('+','.join('?' for _ in original)+')',tuple(original))]
        replacement=dict(original);replacement['stop_operation_id']='replacement'
        operations.append((operations[-1][0],tuple(replacement.values())))
        for sql,args in operations:
            with self.subTest(sql=sql),self.assertRaises(sqlite3.IntegrityError):connection.execute(sql,args)
            connection.rollback()
            self.assertEqual(tuple(connection.execute('SELECT * FROM product_dispatch_stop_cleanup_claims').fetchone()),tuple(original))

    def test_copied_expired_native_nonzero_or_unowned_inventory_cannot_cancel(self):
        self.flat();reads=self.reads();stop,native,inventory,metadata,proof=reads
        for bad in ((replace(stop),native,inventory,metadata,proof),(stop,replace(native),inventory,metadata,proof),
                (stop,native,replace(inventory),metadata,proof)):
            with self.subTest(source=type(bad[0])),self.assertRaises(ValueError):self.prepare(bad)
        prepared=self.prepare(reads)
        with self.assertRaises(ValueError):self.execute(replace(prepared))
        self.fixture.clock[0]+=timedelta(seconds=6)
        with self.assertRaises(ValueError):self.execute(prepared)
        self.assertEqual(self.cancel_calls(),[])

    def test_empty_inventory_or_competing_active_object_is_not_cleanup_authority(self):
        self.flat()
        for empty,extra in ((True,False),(False,True)):
            with self.subTest(empty=empty,extra=extra),self.assertRaises(ValueError):
                self.prepare(self.reads(empty=empty,extra=extra))
        self.assertEqual(self.cancel_calls(),[])

    def test_lost_cancel_ack_keeps_claim_then_native_terminal_is_reconciled_without_another_cancel(self):
        self.flat();prepared=self.prepare(self.reads());self.flow.append('LOST_ACK')
        outcome=self.execute(prepared);self.assertEqual(outcome.status,'CLEANUP_READBACK_REQUIRED')
        self.assertEqual(self.execute(prepared),outcome);self.assertEqual(len(self.cancel_calls()),1)
        self.fixture.clock[0]+=timedelta(seconds=1)
        self.flow.append(dict(code='0',data=[self.algo(state='canceled')]))
        result=self.service.reconcile(self.flow.stop.canonical_request.order_request_id,expected_revision=self.fixture.revision)
        self.assertEqual(result.status,'ALGO_OBSERVED')
        recovered=self.flow.recover();stop=next(r.payload for r in recovered.current_order_results
            if r.payload['order_request_id']==self.flow.stop.canonical_request.order_request_id)
        self.assertEqual(stop['order_status'],'CANCELED');self.assertEqual(len(self.cancel_calls()),1)
        self.assertIsNone(recovered.trade_result);self.assertEqual(recovered.current_position_projection.payload['lifecycle_state'],'EXIT_REQUESTED')

    def test_provider_or_execution_replacement_denies_before_any_cancel(self):
        from application.trading.provider import FakeProductProvider
        self.flat();prepared=self.prepare(self.reads());old=self.service.provider
        self.service.provider=FakeProductProvider([])
        with self.assertRaises(ValueError):self.execute(prepared)
        self.service.provider=old;self.service.execution='PRODUCTION'
        with self.assertRaises(ValueError):self.execute(prepared)
        self.assertEqual(self.cancel_calls(),[])

    def test_successor_process_generation_two_reads_original_stop_without_resending_cancel(self):
        self.flat();prepared=self.prepare(self.reads());self.flow.append("LOST_ACK");self.execute(prepared)
        self.assertEqual(len(self.cancel_calls()),1)
        # self is TradingStopCleanupV02Tests after real flat + cleanup LOST_ACK.
        from dataclasses import replace
        from datetime import timedelta
        from tests.integration.test_runtime_preflight import RuntimePreflightV01Tests
        from registry.operational_authority import stamp
        from application.trading.admission import RuntimeAdmission
        from application.trading.service import TradingService
        from application.trading.provider import FakeProductProvider
        from brokers.okx_product_capability import OKXProductCapabilityOwner
        from brokers.okx_product import OKXProductTranslator
        from storage.product_dispatch import open_product_dispatch_journal
        from storage.runtime import open_paper_runtime_journal

        self.fixture.clock[0] += timedelta(seconds=1)
        successor_started_at = self.fixture.clock[0]
        successor_instance = 'process-fixture-cleanup-successor-002'

        def successor_preflight():
            base = RuntimePreflightV01Tests(); base.setUp()
            release = self.fixture.release[0]
            base.revision = release.executable_revision
            base.config_hash = release.config_hash
            base.capability_hash = release.capability_hash
            base.authorization_capability_hash = release.capability_hash
            value = base._input(role='PAPER_RUNTIME')
            now = self.fixture.clock[0]
            runtime_generation = 'runtime-generation:' + str(release.runtime_generation)
            config_generation = 'config-generation:' + str(release.config_generation)
            authorization = dict(value.authorization_evidence,
                authorization_class='PERSISTENT_LIVE_RUNTIME', authorized_runtime_role='LIVE_RUNTIME')
            value = replace(value,
                runtime_preflight_profile_version='product-runtime-preflight-v0.2',
                runtime_role='LIVE_RUNTIME', requested_operational_mode='LIVE',
                evaluated_at=stamp(now), process_instance_id=successor_instance,
                process_start_generation_id=runtime_generation,
                process_started_at=stamp(successor_started_at),
                runtime_config_generation_id=config_generation,
                heartbeat_evidence=dict(value.heartbeat_evidence,
                    heartbeat_process_instance_id=successor_instance,
                    heartbeat_process_start_generation_id=runtime_generation,
                    heartbeat_observed_at=stamp(now), heartbeat_received_at=stamp(now)),
                reconciliation_evidence=dict(value.reconciliation_evidence,
                    reconciliation_observed_at=stamp(now)),
                external_consumer_evidence=dict(value.external_consumer_evidence,
                    compatibility_observed_at=stamp(now)),
                authorization_evidence=authorization)
            authority = base._authority(value)
            authority = replace(authority,
                runtime_config_authority=dict(authority.runtime_config_authority,
                    runtime_config_generation_id=config_generation))
            return value, authority

        new_admission = RuntimeAdmission(namespace='FIXTURE', registry_factory=self.fixture.factory,
            current_preflight=successor_preflight, clock=lambda: self.fixture.clock[0],
            maximum_observation_age_seconds=5)
        new_capabilities = OKXProductCapabilityOwner()
        new_translator = OKXProductTranslator(new_capabilities)
        new_dispatch = open_product_dispatch_journal(self.fixture.root/'dispatch.sqlite')
        new_canonical = open_paper_runtime_journal(self.fixture.root/'canonical.sqlite')
        self.addCleanup(new_dispatch.close); self.addCleanup(new_canonical.close)
        # Only actual canceled target response; this source cannot submit an effect.
        new_provider = FakeProductProvider([dict(code='0',data=[self.algo(state='canceled')])])
        successor = TradingService(admission=new_admission, translator=new_translator,
            dispatch=new_dispatch, canonical=new_canonical, provider=new_provider,
            identity=self.fixture.identity, run_id=self.service.run_id,
            clock=lambda: self.fixture.clock[0])
        prior_claim = self.service.dispatch.stop_cleanup_claim(self.service.run_id,
            self.flow.stop.canonical_request.order_request_id)
        self.assertIsNotNone(prior_claim)
        old_lease = self.service.lease
        lease = successor.bind_process(expected_revision=self.fixture.revision, expected_generation=1)
        self.assertEqual(2, lease.generation)
        self.assertEqual(successor_instance, lease.instance_id)
        self.assertNotEqual(old_lease.instance_id, lease.instance_id)
        # No issuing old read/proof/preparation object to successor, no replayed cancel.
        successor.recover_publications()
        result = successor.reconcile(self.flow.stop.canonical_request.order_request_id,
                                     expected_revision=self.fixture.revision)
        self.assertEqual('ALGO_OBSERVED', result.status)
        self.assertTrue(new_provider.calls)
        self.assertTrue(all(row['method']=='GET' for row in new_provider.calls))
        self.assertEqual(['/api/v5/trade/order-algo'], [row['path'] for row in new_provider.calls])
        self.assertEqual(prior_claim, new_dispatch.stop_cleanup_claim(successor.run_id,
            self.flow.stop.canonical_request.order_request_id))
        recovered = new_canonical.recover(trade_plan_id=self.flow.recover().trade_plan_id)
        stop_result = next(row.payload for row in recovered.current_order_results
            if row.payload['order_request_id']==self.flow.stop.canonical_request.order_request_id)
        self.assertEqual('CANCELED', stop_result['order_status'])
        self.assertIsNone(recovered.trade_result)
        self.assertEqual('EXIT_REQUESTED', recovered.current_position_projection.payload['lifecycle_state'])
        # Actual result arrival can require E5 execution reinterpretation; do not claim
        # restart_authoritative merely from successful targeted cancel readback.
        with self.assertRaises(ValueError):
            self.service.dispatch.require_process(old_lease,now=self.fixture.clock[0])
        self.assertEqual(len(self.cancel_calls()),1)
