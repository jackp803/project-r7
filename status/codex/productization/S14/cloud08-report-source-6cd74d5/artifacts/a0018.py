"""Two actual local report-owner profiles; no native/full qualification credit."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize
output=BASE/sys.argv[1];create_private_directory(output)
refs=('src/application/cloud/publication_history.py','src/application/research/evidence.py','src/storage/paper_feedback.py',
      'src/application/control_api/app.py','src/application/control_api/owner_services.py','src/application/local_owners.py',
      'ui/src/App.tsx','ui/src/model.ts','ui/qa/serve_fixture.py','ui/qa/control-center.spec.ts',
      'tests/application/report_delivery_fixtures.py','tests/product/test_report_publication_history.py')
def hashes():return {ref:'sha256:'+hashlib.sha256((ROOT/ref).read_bytes()).hexdigest() for ref in refs}
before=hashes();os.environ['R7_BROWSER_ARTIFACT_ROOT']=str(output/'browser')
scratch=PROJECT/'temporary'/('rh-'+hashlib.sha256(output.name.encode()).hexdigest()[:8])
scratch.parent.mkdir(parents=True,exist_ok=True);create_private_directory(scratch)
os.environ['R7_BROWSER_SCRATCH_ROOT']=str(scratch)
config=dict(testDir=str(ROOT/'ui/qa'),testMatch='*.spec.ts',fullyParallel=False,workers=1,
    timeout=35000,expect=dict(timeout=6000),retries=0,outputDir=str(output/'results'),
    reporter=[['line'],['json',dict(outputFile=str(output/'results.json'))]],
    use=dict(browserName='chromium',channel='msedge',headless=True,viewport=dict(width=1440,height=960),
        actionTimeout=8000,trace='off',video='off',screenshot='off'),
    webServer=[dict(command=subprocess.list2cmdline([sys.executable,'-X','utf8','qa/serve_fixture.py','--profile',profile,'--port',str(port)]),
        cwd=str(ROOT/'ui'),url='http://127.0.0.1:'+str(port)+'/api/v1/auth/status',reuseExistingServer=False,
        timeout=90000,stdout='ignore',stderr='pipe') for profile,port in (('report-research',8775),('report-paper',8776))])
write_private_new(output/'report.config.mjs',('export default '+json.dumps(config)+';\n').encode())
owned=None;cleanup=None;code=None;started=datetime.now(timezone.utc).isoformat()
try:
    with (output/'browser.raw').open('xb') as stream:
        owned=spawn_owned(['C:/Program Files/nodejs/node.exe','node_modules/@playwright/test/cli.js','test',
            '--config',str(output/'report.config.mjs'),'--grep','report history'],cwd=ROOT/'ui',
            limits=ResourceLimits(240),stdout=stream,stderr=subprocess.STDOUT)
        code=owned.wait()
finally:
    if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=10)
safe=_sanitize((output/'browser.raw').read_text(encoding='utf-8',errors='replace'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').encode()
write_private_new(output/'browser.log',safe);(output/'browser.raw').unlink()
after=hashes()
report=dict(scope='SOURCE_ACTUAL_LOCAL_BROWSER_ONLY',native_qualification='NONE',exit_code=code,
    started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),tree_reaped=bool(cleanup and cleanup.reaped),
    before=before,after=after,source_unchanged=before==after,additional_public_requests=0,private_requests=0,
    credentials='NONE',capital='NONE',github_compute='NOT_USED',log_hash='sha256:'+hashlib.sha256(safe).hexdigest())
report['passed']=code==0 and report['tree_reaped'] and report['source_unchanged']
write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps({key:value for key,value in report.items() if key not in ('before','after')}),flush=True)
raise SystemExit(0 if report['passed'] else 1)
