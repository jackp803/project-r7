"""Keep exact scoped native outcomes and failures; never include product stores."""
import hashlib,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;REPO=BASE.parents[1]/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(REPO/'src'))
from application.qualification import _sanitize
revision=sys.argv[1];short=revision[:7]
roots=[BASE/('build-'+short),BASE/('fixture-focused-'+short),BASE/('fixture-native-faults-'+short)]
files=[BASE/('build-'+short+'-build.log'),Path(__file__),BASE/'run_fixture_checkpoint.py']
for root in roots:
    files.extend(path for path in root.rglob('*') if path.is_file() and
        (path.suffix=='.log' or path.name in ('checkpoint.json','observations.json','build-result.json')))
target=REPO/('status/codex/productization/S12/sealed-fixture-native-'+short);target.mkdir(exist_ok=False)
artifacts=[]
for path in files:
    raw=_sanitize(path.read_text(encoding='utf-8',errors='replace'),REPO)
    for value in (str(BASE.parents[1]),str(BASE.parents[1]).replace('\\','\\\\')):raw=raw.replace(value,'<PROJECT_ROOT>')
    raw=raw.replace('<USER_HOME>','<USER_HOME>').replace('C:\\\\Users\\\\jackp','<USER_HOME>')
    body=raw.encode();digest=hashlib.sha256(body).hexdigest();ref='artifact-'+digest[:16]+path.suffix
    (target/ref).write_bytes(body);artifacts.append(dict(origin=path.relative_to(BASE).as_posix(),ref=ref,hash='sha256:'+digest))
build=json.loads((roots[0]/'checkpoint.json').read_bytes());source=json.loads((roots[1]/'checkpoint.json').read_bytes())
native=json.loads((roots[2]/'checkpoint.json').read_bytes())
observations=native.get('observations',[])
manifest=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',branch='codex/r7-productization-master-20261002',
    executable_revision=revision,native_identity=native.get('native_identity'),
    scope='FINITE_SEALED_FIXTURE_CASE_BACKUP_RECOVERY_ONLY',full_pqr='NOT_QUALIFIED',ordinary_paper='NOT_QUALIFIED',
    build_passed=build['passed'],focused_tests=source.get('tests_run',0),focused_passed=source['passed'],
    native_passed=native['passed'],native_cases_passed=native.get('scenarios_passed',0),native_cases_total=native.get('scenarios_total',0),
    cases=[dict(case=row['case'],passed=row['passed'],error_type=row.get('error_type'),
        commands=len(row['commands']),all_command_trees_reaped=all(c.get('tree_reaped') is True for c in row['commands']),
        backup_restore=row.get('backup_restore'),market_fault=row.get('market_fault')) for row in observations],
    inputs_unchanged=all(row.get('inputs_unchanged') is True for row in (build,source,native)),
    input_files=native['input_files'],awake_restored=native['awake'].get('restored'),
    failures_preserved=True,provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',artifacts=artifacts)
(target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in manifest.items() if k not in ('artifacts','cases','native_identity')}))
