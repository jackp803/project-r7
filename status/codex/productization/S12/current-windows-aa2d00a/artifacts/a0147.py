"""Fixed discovery only; preserve prior cases/deadlines and reviewed source pins."""
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
def cases(v):return Counter(case for g in v['groups'] for m in g['members'] for case in m['test_cases'])
def native(v):return [g for g in v['groups'] if g['check_id']!='PQR-01']
pins=json.loads((BASE/'k03-actual-review-pins-retry01-20261021.json').read_bytes())
assert all(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'] for row in pins['files'])
assert _revision()=='sha256:b3383337e04626f92bf6d248931de70bd965d981ad56b343c32736c2c5e4653c'
out=BASE/'k03-inventory-freeze-first';create_private_directory(out)
path=ROOT/'src/application/paper/_fixed_inventory.py';old_raw=path.read_bytes();old=value(old_raw)
write_private_new(out/'previous-inventory.py.unapplied',old_raw)
report=dict(scope='DISCOVERY_AND_OFFLINE_CAPABILITY_MANIFEST_REFRESH_ONLY',execution='TEST_EXECUTION_NONE',
    started_at=datetime.now(timezone.utc).isoformat(),old_hash=sha(old_raw),passed=False,
    provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
try:
    with awake_request() as awake:
        report['awake']=awake
        runpy.run_path(str(ROOT/'tools/freeze_paper_inventory.py'),run_name='__main__')
        new_raw=path.read_bytes();new=value(new_raw)
        before,after=cases(old),cases(new)
        assert not before-after and sum((after-before).values())==16
        assert native(old)==native(new) and len(new['groups'])==7
        assert all(m['timeout_seconds']==900 for m in new['groups'][0]['members'])
        assert all(new['source_files'].get(ref)==expected for ref,expected in old['source_files'].items())
        assert all(sha((ROOT/ref).read_bytes())==expected for ref,expected in new['source_files'].items())
        assert all(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'] for row in pins['files'])
        snapshot=build_capability_snapshot().snapshot_hash;implementation=_revision()
        manifests=[]
        for name in ('four-hour','legacy','multitimeframe','tactical'):
            p=ROOT/'docs/strategy/authoring-v0.2/examples'/name/'manifest.json'
            previous=p.read_bytes();document=json.loads(previous)
            prior=document['capability_snapshot_hash'];document['capability_snapshot_hash']=snapshot
            p.write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
            manifests.append(dict(path=p.relative_to(ROOT).as_posix(),old_hash=sha(previous),new_hash=sha(p.read_bytes()),
                previous_capability_hash=prior,current_capability_hash=snapshot))
        assert _revision()==implementation
        report.update(passed=True,new_hash=sha(new_raw),old_cases=sum(before.values()),new_cases=sum(after.values()),
            added_cases=sum((after-before).values()),removed_cases=0,native_members_and_deadlines_unchanged=True,
            source_per_module_seconds=900,groups=len(new['groups']),commands=sum(len(g['members']) for g in new['groups']),
            source_files=len(new['source_files']),reviewed12files_unchanged=True,implementation_hash=implementation,
            capability_hash=snapshot,manifest_bindings=manifests)
except BaseException as error:report.update(passed=False,error_type=type(error).__name__)
finally:
    report['finished_at']=datetime.now(timezone.utc).isoformat()
    if report.get('awake',{}).get('restored') is not True:report['passed']=False
    write_private_new(out/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report),flush=True)
raise SystemExit(0 if report['passed'] else 2)
