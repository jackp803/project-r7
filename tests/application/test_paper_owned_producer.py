"""A zero exit or caller JSON cannot replace observed frozen case execution."""
import importlib
import importlib.util
import unittest


class PaperOwnedProducerTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.producer'))
        return importlib.import_module('application.paper.producer')

    def test_unit_log_binds_exact_executed_case_order_and_success(self):
        m=self.module();cases=['test_owned.Actual.test_first','test_owned.Actual.test_second']
        text='test_first (test_owned.Actual.test_first) ... ok\ntest_second (test_owned.Actual.test_second) ... ok\n\nRan 2 tests in 0.001s\n\nOK\n'
        self.assertEqual(m.executed_cases(text),cases)
        documented=text.replace('test_first (test_owned.Actual.test_first) ... ok',
            'test_first (test_owned.Actual.test_first)\nActual description with (parentheses) ... ok')
        self.assertEqual(m.executed_cases(documented),cases)
        for changed in (text.replace(' ... ok',' ... skipped'),text+'test_first (test_owned.Actual.test_first) ... ok\n',
                        'Ran 2 tests in 0.001s\nOK\n'):
            with self.subTest(changed=changed),self.assertRaises(ValueError):m.require_executed_cases(changed,cases)

    def test_native_manifest_requires_all_actual_bound_assertions_no_supplied_pass(self):
        m=self.module()
        from pathlib import Path
        import tempfile,json,hashlib
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw=b'actual retained output';(root/'actual.log').write_bytes(raw)
            h='sha256:'+hashlib.sha256(raw).hexdigest()
            report=dict(assertions=[dict(assertion_id='measured',status='PASS',evidence_ref='actual.log',evidence_hash=h)],
                        artifacts=[dict(ref='actual.log',hash=h)])
            member=dict(assertions=['measured'])
            self.assertEqual(m.native_assertions(report,member,root),report['assertions'])
            for changed in ({'passed':True},{'assertions':[]}, {'assertions':[{**report['assertions'][0],'evidence_hash':'sha256:'+'0'*64}]}):
                with self.subTest(changed=changed),self.assertRaises(ValueError):m.native_assertions(changed,member,root)

    def test_all_retained_native_logs_and_screenshots_are_bound_not_only_summary(self):
        from pathlib import Path
        import tempfile,hashlib
        m=self.module()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'summary.json').write_bytes(b'actual summary');(root/'screen.png').write_bytes(b'actual screenshot')
            artifacts=[dict(ref=p.name,hash='sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(root.iterdir())]
            commitment=next(a['hash'] for a in artifacts if a['ref']=='summary.json')
            report=dict(assertions=[dict(assertion_id='measured',status='PASS',evidence_ref='summary.json',evidence_hash=commitment)],artifacts=artifacts)
            self.assertEqual(m.native_assertions(report,dict(assertions=['measured']),root),report['assertions'])
            (root/'screen.png').write_bytes(b'mutated screenshot')
            with self.assertRaises(ValueError):m.native_assertions(report,dict(assertions=['measured']),root)
            report['artifacts']=[]
            with self.assertRaises(ValueError):m.native_assertions(report,dict(assertions=['measured']),root)


if __name__=='__main__':unittest.main()
