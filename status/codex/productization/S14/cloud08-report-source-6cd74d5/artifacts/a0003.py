"""Exact-clean report-history source regression, no full/native credit."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.qualification import revision_fact,_sanitize
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.private_files import create_private_directory,write_private_new
from strategy.v02.capabilities import _revision
revision=sys.argv[1];revision_fact(ROOT,revision,True);implementation=_revision()
output=BASE/('cloud08-report-source-'+revision[:7]);create_private_directory(output)
modules=('tests.product.test_report_publication_history','tests.product.test_paper_feedback_outbox',
    'tests.application.test_feedback_redaction','tests.product.test_api_owner_services','tests.product.test_api_paper_services')
owned=None;cleanup=None;started=datetime.now(timezone.utc).isoformat();code=None
try:
    with (output/'source.raw').open('xb') as stream:
        owned=spawn_owned([sys.executable,'-X','utf8','-m','unittest','-v',*modules],cwd=ROOT,
            limits=ResourceLimits(300),stdout=stream,stderr=__import__('subprocess').STDOUT)
        code=owned.wait()
finally:
    if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=10)
safe=_sanitize((output/'source.raw').read_text(encoding='utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').encode()
write_private_new(output/'source.log',safe);(output/'source.raw').unlink()
revision_fact(ROOT,revision,True)
counts=re.findall(rb'Ran (\d+) tests? in ',safe)
count=int(counts[-1]) if counts else None
report=dict(executable_revision=revision,implementation_hash=implementation,scope='CLOUD08_REPORT_HISTORY_SOURCE_ONLY',
    modules=list(modules),tests_run=count,exit_code=code,source_unchanged=_revision()==implementation,
    tree_reaped=bool(cleanup and cleanup.reaped),native_full='NOT_RUN',real_cloud='NOT_RUN',
    additional_public_requests=0,private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',
    log_hash='sha256:'+hashlib.sha256(safe).hexdigest(),helper_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    started_at=started,finished_at=datetime.now(timezone.utc).isoformat())
report['passed']=code==0 and count==53 and b'skipped=' not in safe and report['source_unchanged'] and report['tree_reaped']
write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report),flush=True)
raise SystemExit(0 if report['passed'] else 1)
