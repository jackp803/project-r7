"""Source orchestration checks; mocked passes confer no native credit."""
from contextlib import redirect_stdout
import importlib,io,json,sys,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from unittest.mock import Mock


class NativeGroupCompletionTests(unittest.TestCase):
    def modules(self):
        root=Path(__file__).resolve().parents[2]
        with patch.object(sys,'path',[str(root/'tools'),*sys.path]):
            return tuple(importlib.import_module(name) for name in
                ('verify_paper_product','verify_paper_security','verify_paper_boundaries','verify_paper_publication'))

    def attempt(self,group,security=True,boundary=True,publication=True):
        product,guards,boundaries,reports=self.modules()
        with TemporaryDirectory() as directory:
            root=Path(directory);package=root/'package';package.mkdir()
            with (patch.object(product,'verify_distribution',return_value=dict(build_hash='SOURCE_ONLY')),
                    patch.object(guards,'verify_slice',return_value=[dict(scoped_native_security_passed=security,passed=False)]),
                    patch.object(boundaries,'verify_slice',return_value=[dict(scoped_native_boundaries_passed=boundary,passed=False)]),
                    patch.object(reports,'verify_slice',return_value=[dict(passed=publication)]),redirect_stdout(io.StringIO())):
                result=product.verify(package,root/'result',group)
            return result,json.loads((root/'result/native-observations.json').read_bytes())

    def test_pqr06_requires_both_actual_security_and_boundary_slices(self):
        for security,boundary in ((False,True),(True,False),(True,True)):
            with self.subTest(security=security,boundary=boundary):
                code,report=self.attempt('PQR-06',security,boundary)
                self.assertEqual(code,0 if security and boundary else 2)
                self.assertEqual(report['passed'],security and boundary)

    def test_pqr07_requires_actual_complete_publication_flow(self):
        for passed in (False,True):
            with self.subTest(passed=passed):
                code,report=self.attempt('PQR-07',publication=passed)
                self.assertEqual(code,0 if passed else 2)
                self.assertEqual(report['passed'],passed)

    def test_boundary_driver_rejects_missing_assertion_or_fabricated_qualification(self):
        _,_,module,_=self.modules()
        identity=dict(build_hash='SOURCE_ONLY')
        valid=dict(schema_version='r7-native-boundary-diagnostic-v1',status='COMPONENT_CHECKS_PASS',
            assertions=list(module.REQUIRED_ASSERTIONS),actual_assertions=len(module.REQUIRED_ASSERTIONS),
            qualification_complete=False,completed_pqr_groups=0,software_eligibility='NOT_QUALIFIED',
            diagnostic_all_recorded_checks_passed=True,synthetic_models='IN_MEMORY_ONLY_NEVER_STORED',
            synthetic_represented_members_not_executed=7,financial_selection='NONE',paper='NOT_STARTED',
            provider_requests=0,provider_mutation=0,credentials='NONE',capital='NONE',subject=identity)
        for change in ({},{'assertions':valid['assertions'][:-1]}, {'qualification_complete':True},
                {'completed_pqr_groups':7},{'software_eligibility':'QUALIFIED'},{'subject':{'build_hash':'CHANGED'}}):
            with self.subTest(change=change):
                flow=object.__new__(module.NativeBoundaryFlow)
                flow.config=Path('SOURCE_ONLY.json');flow.data=Path('SOURCE_ONLY_DATA');flow.identity=identity
                flow.observation={};flow.command=Mock(side_effect=[{},dict(valid,**change)])
                flow.guard=Mock();flow.persist=Mock()
                if change:
                    with self.assertRaises(ValueError):flow.run()
                    self.assertNotIn('scoped_native_boundaries_passed',flow.observation)
                else:self.assertTrue(flow.run()['scoped_native_boundaries_passed'])

    def test_pqr05_requires_every_fixed_fault_and_actual_isolation_and_capacity(self):
        product,*_=self.modules()
        with patch.object(sys,'path',[str(Path(__file__).resolve().parents[2]/'tools'),*sys.path]):
            faults=importlib.import_module('verify_paper_faults');isolation=importlib.import_module('verify_paper_isolation')
        complete=[dict(case=case,passed=True,stale_generation_operation_denied=True) for case in faults.NativeFixtureFaultFlow.PAPER_CASES]
        for rows,isolated,measured in ((complete[:-1],True,True),(complete,False,True),
                (complete,True,False),(complete,True,True)):
            with self.subTest(cases=len(rows),isolated=isolated,measured=measured),TemporaryDirectory() as directory:
                root=Path(directory);package=root/'package';package.mkdir()
                observed=[dict(passed=True,research_fault_protection_isolation=isolated,host_bounded_capacity_measured=measured)]
                with (patch.object(product,'verify_distribution',return_value=dict(build_hash='SOURCE_ONLY')),
                        patch.object(product,'current_target',return_value='windows-11-x86_64'),
                        patch.object(faults,'verify_slice',return_value=rows),
                        patch.object(isolation,'verify_slice',return_value=observed) as probe,redirect_stdout(io.StringIO())):
                    code=product.verify(package,root/'result','PQR-05')
                self.assertEqual(code,0 if len(rows)==len(complete) and isolated and measured else 2)
                if len(rows)!=len(complete):probe.assert_not_called()


if __name__=='__main__':unittest.main()
