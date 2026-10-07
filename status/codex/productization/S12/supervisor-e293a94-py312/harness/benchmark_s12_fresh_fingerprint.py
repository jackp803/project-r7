"""Interleaved old/new fresh-byte hash timing on the identical actual source."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,statistics,sys,time
base=Path(__file__).resolve().parent
repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from strategy.v02 import capabilities
from application.qualification import revision_fact
prior=base/'s12_capabilities.before-fingerprint-remediation.py'
spec=importlib.util.spec_from_file_location('r7_prior_fresh_fingerprint',prior)
old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
paths=(Path(__file__),prior,Path(capabilities.__file__))
bind=lambda:{p.relative_to(base.parent).as_posix():'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
target=base/'S12-runtime-supervision-fingerprint-interleaved-benchmark.json'
assert not target.exists()
before=bind();source_before=revision_fact(repo,None,False)
started=datetime.now(timezone.utc).isoformat();rows=[];reference=None
for index in range(40):
    for label,function in ((('old',old._source_revision),('new',capabilities._source_revision)) if index%2==0 else
                           (('new',capabilities._source_revision),('old',old._source_revision))):
        start=time.perf_counter();identity=function(repo/'src');elapsed=time.perf_counter()-start
        if reference is None:reference=identity
        assert identity==reference
        rows.append(dict(iteration=index,algorithm=label,seconds=elapsed,implementation_hash=identity))
after=bind();source_after=revision_fact(repo,None,False)
assert before==after and source_before==source_after
summary={label:dict(samples=sum(row['algorithm']==label for row in rows),
                   median_seconds=statistics.median(row['seconds'] for row in rows if row['algorithm']==label))
         for label in ('old','new')}
facts=dict(scope='DIAGNOSTIC_INTERLEAVED_FRESH_BYTE_TIMING;NOT24GB_CAPACITY_OR_QUALIFICATION',
           started_at_utc=started,finished_at_utc=datetime.now(timezone.utc).isoformat(),
           source_before=source_before,source_after=source_after,harness_binding='BEFORE_AND_AFTER_EXECUTION',
           input_sha256_before=before,input_sha256_after=after,rows=rows,summary=summary,
           identities_equal_on_identical_source=True,cross_call_cache='NONE',provider_requests=0,credentials='NONE',
           capital='NONE',github_compute='NOT_USED')
target.write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(summary))
