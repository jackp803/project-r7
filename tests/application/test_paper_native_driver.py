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

    def test_owner_exit_before_login_prevents_sending_synthetic_password(self):
        m=self.module();fixture=object.__new__(m.NativeExpiryFlow)
        fixture.origin='http://127.0.0.1:8765';fixture.control=object()
        fixture.health=Mock(side_effect=ValueError('Actual owned process unavailable'))
        fixture.opener=Mock()
        with self.assertRaises(ValueError):fixture.request('POST','/api/v1/auth/login',dict(password='SOURCE_SYNTHETIC_ONLY'))
        fixture.opener.open.assert_not_called()

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
