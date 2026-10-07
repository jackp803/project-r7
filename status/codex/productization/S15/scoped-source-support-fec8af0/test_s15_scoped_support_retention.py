"""Exercise the actual retainer publication call with the real helper."""
import ast,hashlib,json,sys,types,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
base=Path(__file__).resolve().parent
sys.path.insert(0,str(base))
sys.path.insert(0,str(base.parent/'workspaces/project-r7-productization-master-20261002/src'))
from s14_feedback_cli_acceptance_core import publish_retention_manifest,require_artifact
from application.datasets.catalog import read_local
from application.qualification import parse_result

class ScopedRetentionPublicationTests(unittest.TestCase):
    def invoke(self,repo,target,manifest_path,retention,required):
        tree=ast.parse((base/'retain_s15_scoped_support_fec8af0.py').read_text(encoding='utf-8'))
        calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='publish_retention_manifest']
        self.assertEqual(1,len(calls))
        namespace=dict(repo=repo,target=target,manifest_path=manifest_path,retention=retention,required=required,
                       publish_retention_manifest=publish_retention_manifest)
        try:return eval(compile(ast.Expression(calls[0]),str(base/'retain_s15_scoped_support_fec8af0.py'),'eval'),namespace)
        except TypeError as exc:self.fail('Actual retainer call does not match real publication API: '+str(exc))
    def fixture(self,root):
        repo=Path(root);target=repo/'status'/'selected';target.mkdir(parents=True)
        payload=b'sanitized controlled proof\n';(target/'proof.json').write_bytes(payload)
        value='sha256:'+hashlib.sha256(payload).hexdigest()
        rows=[dict(original_ref='artifacts/proof.json',original_sha256=value,retained_file='proof.json',retained_sha256=value)]
        return repo,target,repo/'status'/'hashes.json',rows,{'artifacts/proof.json':value}
    def test_actual_publication_call_writes_complete_repository_relative_hashes(self):
        with TemporaryDirectory() as root:
            repo,target,manifest,rows,required=self.fixture(root)
            try:self.invoke(repo,target,manifest,rows,required)
            except TypeError as exc:self.fail('Actual retainer call does not match real publication API: '+str(exc))
            self.assertEqual({'status/selected/proof.json':rows[0]['retained_sha256']},json.loads(manifest.read_bytes()))
    def test_actual_call_refuses_tampered_retained_bytes_before_manifest(self):
        with TemporaryDirectory() as root:
            repo,target,manifest,rows,required=self.fixture(root);(target/'proof.json').write_bytes(b'changed\n')
            with self.assertRaises(ValueError):self.invoke(repo,target,manifest,rows,required)
            self.assertFalse(manifest.exists())
    def test_actual_call_refuses_missing_original_input_before_manifest(self):
        with TemporaryDirectory() as root:
            repo,target,manifest,rows,required=self.fixture(root)
            required['artifacts/missing.json']='sha256:'+'1'*64
            with self.assertRaises(ValueError):self.invoke(repo,target,manifest,rows,required)
            self.assertFalse(manifest.exists())
    def test_actual_call_refuses_retained_path_escape_before_manifest(self):
        with TemporaryDirectory() as root:
            repo,target,manifest,rows,required=self.fixture(root);rows[0]['retained_file']='../outside.json'
            with self.assertRaises(ValueError):self.invoke(repo,target,manifest,rows,required)
            self.assertFalse(manifest.exists())
    def test_original_inputs_require_the_captured_reviewed_commitments_before_accepting_bytes(self):
        tree=ast.parse((base/'retain_s15_scoped_support_fec8af0.py').read_text(encoding='utf-8'))
        policies={f'S15-{group}-support-draft-fec8af0.json':(base/f'S15-{group}-support-draft-fec8af0.json').read_bytes()
                  for group in ('strategy','cloud','data-research')}
        refs=['artifacts/S15-executed-case-index-fec8af0.json',
              'workspaces/project-r7-productization-master-20261002/status/codex/productization/S15/execution-index-fec8af0/retention-index.json',
              'workspaces/project-r7-productization-master-20261002/status/codex/productization/S15/execution-index-artifact-hashes-fec8af0.json',
              'workspaces/project-r7-productization-master-20261002/docs/product/v0_2/07_ACCEPTANCE_MATRIX.json']
        definitions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('raw','captured_hash')]
        for reference in refs:
            with self.subTest(reference=reference),TemporaryDirectory() as temporary:
                project=Path(temporary);repo=project/'workspaces/project-r7-productization-master-20261002';artifact=project/reference
                artifact.parent.mkdir(parents=True);artifact.write_bytes(b'{"coherently_replaced":true}\n')
                namespace=dict(base=project/'artifacts',repo=repo,project=project,snapshots=policies,
                    Path=Path,json=json,hashlib=hashlib,read_local=read_local,require_artifact=require_artifact,
                    digest=lambda value:'sha256:'+hashlib.sha256(value).hexdigest(),
                    prior='status/codex/productization/S15/execution-index-fec8af0')
                exec(compile(ast.Module(definitions,type_ignores=[]),'<actual retainer guards>','exec'),namespace)
                expressions=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)
                    and node.func.id=='raw' and node.args and artifact.name in ast.unparse(node.args[0])]
                self.assertEqual(1,len(expressions),reference)
                with self.assertRaises(ValueError):eval(compile(ast.Expression(expressions[0]),'<actual original input read>','eval'),namespace)
    def test_replacement_external_validator_cannot_execute_before_the_byte_gate(self):
        tree=ast.parse((base/'retain_s15_scoped_support_fec8af0.py').read_text(encoding='utf-8'))
        loader=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='reviewed_core']
        with TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'s14_feedback_cli_acceptance_core.py').write_bytes(b"raise RuntimeError('MUTANT_EXECUTED')\n")
            namespace=dict(base=root,read_local=read_local,hashlib=hashlib,types=types)
            if loader:
                exec(compile(ast.Module(loader,type_ignores=[]),'<actual protected core loader>','exec'),namespace)
                with self.assertRaises(ValueError):namespace['reviewed_core']()
            else:
                self.fail('Current retainer imports external decision helpers without a protected fixed-byte execution gate')
    def test_actual_validation_and_retention_cannot_swap_verified_tools_or_primary_proof(self):
        tree=ast.parse((base/'retain_s15_scoped_support_fec8af0.py').read_text(encoding='utf-8'))
        def assigns(node,name):return isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id==name for target in node.targets)
        first=next(i for i,node in enumerate(tree.body) if assigns(node,'stem'))
        last=next(i for i,node in enumerate(tree.body[first:],first) if assigns(node,'ref'))
        gate=tree.body[first:last]
        count=next(node.comparators[0].value for statement in gate for node in ast.walk(statement)
            if isinstance(node,ast.Compare) and ast.unparse(node.left)=="guard['tests_run']")
        stem=next(node.value.value for node in gate if assigns(node,'stem'))
        retention_loop=next(node for node in tree.body if isinstance(node,ast.For) and ast.unparse(node.target)=='path' and ast.unparse(node.iter)=='paths')
        original={name:(base/name).read_bytes() for name in ('S15-strategy-support-draft-fec8af0.json',
            'S15-cloud-support-draft-fec8af0.json','S15-data-research-support-draft-fec8af0.json')}
        tools=['run_s15_scoped_support_retention_tests.py','test_s15_scoped_support_retention.py',
               'retain_s15_scoped_support_fec8af0.py','s14_feedback_cli_acceptance_core.py']
        material={name:('verified '+name+'\n').encode() for name in tools}
        digest=lambda value:'sha256:'+hashlib.sha256(value).hexdigest()
        log=(f'Ran {count} tests in 0.001s\n\nOK\n').encode()
        implementation='sha256:ba01027908e0e8ddf694eb8619d28b5d7a1bd9f94de0df804dc1471afe189576'
        source=dict(revision='0d34e45ae81760eb5de6db368a92893e20b868aa',worktree='CLEAN')
        inputs={name:digest(value) for name,value in dict(material,**original).items()}
        proof=dict(tests_run=count,failures=0,errors=0,skipped=0,expected_failures=0,unexpected_successes=0,
            passed=True,tree_reaped=True,exit_code=0,harness_binding='BEFORE_AND_AFTER_EXECUTION',
            input_sha256_before=inputs,input_sha256_after=inputs,source_before=source,source_after=source,
            implementation_hash_before=implementation,implementation_hash_after=implementation,log_sha256=digest(log))
        material[stem+'.log']=log;material[stem+'.json']=json.dumps(proof).encode()
        receipt=dict(remaining_critical=0,remaining_important=0,reviewer_execution='NONE',
            reviewed_original_files={'artifacts/'+name:digest(material[name]) for name in tools},
            primary_report_sha256=digest(material[stem+'.json']),primary_log_sha256=digest(log))
        material['S15-scoped-source-support-retention-review.json']=json.dumps(receipt).encode()
        consumed={}
        def replacement_after_verification(path,expected=None):
            name=path.name;consumed[name]=consumed.get(name,0)+1
            value=material[name] if consumed[name]==1 else b'REPLACED_AFTER_VERIFICATION\n'
            if expected is not None and digest(value)!=expected:raise ValueError('Retained subject changed')
            return value
        with TemporaryDirectory() as temporary:
            project=Path(temporary);repo=project/'workspaces/project-r7-productization-master-20261002';target=repo/'retained';target.mkdir(parents=True)
            artifact_base=project/'artifacts'
            namespace=dict(__file__=str(artifact_base/'retain_s15_scoped_support_fec8af0.py'),Path=Path,
                base=artifact_base,project=project,repo=repo,target=target,json=json,hashlib=hashlib,
                snapshots=original,raw=replacement_after_verification,digest=digest,parse_result=parse_result,
                index={'implementation_hash_after':implementation},_sanitize=lambda text,repository:text,
                reviewed={},required={},retention=[],paths=[artifact_base/name for name in material])
            try:
                exec(compile(ast.Module(gate+[retention_loop],type_ignores=[]),'<actual validation-to-retention flow>','exec'),namespace)
            except ValueError:
                self.assertFalse(any(b'REPLACED_AFTER_VERIFICATION' in path.read_bytes() for path in target.iterdir()))
            else:
                for name,value in material.items():self.assertEqual(value,(target/name).read_bytes(),name)
