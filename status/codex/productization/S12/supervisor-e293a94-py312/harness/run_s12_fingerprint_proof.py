from pathlib import Path
import hashlib,json,os,re,sys
base=Path(__file__).resolve().parent
repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.platform.processes import spawn_owned,ResourceLimits
from application.qualification import _sanitize,parse_result,revision_fact
label=sys.argv[1];assert re.fullmatch('[A-Za-z0-9_-]+',label)
paths=[Path(__file__),base/'test_s12_fingerprint_proof.py',base/'run_s12_fingerprint_remediation.py']
if (base/'s12_fingerprint_proof.py').exists():paths.append(base/'s12_fingerprint_proof.py')
capture=lambda:{p.name:'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
before=capture();source_before=revision_fact(repo,None,False)
raw=base/(label+'.owned.raw');log=base/(label+'.log');report=base/(label+'.json')
assert not any(p.exists() for p in (raw,log,report))
with raw.open('xb') as stream:
    owned=spawn_owned([sys.executable,'-m','unittest','test_s12_fingerprint_proof','-v'],cwd=base,
        env=dict(os.environ,PYTHONPATH=str(repo/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),
        limits=ResourceLimits(30),stdout=stream,stderr=stream)
    code=owned.wait(timeout=40)
text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo);raw.unlink();log.write_text(text,encoding='utf-8',newline='\n')
result=parse_result(text,returncode=code);after=capture();source_after=revision_fact(repo,None,False)
facts=dict(**result.__dict__,exit_code=code,tree_reaped=owned.termination_report.reaped,
    harness_binding='BEFORE_AND_AFTER_EXECUTION',input_sha256_before=before,input_sha256_after=after,
    source_before=source_before,source_after=source_after,
    log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest())
facts['passed']=result.passed and owned.termination_report.reaped and before==after and source_before==source_after
report.write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(facts));raise SystemExit(0 if facts['passed'] else 1)
