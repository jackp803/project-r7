"""Owned bounded evidence-tool regressions; no new product qualification."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re,sys
base=Path(__file__).resolve().parent;repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.datasets.catalog import read_local
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize,parse_result,revision_fact
from strategy.v02.capabilities import _revision
label=sys.argv[1];assert re.fullmatch('[A-Za-z0-9_-]+',label)
paths=[Path(__file__),base/'test_s15_owner_temporal_retention.py',base/'retain_s15_owner_temporal_support.py']
paths += [base/'S15-executed-case-index-fec8af0.json',repo/'docs/product/v0_2/07_ACCEPTANCE_MATRIX.json']
paths += [base/f'S15-{g}-support-{s}-fec8af0.json' for g in ('temporal','lifecycle-trading') for s in ('selection','draft')]
prior=repo/'status/codex/productization/S15/scoped-source-support-fec8af0'
paths += [prior/f'S15-{g}-support-{s}-fec8af0.json' for g in ('strategy','cloud','data-research') for s in ('selection','draft')]
paths += [base/(stem+suffix) for stem in ('S15-tactical-owner-target-reason-NORMAL','S15-tactical-owner-target-reason-MUTATION_CONTROL') for suffix in ('.json','.log')]
paths.append(base/'s15_tactical_owner_acceptance_cases.py')
def bind():return {p.relative_to(base.parent).as_posix():'sha256:'+hashlib.sha256(read_local(p.parent,p.name,8*1024*1024)).hexdigest() for p in paths}
before=bind();source_before=revision_fact(repo,None,False);impl_before=_revision();started=datetime.now(timezone.utc).isoformat()
raw=base/(label+'.owned.raw');log=base/(label+'.log');report=base/(label+'.json')
assert not any(p.exists() for p in (raw,log,report))
with raw.open('xb') as stream:
    owned=spawn_owned([sys.executable,'-m','unittest','test_s15_owner_temporal_retention','-v'],cwd=base,
        env=dict(os.environ,PYTHONPATH=str(repo/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),
        limits=ResourceLimits(30),stdout=stream,stderr=stream)
    code=owned.wait(timeout=40)
finished=datetime.now(timezone.utc).isoformat()
content=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo);raw.unlink();log.write_text(content,encoding='utf-8',newline='\n')
result=parse_result(content,returncode=code);after=bind();source_after=revision_fact(repo,None,False);impl_after=_revision()
facts=dict(**result.__dict__,exit_code=code,tree_reaped=owned.termination_report.reaped,started_at_utc=started,finished_at_utc=finished,
    harness_binding='BEFORE_AND_AFTER_EXECUTION',input_sha256_before=before,input_sha256_after=after,source_before=source_before,source_after=source_after,
    implementation_hash_before=impl_before,implementation_hash_after=impl_after,log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest(),
    scope='S15_OWNER_TEMPORAL_RETENTION_TOOLING_ONLY;NOT_REQUIREMENT_OR_PRODUCT_ACCEPTANCE')
facts['passed']=result.passed and result.tests_run==7 and owned.termination_report.reaped and before==after and source_before==source_after and impl_before==impl_after
report.write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in facts.items() if not k.startswith('input_')}));raise SystemExit(0 if facts['passed'] else 1)
