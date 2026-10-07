import ast,copy,importlib,json,shutil,tempfile,unittest
from pathlib import Path
base=Path(__file__).resolve().parent
source=base/'r7-native-S13-installer-denial-fa3b786-bound-v3'

class InstallerAcceptanceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='installer-guard-',dir=base);self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.report=json.loads((source/'native-installer-denial.json').read_bytes());self.identity=copy.deepcopy(self.report['identity'])
        for row in self.report['commands']:shutil.copyfile(source/row['log'],self.folder/row['log'])
    def validate(self):
        module=importlib.import_module('s13_installer_acceptance_integrity');verified={}
        module.validate_installer_report(self.folder,self.report,self.identity,verified,base.parent);return verified
    def test_actual_five_native_denials_match_all_observed_command_logs(self):self.assertEqual(len(self.validate()),5)
    def test_missing_log_is_never_accepted(self):
        (self.folder/'install-dry.log').unlink()
        with self.assertRaises(ValueError):self.validate()
    def test_same_length_changed_log_is_never_accepted(self):
        path=self.folder/'install-dry.log';raw=path.read_bytes();path.write_bytes(b'!'+raw[1:])
        with self.assertRaises(ValueError):self.validate()
    def test_self_reported_identity_cannot_replace_current_subject(self):
        self.report['identity']['build_hash']='sha256:'+'e'*64
        with self.assertRaises(ValueError):self.validate()
    def test_command_inventory_cannot_omit_a_required_dry_run(self):
        self.report['commands'].pop(0)
        with self.assertRaises(ValueError):self.validate()
    def test_success_stdout_cannot_be_accepted_as_platform_denial_even_with_new_hash(self):
        path=self.folder/'install-dry.log';path.write_bytes(b'{"status":"FILES_INSTALLED"}\n')
        self.report['commands'][0]['log_sha256']='sha256:'+__import__('hashlib').sha256(path.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):self.validate()
    def test_native_windows_denial_cannot_be_promoted_to_ubuntu_pass(self):
        self.report['native_ubuntu']='PASS'
        with self.assertRaises(ValueError):self.validate()
    def test_collector_publish_precedes_all_acceptance_checkpoint_writes(self):
        tree=ast.parse((base/'s13_installer_accept.py').read_text(encoding='utf-8'))
        publish=[n.lineno for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='publish_retention_manifest']
        writes=[n.lineno for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='write_text'
            and isinstance(n.func.value,ast.Name) and n.func.value.id in ('path','handoff')]
        self.assertEqual(len(publish),1);self.assertTrue(writes);self.assertLess(publish[0],min(writes))
    def test_actual_report_loaders_keep_one_path_argument(self):
        tree=ast.parse((base/'s13_installer_accept.py').read_text(encoding='utf-8'))
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='load']
        self.assertGreater(len(calls),10);self.assertEqual([n.lineno for n in calls if len(n.args)!=1 or n.keywords],[])
    def test_empty_or_incomplete_execution_harness_map_is_refused(self):
        module=importlib.import_module('s13_installer_acceptance_integrity')
        for mapping in ({},{'s13_native_installer_denial_v2.py':'sha256:'+'a'*64}):
            with self.subTest(keys=list(mapping)),self.assertRaises(ValueError):module.validate_harness_commitments(base,mapping,{},base.parent)
    def test_actual_before_and_after_execution_commitments_are_complete(self):
        module=importlib.import_module('s13_installer_acceptance_integrity');verified={}
        proof=json.loads((base/'S13-service-installer-bound-v3-fa3b786-pipeline.json').read_bytes())
        self.assertEqual(proof['harness_binding'],'BEFORE_AND_AFTER_EXECUTION')
        module.validate_harness_commitments(base,proof['harness_hashes'],verified,base.parent)
        self.assertEqual(len(verified),3)
    def test_changed_execution_harness_is_rejected(self):
        module=importlib.import_module('s13_installer_acceptance_integrity')
        proof=json.loads((base/'S13-service-installer-bound-v3-fa3b786-pipeline.json').read_bytes())
        for name in proof['harness_hashes']:shutil.copyfile(base/name,self.folder/name)
        (self.folder/'s13_installer_package_binding.py').write_bytes(b'changed\n')
        with self.assertRaises(ValueError):module.validate_harness_commitments(self.folder,proof['harness_hashes'],{},base.parent)
    def test_bound_report_records_the_exact_parsed_bytes(self):
        module=importlib.import_module('s13_installer_acceptance_integrity');verified={}
        shutil.copyfile(source/'native-installer-denial.json',self.folder/'native-installer-denial.json')
        self.assertEqual(module.read_bound_report(self.folder,'native-installer-denial.json',verified,base.parent),self.report)
        expected='sha256:'+__import__('hashlib').sha256((self.folder/'native-installer-denial.json').read_bytes()).hexdigest()
        self.assertEqual(list(verified.values()),[expected])
    def test_parsed_report_and_commitment_share_one_read_and_refuse_replacement(self):
        module=importlib.import_module('s13_installer_acceptance_integrity')
        from unittest.mock import patch
        real_reader=module.read_local
        def replaced(folder,name,limit):
            raw=real_reader(folder,name,limit)
            (folder/name).write_bytes(b'{"passed":true,"changed":true}\n')
            return raw
        shutil.copyfile(source/'native-installer-denial.json',self.folder/'native-installer-denial.json')
        with patch.object(module,'read_local',side_effect=replaced),self.assertRaises(ValueError):
            module.read_bound_report(self.folder,'native-installer-denial.json',{},base.parent)
    def test_retention_refuses_duplicate_originals_before_copy_and_index(self):
        tree=ast.parse((base/'s13_installer_accept.py').read_text(encoding='utf-8'))
        retain=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='retain')
        guard=next(n for n in ast.walk(retain) if isinstance(n,ast.If) and 'retained_originals' in ast.unparse(n.test))
        writes=next(n.lineno for n in ast.walk(retain) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='write_bytes')
        self.assertLess(guard.lineno,writes);self.assertTrue(any(isinstance(n,ast.Return) for n in ast.walk(guard)))
    def test_actual_retention_reuses_identical_original_and_refuses_changed_repeat(self):
        tree=ast.parse((base/'s13_installer_accept.py').read_text(encoding='utf-8'))
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='retain')
        target=self.folder/'retained';target.mkdir()
        fixture=self.folder/'fixture.log';fixture.write_bytes(b'original\n')
        state=dict(target=target,index=[],retained_originals={},project=base.parent,root=base.parent,
            integrity={'verified_artifact_hashes':{}},hash_bytes=lambda raw:'sha256:'+__import__('hashlib').sha256(raw).hexdigest(),
            _sanitize=lambda text,root:text)
        exec(compile(ast.Module(body=[function],type_ignores=[]),'actual-retain-function','exec'),state)
        state['retain'](fixture,'first.log');state['retain'](fixture,'second.log')
        self.assertEqual(len(state['index']),1);self.assertFalse((target/'second.log').exists())
        fixture.write_bytes(b'replacement\n')
        with self.assertRaises(ValueError):state['retain'](fixture,'third.log')
        self.assertEqual((target/'first.log').read_bytes(),b'original\n')

if __name__=='__main__':unittest.main()
