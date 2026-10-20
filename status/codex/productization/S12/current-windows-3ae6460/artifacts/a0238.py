"""Reference substitution regressions; no operational DB/native execution."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,sys,unittest
from unittest.mock import patch

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(BASE),str(ROOT/'src'),str(ROOT)]
import verify_b03_m04_f11_supplement as helper

def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()

class ReferenceGuardTests(unittest.TestCase):
    def arguments(self):
        return SimpleNamespace(output=BASE/'b03-reference-guard-never-created',
            paper_proof=helper.PROJECT/'public-test-proof/native-observations.json',
            pins=BASE/'alternate-untrusted-pins.json')

    def test_alternate_pins_refused_before_any_referenced_file_read(self):
        with patch.object(Path,'open',side_effect=AssertionError('Untrusted read')):
            with self.assertRaisesRegex(ValueError,'Exact reviewed pins path'):
                helper.run(self.arguments())
        self.assertFalse(self.arguments().output.exists())

    def test_changed_fixed_pins_refused_before_json_refs_or_source_reads(self):
        args=self.arguments();args.pins=BASE/'b03-m04-f11-supplement-source-pins.unapplied.json'
        hostile=b'{"source_files":[{"path":"../private-file"}]}'
        with patch('application.paper.qualification.artifact_bytes',return_value=hostile) as read:
            with self.assertRaisesRegex(ValueError,'Exact reviewed pins bytes'):
                helper.run(args)
        self.assertEqual(1,read.call_count)
        self.assertEqual((BASE,args.pins.name),read.call_args.args)
        self.assertFalse(args.output.exists())

    def test_native_proof_hash_applies_to_exact_same_single_captured_bytes(self):
        first=b'{"run":"original"}';substitute=b'{"run":"substituted"}'
        path=BASE/'public-test-proof/native-observations.json'
        with patch('application.paper.qualification.artifact_bytes',side_effect=(first,substitute)) as read:
            captured,document=helper.capture_native_proof(path,sha(first))
        self.assertEqual(first,captured);self.assertEqual({'run':'original'},document)
        self.assertEqual(1,read.call_count)
        with patch('application.paper.qualification.artifact_bytes',return_value=substitute):
            with self.assertRaisesRegex(ValueError,'Same captured public proof commitment'):
                helper.capture_native_proof(path,sha(first))

    def test_nonpublic_proof_filename_refused_before_read(self):
        with patch('application.paper.qualification.artifact_bytes',side_effect=AssertionError('Unexpected read')):
            with self.assertRaisesRegex(ValueError,'Only original public native proof'):
                helper.capture_native_proof(BASE/'private-file','sha256:'+'0'*64)

if __name__=='__main__':unittest.main(verbosity=2)
