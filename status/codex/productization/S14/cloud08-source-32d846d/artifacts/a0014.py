"""Bounded actual local browser checks; no native or full qualification credit."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize
output=BASE/'cloud08-browser-green';create_private_directory(output)
refs=('src/application/research/queue.py','src/application/control_api/owner_services.py','ui/src/App.tsx',
      'ui/playwright.config.ts','ui/qa/serve_fixture.py','ui/qa/control-center.spec.ts','tests/application/cloud_delivery_fixtures.py')
def hashes():return {ref:'sha256:'+hashlib.sha256((ROOT/ref).read_bytes()).hexdigest() for ref in refs}
before=hashes();os.environ['R7_BROWSER_ARTIFACT_ROOT']=str(output/'browser')
owned=None;cleanup=None;code=None;started=datetime.now(timezone.utc).isoformat()
try:
    with (output/'browser.raw').open('xb') as stream:
        owned=spawn_owned(['C:/Program Files/nodejs/node.exe','node_modules/@playwright/test/cli.js',
            'test','--grep','delivery|health|empty views'],cwd=ROOT/'ui',limits=ResourceLimits(600),stdout=stream,stderr=subprocess.STDOUT)
        code=owned.wait()
finally:
    if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=10)
safe=_sanitize((output/'browser.raw').read_text(encoding='utf-8',errors='replace'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').encode()
write_private_new(output/'browser.log',safe);(output/'browser.raw').unlink()
after=hashes()
report=dict(scope='DIRTY_SOURCE_ACTUAL_LOCAL_BROWSER_ONLY',native_qualification='NONE',exit_code=code,
    started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),tree_reaped=bool(cleanup and cleanup.reaped),
    before=before,after=after,source_unchanged=before==after,additional_public_requests=0,private_requests=0,
    credentials='NONE',capital='NONE',github_compute='NOT_USED',log_hash='sha256:'+hashlib.sha256(safe).hexdigest())
report['passed']=code==0 and report['tree_reaped'] and report['source_unchanged']
write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report),flush=True)
raise SystemExit(0 if report['passed'] else 1)
