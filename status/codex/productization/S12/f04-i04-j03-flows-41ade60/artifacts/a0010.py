"""Actual existing two-version browser flow; source freeze and owned cleanup."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002';UI=ROOT/'ui'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.qualification import _sanitize
from strategy.v02.capabilities import _revision
out=BASE/'i04-j03-two-version-browser-development';out.mkdir(exist_ok=False)
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
report=dict(status='EXECUTED_DEVELOPMENT_ONLY',implementation_hash=source,source_and_tests_unchanged=_revision()==source and pin()==pins,
 source_test_hashes=pins,commands=results,started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),
 acceptance_credit='NONE',public_requests=0,private_requests=0,provider_mutation=0,native='NOT_RUN',master='IN_PROGRESS')
(out/'checkpoint.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in report.items() if k!='source_test_hashes'}))
