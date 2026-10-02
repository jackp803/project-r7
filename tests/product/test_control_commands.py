from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


class ControlCommandTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('application.control_api.commands'),
                             'Durable exact-subject command ledger is missing')
        from application.control_api.commands import CommandLedger, CommandError
        self.type, self.error = CommandLedger, CommandError
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'commands.sqlite'
        self.clock = [datetime(2026, 10, 3, tzinfo=timezone.utc)]
        self.ledger = self.type(self.path, namespace='FIXTURE', clock=lambda: self.clock[0])

    def prepare(self, command='command-one', *, actor='local-owner', expected=4, actual=4, request=None, resource='strategy:one:1'):
        return self.ledger.prepare(command_id=command, operation='PAPER_START', resource=resource,
            actor=actor, expected_revision=expected, actual_revision=actual,
            arguments={'policy_id': 'selected'} if request is None else request)

    def test_completed_retry_returns_identical_historical_receipt_after_revision_changes(self):
        claim = self.prepare()
        receipt = {'command_id': 'command-one', 'status': 'COMPLETE', 'resource_revision': 5, 'effect_ref': 'actual-owner:one'}
        self.ledger.complete(claim, receipt)
        other = self.type(self.path, namespace='FIXTURE', clock=lambda: self.clock[0])
        self.assertEqual(other.prepare(command_id='command-one', operation='PAPER_START', resource='strategy:one:1',
            actor='local-owner', expected_revision=4, actual_revision=100, arguments={'policy_id': 'selected'}), receipt)

    def test_changed_request_actor_subject_or_expected_revision_conflicts_under_same_id(self):
        claim = self.prepare()
        self.ledger.complete(claim, {'status': 'COMPLETE'})
        cases = ({'actor': 'another'}, {'resource': 'strategy:two:1'}, {'request': {'policy_id': 'different'}}, {'expected': 5, 'actual': 5})
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(self.error) as error: self.prepare(**case)
                self.assertEqual(error.exception.code, 'CONFLICT')

    def test_stale_revision_is_rejected_without_reserving_command(self):
        with self.assertRaises(self.error) as error: self.prepare(actual=5)
        self.assertEqual(getattr(error.exception,'reason',None),'RESOURCE_REVISION_CONFLICT')
        self.assertIsNotNone(self.prepare())

    def test_pending_effect_fences_other_commands_without_holding_sql_transaction(self):
        claim = self.prepare()
        with self.assertRaises(self.error): self.prepare('other-command')
        independent = self.prepare('independent', resource='strategy:two:1')
        self.ledger.complete(independent, {'status': 'COMPLETE'})
        self.ledger.complete(claim, {'status': 'COMPLETE'})
        self.assertIsNotNone(self.prepare('other-command', actual=5, expected=5))

    def test_expired_crash_claim_reuses_same_owner_command_and_fences_old_completion(self):
        old = self.prepare()
        self.clock[0] += timedelta(seconds=31)
        new = self.prepare(actual=5)
        self.assertEqual(new.command_id, old.command_id)
        self.assertEqual(new.request_json, old.request_json)
        self.assertGreater(new.generation, old.generation)
        with self.assertRaises(self.error): self.ledger.complete(old, {'status': 'COMPLETE'})
        self.ledger.complete(new, {'status': 'COMPLETE', 'resource_revision': 5})

    def test_active_identical_command_reports_busy_instead_of_dispatching_twice(self):
        self.prepare()
        with self.assertRaises(self.error) as error: self.prepare()
        self.assertEqual(error.exception.code, 'COMMAND_IN_PROGRESS')

    def test_expired_lease_cannot_publish_success(self):
        claim = self.prepare()
        self.clock[0] += timedelta(seconds=30)
        with self.assertRaises(self.error): self.ledger.complete(claim, {'status': 'COMPLETE'})

    def test_secret_fields_and_unbounded_payload_never_enter_command_store(self):
        for request in ({'password': 'fixture'}, {'nested': {'access_token': 'fixture'}}, {'value': 'x' * 70000}, {'float': float('nan')}):
            with self.subTest(kind=list(request)):
                with self.assertRaises(self.error): self.prepare(request=request)
        self.assertIsNotNone(self.prepare())

    def test_namespace_mismatch_and_boolean_revisions_are_rejected(self):
        with self.assertRaises(self.error): self.type(self.path, namespace='LOCAL_RESEARCH', clock=lambda: self.clock[0])
        with self.assertRaises(self.error): self.prepare(expected=True, actual=True)


if __name__ == '__main__': unittest.main()
