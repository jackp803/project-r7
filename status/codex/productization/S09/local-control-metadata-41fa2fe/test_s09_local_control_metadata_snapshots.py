"""Exercise verified metadata snapshots using isolated public checkpoint copies."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import record_s09_local_control_qualified_checkpoint as recorder

class MetadataSnapshotTests(unittest.TestCase):
    def run_recorder(self, mutation=None, empty=False):
        original_root=recorder.REPO
        original=lambda name:recorder.read_local(original_root,name,64*1024**2)
        disposition=recorder.REF+'/disposition.json'
        build=recorder.REF+'/native-build/build-result.json'
        reads={};saved={}
        def read(name):
            if empty and name==recorder.MANIFEST:return b'{"files":{}}'
            raw=original(name);reads[name]=reads.get(name,0)+1
            if name==mutation and reads[name]>=2:
                value=json.loads(raw)
                if name==disposition:value['implementation_hash']='sha256:'+'a'*64
                else:value['archive_sha256']='b'*64
                return json.dumps(value).encode()
            return raw
        def save(path,value):saved[path.name]=copy.deepcopy(value)
        with tempfile.TemporaryDirectory(prefix='s09-metadata-public-',dir=recorder.BASE) as directory:
            root=Path(directory).resolve();assert root.is_relative_to(recorder.BASE.resolve())
            (root/'coordination/CODEX').mkdir(parents=True)
            (root/'status/codex/productization/S09').mkdir(parents=True)
            (root/'coordination/CODEX/PROGRESS.json').write_bytes((recorder.REPO/'coordination/CODEX/PROGRESS.json').read_bytes())
            (root/'coordination/CODEX/HANDOFF.md').write_text('isolated public test handoff',encoding='utf-8')
            with patch.object(recorder,'REPO',root),patch.object(recorder,'read',side_effect=read),patch.object(recorder,'save',side_effect=save):
                recorder.main()
        return saved,reads

    def test_metadata_uses_the_verified_disposition_bytes(self):
        name=recorder.REF+'/disposition.json';expected=json.loads(recorder.read(name))['implementation_hash']
        saved,reads=self.run_recorder(mutation=name)
        self.assertEqual(saved['PROGRESS.json']['paper_read_control_composition']['implementation_hash'],expected)
        self.assertEqual(reads[name],1)

    def test_metadata_uses_the_verified_build_bytes(self):
        name=recorder.REF+'/native-build/build-result.json';expected=json.loads(recorder.read(name))['archive_sha256']
        saved,reads=self.run_recorder(mutation=name)
        self.assertEqual(saved['PROGRESS.json']['platforms']['windows-11-x86_64']['native_archive_sha256'],expected)
        self.assertEqual(reads[name],1)

    def test_empty_manifest_is_rejected_before_progress_update(self):
        with self.assertRaisesRegex(AssertionError,'MISSING_MANDATORY_QUALIFICATION_ARTIFACTS'):
            self.run_recorder(empty=True)

if __name__=='__main__':unittest.main()
