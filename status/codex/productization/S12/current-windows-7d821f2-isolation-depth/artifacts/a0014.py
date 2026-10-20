"""Source-only retention regressions; actual public observations are read only."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import retain_isolation_depth_history as helper

REVISION='7d821f29837e95e46bcd5fe32f14d536a28c9aa8'
BASE=Path(__file__).resolve().parent
PROJECT=BASE.parents[1]

class HistoryRetentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        stage=BASE/'isolation-7d821f2-probe01'
        cls.row=json.loads((stage/'checkpoint.json').read_bytes())
        root=PROJECT/cls.row['artifact_root_ref']
        cls.child=json.loads((root/'probe-result.json').read_bytes())
        cls.observation=json.loads((root/'observations.json').read_bytes())
        cls.outer=(stage/'actual-isolation.log').read_bytes()
        cls.research=(root/'concurrent-research.log').read_bytes()

    def validate(self,observation=None,outer=None,research=None):
        return helper.require_bound_observation(self.child,
            self.observation if observation is None else observation,
            self.outer if outer is None else outer,
            self.research if research is None else research)

    def test_actual_wrapper_and_concurrent_command_are_bound_without_native_rerun(self):
        command=self.validate()
        self.assertEqual(command['exit_code'],2)
        self.assertTrue(command['tree_reaped'])
        self.assertEqual(command['log_hash'],helper.sha(self.research))

    def test_changed_measurement_summaries_are_rejected(self):
        replacements=dict(sample_count=999,actual_target_concurrent_protected_samples=999,
            actual_research_target_pids=[999],progress={},research_result={})
        for field,value in replacements.items():
            with self.subTest(field=field):
                changed=deepcopy(self.observation);changed[field]=value
                with self.assertRaises(ValueError):self.validate(observation=changed)

    def test_changed_actual_wrapper_or_concurrent_output_are_rejected(self):
        with self.assertRaises(ValueError):self.validate(outer=b'{}')
        with self.assertRaises(ValueError):self.validate(research=b'{}\n')

    def test_missing_duplicate_or_changed_recorded_command_are_rejected(self):
        for mode in ('missing','duplicate','exit','hash'):
            with self.subTest(mode=mode):
                changed=deepcopy(self.observation)
                rows=[r for r in changed['commands'] if r['command']=='concurrent-research']
                self.assertEqual(len(rows),1)
                if mode=='missing':changed['commands'].remove(rows[0])
                elif mode=='duplicate':changed['commands'].append(deepcopy(rows[0]))
                elif mode=='exit':rows[0]['exit_code']=0
                else:rows[0]['log_hash']='sha256:'+'0'*64
                with self.assertRaises(ValueError):self.validate(observation=changed)

    def test_gate_uses_protected_captured_documents_and_exact_subjects(self):
        q=dict(stage='qualify',revision=REVISION,attempt='first',passed=False,source_unchanged=True,source_worktree='CLEAN')
        m=dict(kind='ACTUAL_OWNING_EXECUTION_RESOURCE_OBSERVATION',revision=REVISION,attempt='first',tree_reaped=True,monitor_stopped=True,
            source_unchanged=True,wrapper_unchanged=True,owning_passed=False,exit_code=2)
        class Capture:
            def __init__(self):self.paths=[]
            def document(self,path):
                self.paths.append(path)
                return q if path.parent.name.startswith('qualify-') else m
        captured=Capture()
        with patch.object(Path,'read_bytes',side_effect=AssertionError('Unprotected gate read')):
            helper.require_ended_chain(captured,REVISION,'first')
        self.assertEqual(len(captured.paths),2)
        q['attempt']='retry01'
        with self.assertRaises(ValueError):helper.require_ended_chain(Capture(),REVISION,'first')

    def test_publication_is_exclusive_and_verifies_published_bytes(self):
        with TemporaryDirectory(dir=BASE) as temporary:
            target=Path(temporary)/'history'
            helper.publish_archive(target,[('artifacts/a0001.log',b'actual\n')],dict(passed=True))
            self.assertEqual((target/'artifacts/a0001.log').read_bytes(),b'actual\n')
            with self.assertRaises((ValueError,FileExistsError)):
                helper.publish_archive(target,[('artifacts/a0001.log',b'replaced\n')],dict(passed=True))
        original=helper.write_private_new
        def corrupt(path,raw):
            original(path,raw)
            if path.suffix=='.log':path.write_bytes(b'changed\n')
        with TemporaryDirectory(dir=BASE) as temporary,patch.object(helper,'write_private_new',side_effect=corrupt):
            with self.assertRaises(ValueError):
                helper.publish_archive(Path(temporary)/'history',[('artifacts/a0001.log',b'actual\n')],dict(passed=True))

if __name__=='__main__':unittest.main()
