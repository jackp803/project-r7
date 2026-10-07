from pathlib import Path
import ast,hashlib,json,sys,tempfile,unittest
from unittest.mock import patch
base=Path(__file__).resolve().parent
sys.path.insert(0,str(base))
from s13_acceptance_integrity import require_artifact,require_sequence,require_native_lists,require_browser_subject

class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='S13-acceptance-guard-',dir=base)
        self.root=Path(self.temp.name);self.addCleanup(self.temp.cleanup)
        self.file=self.root/'required.log';self.file.write_bytes(b'Actual captured bytes\n')
        self.hash='sha256:'+hashlib.sha256(self.file.read_bytes()).hexdigest()

    def test_required_artifact_matches_exact_recorded_bytes(self):
        self.assertEqual(require_artifact(self.root,'required.log',self.hash),self.file)

    def test_deleted_required_artifact_refuses_acceptance(self):
        self.file.unlink()
        with self.assertRaises(ValueError):require_artifact(self.root,'required.log',self.hash)

    def test_changed_required_artifact_refuses_acceptance_even_with_same_length(self):
        self.file.write_bytes(b'Changed captured byte\n')
        with self.assertRaises(ValueError):require_artifact(self.root,'required.log',self.hash)

    def test_report_reference_cannot_escape_or_select_a_link(self):
        for name in ('../required.log',str(self.file),'/required.log','missing.log'):
            with self.subTest(name=name),self.assertRaises(ValueError):require_artifact(self.root,name,self.hash)

    def test_unknown_command_cannot_replace_required_case_while_counts_match(self):
        rows=[dict(name='first'),dict(name='unrelated')]
        with self.assertRaises(ValueError):require_sequence(rows,['first','last'])

    def test_reordered_duplicate_and_omitted_commands_are_denied(self):
        for names in (['last','first'],['first','first'],['first']):
            with self.subTest(names=names),self.assertRaises(ValueError):require_sequence([dict(name=n) for n in names],['first','last'])

    def test_native_counter_cannot_count_missing_commands(self):
        from s13_acceptance_integrity import NATIVE_COMMANDS,NATIVE_SCENARIOS
        report=dict(commands=[dict(name=n,passed=True,tree_reaped=True) for n in NATIVE_COMMANDS['restore']],
            scenarios=[dict(name=n,result='PASS') for n in NATIVE_SCENARIOS['restore']],command_count=15,scenario_count=12)
        require_native_lists(report,'restore')
        report['commands'].pop()
        with self.assertRaises(ValueError):require_native_lists(report,'restore')

    def test_native_extra_or_duplicate_scenarios_cannot_inflate_counts(self):
        from s13_acceptance_integrity import NATIVE_COMMANDS,NATIVE_SCENARIOS
        report=dict(commands=[dict(name=n,passed=True,tree_reaped=True) for n in NATIVE_COMMANDS['restore']],
            scenarios=[dict(name=n,result='PASS') for n in NATIVE_SCENARIOS['restore']],command_count=15,scenario_count=12)
        report['scenarios'].append(dict(report['scenarios'][0]));report['scenario_count']=13
        with self.assertRaises(ValueError):require_native_lists(report,'restore')

    def test_browser_matching_internal_lists_do_not_override_authoritative_subject(self):
        expected=dict(executable_revision='a'*40,build_hash='sha256:'+'b'*64)
        report=dict(native_build_identity=dict(expected,executable_revision='c'*40),native_browser_assets='EXACT_INVENTORY_MATCH',
            expected_cases=['invented']*11,browser_cases_observed=['invented']*11,build_hashes={'index.html':self.hash})
        with self.assertRaises(ValueError):require_browser_subject(report,identity=expected,cases=['actual'],assets={'index.html':self.hash})

    def test_browser_build_inventory_must_match_actual_native_package(self):
        identity=dict(executable_revision='a'*40)
        report=dict(native_build_identity=identity,native_browser_assets='EXACT_INVENTORY_MATCH',expected_cases=['actual'],
            browser_cases_observed=['actual'],build_hashes={'index.html':'sha256:'+'d'*64})
        with self.assertRaises(ValueError):require_browser_subject(report,identity=identity,cases=['actual'],assets={'index.html':self.hash})

    def old_assert(self,signature,**values):
        tree=ast.parse((base/'s13_service_accept.py').read_text(encoding='utf-8'))
        found=[node for node in tree.body if isinstance(node,ast.Assert) and signature in ast.unparse(node.test)]
        self.assertEqual(len(found),1)
        return eval(compile(ast.Expression(found[0].test),'old-collector-assertion-only','eval'),values)

    def test_original_collector_skips_deleted_screenshot_despite_green_recorded_map(self):
        names=['overview.png','health.png','supervised-health.png','protected-paper.png','approval-preview.png','deployment-pause.png']
        ui=dict(missing_screenshots=[],screenshot_hashes={name:self.hash for name in names})
        self.assertTrue(self.old_assert('missing_screenshots',ui=ui))
        for name in names[:-1]:(self.root/name).write_bytes(b'controlled fixture image bytes')
        tree=ast.parse((base/'s13_service_accept.py').read_text(encoding='utf-8'))
        function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='top')
        retained=[];namespace=dict(retain=lambda file,*args:retained.append(file.name))
        exec(compile(ast.Module(body=[function],type_ignores=[]),'original-top-retention-only','exec'),namespace)
        namespace['top'](self.root,'fixture',True)
        self.assertNotIn(names[-1],retained)
        with self.assertRaises(ValueError):require_artifact(self.root,names[-1],self.hash)

    def test_original_collector_accepts_15_counter_with_14_command_rows(self):
        from s13_acceptance_integrity import NATIVE_COMMANDS,NATIVE_SCENARIOS
        report=dict(commands=[dict(name=n,passed=True,tree_reaped=True) for n in NATIVE_COMMANDS['restore'][:-1]],
            scenarios=[dict(name=n,result='PASS') for n in NATIVE_SCENARIOS['restore']],command_count=15,scenario_count=12)
        self.assertTrue(self.old_assert("restore['scenario_count']",restore=report))
        self.assertTrue(self.old_assert("all((c['passed'] and c['tree_reaped'] for c in restore['commands']))",restore=report))
        with self.assertRaises(ValueError):require_native_lists(report,'restore')

    def test_original_collector_matching_case_lists_can_name_unexecuted_cases(self):
        identity=dict(executable_revision='a'*40)
        cases=['invented-'+str(index) for index in range(11)]
        report=dict(native_build_identity=identity,native_browser_assets='EXACT_INVENTORY_MATCH',build_hashes={'index.html':self.hash},
            expected_cases=cases,browser_cases_observed=cases)
        self.assertTrue(self.old_assert("set(ui['browser_cases_observed']) == set(ui['expected_cases'])",ui=report))
        with self.assertRaises(ValueError):require_browser_subject(report,identity=identity,cases=['actual-'+str(index) for index in range(11)],assets={'index.html':self.hash})

    def publish(self,index,required,manifest=None):
        import s13_acceptance_integrity as guard
        return guard.publish_retention_manifest(self.root,manifest or self.root.parent/(self.root.name+'-manifest.json'),index,required)

    def test_deletion_between_validation_and_retention_cannot_skip_required_reference(self):
        self.file.unlink()
        with self.assertRaises(ValueError):self.publish([],{'required.log':self.hash})

    def test_changed_retained_bytes_refuse_manifest_publication(self):
        index=[dict(original_ref='required.log',retained_file='required.log',original_sha256=self.hash,retained_sha256=self.hash)]
        self.file.write_bytes(b'changed after copy')
        with self.assertRaises(ValueError):self.publish(index,{'required.log':self.hash})

    def test_manifest_failure_does_not_advance_checkpoint(self):
        index=[dict(original_ref='required.log',retained_file='required.log',original_sha256=self.hash,retained_sha256=self.hash)]
        checkpoint=[]
        with self.assertRaises(OSError):
            self.publish(index,{'required.log':self.hash},self.root/'missing-parent'/'manifest.json')
            checkpoint.append('ACCEPTED')
        self.assertEqual(checkpoint,[])

    def test_collector_publishes_manifest_before_actual_checkpoint_writes(self):
        tree=ast.parse((base/'s13_service_accept_v2.py').read_text(encoding='utf-8'))
        publish=[node.lineno for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='publish_retention_manifest']
        writes=[node.lineno for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
            and node.func.attr=='write_text' and isinstance(node.func.value,ast.Name) and node.func.value.id in ('path','handoff')]
        self.assertEqual(len(publish),1)
        self.assertTrue(writes)
        self.assertLess(publish[0],min(writes))

    def test_published_manifest_commits_actual_retained_bytes(self):
        manifest=self.root.parent/(self.root.name+'-manifest.json')
        self.addCleanup(lambda:manifest.unlink(missing_ok=True))
        index=[dict(original_ref='required.log',retained_file='required.log',original_sha256=self.hash,retained_sha256=self.hash)]
        files=self.publish(index,{'required.log':self.hash},manifest)
        self.assertEqual(files,{self.root.name+'/required.log':self.hash})
        self.assertEqual(json.loads(manifest.read_bytes()),files)

    def test_incomplete_manifest_write_is_detected_before_acceptance(self):
        manifest=self.root.parent/(self.root.name+'-manifest.json')
        self.addCleanup(lambda:manifest.unlink(missing_ok=True))
        index=[dict(original_ref='required.log',retained_file='required.log',original_sha256=self.hash,retained_sha256=self.hash)]
        original=Path.write_text
        def incomplete(path,text,**options):return original(path,'{}\n',**options)
        with patch.object(Path,'write_text',incomplete),self.assertRaises(ValueError):self.publish(index,{'required.log':self.hash},manifest)

if __name__=='__main__':unittest.main()
