"""Bounded offline frontend RED/GREEN probe; no full qualification credit."""
from pathlib import Path
import json,os,subprocess,sys
from s09_normal_fixture_source_qualify import BASE,REPO,inputs
from s09_owner_worker_native_regression import OwnedProof,sha,stamp
from s09_local_paper_control_native_regression import read_input
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.platform.private_files import create_private_directory
from application.qualification import revision_fact,_sanitize

label=sys.argv[1]
assert label in {'RED','GREEN'}
output=BASE/('S09-forward-ui-'+label)
assert not os.path.lexists(output)
create_private_directory(output)
node=Path('C:/Program Files/nodejs/node.exe')
captured=inputs()
helpers=[Path(__file__),BASE/'s09_normal_fixture_source_qualify.py',
 BASE/'s09_owner_worker_native_regression.py',BASE/'s09_local_paper_control_native_regression.py',node]
commitments={str(p):sha(read_input(p,128*1024**2)) for p in helpers}
commands=[('unit',[str(node),'node_modules/vitest/vitest.mjs','run','--reporter=json','--outputFile='+str(output/'unit-results.json')],120)]
if label=='GREEN':
    commands=[('contract',[str(node),'scripts/verify-contract.mjs'],60),
      ('typecheck',[str(node),'node_modules/typescript/bin/tsc','--noEmit'],120),*commands,
      ('build',[str(node),'node_modules/vite/bin/vite.js','build'],180)]
environment=os.environ.copy()
environment.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',NO_COLOR='1')
report=dict(label=label,source_before=revision_fact(REPO),input_hashes=captured,
 helper_hashes=commitments,commands=[],passed=False,scope='BOUNDED_DIRTY_SOURCE_FRONTEND_ONLY;NO_NATIVE_OR_FULL_PRODUCT_QUALIFICATION',
 real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
with OwnedProof(output/'probe.json') as proof:
    proof.persist(report)
    for name,argv,timeout in commands:
        assert inputs()==captured
        for path,digest in commitments.items():assert sha(read_input(Path(path),128*1024**2))==digest
        owned=None;started=stamp()
        with OwnedProof(output/(name+'.log')) as log:
            try:
                owned=spawn_owned(argv,cwd=REPO/'ui',limits=ResourceLimits(timeout),
                  stdout=log.stream,stderr=subprocess.STDOUT,env=environment)
                code=owned.wait()
            finally:
                cleanup=None if owned is None else terminate_owned(owned,deadline_seconds=5)
            assert cleanup is not None and cleanup.reaped
            log.require_owned();log.stream.seek(0);raw=log.stream.read(8*1024**2+1)
            assert len(raw)<=8*1024**2
            published=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace('\r\n','\n').encode()
            log.stream.seek(0);log.stream.write(published);log.stream.truncate();log.stream.flush();log.require_owned()
        result=dict(label=name,argv=argv,exit_code=code,tree_reaped=True,
          started_at_utc=started,finished_at_utc=stamp(),log=name+'.log',
          original_log_sha256=sha(raw),published_log_sha256=sha(published))
        if name=='unit':
            stats=json.loads(read_input(output/'unit-results.json',8*1024**2))
            result.update(tests=stats['numTotalTests'],passed=stats['numPassedTests'],
              failed=stats['numFailedTests'],pending=stats['numPendingTests'])
        report['commands'].append(result);proof.persist(report)
        print(json.dumps(result),flush=True)
        assert inputs()==captured
        if label=='GREEN' and code!=0:break
    for path,digest in commitments.items():assert sha(read_input(Path(path),128*1024**2))==digest
    assert inputs()==captured
    report.update(input_bytes_unchanged=True,source_after=revision_fact(REPO))
    report['passed']=label=='GREEN' and len(report['commands'])==4 and all(c['exit_code']==0 for c in report['commands'])
    proof.persist(report)
print(json.dumps(dict(label=label,passed=report['passed'],inputs_unchanged=True)),flush=True)
