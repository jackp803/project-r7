"""Source-only driver boundary checks; mocked flows earn no native credit."""
import importlib
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from unittest.mock import Mock


class PaperNativeDriverTests(unittest.TestCase):
    def module(self):
        root=Path(__file__).resolve().parents[2]
        with patch.object(sys,'path',[str(root/'tools'),*sys.path]):
            return importlib.import_module('tools.verify_paper_product')

    def verify(self,module,package,output,group='PQR-03'):
        progress=io.StringIO()
        with redirect_stdout(progress):
            code=module.verify(package,output,group)
        self.assertEqual(json.loads(progress.getvalue())['passed'],code==0)
        return code

    def test_every_scenario_and_final_distribution_match_original_group_subject(self):
        m=self.module();a=dict(build_hash='a');b=dict(build_hash='b')
        for identities in ([a,b,a,a,a],[a,a,a,a,b]):
            with self.subTest(identities=identities),TemporaryDirectory() as temp:
                root=Path(temp);output=root/'result'
                with patch.object(m,'verify_distribution',side_effect=identities), \
                     patch.object(m.PublicFixture,'run',lambda self:dict(passed=True,identity=self.identity)):
                    (root/'package').mkdir()
                    (root/'package/distribution.json').write_text('{"entrypoint":"R7.exe"}')
                    self.assertEqual(self.verify(m,root/'package',output),2)
                report=json.loads((output/'native-observations.json').read_bytes())
                self.assertFalse(report['passed'])
                self.assertEqual(report['reason'],'ACTUAL_NATIVE_GROUP_FAILED')

    def test_artifact_alias_is_rejected_before_reading_external_sentinel(self):
        m=self.module()
        with TemporaryDirectory() as temp:
            root=Path(temp);output=root/'result';sentinel=root/'external.log'
            sentinel.write_bytes(b'OWNED_EXTERNAL_SENTINEL')
            def observation(fixture):
                if fixture.scenario=='positive':os.link(sentinel,fixture.output/'aliased.log')
                return dict(passed=True,identity=fixture.identity)
            package=root/'package';package.mkdir();(package/'distribution.json').write_text('{"entrypoint":"R7.exe"}')
            with patch.object(m,'verify_distribution',return_value=dict(build_hash='a')), \
                 patch.object(m.PublicFixture,'run',observation):
                self.assertEqual(self.verify(m,package,output),2)
            self.assertFalse(json.loads((output/'native-observations.json').read_bytes())['passed'])
            self.assertEqual(sentinel.read_bytes(),b'OWNED_EXTERNAL_SENTINEL')

    def test_expiry_group_executes_every_fixed_case_and_retains_original_subject(self):
        m=self.module();seen=[];identity=dict(build_hash='a')
        def observed(fixture):
            seen.append(fixture.native_case)
            self.assertEqual(fixture.identity,identity)
            return dict(passed=True,identity=fixture.identity,case=fixture.native_case)
        with TemporaryDirectory() as temp:
            root=Path(temp);package=root/'package';package.mkdir()
            (package/'distribution.json').write_text('{"entrypoint":"R7.exe"}')
            with patch.object(m,'verify_distribution',return_value=identity), \
                 patch.object(m.NativeExpiryFlow,'run',observed):
                self.assertEqual(self.verify(m,package,root/'result','PQR-04'),0)
            self.assertEqual(seen,['intake-faults','discovery-expired','enqueue-expired',
                'research-checkpoint-expired','pre-entry-expired','protected-expired','checkpoint-cancel'])

    def test_expiry_group_partial_failure_cannot_issue_group_success(self):
        m=self.module()
        def observed(fixture):
            return dict(passed=fixture.native_case!='protected-expired',identity=fixture.identity)
        with TemporaryDirectory() as temp:
            root=Path(temp);package=root/'package';package.mkdir()
            (package/'distribution.json').write_text('{"entrypoint":"R7.exe"}')
            with patch.object(m,'verify_distribution',return_value=dict(build_hash='a')), \
                 patch.object(m.NativeExpiryFlow,'run',observed):
                self.assertEqual(self.verify(m,package,root/'result','PQR-04'),2)
            result=json.loads((root/'result/pqr-result.json').read_bytes())
            self.assertTrue(all(row['status']=='NOT_RUN' for row in result['assertions']))

    def test_api_observation_requires_same_actual_owned_control_before_and_after(self):
        m=self.module();fixture=object.__new__(m.NativeExpiryFlow)
        fixture.origin='http://127.0.0.1:8765';fixture.csrf=None;fixture.requests=[]
        fixture.control=object();fixture.api_control_identity=dict(pid=123,generation=1,process_generation_id='one',config_hash='a')
        fixture.persist=Mock();fixture.health=Mock(side_effect=[fixture.api_control_identity,
            {**fixture.api_control_identity,'generation':2}])
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        response.read.return_value=b'{}';response.code=200;response.geturl.return_value=fixture.origin+'/api/v1/health'
        fixture.opener=Mock();fixture.opener.open.return_value=response
        with self.assertRaisesRegex(ValueError,'control identity changed'):
            fixture.request('GET','/api/v1/health')
        self.assertEqual(fixture.health.call_count,2)
        self.assertEqual(fixture.requests,[],'Changed control cannot contribute API evidence')

    def test_actual_paper_read_port_forward_shape_is_used(self):
        m=self.module()
        self.assertEqual(m.NativeExpiryFlow.forward_elapsed(dict(forward_observations=dict(real_elapsed_ns=0))),0)
        with self.assertRaises(ValueError):m.NativeExpiryFlow.forward_elapsed(dict(forward=dict(real_elapsed_ns=0)))

    def test_scoped_fixture_fault_success_cannot_issue_complete_pqr05_pass(self):
        m=self.module()
        root=Path(__file__).resolve().parents[2]
        with patch.object(sys,'path',[str(root/'tools'),*sys.path]):
            faults=importlib.import_module('verify_paper_faults')
        scoped=[dict(case=case,passed=True) for case in faults.NativeFixtureFaultFlow.PAPER_CASES]
        with TemporaryDirectory() as temp:
            directory=Path(temp);package=directory/'package';package.mkdir()
            identity=dict(build_hash='source-boundary-only')
            with patch.object(m,'verify_distribution',return_value=identity),patch.object(faults,'verify_slice',return_value=scoped):
                self.assertEqual(self.verify(m,package,directory/'result','PQR-05'),2)
            report=json.loads((directory/'result/native-observations.json').read_bytes())
            self.assertEqual(report['scoped_fixture_cases_passed'],6)
            self.assertFalse(report['passed']);self.assertIn('STANDING_PROTECTION_MISSING_STALE_LOST',report['remaining_native_observations'])
            result=json.loads((directory/'result/pqr-result.json').read_bytes())
            self.assertTrue(all(row['status']=='NOT_RUN' for row in result['assertions']))

    def test_native_fault_exception_retains_type_without_private_exception_text(self):
        self.module()
        root=Path(__file__).resolve().parents[2]
        with patch.object(sys,'path',[str(root/'tools'),*sys.path]):
            faults=importlib.import_module('verify_paper_faults')
        class FailingFlow:
            PAPER_CASES=('hold-for-recovery',)
            def __init__(self,package,output,case,**kwargs):
                self.output=output;output.mkdir();self.observation=dict(case=case,passed=False)
            def run(self):raise OSError('PRIVATE_EXCEPTION_CANARY: '+str(self.output/'product.json'))
            def persist(self):(self.output/'observations.json').write_text(json.dumps(self.observation))
        with TemporaryDirectory() as temp,patch.object(faults,'NativeFixtureFaultFlow',FailingFlow):
            root=Path(temp);rows=faults.verify_slice(root/'package',root,dict(build_hash='source-only'))
            raw=(root/'hold-for-recovery/observations.json').read_text()
            self.assertEqual(rows[0]['error_type'],'OSError')
            self.assertNotIn('PRIVATE_EXCEPTION_CANARY',raw);self.assertNotIn(str(root),raw)

    def test_native_fault_unconfirmed_cleanup_retains_handle_and_closed_capture(self):
        self.module();root=Path(__file__).resolve().parents[2]
        with patch.object(sys,'path',[str(root/'tools'),*sys.path]):faults=importlib.import_module('verify_paper_faults')
        from types import SimpleNamespace
        for failure in (None,TimeoutError('SOURCE_ONLY_CLEANUP_FAILURE')):
            with self.subTest(failure=type(failure).__name__),TemporaryDirectory() as temp:
                fixture=object.__new__(faults.NativeFixtureFaultFlow)
                fixture.output=Path(temp);fixture.config=fixture.output/'unused-config.json'
                fixture.runtime_log=fixture.output/'worker.log';fixture.runtime_stream=fixture.runtime_log.open('xb')
                capture=fixture.runtime_stream
                fixture.runtime_child=Mock();original=fixture.runtime_child
                original.process.returncode=1;fixture.commands=[];fixture.password='SOURCE_SYNTHETIC';fixture.persist=Mock()
                with patch.object(faults,'terminate_owned',return_value=SimpleNamespace(reaped=False),side_effect=failure), \
                        patch.object(faults,'load_config',return_value=object()), \
                        patch.object(faults,'process_health',return_value=dict(state='RUNNING',status='PROCESS_NOT_RUNNING')):
                    try:
                        with self.assertRaises(Exception):fixture.finish_runtime(crash=True)
                    finally:
                        capture_was_closed=capture.closed;capture.close()
                self.assertIs(fixture.runtime_child,original,'Unconfirmed cleanup must retain exact owned handle for retry')
                self.assertTrue(capture_was_closed);self.assertIsNone(fixture.runtime_stream);self.assertFalse(fixture.commands[-1]['tree_reaped'])

    def test_native_fault_unreaped_scope_aborts_later_cases(self):
        self.module();root=Path(__file__).resolve().parents[2]
        with patch.object(sys,'path',[str(root/'tools'),*sys.path]):faults=importlib.import_module('verify_paper_faults')
        class UnreapedFlow:
            PAPER_CASES=('hold-for-recovery','partial-fill-hold')
            def __init__(self,package,output,case,**kwargs):
                self.observation=dict(case=case,passed=False);self.runtime_child=object()
            def run(self):raise RuntimeError('SOURCE_ONLY_UNREAPED_SCOPE')
            def persist(self):pass
        with TemporaryDirectory() as temp,patch.object(faults,'NativeFixtureFaultFlow',UnreapedFlow):
            rows=faults.verify_slice(Path(temp)/'package',Path(temp),dict(build_hash='source-only'))
            self.assertEqual(len(rows),1,'A surviving owned process must stop the native slice')

    def test_scope_denial_uses_actual_cli_banner_and_one_bounded_diagnostic(self):
        self.module();root=Path(__file__).resolve().parents[2]
        with patch.object(sys,'path',[str(root/'tools'),*sys.path]):faults=importlib.import_module('verify_paper_faults')
        from application import cli
        from application.platform.scope_lock import ScopeBusy
        from contextlib import redirect_stderr
        captured=io.StringIO()
        with redirect_stderr(captured),patch.object(cli,'main',side_effect=ScopeBusy('SOURCE_ONLY_SCOPE_BUSY')):
            self.assertEqual(cli.run(),2)
        raw=captured.getvalue().encode();parser=getattr(faults,'require_scope_denial',None)
        self.assertIsNotNone(parser,'Actual two-line native scope denial parser required')
        parser(raw)
        for changed in (raw+b'{}\n',b'{}\n',raw.replace(b'OWNER_SCOPE_BUSY',b'VALIDATION'),raw*300):
            with self.subTest(changed=changed[:24]),self.assertRaises(ValueError):parser(changed)

    def test_successor_observation_waits_for_new_generation_and_consumed_pause(self):
        self.module();root=Path(__file__).resolve().parents[2]
        with patch.object(sys,'path',[str(root/'tools'),*sys.path]):faults=importlib.import_module('verify_paper_faults')
        from types import SimpleNamespace
        def recovered(generation,paused):
            return SimpleNamespace(process_generation=generation,state=dict(runtime=dict(
                position=dict(lifecycle_state='OPEN_PROTECTED'),paper_entries_allowed=not paused)))
        old=recovered(1,False);attached=recovered(2,False);new=recovered(2,True)
        flow=object.__new__(faults.NativeFixtureFaultFlow);flow.paper_run='source-only-run'
        flow.runtime_child=Mock();flow.runtime_child.process.poll.return_value=None
        flow.journal=Mock(side_effect=[old,attached,new])
        self.assertIs(flow.wait_position('OPEN_PROTECTED',generation=2,entries_paused=True),new)
        self.assertEqual(flow.journal.call_count,3)

    def test_owner_exit_before_login_prevents_sending_synthetic_password(self):
        m=self.module();fixture=object.__new__(m.NativeExpiryFlow)
        fixture.origin='http://127.0.0.1:8765';fixture.control=object()
        fixture.health=Mock(side_effect=ValueError('Actual owned process unavailable'))
        fixture.opener=Mock()
        with self.assertRaises(ValueError):fixture.request('POST','/api/v1/auth/login',dict(password='SOURCE_SYNTHETIC_ONLY'))
        fixture.opener.open.assert_not_called()

    def test_unsupported_fault_changes_actual_package_version_without_adding_fields(self):
        m=self.module()
        from application.cloud.manifest import parse_manifest,canonical_bytes
        from application.cloud.protocol import CloudError
        original=dict(package_schema_version='r7-strategy-package-v0.2',submission_id='source-driver-test')
        changed=m.NativeExpiryFlow.unsupported_manifest(canonical_bytes(original))
        self.assertEqual(set(json.loads(changed)),set(original))
        self.assertEqual(original['package_schema_version'],'r7-strategy-package-v0.2')
        with self.assertRaises(CloudError) as denied:parse_manifest(changed)
        self.assertEqual(denied.exception.reason,'UNSUPPORTED_PACKAGE_VERSION')

    def test_expected_native_expiry_requires_exact_negative_worker_result(self):
        m=self.module();fixture=object.__new__(m.NativeExpiryFlow)
        fixture.config=Path('SOURCE_ONLY.json')
        exact=dict(status='JOB_TERMINATED',job_state='EXPIRED',exit_code=2,tree_reaped=True,
            parent_pid=1,child_pid=2,reason_codes=['SUBMISSION_EXPIRED'])
        fixture.command=Mock(return_value=exact)
        self.assertEqual(fixture.research(expected_state='EXPIRED'),exact)
        self.assertEqual(fixture.command.call_args.kwargs['expected'],2)
        self.assertTrue(fixture.command.call_args.kwargs['json_result'])
        for bad in ({**exact,'job_state':'FAILED'},{**exact,'reason_codes':['OWNED_WORKER_TIMEOUT']},
                    {**exact,'tree_reaped':False},{**exact,'child_pid':1}):
            with self.subTest(bad=bad):
                fixture.command=Mock(return_value=bad)
                with self.assertRaises(ValueError):fixture.research(expected_state='EXPIRED')

    def test_failed_expiry_case_still_binds_sanitized_log_and_partial_observation(self):
        m=self.module()
        def failed(fixture):
            (fixture.output/'failed.log').write_bytes(b'SOURCE_DRIVER_BOUNDARY_ONLY')
            fixture.persist()
            raise TimeoutError('source-only simulated timeout')
        with TemporaryDirectory() as temp:
            root=Path(temp);package=root/'package';package.mkdir()
            (package/'distribution.json').write_text('{"entrypoint":"R7.exe"}')
            with patch.object(m,'verify_distribution',return_value=dict(build_hash='a')), \
                 patch.object(m.NativeExpiryFlow,'run',failed):
                self.assertEqual(self.verify(m,package,root/'result','PQR-04'),2)
            result=json.loads((root/'result/pqr-result.json').read_bytes())
            refs={row['ref'] for row in result['artifacts']}
            self.assertTrue({'intake-faults/failed.log','intake-faults/observations.json'}.issubset(refs))
            report=json.loads((root/'result/native-observations.json').read_bytes())
            self.assertFalse(report['observations'][0]['passed'])

    def test_cancel_exception_retains_child_cleanup_facts_and_log(self):
        m=self.module()
        for reaped in (True,False):
            with self.subTest(reaped=reaped),TemporaryDirectory() as temp:
                root=Path(temp);package=root/'package';package.mkdir()
                (package/'distribution.json').write_text('{"entrypoint":"R7.exe"}')
                with patch.object(m,'verify_distribution',return_value=dict(build_hash='a')):
                    fixture=m.NativeExpiryFlow(package,root/'result','checkpoint-cancel')
                fixture.guard=Mock();(fixture.data/'fixture-observations').mkdir(parents=True)
                (fixture.data/'fixture-observations/source-start.json').write_bytes(b'{}')
                fixture.view=Mock(return_value=dict(revision=0));fixture.request=Mock(side_effect=TimeoutError('source only'))
                owned=Mock();owned.process.poll.return_value=None
                cleanup=Mock(reaped=reaped)
                with patch.object(m,'spawn_owned',return_value=owned),patch.object(m,'terminate_owned',return_value=cleanup):
                    with self.assertRaises(TimeoutError):fixture.cancel_checkpoint('source-job')
                self.assertTrue((fixture.output/'research-worker.log').is_file())
                self.assertFalse((fixture.output/'research-worker.raw').exists())
                self.assertEqual(fixture.commands[-1]['tree_reaped'],reaped)
                self.assertEqual(fixture.commands[-1]['error_type'],'TimeoutError')


if __name__=='__main__':unittest.main()
