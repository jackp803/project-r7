"""APPLIED; NOT_EXECUTED. Supplemental B03/M04/F11 only, outside fixed receipt.
Root must review/apply after owning native03 stops. No provider or old auth access.
"""
import argparse
from contextlib import ExitStack, closing
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sqlite3
import sys
import time

BASE=Path(__file__).resolve().parent
PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
REVISION='3ae6460c69a8a8f90588c396b819af7079e7546d'
SUPPORT_HASH='sha256:e9bae453af1e9dd694b198f1c3edabaec39846228d555755de69ab9475f1e54a'

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        while chunk:=source.read(1024*1024):h.update(chunk)
    return 'sha256:'+h.hexdigest()

def utc():return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
def require(value,message):
    if not value:raise ValueError(message)


def capture_native_proof(path,expected):
    from application.paper.qualification import artifact_bytes
    require(path.name=='native-observations.json','Only original public native proof allowed')
    raw=artifact_bytes(path.parent,path.name)
    require('sha256:'+hashlib.sha256(raw).hexdigest()==expected,'Same captured public proof commitment differs')
    return raw,json.loads(raw)


def run(args):
    require(os.name=='nt','Windows-only supplemental draft')
    require(args.output.is_absolute() and not args.output.exists(),'Fresh absolute external output required')
    require(args.output.parent==BASE and args.paper_proof.is_relative_to(PROJECT) and args.pins.is_relative_to(BASE),'Exact ART child output and project-local public proof required')
    # Pin the fixed public reference document BEFORE following any source ref.
    require(args.pins==BASE/'b03-m04-f11-supplement-source-pins.unapplied.json','Exact reviewed pins path required')
    sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
    from application.paper.qualification import artifact_bytes
    pins_raw=artifact_bytes(BASE,args.pins.name)
    require('sha256:'+hashlib.sha256(pins_raw).hexdigest()=='sha256:23fcbbf875a250e9e3460293f977e91bc261515c09c49d5212b4bce9208a3d5d','Exact reviewed pins bytes required')
    pins=json.loads(pins_raw)
    reviewed_refs=frozenset((
        'tools/verify_paper_product.py','tools/native_console.py','src/application/fixtures/temporal.py',
        'src/application/research/worker.py','src/application/control_api/owner_services.py',
        'src/application/control_api/app.py','src/application/cloud/publication_history.py',
        'src/application/cloud/feedback.py','src/storage/paper_process.py','src/storage/runtime.py',
        'src/storage/runtime_models.py','src/storage/_paper_runtime.py','src/storage/trading_feedback.py',
        'src/position/trade_result.py','src/execution/funding.py','src/application/platform/processes.py',
        'src/application/platform/supervision.py'))
    require(len(pins['source_files'])==len(reviewed_refs) and {row['path'] for row in pins['source_files']}==reviewed_refs,'Exact reviewed relative source inventory required')
    def source_guard():
        require(pins['revision']==REVISION,'Exact current subject required')
        for row in pins['source_files']:
            require(digest(ROOT/row['path'])==row['sha256'],'Pinned source changed')
        require(digest(BASE/'verify_plat08_crossversion_native.py')==SUPPORT_HASH,'Reviewed support changed')
    source_guard()
    sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
    support_path=BASE/'verify_plat08_crossversion_native.py'
    spec=importlib.util.spec_from_file_location('reviewed_supplement_support',support_path)
    support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)
    from verify_paper_product import NativeExpiryFlow
    from application.config import load_config
    from application.paper.qualification import artifact_bytes
    from application.platform.private_files import create_private_directory,write_private_new
    from application.platform.processes import terminate_owned
    from application.platform.scope_lock import ProcessScopeLock,operational_lock_root
    from application.platform.supervision import PROCESS_ROLES,process_health,config_hash,_local_path
    from storage.paper_process import PaperProcessJournal
    from storage.runtime import PaperRuntimeJournal
    from storage._paper_runtime import _PaperRuntimeStore
    from strategy.v02.capabilities import _source_revision
    identity=support.subject(args.package,args.build_result,args.build_sha256,args.manifest_sha256,args.exe_sha256,REVISION)
    require(_source_revision(ROOT/'src')==identity['implementation_hash'],'Actual source input owner differs')
    create_private_directory(args.output)
    report=dict(status='NOT_RUN',passed=False,execution='SUPPLEMENTAL_NATIVE_AND_READONLY_AUDIT_OUTSIDE_FIXED_RECEIPT',
        revision=REVISION,identity=identity,started_at_utc=utc(),finished_at_utc=None,records=[],errors=[],cleanup_errors=[],
        provider_requests=0,private_requests=0,financial_authority='NONE',paper='NO_NEW_PAPER_RUN',
        owning_receipt_membership='NONE',helper_hash=digest(Path(__file__)),pins_hash='sha256:'+hashlib.sha256(pins_raw).hexdigest())
    flows=[];proof_raw=None
    def guard():
        source_guard()
        require(_source_revision(ROOT/'src')==identity['implementation_hash'],'Source producer changed')
        require(support.subject(args.package,args.build_result,args.build_sha256,args.manifest_sha256,args.exe_sha256,REVISION)==identity,'Native subject changed')
    class Flow(NativeExpiryFlow):
        _spawn=support.LocalDiagnosticControl._spawn
        command=support.LocalDiagnosticControl.command
        def __init__(self,leaf):
            super().__init__(args.package,args.output/leaf,'intake-faults',expected_identity=identity)
            self.owned=[]
            self.observation.pop('passed',None)
            self.observation['result_scope']='OBSERVATIONS_ONLY;OUTER_RESULT_DECIDES'
        def start_control(self,label):
            try:return super().start_control(label)
            finally:
                if self.control is not None and all(self.control is not p for p in self.owned):
                    require(len(self.owned)<32,'Finite actual child registry required')
                    self.owned.append(self.control)
    def record(rid,start,config,facts,commands,assertion):
        report['records'].append(dict(requirement_id=rid,status='NOT_RUN',test_ids=[assertion],command=commands,
            source_revision=REVISION,spec_revision=pins['spec_revision'],environment_class='CURRENT_WINDOWS_SUPPLEMENTAL_FIXTURE_NATIVE',
            os_version=platform.version(),architecture=platform.machine(),runtime_versions={
                'wrapper_python':dict(version=platform.python_version(),sha256=digest(Path(sys.executable)),scope='LOCAL_EXECUTION_TOOL_ONLY'),
                'native_product':dict(identity=identity,scope='ACTUAL_FIXED_NATIVE_COMMANDS' if rid!='F11' else 'STOPPED_NATIVE_PRODUCED_STORE_READONLY_AUDIT')},
            config_hash=config_hash(config),started_at_utc=start,finished_at_utc=utc(),exit_code=None,
            passed=0,failed=0,errors=0,skipped=0,artifact_refs=[],artifact_hashes={},
            limitations=['Outside fixed owning receipt; no full current PQR or Ubuntu/cloud/provider/LIVE/real-forward credit.',
                'Actual helper interval; no per-child OS argv trace. Fresh disposable local test enrollment only for intake cases.',
                'F11 reads existing stopped actual native producer facts; wrapper itself is not a second native execution.'],facts=facts))
    def package_bytes(flow):
        folder=flow.cloud/'inbox/strategies'/flow.generated['submission_id']
        return folder,artifact_bytes(flow.cloud,(folder/'manifest.json').relative_to(flow.cloud).as_posix()),artifact_bytes(flow.cloud,(folder/'strategy.json').relative_to(flow.cloud).as_posix())
    try:
        # B03: do not scan until original manifest is absent. Payload is authored,
        # not manufactured financial data; only its publication order changes.
        start=utc();flow=Flow('b03-manifest-last');flows.append(flow);flow.setup()
        folder,manifest,payload=package_bytes(flow);(folder/'manifest.json').unlink()
        before=flow.scan()[2]
        require(before['accepted']==0 and not flow.view('strategies')['items'],'Payload-only unexpectedly accepted')
        write_private_new(folder/'manifest.json',manifest)
        body,receipt,summary=flow.scan();accepted=flow.submission()['receipt']
        require(summary['accepted']==1 and accepted is not None,'Original manifest-last not accepted exactly once')
        revision=flow.view('overview')['scan_revision']
        require(flow.scan(body=body)[1]==receipt and flow.view('overview')['scan_revision']==revision,'Exact command replay changed effects')
        replay=flow.scan()[2]
        require(replay['idempotent']==1 and flow.submission()['receipt']==accepted and len(flow.view('strategies')['items'])==1,'Immutable submission replay duplicated effects')
        flow.stop_control()
        record('B03',start,load_config(flow.config),dict(payload_only_summary=before,manifest_last_summary=summary,
            immutable_receipt=accepted,replay_summary=replay,manifest_sha256='sha256:'+hashlib.sha256(manifest).hexdigest()),flow.commands,
            'SUPPLEMENTAL_B03_ACTUAL_PAYLOAD_ONLY_THEN_ORIGINAL_MANIFEST_LAST_SINGLE_INTAKE')
        guard()
        # M04: separate fresh store, original manifest present/payload missing.
        start=utc();flow=Flow('m04-partial-single-processing');flows.append(flow);flow.setup()
        folder,manifest,payload=package_bytes(flow);(folder/'strategy.json').unlink()
        incomplete=flow.scan()[2]
        require(flow.submission()['latest_observation']['state']=='INCOMPLETE_SYNC' and flow.submission()['receipt'] is None,'Actual partial state missing')
        write_private_new(folder/'strategy.json',payload)
        time.sleep(5.1)  # Existing bounded native fixture retry backoff, not a policy override.
        body,scan_receipt,summary=flow.scan();accepted=flow.submission()['receipt']
        require(summary['accepted']==1 and accepted is not None,'Same repaired submission not accepted')
        enqueue_body,enqueue_receipt,job_id=flow.enqueue();worker=flow.research()
        job=flow.view('research/runs/'+job_id)['payload']
        require(job['state']=='COMPLETE' and job['owner_run_id'] and job['outcome'] is not None,'Same actual repaired research outcome missing')
        queued=flow.command('queue-same-owner-report',['queue-research-feedback','--config',flow.config,'--run-id',job['owner_run_id'],'--namespace','FIXTURE'])
        require(queued['status']=='FEEDBACK_QUEUED','Actual normal report queue failed')
        publications=flow.view('research/runs/'+job_id+'/publications')
        require(publications['total']==1 and publications['items'][0]['operation_id']==queued['operation_id'],'Actual same-job validated report outbox missing')
        job_before=job
        require(flow.request('POST','/api/v1/research/runs',enqueue_body,expected=202)==enqueue_receipt,'Exact enqueue retry changed receipt')
        require(flow.scan(body=body)[1]==scan_receipt,'Exact scan retry changed receipt')
        require(flow.scan()[2]['idempotent']==1 and flow.submission()['receipt']==accepted,'Same submission replay changed intake')
        idle=flow.command('research-no-second-job',['research-worker','--config',flow.config,'--once'],timeout=90)
        require(idle['status']=='IDLE','Replay introduced another research job')
        require(flow.view('research/runs')['total']==1 and flow.view('research/runs/'+job_id)['payload']==job_before,'Replay changed actual job/outcome')
        require(flow.view('research/runs/'+job_id+'/publications')==publications,'Replay changed report count/content')
        flow.stop_control()
        record('M04',start,load_config(flow.config),dict(submission_id=flow.generated['submission_id'],incomplete=incomplete,
            accepted_receipt=accepted,job_id=job_id,owner_run_id=job['owner_run_id'],terminal_state=job['state'],
            outcome=job['outcome'],actual_native_child_reaped=worker['tree_reaped'],report_publications=publications,
            exact_replay_stable=True,second_worker_status=idle['status']),flow.commands,
            'SUPPLEMENTAL_M04_SAME_PARTIAL_SUBMISSION_ACTUAL_TERMINAL_RESEARCH_REPORT_SINGLE_REPLAY')
        guard()
        # F11: existing proof/config/run selected by root after original PQR03 stop.
        # No enroll/login, journal factory, migration, producer replay or DB write.
        start=utc()
        proof_raw,proof=capture_native_proof(args.paper_proof,args.paper_proof_sha256)
        require(proof['identity']==identity,'Existing actual native proof subject differs')
        positives=[row for row in proof['observations'] if row.get('scenario')=='positive' and row.get('passed') is True and row.get('canonical_trades')==1]
        require(len(positives)==1 and any(row.get('run_id')==args.paper_run_id for row in positives[0]['browser']),'Exact genuine closed positive run required')
        config=load_config(args.paper_config)
        require(config_hash(config)==args.paper_config_hash,'Explicit original Paper config commitment differs')
        path=config.database_path
        _local_path(path);require(path.is_file() and path.stat().st_nlink==1,'Actual local single-link canonical source required')
        with ExitStack() as locks:
            for role in PROCESS_ROLES:
                locks.enter_context(ProcessScopeLock(role+':'+config.product_instance_id,lock_root=operational_lock_root(config)))
                require(process_health(config,role).get('state')!='RUNNING','Original native role still running')
            require(not any(path.with_name(path.name+suffix).exists() for suffix in ('-wal','-shm','-journal')),'Quiescent complete main database required; preserve sidecars, no checkpoint')
            original_config_bytes=digest(args.paper_config)
            sources=[path]
            before={p.name:digest(p) for p in sources};end=time.monotonic()+15
            with closing(sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True,timeout=1)) as db:
                db.row_factory=sqlite3.Row;db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,32*1024*1024)
                db.set_progress_handler(lambda:int(time.monotonic()>=end),1000)
                db.execute('PRAGMA query_only=ON');db.execute('PRAGMA trusted_schema=OFF');db.execute('PRAGMA temp_store=MEMORY')
                closed=PaperProcessJournal(db).recover(args.paper_run_id)
                require(closed.binding['namespace']=='FIXTURE' and closed.binding['implementation_hash']==identity['implementation_hash'],'Actual native original binding differs')
                position=closed.state['runtime']['position'];require(Decimal(position['actual_quantity'])==0,'Original Paper not flat')
                graph=PaperRuntimeJournal(_PaperRuntimeStore(db)).recover(position_id=position['position_id'])
                require(graph.status=='READY' and graph.trade_result is not None and graph.current_position_projection.payload['lifecycle_state']=='CLOSED','Actual canonical closed graph missing')
                result=graph.trade_result.payload
                require(len(closed.state['runtime']['closed_trades'])==1 and result==closed.state['runtime']['closed_trades'][0],'Checkpoint/canonical exact result differs')
                fills={item.canonical_id:item for item in graph.fills}
                ids=result['entry_fill_ids']+result['exit_fill_ids']
                require(len(ids)==len(set(ids)) and set(ids)==set(fills),'Actual result fill closure differs')
                fees=sum((Decimal(fills[key].payload['fee']) for key in ids),Decimal(0))
                require(Decimal(result['total_fees'])==fees,'Persisted exact fill fee sum differs')
                evidence=[item for item in graph.funding_evidence if item.canonical_id==result['funding_evidence_id']]
                require(len(evidence)==1,'Exact persisted funding allocation missing');funding=evidence[0].payload
                require(funding['trade_plan_id']==graph.trade_plan_id and funding['position_id']==position['position_id'] and funding['interval_start']==result['opened_at'] and funding['interval_end']==result['closed_at'],'Exact funding position/interval differs')
                require(funding['status']==result['funding_evidence_status'] and funding['source_kind']=='PAPER_MODEL','Persisted Paper funding provenance differs')
                require(funding['interval_semantics']=='START_INCLUSIVE_END_EXCLUSIVE' and funding['cost_currency']=='USDT' and datetime.fromisoformat(funding['source_complete_through'].replace('Z','+00:00'))>=datetime.fromisoformat(funding['interval_end'].replace('Z','+00:00')),'Actual allocation interval/coverage differs')
                if funding['status']=='ZERO_CONFIRMED':
                    require(Decimal(funding['funding_cost'])==0 and funding['source_record_count']==0 and 'funding_cost' not in result,'Actual ZERO_CONFIRMED semantics differ')
                else:require(Decimal(result['funding_cost'])==Decimal(funding['funding_cost']),'Persisted included funding differs')
                require(Decimal(result['net_pnl'])==Decimal(result['gross_pnl'])-fees-Decimal(funding['funding_cost']),'Persisted canonical signed cost equation differs')
                facts=dict(run_id=args.paper_run_id,position_id=position['position_id'],trade_result_id=graph.trade_result.canonical_id,
                    trade_result_payload_hash=graph.trade_result.payload_hash,total_fees=result['total_fees'],actual_fill_fee_sum=str(fees),
                    fill_ids=ids,funding_evidence_id=evidence[0].canonical_id,funding_payload_hash=evidence[0].payload_hash,
                    funding_status=funding['status'],funding_cost=funding['funding_cost'],source_kind=funding['source_kind'],
                    interval_start=funding['interval_start'],interval_end=funding['interval_end'],source_record_count=funding['source_record_count'],
                    no_broker_ledger_claim=True,original_proof_hash='sha256:'+hashlib.sha256(proof_raw).hexdigest())
            after={p.name:digest(p) for p in sources}
            require(before==after and digest(args.paper_config)==original_config_bytes and artifact_bytes(args.paper_proof.parent,args.paper_proof.name)==proof_raw and not any(path.with_name(path.name+suffix).exists() for suffix in ('-wal','-shm','-journal')) and time.monotonic()<end,'Readonly source bytes/sidecars changed or deadline exceeded')
        record('F11',start,config,facts,[dict(command='QUERY_ONLY_TYPED_OWNER_RECOVERY',native_command=False)],
            'SUPPLEMENTAL_F11_EXISTING_STOPPED_NATIVE_CANONICAL_FEES_FUNDING_ALLOCATION_AUDIT')
        report['completed_assertions']=True
    except Exception as error:report['errors'].append(type(error).__name__)
    finally:
        for flow in flows:
            try:flow.stop_control()
            except Exception as error:report['cleanup_errors'].append(type(error).__name__)
            for owned in flow.owned:
                try:
                    reap=terminate_owned(owned,deadline_seconds=5)
                    flow.observation.setdefault('owned_cleanup',[]).append(dict(pid=owned.process.pid,reaped=reap.reaped))
                    if not reap.reaped:raise ValueError('Owned tree unreaped; retain handle')
                except Exception as error:report['cleanup_errors'].append(type(error).__name__)
            try:
                if flow.control_stream is not None:flow.control_stream.close();flow.control_stream=None
                flow.persist()
            except Exception as error:report['cleanup_errors'].append(type(error).__name__)
        try:
            guard();require(digest(Path(__file__))==report['helper_hash'],'Helper changed')
            require(artifact_bytes(BASE,args.pins.name)==pins_raw,'Reviewed public pins changed')
            if proof_raw is not None:require(artifact_bytes(args.paper_proof.parent,args.paper_proof.name)==proof_raw,'Captured public proof changed')
        except Exception as error:report['errors'].append('FINAL_GUARD:'+type(error).__name__)
        report['passed']=bool(report.get('completed_assertions')) and not report['errors'] and not report['cleanup_errors']
        report['status']='PASS' if report['passed'] else 'FAIL';report['finished_at_utc']=utc()
        refs={}
        for flow in flows:
            for path in flow.output.glob('*.json'):
                if path.name=='product.json':continue
                refs[path.relative_to(PROJECT).as_posix()]=digest(path)
            for path in flow.output.glob('*.log'):refs[path.relative_to(PROJECT).as_posix()]=digest(path)
        if proof_raw is not None:refs[args.paper_proof.relative_to(PROJECT).as_posix()]='sha256:'+hashlib.sha256(proof_raw).hexdigest()
        refs[args.pins.relative_to(PROJECT).as_posix()]='sha256:'+hashlib.sha256(pins_raw).hexdigest()
        for row in report['records']:
            row.update(status='PASS' if report['passed'] else 'NOT_RUN',exit_code=0 if report['passed'] else None,
                passed=1 if report['passed'] else 0,artifact_refs=sorted(refs),artifact_hashes=refs)
        write_private_new(args.output/'supplemental-assertions.json',(json.dumps(report,indent=2)+'\n').encode())
    return 0 if report['passed'] else 2


def main():
    p=argparse.ArgumentParser()
    for name in ('package','build-result','output','pins','paper-proof','paper-config'):
        p.add_argument('--'+name,type=lambda value:Path(value).absolute(),required=True)
    for name in ('build-sha256','manifest-sha256','exe-sha256','paper-run-id','paper-config-hash','paper-proof-sha256'):p.add_argument('--'+name,required=True)
    return run(p.parse_args())
if __name__=='__main__':raise SystemExit(main())
