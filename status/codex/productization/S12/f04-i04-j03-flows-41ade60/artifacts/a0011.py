"""Actual existing two-version browser flow; source freeze and owned cleanup."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002';UI=ROOT/'ui'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.qualification import _sanitize,revision_fact
from strategy.v02.capabilities import _revision
revision=sys.argv[1];revision_fact(ROOT,revision,True)
out=BASE/('i04-j03-two-version-browser-source-'+revision[:7]);out.mkdir(exist_ok=False)
os.environ['R7_BROWSER_ARTIFACT_ROOT']=str(out/'browser-artifacts')
config=out/'two-version.config.mts'
config.write_text('import base from '+json.dumps((UI/'playwright.config.ts').as_uri())+';\n'+
 'export default {...base,testDir:'+json.dumps((UI/'qa').as_posix())+',webServer:base.webServer.filter(s=>s.command.includes("--profile versions ")).map(s=>({...s,cwd:'+json.dumps(UI.as_posix())+'}))};\n',encoding='utf-8',newline='\n')
paths=sorted([*list((ROOT/'tests').rglob('*.py')),*list((UI/'src').rglob('*.ts')),*list((UI/'src').rglob('*.tsx')),*list((UI/'qa').glob('*')),UI/'package.json',UI/'package-lock.json',UI/'playwright.config.ts'])
paths=[p for p in paths if p.is_file()]
def pin():return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
pins=pin();source=_revision();started=datetime.now(timezone.utc).isoformat();results=[]
node=r'C:\Program Files\nodejs\node.exe'
commands=[('build',[node,str(UI/'node_modules/vite/bin/vite.js'),'build']),('browser',[node,str(UI/'node_modules/@playwright/test/cli.js'),'test','--config',str(config),'--grep','two actual immutable versions'])]
for label,argv in commands:
    owned=None;cleanup=None;code=None
    try:
        with (out/(label+'.raw')).open('xb') as stream:
            owned=spawn_owned(argv,cwd=UI,limits=ResourceLimits(300),stdout=stream,stderr=subprocess.STDOUT)
            code=owned.wait()
    finally:
        if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=10)
    raw=(out/(label+'.raw')).read_text(encoding='utf-8')
    safe=_sanitize(raw,ROOT).replace(str(PROJECT),'<PROJECT_ROOT>')
    (out/(label+'.log')).write_text(safe.replace('\r\n','\n'),encoding='utf-8',newline='\n');(out/(label+'.raw')).unlink()
    results.append(dict(label=label,exit_code=code,tree_reaped=bool(cleanup and cleanup.reaped)))
    print(json.dumps(results[-1]),flush=True)
    if code!=0:break
revision_fact(ROOT,revision,True)
result_path=out/'browser-artifacts/results.json'
actual=json.loads(result_path.read_bytes()) if result_path.exists() else {'stats':{'expected':0,'unexpected':0,'flaky':0,'skipped':0}}
passed=len(results)==2 and all(r['exit_code']==0 and r['tree_reaped'] for r in results) and actual['stats']['expected']==1 and actual['stats']['unexpected']==actual['stats']['flaky']==actual['stats']['skipped']==0
report=dict(status='EXACT_CLEAN_SOURCE_BROWSER',executable_revision=revision,passed=passed,browser_cases=1,browser_stats=actual['stats'],implementation_hash=source,source_and_tests_unchanged=_revision()==source and pin()==pins,
 source_test_hashes=pins,commands=results,started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),
 acceptance_credit='SCOPED_SOURCE_FLOW_ONLY',public_requests=0,private_requests=0,provider_mutation=0,native='NOT_RUN',master='IN_PROGRESS')
report['passed']=report['passed'] and report['source_and_tests_unchanged']
(out/'checkpoint.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in report.items() if k!='source_test_hashes'}))
