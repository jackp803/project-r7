"""Explicit synthetic local-folder/native research verification; no trading."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib, json, os
from pathlib import Path
import subprocess, sys
project = Path(__file__).resolve().parent.parent
repo = project / 'workspaces/project-r7-productization-master-20261002'
sys.path[:0] = [str(repo), str(repo / 'src')]
from application.local_owners import LocalOwners
from application.platform.processes import ResourceLimits, spawn_owned, terminate_owned
from application.platform.distribution import verify_distribution
from application.platform.supervision import config_hash
from application.datasets.catalog import canonical, digest
from tests.application.test_local_owner_composition import LocalOwnerCompositionTests
def stamp(): return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
package = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).absolute()
if output.exists() or output.is_relative_to(repo): raise ValueError('Fresh project artifact root required')
output.mkdir(parents=True)
identity = verify_distribution(package)
executable = package / json.loads((package / 'distribution.json').read_bytes())['entrypoint']
case = LocalOwnerCompositionTests(methodName='test_absent_local_selection_leaves_research_cloud_and_runtime_unconfigured')
case.setUp()
case.base = output
case.root, case.cloud = output / '合成 本機 資料', output / '模擬 同步 暫存'
case.root.mkdir(); case.cloud.mkdir()
case.config = replace(case.config, product_instance_id='native-research-probe-fixture', local_data_root=case.root,
                      cloud_root=case.cloud, database_path=case.root / 'canonical.sqlite3')
case.selection = case.root / 'owner-selections.json'
case.clock = lambda: datetime.now(timezone.utc)
def compose_new_synthetic_local_inputs():
    # Generate new unexecuted LOCAL_RESEARCH test inputs. Never rewrite a
    # previously executed FIXTURE journal, result, consent or financial evidence.
    if case.config.database_path.exists(): raise ValueError('Fresh synthetic owner store required')
    values = {}
    for name in ('dataset','split','cost','risk'):
        path = case.root / (name + '.json')
        value = json.loads(path.read_bytes())
        value['namespace'] = 'LOCAL_RESEARCH'
        path.write_text(canonical(value),encoding='utf-8')
        values[name] = value
    for name in ('research','robustness'):
        path = case.root / (name + '.json')
        value = json.loads(path.read_bytes())
        value.update(namespace='LOCAL_RESEARCH',split_policy_hash=digest(canonical(values['split']).encode()),
                     cost_policy_hash=digest(canonical(values['cost']).encode()))
        path.write_text(canonical(value),encoding='utf-8')
    return LocalOwners(case.config, namespace='LOCAL_RESEARCH', clock=case.clock)
case.compose = compose_new_synthetic_local_inputs
report = dict(profile='r7-native-selected-synthetic-research-probe-v0.2', identity=identity, passed=False,
    fixture='SYNTHETIC_DATA_AND_LOCAL_FOLDER_ONLY', namespace='LOCAL_RESEARCH', cloud='LOCAL_FOLDER_SIMULATION',
    actual_provider_requests=0, credentials='NONE', capital='NONE', trading_runtime='NOT_STARTED',
    paper='NOT_STARTED', live='NOT_STARTED', github_compute='NOT_USED', product_path='EMPTY', pythonpath='UNSET')
owned = None
try:
    owners = case.configured()
    with owners.inbox_factory() as inbox: summary = inbox.scan_once(case.clock())
    if summary.accepted != 1: raise ValueError('Synthetic native input intake did not accept exactly one subject')
    revision = owners.queue.selected_submission_revision('native-owner-fixture','selected-fixture')
    queued = owners.queue.enqueue('native-owner-fixture','selected-fixture','native-probe-enqueue',revision,actor='synthetic-fixture-owner')
    profile = output / '研究 設定.json'
    settings = {key:str(value) if isinstance(value,Path) else value for key,value in asdict(case.config).items()}
    profile.write_text(json.dumps(settings,ensure_ascii=False),encoding='utf-8')
    cwd = output / '空白 工作 目錄'; cwd.mkdir()
    env = {key:os.environ[key] for key in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if key in os.environ}
    env.update(PATH='',PYTHONUTF8='1')
    log = output / 'selected-native-worker.log'
    report.update(started_at_utc=stamp(), config_hash=config_hash(case.config),
                  config_file_sha256='sha256:'+hashlib.sha256(profile.read_bytes()).hexdigest(), run_id=queued['run_id'])
    with log.open('xb') as stream:
        owned = spawn_owned([str(executable),'research-worker','--config',str(profile),'--once'],cwd=cwd,
                            limits=ResourceLimits(90),stdout=stream,stderr=subprocess.STDOUT,env=env)
        code = owned.wait()
    report.update(finished_at_utc=stamp(),exit_code=code,tree_reaped=owned.termination_report.reaped,
                  log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest())
    result = json.loads(log.read_text(encoding='utf-8'))
    job = owners.queue.get(queued['run_id'])
    report.update(worker_result=result,actual_job=job,actual_evidence=owners.queue.evidence_view(queued['run_id']))
    report['passed'] = code == 0 and result['status'] == 'JOB_FINISHED' and result['tree_reaped'] and job['state'] == 'COMPLETE'
finally:
    if owned is not None:
        report['tree_reaped'] = terminate_owned(owned,deadline_seconds=5).reaped
    case.doCleanups()
    (output/'native-selected-research.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(passed=report['passed'],job_state=report.get('actual_job',{}).get('state'),
                      outcome=report.get('actual_job',{}).get('outcome')),ensure_ascii=False))
raise SystemExit(0 if report['passed'] else 2)
