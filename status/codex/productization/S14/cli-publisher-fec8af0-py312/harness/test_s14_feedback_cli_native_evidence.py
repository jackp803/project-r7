import ast,copy,hashlib,json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from application.datasets.catalog import read_local
from application.qualification import parse_result
import s14_feedback_cli_acceptance_core as core
from s14_feedback_cli_native_evidence import COMMANDS,SCENARIOS,validate_native_paper

class NativeHistoricalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(dir=Path(__file__).parent);self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name);self.folder=self.project/'native';self.folder.mkdir()
        self.inputs={}
        for index in range(7):
            path=self.project/f'input-{index}.py';path.write_bytes(b'CONTROLLED_INPUT\n')
            self.inputs[path.name]=path
        self.identity=dict(executable_revision='a'*40,implementation_hash='sha256:'+'b'*64)
        hashes={key:'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest() for key,path in self.inputs.items()}
        self.report=dict(passed=True,fixture_cleanup_complete=True,identity=self.identity,
            source_before=dict(revision='a'*40,worktree='CLEAN'),source_after=dict(revision='a'*40,worktree='CLEAN'),
            implementation_hash_after=self.identity['implementation_hash'],harness_binding='BEFORE_AND_AFTER_EVERY_NATIVE_COMMAND',
            fixture_origin='SOURCE_CREATED_ACTUAL_E2_E5_E6_ACCELERATED_FIXTURE;NOT_NATIVE_RUNTIME_COMPOSITION',
            transport='OFFLINE_COMPILED_FAKE_ONLY',normal_runtime='NOT_RUN',real_cloud='NOT_RUN',real_forward='NOT_RUN',ubuntu='NOT_RUN',
            provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',financial_authority='NONE',
            native_path='EMPTY',native_pythonpath='UNSET',native_node='UNAVAILABLE_ON_PATH',
            input_sha256_before=hashes,input_sha256_after=dict(hashes),commands=[],scenarios=[dict(name=name,passed=True) for name in SCENARIOS],
            command_count=2,scenario_count=3)
        for index,name in enumerate(COMMANDS,1):
            result=dict(status='COMPLETE',attempted=1 if index==1 else 0,local_staged=0,
                cloud_acknowledged=1 if index==1 else 0,unavailable=0,conflicts=0)
            path=self.folder/f'{index:02d}-{name}.log';path.write_bytes(json.dumps(result).encode())
            self.report['commands'].append(dict(name=name,passed=True,tree_reaped=True,exit_code=0,
                log=path.name,log_sha256='sha256:'+hashlib.sha256(path.read_bytes()).hexdigest(),result=result))
    def validate(self,report=None):
        bound={};validate_native_paper(self.folder,self.report if report is None else report,self.identity,
            inputs=self.inputs,bound=bound,project=self.project);return bound
    def test_exact_owned_historical_subject_with_complete_fixture_cleanup_is_bound(self):
        self.assertEqual(len(self.validate()),9)
    def test_retained_pass_cannot_override_failed_cleanup_or_normal_runtime_claim(self):
        for key,value in (('fixture_cleanup_complete',False),('normal_runtime','PASS'),('real_cloud','PASS')):
            report=copy.deepcopy(self.report);report[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(report)
    def test_missing_extra_or_relabelled_scenario_is_not_complete_coverage(self):
        for rows in (self.report['scenarios'][:-1],self.report['scenarios']+[dict(name='invented',passed=True)]):
            report=copy.deepcopy(self.report);report['scenarios']=rows
            with self.subTest(length=len(rows)),self.assertRaises(ValueError):self.validate(report)
    def test_unreaped_command_or_borrowed_zero_exit_cannot_establish_native_pass(self):
        report=copy.deepcopy(self.report);report['commands'][0]['tree_reaped']=False
        with self.assertRaises(ValueError):self.validate(report)
    def test_changed_native_stdout_is_refused_before_parsing_an_uncommitted_result(self):
        (self.folder/self.report['commands'][0]['log']).write_bytes(b'{"status":"invented"}')
        with self.assertRaises(ValueError):self.validate()
    def test_changed_or_omitted_consumed_fixture_input_is_refused(self):
        report=copy.deepcopy(self.report)
        key=next(iter(report['input_sha256_before']))
        report['input_sha256_before'].pop(key);report['input_sha256_after'].pop(key)
        with self.assertRaises(ValueError):self.validate(report)
        path=next(iter(self.inputs.values()));path.write_bytes(b'CHANGED_INPUT\n')
        with self.assertRaises(ValueError):self.validate()

class ProtectedPrimarySnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(dir=Path(__file__).parent);self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.primary_tree=ast.parse(Path(core.__file__).read_bytes())
        self.retention_tree=ast.parse((Path(__file__).parent/'s14_feedback_cli_accept.py').read_bytes())
    def primary_loop(self,predicate,namespace):
        tree=self.primary_tree
        function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='validate_primary_artifacts')
        loop=next(node for node in function.body if isinstance(node,ast.For) and predicate(ast.unparse(node.iter)))
        helpers=[node for node in function.body if isinstance(node,ast.FunctionDef) and node.name in ('verify','read_verified')]
        namespace.update(project=self.folder,verified={},require_artifact=core.require_artifact,read_local=read_local,
            hashlib=hashlib,asdict=asdict,parse_result=parse_result,json=json,specs=core.specs)
        exec(compile(ast.Module(body=helpers,type_ignores=[]),str(core.__file__),'exec'),namespace)
        exec(compile(ast.Module(body=[loop],type_ignores=[]),str(core.__file__),'exec'),namespace)
    def test_actual_source_decision_cannot_parse_temporary_uncommitted_pass_bytes(self):
        name='001-phase_1-controlled.log';failed=b'Ran 1 test in 0.001s\n\nFAILED (failures=1)\n'
        path=self.folder/name;path.write_bytes(failed)
        row=dict(phase='phase_1',suite='controlled',log=name,log_sha256='sha256:'+hashlib.sha256(failed).hexdigest(),
            **asdict(parse_result('Ran 1 test in 0.001s\n\nOK\n',returncode=0)),tests_passed=1,source_after=dict(revision='a'*40,worktree='CLEAN'))
        with patch.object(Path,'read_text',return_value='Ran 1 test in 0.001s\n\nOK\n'):
            with self.assertRaises(ValueError):
                self.primary_loop(lambda text:"full['commands']" in text,dict(source=self.folder,full=dict(commands=[row]),revision='a'*40))
    def test_actual_browser_decision_cannot_parse_temporary_uncommitted_pass_json(self):
        good=dict(suites=[dict(specs=[dict(title='controlled',ok=True,tests=[dict(status='expected',results=[dict(status='passed')])])])],stats=dict(expected=1),errors=[])
        bad=copy.deepcopy(good);bad['suites'][0]['specs'][0]['ok']=False
        values={'empty.log':b'CONTROLLED','empty.config.mjs':b'CONTROLLED','empty-browser-results.json':json.dumps(bad).encode()}
        hashes={}
        for name,raw in values.items():
            (self.folder/name).write_bytes(raw);hashes[name]='sha256:'+hashlib.sha256(raw).hexdigest()
        row=dict(profile='empty',expected_cases=['controlled'],observed_cases=['controlled'],build_inventory_after='MATCH',
            log='empty.log',log_sha256=hashes['empty.log'],config_sha256=hashes['empty.config.mjs'],
            browser_results_sha256=hashes['empty-browser-results.json'],browser_stats=good['stats'])
        with patch.object(Path,'read_bytes',return_value=json.dumps(good).encode()):
            with self.assertRaises(ValueError):
                self.primary_loop(lambda text:text=="ui['commands']",dict(ui_root=self.folder,ui=dict(commands=[row]),groups=dict(empty=['controlled']),observed=[]))
    def retain(self,path):
        tree=self.retention_tree
        node=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='retain')
        target=self.folder/'retained';target.mkdir(exist_ok=True)
        namespace=dict(project=self.folder,target=target,index=[],seen={},Path=Path,hashlib=hashlib,
            require_artifact=core.require_artifact,read_local=read_local,_sanitize=lambda text,repo:text,repo=self.folder)
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-retain>','exec'),namespace)
        namespace['retain'](path,path.name);return namespace['index']
    def test_actual_retention_denies_oversized_supplement_before_unbounded_read(self):
        path=self.folder/'controlled.log';path.write_bytes(b'x'*(4*1024*1024+1))
        with patch.object(Path,'read_bytes',side_effect=AssertionError('Unbounded read forbidden')) as unbounded:
            with self.assertRaises(ValueError):self.retain(path)
        unbounded.assert_not_called()
    def test_actual_retention_checks_protected_reader_before_link_guarded_content(self):
        path=self.folder/'controlled.log';path.write_bytes(b'CONTROLLED')
        tree=self.retention_tree
        node=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='retain')
        namespace=dict(project=self.folder,target=self.folder/'retained',index=[],seen={},Path=Path,hashlib=hashlib,
            require_artifact=lambda *args:(_ for _ in ()).throw(ValueError('Linked evidence forbidden')),
            read_local=lambda *args:(_ for _ in ()).throw(ValueError('Linked evidence forbidden')),
            _sanitize=lambda text,repo:text,repo=self.folder)
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-retain>','exec'),namespace)
        with patch.object(Path,'read_bytes',return_value=b'CONTROLLED') as unbounded:
            with self.assertRaises(ValueError):namespace['retain'](path,path.name)
        unbounded.assert_not_called()
    def test_actual_auxiliary_snapshot_rejects_uncommitted_installer_and_ssh_outcomes(self):
        node=next(node for node in self.retention_tree.body if isinstance(node,ast.FunctionDef) and node.name=='validate_auxiliary_snapshot')
        namespace=dict(read_local=read_local,hashlib=hashlib,require_artifact=core.require_artifact,bound={},project=self.folder,json=json)
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-auxiliary>','exec'),namespace)
        for kind,raw,result in (('installer',b'INVENTED',None),('ssh',b'{"status":"FAILED"}',dict(status='PASS'))):
            path=self.folder/'controlled.log';path.write_bytes(raw)
            row=dict(log=path.name,log_sha256='sha256:'+hashlib.sha256(raw).hexdigest())
            if result is not None:row['result']=result
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                namespace['validate_auxiliary_snapshot'](self.folder,dict(commands=[row]),kind)

if __name__=='__main__':unittest.main(verbosity=2)
