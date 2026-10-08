"""Fixed complete local source qualification for the independent PAPER owner."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, os, re, stat, subprocess, sys, threading

BASE=Path(__file__).resolve().parent
REPO=BASE.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(REPO/'src'))
from application.qualification import run_qualification, revision_fact
from application.platform.resources import _memory
from strategy.v02.capabilities import _revision
from application.datasets.catalog import read_local
from local_windows_qualification_awake import awake_request

def stamp(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def sha(raw): return 'sha256:'+hashlib.sha256(raw).hexdigest()
def inputs():
    names=subprocess.check_output(['git','ls-files','--','src','tests','tools','packaging','ui','docs','contracts'],
        cwd=REPO,text=True,encoding='utf-8').splitlines()
    result={}
    for name in names:
        path=REPO/name
        for ancestor in (*reversed(path.parents),path):
            info=ancestor.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
                raise ValueError('Regular exact source input required')
        result[name]=sha(path.read_bytes())
    return result

def main():
    revision=sys.argv[1]
    if not re.fullmatch('[0-9a-f]{40}',revision): raise ValueError('Exact revision required')
    output=BASE/f'r7-productization-S12-storage-memory-retry-qualified-{revision[:7]}'
    if output.exists(): raise ValueError('Fresh output required')
    before=revision_fact(REPO,revision,True)
    captured=inputs(); implementation=_revision(); launcher=sha(Path(__file__).read_bytes())
    helper=BASE/'local_windows_qualification_awake.py'
    helper_before=sha(read_local(helper.parent,helper.name,1024**2))
    config=dict(suites=['all'],include_focused=True,require_clean=True,timeout_seconds=900,expected_revision=revision)
    started=stamp(); samples=[]; stop=threading.Event()
    def monitor():
        while not stop.is_set():
            total,available=_memory()
            samples.append(dict(observed_at_utc=stamp(),physical_memory_bytes=total,available_memory_bytes=available,
                existing_admission_minimum_bytes=max(2*1024**3,total*15//100)))
            stop.wait(2)
    thread=threading.Thread(target=monitor,daemon=True); thread.start()
    try:
        with awake_request() as awake:
            report=run_qualification(REPO,output,**config)
    finally:
        stop.set();thread.join(5)
        if thread.is_alive(): raise ValueError('Memory monitor cleanup not confirmed')
    after=revision_fact(REPO,revision,True)
    helper_after=sha(read_local(helper.parent,helper.name,1024**2))
    unchanged=inputs()==captured and _revision()==implementation and sha(Path(__file__).read_bytes())==launcher and helper_after==helper_before
    assert awake['restored'] is True
    context=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',spec_baseline='r7-product-v0.2',
        spec_revision='9fd277798b1c51d1bc79b29a61bec81b552efeb1',started_at_utc=started,finished_at_utc=stamp(),
        source_before=before,source_after=after,implementation_hash=implementation,configuration=config,
        awake_request=awake,awake_helper_sha256_before=helper_before,awake_helper_sha256_after=helper_after,
        prior_attempt='083fd10_FIRST_ATTEMPT_HOST_SLEEP;SECOND_ATTEMPT_TWO_ACTUAL_MEMORY_PRESSURE_ERRORS;NO_QUALIFICATION_CREDIT;UNCHANGED_THRESHOLDS',
        config_hash=sha(json.dumps(config,sort_keys=True,separators=(',',':')).encode()),
        launcher_sha256=launcher,source_input_hashes=captured,inputs_unchanged=unchanged,
        memory_monitor_joined=True,real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
        scope='COMPLETE_SOURCE_LF_FP_REGRESSION_WITH_INTERNAL_STORAGE_INCREMENT;SCOPED_WINDOWS_IDLE_SLEEP_REQUEST_ONLY',
        ordinary_native_paper='NOT_RUN',production_qualified_release_profile='PROPOSED_NOT_ACTIVE',
        real_cloud='NOT_RUN',real_forward='NOT_RUN',ubuntu24='NOT_RUN',ubuntu26='NOT_RUN')
    (output/'qualification-context.json').write_text(json.dumps(context,indent=2)+'\n',encoding='utf-8',newline='\n')
    (output/'hardware-observations.json').write_text(json.dumps(dict(scope='ACTUAL_HOST_SAMPLES_ONLY;NO_24GB_TARGET_CLAIM',samples=samples),indent=2)+'\n',encoding='utf-8',newline='\n')
    passed=report['passed'] and unchanged
    print(json.dumps(dict(passed=passed,tests_run=report['tests_run'],commands=len(report['commands']),
        input_files=len(captured),inputs_unchanged=unchanged)),flush=True)
    return 0 if passed else 1

if __name__=='__main__': raise SystemExit(main())
