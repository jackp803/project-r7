from pathlib import Path
import hashlib,json,os,re,sys
base=Path(__file__).resolve().parent
repo=base.parent/'workspaces/project-r7-productization-master-20261002';sys.path.insert(0,str(repo/'src'))
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize,parse_result,revision_fact
from strategy.v02.capabilities import _revision
label=sys.argv[1];assert re.fullmatch('[A-Za-z0-9_-]+',label)
paths=[Path(__file__),base/'test_s15_execution_index_fec8af0.py',base/'build_s15_execution_index_fec8af0.py']
if (base/'s15_execution_index.py').exists():paths.append(base/'s15_execution_index.py')
bind=lambda:{p.name:'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
before=bind();source_before=revision_fact(repo,None,False);implementation_before=_revision()
raw=base/(label+'.owned.raw');log=base/(label+'.log');report=base/(label+'.json')
assert not any(p.exists() for p in (raw,log,report))
with raw.open('xb') as stream:
 owned=spawn_owned([sys.executable,'-m','unittest','test_s15_execution_index_fec8af0','-v'],cwd=base,
  env=dict(os.environ,PYTHONPATH=str(repo/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),
  limits=ResourceLimits(30),stdout=stream,stderr=stream);code=owned.wait(timeout=40)
text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo);raw.unlink();log.write_text(text,encoding='utf-8',newline='\n')
result=parse_result(text,returncode=code);after=bind();source_after=revision_fact(repo,None,False);implementation_after=_revision()
facts=dict(**result.__dict__,exit_code=code,tree_reaped=owned.termination_report.reaped,
 harness_binding='BEFORE_AND_AFTER_EXECUTION',input_sha256_before=before,input_sha256_after=after,
 source_before=source_before,source_after=source_after,
 implementation_hash_before=implementation_before,implementation_hash_after=implementation_after,
 log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest(),scope='S15_EXECUTION_INDEX_HARNESS_ONLY;NOT_REQUIREMENT_ACCEPTANCE')
facts['passed']=result.passed and result.tests_run==14 and owned.termination_report.reaped and before==after and source_before==source_after and implementation_before==implementation_after
report.write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in facts.items() if not k.startswith('input_')}));raise SystemExit(0 if facts['passed'] else 1)
