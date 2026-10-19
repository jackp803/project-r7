"""Owned local source browser regression; response fault is never native proof."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1];ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize
attempt=sys.argv[1]
if not re.fullmatch('red[0-9]{2}|green[0-9]{2}',attempt):raise ValueError('Fresh fixed source attempt required')
output=BASE/('paper-original-retry-source-'+attempt);create_private_directory(output)
env={**os.environ,'R7_BROWSER_ARTIFACT_ROOT':str(output),'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'}
owned=None;code=None;cleanup=None
with (output/'browser.raw').open('xb') as stream:
    try:
        owned=spawn_owned([r'C:\Program Files\nodejs\node.exe',str(ROOT/'ui/node_modules/@playwright/test/cli.js'),
            'test','--grep','actual candidate PAPER start'],cwd=ROOT/'ui',env=env,
            limits=ResourceLimits(240),stdout=stream,stderr=subprocess.STDOUT)
        code=owned.wait()
    finally:
        if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=5)
raw=(output/'browser.raw').read_bytes();safe=_sanitize(raw.decode('utf-8',errors='replace'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').encode()
write_private_new(output/'browser.log',safe)
value=dict(attempt=attempt,exit_code=code,tree_reaped=bool(cleanup and cleanup.reaped),
    log_hash='sha256:'+hashlib.sha256(safe).hexdigest(),scope='ACTUAL_SOURCE_UI_REAL_OWNER_WITH_FIRST_RESPONSE_LOSS;NOT_NATIVE',
    provider_requests=0,credentials='NONE',capital='NONE')
write_private_new(output/'checkpoint.json',(json.dumps(value,indent=2)+'\n').encode());print(json.dumps(value))
raise SystemExit(code if code else (0 if value['tree_reaped'] else 2))
