"""Driver contract tests only; mocks never establish native qualification."""
from contextlib import closing
import importlib
import io
import json
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from application.cloud.manifest import canonical_bytes
from application.cloud.paper_feedback import SCHEMA, UNCERTAINTY, paper_feedback_bundle
from application.platform.private_files import create_private_directory, write_private_new

TOOLS = Path(__file__).resolve().parents[2] / 'tools'
sys.path.insert(0, str(TOOLS))


class PaperPublicationDriverTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module('verify_paper_publication')
        temp = TemporaryDirectory(prefix='R7 publication driver ')
        self.addCleanup(temp.cleanup)
        self.output = Path(temp.name) / 'scope'
        create_private_directory(self.output)
        self.flow = object.__new__(self.module.NativePublicationFlow)
        self.flow.output = self.output
        self.flow.data = self.output / 'data'
        self.flow.cloud = self.output / 'synthetic-cloud'
        for path in (self.flow.data, self.flow.cloud):
            create_private_directory(path)
        self.flow.config = self.output / 'product.json'
        self.flow.password = 'SYNTHETIC_TEST_PASSWORD_ONLY'
        self.flow.observation = {'passed': False, 'commands': []}
        self.flow.commands = self.flow.observation['commands']
        self.flow.persist = Mock()
        self.flow.guard = Mock()

    def test_internal_hashed_owner_input_none_disclosure_is_not_an_untrusted_public_payload(self):
        h='sha256:'+'1'*64
        value=dict(strategy={'content_hash':h},dataset_manifest_hash=h,split_policy_hash=h,
            provenance=dict(credentials='NONE',provider_requests=0,capital='NONE',github_compute='NOT_USED'))
        raw=canonical_bytes(value)
        row=dict(input_json=raw.decode(),input_hash=self.module.sha(raw))
        self.assertEqual(self.module.observed_research_input(row),value)
        from application.cloud.manifest import load_json
        from application.cloud.protocol import CloudError
        with self.assertRaisesRegex(CloudError,'SECRET_FIELD_FORBIDDEN'):load_json(raw)
        for changed in (dict(row,input_hash='sha256:'+'2'*64),
                dict(input_json='{"provenance":{},"provenance":{}}',input_hash=self.module.sha(b'{"provenance":{},"provenance":{}}')),
                dict(input_json=' '*(self.module.MAX_PAYLOADS+1),input_hash=self.module.sha(b' '*(self.module.MAX_PAYLOADS+1)))):
            with self.subTest(changed=tuple(changed)),self.assertRaises(ValueError):self.module.observed_research_input(changed)

    def row(self):
        h = 'sha256:' + '1' * 64
        document = dict(schema_version=SCHEMA, run_id='paper-run', namespace='FIXTURE',
            strategy=dict(strategy_id='synthetic', strategy_version='1', content_hash=h),
            source=dict(executable_revision='1'*40, implementation_hash=h, execution='LOCAL', worktree='CLEAN'),
            binding=dict(config_hash=h, risk_policy_hash=h, paper_policy_hash=h),
            producer=dict(process_generation=1, process_instance_hash=h),
            observation=dict(mode='ACCELERATED_FIXTURE', execution='SIMULATED_MECHANICS',
                started_at='2026-10-01T00:00:00Z', observed_at='2026-10-01T00:00:05Z',
                actual_elapsed_seconds=0, actual_healthy_seconds=0, simulated_elapsed_seconds=5,
                simulated_healthy_seconds=3, max_observed_gap_seconds=1, closed_trades=1),
            assessment=dict(status='BLOCKED', reason_codes=['INSUFFICIENT_CLOSED_TRADES'], run_revision=2, assessment_hash=h),
            performance_policy='OPT_OUT', performance=None,
            cost_conventions=dict(slippage='IN_FILL_PRICE_NO_ADDITIONAL_DEDUCTION', funding_model='EXPLICIT_REGISTERED_PAPER_ZERO',
                account_scope='ISOLATED_PER_STRATEGY_RUN'), live=dict(status='NOT_RUN', performance=None),
            broker_kind='PAPER_ONLY', financial_authority='NONE', artifact_links=[], uncertainty=list(UNCERTAINTY),
            created_at='2026-10-01T00:00:05Z')
        bundle = paper_feedback_bundle(document)
        raw = bundle.payloads['feedback.json']
        digest = self.module.sha(raw)
        return dict(operation_id='r7-paper-feedback-'+digest[7:], run_id='paper-run',
            feedback_json=raw.decode(), feedback_hash=digest, logical_path=bundle.logical_path,
            payloads_json=canonical_bytes({key:value.decode() for key,value in bundle.payloads.items()}).decode(),
            artifact_hash=self.module.sha(canonical_bytes({key:self.module.sha(value) for key,value in bundle.payloads.items()})),
            state='PENDING', attempts=0, run_revision=2, process_generation=1)

    def test_actual_schema_bundle_hashes_and_elapsed_disclosure_are_checked(self):
        row = self.row()
        document, payloads = self.module.validate_report_row(row, 'paper')
        self.assertEqual(document['observation']['actual_elapsed_seconds'], 0)
        self.assertEqual(document['observation']['simulated_elapsed_seconds'], 5)
        self.assertIn(b'R7', payloads['report.html'])

    def test_changed_html_payload_hash_operation_and_disclosure_are_rejected(self):
        original = self.row()
        for change in ({'feedback_hash':'sha256:'+'2'*64}, {'operation_id':'forged'},
                {'artifact_hash':'sha256:'+'2'*64}, {'payloads_json':json.dumps({'feedback.json':original['feedback_json'], 'report.html':'changed'})}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.module.validate_report_row({**original, **change}, 'paper')
        with self.assertRaises(ValueError):
            self.module.validate_report_row(original, 'paper', forbidden=('R7',))

    def test_readonly_connection_cannot_write_and_missing_store_is_not_created(self):
        path = self.flow.data / 'test.sqlite'
        with closing(sqlite3.connect(path)) as db:
            db.execute('CREATE TABLE actual(value TEXT)')
            db.commit()
        with self.module.readonly_store(path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM actual').fetchone()[0], 0)
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("INSERT INTO actual VALUES('forbidden')")
        missing = self.flow.data / 'missing.sqlite'
        with self.assertRaises((OSError, ValueError, sqlite3.Error)):
            with self.module.readonly_store(missing):
                self.fail('Missing store opened')
        self.assertFalse(missing.exists())

    def test_pending_intake_hash_is_derived_without_faking_a_staged_receipt(self):
        raw = canonical_bytes({'status':'INTAKE_ACCEPTED'})
        pending = dict(operation_id='actual-intake', logical_path='receipts/synthetic/one',
            payload=raw, payload_hash=self.module.sha(raw), artifact_hash=None, state='PENDING', attempts=0)
        observed = self.module.validate_intake_row(pending)
        self.assertEqual(observed['state'], 'PENDING')
        staged = self.module.validate_intake_row({**pending, 'state':'LOCAL_STAGED',
            'artifact_hash':observed['artifact_hash'], 'attempts':1})
        self.assertEqual(self.module._immutable([observed]), self.module._immutable([staged]))
        for change in ({'state':'LOCAL_STAGED'}, {'artifact_hash':'sha256:'+'2'*64}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.module.validate_intake_row({**pending, **change})

    def test_formal_local_bridge_profile_pins_real_helper_bytes_and_transient_work(self):
        helper = self.output / 'helper.exe'
        write_private_new(helper, b'SYNTHETIC_EXECUTABLE_TEST_BYTES_NOT_RUN')
        write_private_new(self.flow.cloud / '.r7-root.json', canonical_bytes({'root_id':self.module.ROOT_ID}))
        self.flow._build_helper = Mock(return_value=helper)
        profile = self.flow._prepare_bridge()
        value = json.loads(profile.read_bytes())
        self.assertEqual(value['executable_sha256'], self.module.sha(helper.read_bytes()))
        config = json.loads(Path(value['rclone_config_ref']).read_bytes())
        self.assertEqual(config['data_class'], 'SYNTHETIC_FIXTURE_ONLY')
        self.assertEqual(Path(config['work_root']), self.flow.data / 'worker-logs/fixture-bridge')
        self.assertEqual(Path(value['rclone_config_ref']).parent, self.output)
        self.assertEqual(self.flow.remote, self.output / 'local-remote')

    def test_fresh_constructor_provisions_private_worker_log_ancestry_before_product_start(self):
        def base(flow, package, output, scenario, **options):
            flow.output = self.output
            flow.data = self.output / 'fresh-data'
            flow.observation = {}
        with patch.object(self.module.PublicFixture, '__init__', base):
            flow = self.module.NativePublicationFlow(self.output/'not-run-package',self.output)
        from application.platform.private_files import require_private
        require_private(flow.data,directory=True)
        require_private(flow.data/'worker-logs',directory=True)
        self.assertEqual(list((flow.data/'worker-logs').iterdir()), [])

    def test_native_base_pass_cannot_leak_when_later_publication_fails(self):
        def base(_):
            self.flow.observation['passed'] = True
            return self.flow.observation
        self.flow._publication = Mock(side_effect=ValueError('actual publication failure'))
        with patch.object(self.module.PublicFixture, 'run', base):
            with self.assertRaises(ValueError):
                self.flow.run()
        self.assertFalse(self.flow.observation['passed'])
        self.flow.persist.assert_called()

    def test_base_cleanup_failure_also_cannot_leak_pass(self):
        def base(_):
            self.flow.observation['passed'] = True
            raise ValueError('unreaped native process')
        self.flow._publication = Mock()
        with patch.object(self.module.PublicFixture, 'run', base):
            with self.assertRaises(ValueError):
                self.flow.run()
        self.assertFalse(self.flow.observation['passed'])
        self.flow._publication.assert_not_called()

    def test_missing_marker_failure_restores_original_when_native_command_raises(self):
        self.flow._require_helper=Mock()
        self.flow.remote = self.output / 'local-remote'
        create_private_directory(self.flow.remote)
        marker = self.flow.remote / '.r7-root.json'
        original = canonical_bytes({'root_id':self.module.ROOT_ID})
        write_private_new(marker, original)
        self.flow.command = Mock(side_effect=ValueError('native failure'))
        self.flow._publications = Mock(return_value=[])
        self.flow._run_facts = Mock(return_value={})
        with self.assertRaises(ValueError):
            self.flow._remote_cycle(self.output / 'bridge.json', [], {})
        self.assertEqual(marker.read_bytes(), original)
        self.assertFalse((self.flow.remote / 'retained-root-marker.json').exists())

    def test_remote_retry_orders_real_marker_fault_then_ack_then_empty_replay(self):
        self.flow._require_helper=Mock()
        self.flow.remote = self.output / 'local-remote'
        create_private_directory(self.flow.remote)
        marker = self.flow.remote / '.r7-root.json'
        original = canonical_bytes({'root_id':self.module.ROOT_ID})
        write_private_new(marker, original)
        rows = [dict(self.row(),kind='paper',state='LOCAL_STAGED',attempts=1)]
        current = [dict(rows[0])]
        facts = {'revision':2,'process_generation':1}
        calls = []
        def command(label, argv, **options):
            calls.append((label, argv, options))
            counters = dict(attempted=1,local_staged=0,cloud_acknowledged=0,unavailable=0,conflicts=0)
            if len(calls)==1:
                self.assertFalse(marker.exists())
                self.assertEqual(options, {'expected':2,'json_result':True})
                current[0].update(state='UNAVAILABLE',attempts=2)
                return dict(counters,status='INCOMPLETE',unavailable=1)
            self.assertEqual(marker.read_bytes(), original)
            if len(calls)==2:
                current[0].update(state='CLOUD_ACKNOWLEDGED',attempts=3)
                return dict(counters,status='COMPLETE',cloud_acknowledged=1)
            return dict(counters,status='COMPLETE',attempted=0)
        self.flow.command = command
        self.flow._publications = lambda:[dict(row) for row in current]
        self.flow._run_facts = lambda:dict(facts)
        self.flow._artifact_closures = Mock(return_value=[{'actual-hash':'source-contract-test'}])
        self.flow._remote_cycle(self.output / 'bridge.json',rows,facts)
        self.assertEqual(len(calls),3)
        self.assertTrue(all('cloud-publish-outbox' in call[1] for call in calls))
        self.assertEqual(self.flow.observation['remote_scope'],'LOCAL_FIXTURE_VERIFIED_COPY_ACK')
        self.assertEqual(self.flow.observation['real_cloud'],'NOT_RUN')

    def test_staging_is_bounded_and_never_accepts_remote_ack_or_false_empty(self):
        for result in (dict(status='LOCAL_STAGED',attempted=1,local_staged=1,cloud_acknowledged=1,unavailable=0,conflicts=0,remote_verification='NOT_RUN'),
                dict(status='LOCAL_STAGED',attempted=0,local_staged=0,cloud_acknowledged=0,unavailable=0,conflicts=0,remote_verification='NOT_RUN')):
            with self.subTest(result=result):
                self.flow.command = Mock(return_value=result)
                self.flow._publications = Mock(return_value=[dict(self.row(), kind='paper', state='PENDING')])
                with self.assertRaises(ValueError):
                    self.flow._stage_outboxes()

    def test_stage_closure_matches_actual_files_and_detects_changed_manifest(self):
        row = dict(self.row(), kind='paper')
        directory = self.flow.cloud / row['logical_path']
        current = self.flow.cloud
        for part in Path(row['logical_path']).parts:
            current /= part
            create_private_directory(current)
        payloads = {key:value.encode() for key,value in json.loads(row['payloads_json']).items()}
        for name, raw in payloads.items():
            write_private_new(directory / name, raw)
        manifest = dict(schema_version='r7-result-bundle-v0.2', operation_id=row['operation_id'],
            artifact_hash=row['artifact_hash'], payload_hashes={key:self.module.sha(value) for key,value in payloads.items()})
        write_private_new(directory / 'manifest.json', canonical_bytes(manifest))
        closure = self.flow._artifact_closures(self.flow.cloud, [row])
        self.assertEqual(closure[0]['artifact_hash'], row['artifact_hash'])
        (directory / 'manifest.json').write_bytes(b'{}')
        with self.assertRaises(ValueError):
            self.flow._artifact_closures(self.flow.cloud, [row])

    def test_helper_build_is_owned_fixed_bounded_and_never_uses_clean(self):
        self.flow.env = {}
        self.flow._build_python = Mock(return_value=Path(sys.executable))
        recorded = []
        def spawn(argv, **kwargs):
            recorded.append((argv, kwargs))
            destination = Path(argv[argv.index('--distpath')+1]) / 'R7FixtureCopy'
            destination.mkdir(parents=True)
            write_private_new(destination / ('R7FixtureCopy.exe' if self.module.os.name=='nt' else 'R7FixtureCopy'), b'compiled fixture test bytes')
            return SimpleNamespace(wait=lambda:0, termination_report=SimpleNamespace(reaped=True))
        with patch.object(self.module, 'spawn_owned', side_effect=spawn), patch.object(self.module, 'terminate_owned', return_value=SimpleNamespace(reaped=True)):
            helper = self.flow._build_helper()
        self.assertEqual(helper.read_bytes(), b'compiled fixture test bytes')
        argv, options = recorded[0]
        self.assertNotIn('--clean', argv)
        self.assertIn('--onedir', argv)
        self.assertLessEqual(options['limits'].timeout_seconds, 900)
        self.assertTrue(self.flow.commands[-1]['tree_reaped'])

    def test_helper_dependency_change_is_denied_even_with_unchanged_launcher(self):
        base=self.output/'helper';create_private_directory(base)
        internal=base/'_internal';create_private_directory(internal)
        self.flow.helper=base/'R7FixtureCopy.exe';write_private_new(self.flow.helper,b'unchanged launcher')
        dependency=internal/'python312.dll';write_private_new(dependency,b'original runtime')
        self.flow.helper_hash=self.module.sha(self.flow.helper.read_bytes())
        self.flow.helper_inventory=self.module.helper_inventory(base)
        self.flow._require_helper()
        dependency.write_bytes(b'replaced runtime')
        self.assertEqual(self.module.sha(self.flow.helper.read_bytes()),self.flow.helper_hash)
        with self.assertRaises(ValueError):self.flow._require_helper()


if __name__ == '__main__':
    unittest.main()
