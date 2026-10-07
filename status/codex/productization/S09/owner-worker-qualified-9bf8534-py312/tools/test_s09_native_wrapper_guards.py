"""Bounded external tool regressions; controlled fixtures, no native claims."""
import hashlib, importlib, json, os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

wrapper=importlib.import_module('s09_owner_worker_native_regression')
REVISION='9bf85349a81486297dbfb3e452f84f67421230d5'

class NativeWrapperGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(prefix='R7 wrapper guard ');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def qualification(self):
        report=dict(passed=True,commands=[{} for _ in range(33)],
            source_before=dict(revision=REVISION,worktree='CLEAN'),source_after=dict(revision=REVISION,worktree='CLEAN'))
        context=dict(inputs_unchanged=True)
        for name,value in [('qualification.json',report),('qualification-context.json',context)]:
            (self.root/name).write_text(json.dumps(value),encoding='utf-8')

    def test_validation_and_hashes_use_same_captured_report_bytes(self):
        self.assertTrue(hasattr(wrapper,'capture_qualification'),'Same-snapshot qualification capture required')
        self.qualification();old=(self.root/'qualification.json').read_bytes()
        from application.datasets.catalog import read_local
        def replace_after_read(root,name,limit):
            raw=read_local(root,name,limit)
            if name=='qualification.json':
                (self.root/name).write_text('{"passed":false}',encoding='utf-8')
            return raw
        with patch.object(wrapper,'read_local',side_effect=replace_after_read):
            report,context,captured=wrapper.capture_qualification(self.root,REVISION)
        self.assertTrue(report['passed'])
        self.assertEqual(captured[self.root/'qualification.json'],wrapper.sha(old))
        self.assertNotEqual(captured[self.root/'qualification.json'],wrapper.sha((self.root/'qualification.json').read_bytes()))

    def test_existing_proof_is_preserved_and_exclusive_creation_denied(self):
        self.assertTrue(hasattr(wrapper,'OwnedProof'),'Exclusive owned proof descriptor required')
        proof=self.root/'proof.json';proof.write_bytes(b'PRESERVE')
        with self.assertRaises((ValueError,OSError)):
            with wrapper.OwnedProof(proof): self.fail('Existing proof admitted')
        self.assertEqual(proof.read_bytes(),b'PRESERVE')

    def test_unlinked_proof_updates_same_inode_with_exact_bytes(self):
        self.assertTrue(hasattr(wrapper,'OwnedProof'),'Exclusive owned proof descriptor required')
        proof=self.root/'proof.json'
        with wrapper.OwnedProof(proof) as owner:
            identity=proof.stat()
            owner.persist(dict(passed=False,commands=[]))
            owner.persist(dict(passed=True,commands=[1]))
            self.assertTrue(os.path.samestat(identity,proof.stat()))
            self.assertEqual(json.loads(proof.read_bytes()),dict(passed=True,commands=[1]))

    def test_linked_proof_path_is_rejected_before_any_write(self):
        self.assertTrue(hasattr(wrapper,'OwnedProof'),'Exclusive owned proof descriptor required')
        # Controlled reparse rejection seam; no Windows symlink-privilege claim.
        proof=self.root/'dangling-proof.json'
        with patch.object(wrapper,'_local_path',side_effect=ValueError('Linked proof forbidden')):
            with self.assertRaises(ValueError):
                with wrapper.OwnedProof(proof): self.fail('Linked proof admitted')
        self.assertFalse(proof.exists())

if __name__=='__main__':unittest.main()
