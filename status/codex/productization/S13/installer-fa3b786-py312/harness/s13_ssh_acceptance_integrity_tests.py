import ast,copy,json,shutil,tempfile,unittest
from pathlib import Path
from s13_ssh_acceptance_integrity import validate_ssh_report
base=Path(__file__).resolve().parent
source=base/'r7-native-S13-ssh-access-9245c3c'

class SSHAcceptanceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='S13-ssh-acceptance-guard-',dir=base);self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.report=json.loads((source/'native-ssh-access.json').read_bytes())
        self.identity=copy.deepcopy(self.report['identity'])
        for row in self.report['commands']:shutil.copyfile(source/row['log'],self.folder/row['log'])

    def validate(self):
        verified={};validate_ssh_report(self.folder,self.report,self.identity,verified,base.parent)
        return verified

    def test_actual_native_public_access_report_matches_all_ten_observed_logs(self):
        self.assertEqual(len(self.validate()),10)

    def test_missing_required_actual_native_log_refuses_acceptance(self):
        (self.folder/'public-probe.log').unlink()
        with self.assertRaises(ValueError):self.validate()

    def test_same_length_changed_native_log_refuses_acceptance(self):
        file=self.folder/'public-probe.log';raw=file.read_bytes();file.write_bytes(b'!'+raw[1:])
        with self.assertRaises(ValueError):self.validate()

    def test_changed_self_reported_native_identity_does_not_replace_actual_subject(self):
        self.report['identity']['executable_revision']='e'*40
        with self.assertRaises(ValueError):self.validate()

    def test_counter_cannot_inflate_omitted_native_command(self):
        self.report['commands'].pop()
        with self.assertRaises(ValueError):self.validate()

    def test_generation_must_match_before_and_after_actual_probe_sequence(self):
        self.report['control_generation_after']['pid']+=1
        with self.assertRaises(ValueError):self.validate()

    def test_changed_public_result_cannot_override_actual_native_stdout(self):
        row=next(r for r in self.report['commands'] if r['name']=='public-probe')
        row['result']['public_auth_status']['configured']=True
        with self.assertRaises(ValueError):self.validate()

    def test_ssh_collector_publishes_complete_manifest_before_checkpoint_writes(self):
        tree=ast.parse((base/'s13_ssh_accept.py').read_text(encoding='utf-8'))
        publish=[n.lineno for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='publish_retention_manifest']
        writes=[n.lineno for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='write_text'
            and isinstance(n.func.value,ast.Name) and n.func.value.id in ('path','handoff')]
        self.assertEqual(len(publish),1);self.assertTrue(writes);self.assertLess(publish[0],min(writes))

    def test_every_actual_collector_report_loader_call_has_one_path_argument(self):
        tree=ast.parse((base/'s13_ssh_accept.py').read_text(encoding='utf-8'))
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='load']
        self.assertGreater(len(calls),10)
        self.assertEqual([(n.lineno,len(n.args)) for n in calls if len(n.args)!=1 or n.keywords],[])

if __name__=='__main__':unittest.main()
