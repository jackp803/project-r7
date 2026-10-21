"""One missing visible-version assertion on current source, no code change."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,socket,sys,time,urllib.request
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import revision_fact,_sanitize
from strategy.v02.capabilities import _revision
REV='bffc558b9652dc41c0804896436ac7ad8744f7f8'
IMPL='sha256:387238c130af7b96f59578fdfec3b1fa76fc9443daa8a174be00d79ba166c666'
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
revision_fact(ROOT,REV,True);assert _revision()==IMPL
out=BASE/'a08-visible-bffc558-retry01';create_private_directory(out)
scratch=PROJECT/'artifacts/a08-bffc558-retry01';create_private_directory(scratch)
with socket.socket() as reserve:reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
origin='http://127.0.0.1:'+str(port)
env=os.environ.copy();env.update(R7_BROWSER_SCRATCH_ROOT=str(scratch),PYTHONUTF8='1',PYTHONPATH=str(ROOT/'src')+os.pathsep+str(ROOT))
helper=BASE/'verify_a08_visible_revision.mjs';before=helper.read_bytes()
report=dict(started_at=datetime.now(timezone.utc).isoformat(),passed=False,revision=REV,implementation_hash=IMPL,
 scope='SUPPLEMENTAL_A08_CURRENT_SOURCE_BROWSER_ONLY;NOT_NATIVE_OR_RECEIPT_MEMBERSHIP',
 helper_hash=sha(Path(__file__).read_bytes()),browser_helper_hash=sha(before),public_requests=0,private_requests=0)
server=None;browser=None;cleanups=[]
try:
 with (out/'server.raw').open('xb') as stream:
  server=spawn_owned([sys.executable,'-X','utf8',str(ROOT/'ui/qa/serve_fixture.py'),'--profile','empty','--port',str(port)],
   cwd=ROOT/'ui',env=env,limits=ResourceLimits(90),stdout=stream,stderr=stream)
  deadline=time.monotonic()+30
  while True:
   try:
    with urllib.request.urlopen(origin+'/api/v1/auth/status',timeout=1) as response:assert response.status==200
    break
   except OSError:
    if server.process.poll() is not None or time.monotonic()>=deadline:raise ValueError('Actual fixture startup failed')
    time.sleep(.2)
  with (out/'browser.raw').open('xb') as capture:
   browser=spawn_owned(['C:/Program Files/nodejs/node.exe',str(helper),origin,REV,IMPL,str(out/'visible.json')],
    cwd=ROOT/'ui',env=env,limits=ResourceLimits(45),stdout=capture,stderr=capture)
   code=browser.wait();report['browser_exit_code']=code
   if code!=0:raise ValueError('Actual visible version assertion failed')
  observed=json.loads((out/'visible.json').read_bytes());assert observed['passed']
  report['actual_visible']=observed;report['passed']=True
except BaseException as error:report.update(error_type=type(error).__name__,error=str(error))
finally:
 for label,owner in (('browser',browser),('server',server)):
  if owner is not None:cleanups.append(dict(role=label,reaped=terminate_owned(owner,deadline_seconds=10).reaped))
 for label in ('server','browser'):
  raw=out/(label+'.raw')
  if raw.exists():
   safe=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n')
   write_private_new(out/(label+'.log'),safe.encode());raw.unlink()
 revision_fact(ROOT,REV,True);report['source_unchanged']=_revision()==IMPL;report['browser_helper_unchanged']=helper.read_bytes()==before
 report['cleanups']=cleanups;report['finished_at']=datetime.now(timezone.utc).isoformat()
 report['passed']=report['passed'] and all(r['reaped'] for r in cleanups) and len(cleanups)==2 and report['source_unchanged'] and report['browser_helper_unchanged']
 write_private_new(out/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report),flush=True);raise SystemExit(0 if report['passed'] else 1)
