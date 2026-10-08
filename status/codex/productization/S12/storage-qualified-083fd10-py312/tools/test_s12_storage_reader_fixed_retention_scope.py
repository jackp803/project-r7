"""Mock private reads; require rejection at the exact allowlist guard."""
import copy,json,unittest
from unittest.mock import patch
import retain_s12_storage_reader_fixed_qualification as retain

class ForbiddenPrivateRead(RuntimeError):pass

class RetentionScopeTests(unittest.TestCase):
    def test_context_cannot_select_untracked_private_source(self):
        context_path=retain.BASE/f'r7-productization-S12-storage-memory-retry-qualified-{retain.SHORT}'/'qualification-context.json'
        native_path=retain.BASE/f'S12-storage-reader-fixed-{retain.SHORT}-native-regression.json'
        context=json.loads(retain.read_local(context_path.parent,context_path.name,64*1024**2))
        native=json.loads(retain.read_local(native_path.parent,native_path.name,64*1024**2))
        context=copy.deepcopy(context);names=context['source_input_hashes']
        names.pop(next(iter(names)));names['.env']='sha256:'+'0'*64
        changed=json.dumps(context).encode()
        native['input_hashes_before'][context_path.relative_to(retain.PROJECT).as_posix()]=retain.sha(changed)
        native['input_hashes_after']=copy.deepcopy(native['input_hashes_before'])
        original=retain.read_local;kernel=retain._windows_read
        def read(root,name,limit):
            path=retain.Path(root)/name
            if path==context_path:return changed
            if path==native_path:return json.dumps(native).encode()
            return original(root,name,limit)
        def protected(path,limit):
            if path==retain.REPO/'.env':raise ForbiddenPrivateRead('Mocked private source would be read')
            return kernel(path,limit)
        with patch.object(retain,'read_local',side_effect=read),patch.object(retain,'_windows_read',side_effect=protected):
            with self.assertRaisesRegex(AssertionError,'UNEXPECTED_SOURCE_INPUT_SET'):retain.collect()

    def test_native_report_cannot_add_private_input(self):
        native_path=retain.BASE/f'S12-storage-reader-fixed-{retain.SHORT}-native-regression.json'
        native=json.loads(retain.read_local(native_path.parent,native_path.name,64*1024**2))
        sentinel='artifacts/private-sentinel.env'
        native['input_hashes_before'][sentinel]='sha256:'+'0'*64
        native['input_hashes_after']=copy.deepcopy(native['input_hashes_before'])
        original=retain.read_local
        def read(root,name,limit):
            path=retain.Path(root)/name
            if path==retain.PROJECT/sentinel:raise ForbiddenPrivateRead('Mocked private native input would be read')
            if path==native_path:return json.dumps(native).encode()
            return original(root,name,limit)
        with patch.object(retain,'read_local',side_effect=read):
            with self.assertRaisesRegex(AssertionError,'UNEXPECTED_NATIVE_INPUT_SET'):retain.collect()

if __name__=='__main__':unittest.main()
