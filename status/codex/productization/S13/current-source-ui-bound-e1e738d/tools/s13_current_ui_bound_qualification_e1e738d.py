"""Owned current source UI qualification using installed local Node/Edge only."""
from pathlib import Path
import json,os,stat,subprocess,sys
BASE=Path(__file__).resolve().parent
REPO=BASE.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(BASE));sys.path.insert(0,str(REPO/'src'))
from s09_owner_worker_native_regression import OwnedProof,sha,stamp
from s09_owner_worker_source_qualify import inputs
from application.qualification import revision_fact,_sanitize
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.platform.supervision import _local_path
from application.datasets.catalog import read_local
from strategy.v02.capabilities import _revision
from local_windows_qualification_awake import awake_request

REVISION='e1e738dc0384e56cf0a6a3d56c16a37279e6d4b9'
NODE=Path('C:/Program Files/nodejs/node.exe')
OUTPUT=BASE/'S13-current-ui-bound-e1e738d'

def capture_dist(root):
    root=Path(root);_local_path(root)
    if not root.is_dir():raise ValueError('Existing built UI directory required')
    paths=sorted(root.rglob('*'));inventory={};total=0
    if len(paths)>1024:raise ValueError('Bounded built UI inventory required')
    for path in paths:
        _local_path(path);info=path.lstat();name=path.relative_to(root).as_posix()
        if stat.S_ISDIR(info.st_mode):inventory['d:'+name]='DIRECTORY'
        elif stat.S_ISREG(info.st_mode) and info.st_nlink==1:
            raw=read_local(path.parent,path.name,16*1024**2);total+=len(raw)
            if total>16*1024**2:raise ValueError('Bounded built UI bytes required')
            inventory['f:'+name]=sha(raw)
        else:raise ValueError('Ordinary unlinked built UI asset required')
    if 'f:index.html' not in inventory:raise ValueError('Built UI index required')
    return inventory

def require_dist(root,expected):
    assert capture_dist(root)==expected,'Built UI asset subject changed'

def main():
    before=revision_fact(REPO,REVISION,True);captured=inputs();implementation=_revision()
    helper_paths=[Path(__file__),BASE/'s09_owner_worker_native_regression.py',BASE/'s09_owner_worker_source_qualify.py',BASE/'local_windows_qualification_awake.py',NODE]
    helpers={str(p.relative_to(BASE)) if p.is_relative_to(BASE) else 'LOCAL_NODE_EXECUTABLE':sha(p.read_bytes()) for p in helper_paths}
    _local_path(OUTPUT);OUTPUT.mkdir();temporary=OUTPUT/'temporary';temporary.mkdir()
    environment=os.environ.copy();environment.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(temporary),TMP=str(temporary),R7_BROWSER_ARTIFACT_ROOT=str(OUTPUT/'browser'),R7_BROWSER_CHANNEL='msedge',NO_COLOR='1')
    commands=[('contract',[str(NODE),'scripts/verify-contract.mjs'],60),
        ('typecheck',[str(NODE),'node_modules/typescript/bin/tsc','--noEmit'],120),
        ('unit',[str(NODE),'node_modules/vitest/vitest.mjs','run','--reporter=json','--outputFile='+str(OUTPUT/'unit-results.json')],120),
        ('build',[str(NODE),'node_modules/vite/bin/vite.js','build'],180),
        ('browser',[str(NODE),'node_modules/@playwright/test/cli.js','test'],600)]
    report=dict(passed=False,source_before=before,implementation_hash=implementation,source_input_hashes=captured,
        helper_hashes=helpers,commands=[],scope='CURRENT_SOURCE_UI_ACTUAL_LOCAL_WINDOWS_EDGE_AND_ISOLATED_FIXTURE_API;NO_NATIVE_UI_OR_ORDINARY_PAPER_OR_FORWARD_ACCEPTANCE',
        real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
    dist_inventory=None
    with OwnedProof(OUTPUT/'ui-qualification.json') as report_owner:
        with awake_request() as awake:
            for label,argv,seconds in commands:
                revision_fact(REPO,REVISION,True);assert inputs()==captured and _revision()==implementation
                if label=='browser':require_dist(REPO/'ui/dist',dist_inventory)
                started=stamp();handle=None
                with OwnedProof(OUTPUT/(label+'.log')) as owner:
                    try:
                        handle=spawn_owned(argv,cwd=REPO/'ui',limits=ResourceLimits(seconds),stdout=owner.stream,stderr=subprocess.STDOUT,env=environment);code=handle.wait()
                    finally:
                        reaped=handle is not None and terminate_owned(handle,deadline_seconds=5).reaped
                    owner.require_owned();owner.stream.seek(0);raw=owner.stream.read(8*1024**2+1);assert len(raw)<=8*1024**2
                    text=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace('\r\n','\n')
                    owner.stream.seek(0);owner.stream.write(text.encode());owner.stream.truncate();owner.stream.flush();owner.require_owned()
                result=dict(label=label,started_at_utc=started,finished_at_utc=stamp(),exit_code=code,tree_reaped=reaped,passed=code==0 and reaped,log=label+'.log',log_sha256=sha(text.encode()))
                report['commands'].append(result);report_owner.persist(report);print(json.dumps(result),flush=True)
                if not result['passed']:return 1
                if label=='build':
                    dist_inventory=capture_dist(REPO/'ui/dist');report['ui_dist_inventory']=dist_inventory
                    report['ui_dist_inventory_hash']=sha(json.dumps(dist_inventory,sort_keys=True,separators=(',',':')).encode())
                    report_owner.persist(report)
                if label=='browser':require_dist(REPO/'ui/dist',dist_inventory)
        assert awake['restored']
        unit=json.loads((OUTPUT/'unit-results.json').read_text(encoding='utf-8'))
        browser=json.loads((OUTPUT/'browser/results.json').read_text(encoding='utf-8'))
        assert unit['success'] and unit['numTotalTests']>0 and unit['numFailedTests']==unit['numPendingTests']==0
        assert browser['stats']['expected']>0 and browser['stats']['unexpected']==browser['stats']['skipped']==browser['stats']['flaky']==0
        helper_after={str(p.relative_to(BASE)) if p.is_relative_to(BASE) else 'LOCAL_NODE_EXECUTABLE':sha(p.read_bytes()) for p in helper_paths}
        assert helpers==helper_after and inputs()==captured and _revision()==implementation
        require_dist(REPO/'ui/dist',dist_inventory)
        report.update(passed=True,source_after=revision_fact(REPO,REVISION,True),inputs_unchanged=True,awake_request=awake,
            unit_tests=unit['numTotalTests'],unit_failures=0,unit_skipped=0,browser_tests=browser['stats']['expected'],browser_failures=0,browser_skipped=0,browser_flaky=0)
        report_owner.persist(report)
    print(json.dumps(dict(passed=True,unit_tests=report['unit_tests'],browser_tests=report['browser_tests'],source_revision=REVISION)),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
