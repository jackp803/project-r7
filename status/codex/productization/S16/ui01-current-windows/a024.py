"""Add only actual UI01 cases to unchanged fixed qualification inventory."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import ast,hashlib,json,runpy,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(BASE.parent),str(ROOT/'src'),str(ROOT)]
from local_windows_qualification_awake import awake_request
from application.platform.private_files import create_private_directory,write_private_new
from strategy.v02.capabilities import _revision,build_capability_snapshot
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
def value(raw):
    tree=ast.parse(raw)
    return ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)))
def flattened(v):return [case for g in v['groups'] for m in g['members'] for case in m['test_cases']]
out=BASE/'ui01-inventory-freeze-first';create_private_directory(out)
path=ROOT/'src/application/paper/_fixed_inventory.py';old_raw=path.read_bytes();old=value(old_raw)
assert _revision()=='sha256:3cd53bc4e3ebea8fea95fd246dc692b34c95b59a13560f06ab2d1169ac1f104e'
write_private_new(out/'previous-inventory.py.unapplied',old_raw)
refs=['src/application/control_api/dto.py','src/application/control_api/services.py',
    'src/application/control_api/owner_services.py','src/application/research/queue.py',
    'tests/product/test_ui01_observations.py','ui/src/App.tsx','ui/src/api.generated.ts',
    'ui/qa/control-center.spec.ts','ui/qa/serve_fixture.py','contracts/control_api_v0_2.openapi.json']
pins={ref:sha((ROOT/ref).read_bytes()) for ref in refs}
report=dict(started_at=datetime.now(timezone.utc).isoformat(),passed=False,
    scope='FIXED_DISCOVERY_ONLY;NO_TEST_EXECUTION_OR_RECEIPT',old_inventory_hash=sha(old_raw),
    source_pins=pins,helper_hash=sha(Path(__file__).read_bytes()),public_requests=0,private_requests=0)
try:
    with awake_request() as awake:
        report['awake']=awake
        runpy.run_path(str(ROOT/'tools/freeze_paper_inventory.py'),run_name='__main__')
        new_raw=path.read_bytes();new=value(new_raw)
        before,after=flattened(old),flattened(new);delta=Counter(after)-Counter(before)
        assert sum(delta.values())==10 and not Counter(before)-Counter(after)
        assert all(c.startswith('test_ui01_observations.') and n==1 for c,n in delta.items())
        assert [c for c in after if c not in delta]==before
        assert new['groups'][1:]==old['groups'][1:] and len(new['groups'])==7
        old_members={(m['directory'],m['pattern']):m for m in old['groups'][0]['members']}
        for member in new['groups'][0]['members']:
            previous=old_members.get((member['directory'],member['pattern']))
            if previous:
                for key in ('kind','tool_ref','tool_hash','directory','pattern','test_cases','assertions','timeout_seconds','target_predicate'):
                    assert member[key]==previous[key]
            else:assert member['pattern']=='test_ui01_observations.py' and member['timeout_seconds']==900
        assert len(new['groups'][0]['members'])==len(old_members)+1
        assert all(new['source_files'].get(ref)==h for ref,h in old['source_files'].items())
        assert set(new['source_files'])-set(old['source_files'])=={'tests/product/test_ui01_observations.py'}
        assert all(sha((ROOT/ref).read_bytes())==h for ref,h in new['source_files'].items())
        assert new['execution_toolchains']==old['execution_toolchains']
        assert all(sha((ROOT/ref).read_bytes())==h for ref,h in pins.items())
        impl=_revision();cap=build_capability_snapshot().snapshot_hash;bindings=[]
        for name in ('four-hour','legacy','multitimeframe','tactical'):
            p=ROOT/'docs/strategy/authoring-v0.2/examples'/name/'manifest.json'
            raw=p.read_bytes();doc=json.loads(raw);prior=doc['capability_snapshot_hash']
            doc['capability_snapshot_hash']=cap
            p.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
            bindings.append(dict(ref=p.relative_to(ROOT).as_posix(),before_hash=sha(raw),after_hash=sha(p.read_bytes()),
                before_capability=prior,after_capability=cap))
        assert _revision()==impl
        report.update(passed=True,implementation_hash=impl,capability_hash=cap,
            new_inventory_hash=sha(new_raw),source_cases=len(after),added_cases=10,removed_cases=0,
            commands=sum(len(g['members']) for g in new['groups']),source_files=len(new['source_files']),
            old_case_order_preserved=True,native_members_and_deadlines_unchanged=True,
            prior_source_files_unchanged=True,toolchains_unchanged=True,manifest_bindings=bindings)
except BaseException as error:report.update(error_type=type(error).__name__,error=str(error))
finally:
    report['finished_at']=datetime.now(timezone.utc).isoformat()
    report['passed']=report['passed'] and report.get('awake',{}).get('restored') is True
    write_private_new(out/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report),flush=True)
raise SystemExit(0 if report['passed'] else 1)
