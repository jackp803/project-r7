"""Static, public-source inventory only; it cannot declare requirement PASS."""
import ast,hashlib,json,re,subprocess,sys
from pathlib import Path

base=Path(__file__).resolve().parent
repo=base.parent/'workspaces/project-r7-productization-master-20261002'
revision=sys.argv[1];assert re.fullmatch('[0-9a-f]{40}',revision)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==revision
assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip()
matrix_path=repo/'docs/product/v0_2/07_ACCEPTANCE_MATRIX.json'
matrix=json.loads(matrix_path.read_bytes())
legacy_path=repo/matrix['inherits']
legacy=[]
for line in legacy_path.read_text(encoding='utf-8').splitlines():
    match=re.match(r'^\|\s*([A-Z][0-9]{2})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$',line)
    if match:
        legacy.append(dict(id=match[1],requirement=match[2],requested_evidence=match[3],
            origin=matrix['inherits'],inheritance_classification='PENDING_APPLICABILITY_AND_SUPERSESSION_REVIEW',
            acceptance_status='NOT_RUN',mapping_status='UNMAPPED'))
assert legacy and len({row['id'] for row in legacy})==len(legacy)
declared=[];source_hashes={}
for path in sorted((repo/'tests').rglob('test_*.py')):
    raw=path.read_bytes();relative=path.relative_to(repo).as_posix()
    source_hashes[relative]='sha256:'+hashlib.sha256(raw).hexdigest()
    tree=ast.parse(raw)
    module='.'.join(path.relative_to(repo).with_suffix('').parts)
    for node in tree.body:
        if not isinstance(node,ast.ClassDef):continue
        bases=[ast.unparse(item) for item in node.bases]
        for method in node.body:
            if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef)) and method.name.startswith('test_'):
                declared.append(dict(test_id=module+'.'+node.name+'.'+method.name,source=relative,line=method.lineno,
                    class_bases=bases,discovery='STATIC_DECLARATION;ACTUAL_DISCOVERY_AND_EXECUTION_BINDING_PENDING'))
assert len({row['test_id'] for row in declared})==len(declared)
target=base/f'S15-acceptance-coverage-inventory-{revision[:7]}.json'
assert not target.exists()
inventory=dict(task_id=matrix['task_id'],spec_baseline='r7-product-v0.2',
    document_kind='STATIC_REQUIREMENT_AND_TEST_COVERAGE_WORKING_INVENTORY;NOT_ACCEPTANCE_RESULT',
    candidate_revision=revision,spec_revision='9fd277798b1c51d1bc79b29a61bec81b552efeb1',
    inventory_builder_sha256='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    matrix_sha256='sha256:'+hashlib.sha256(matrix_path.read_bytes()).hexdigest(),
    legacy_matrix_sha256='sha256:'+hashlib.sha256(legacy_path.read_bytes()).hexdigest(),
    requirements=[dict(**row,acceptance_status='NOT_RUN',mapping_status='UNMAPPED') for row in matrix['requirements']],
    legacy_requirements=legacy,separate_commissioning=matrix['separate_commissioning_requirements'],
    declared_tests=declared,test_source_hashes=source_hashes,
    per_result_required_fields=matrix['per_result_required_fields'],
    required_platforms=matrix['required_platforms'],
    limits=['Static declarations are not execution evidence',
        'No requirement becomes PASS from a suite-wide or milestone summary',
        'Native Ubuntu, normal continuous runtime and real commissioning gaps remain explicit',
        'Unmapped rows must prevent whole-product acceptance; applicability requires documented review'])
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==revision
assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip()
for relative,expected in source_hashes.items():
    assert 'sha256:'+hashlib.sha256((repo/relative).read_bytes()).hexdigest()==expected
target.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(v02_requirements=len(matrix['requirements']),legacy_requirements=len(legacy),
    static_declared_test_methods=len(declared),source_files=len(source_hashes),
    requirement_pass_claims=0,state='MAPPING_IN_PROGRESS;NOT_ACCEPTANCE')))
