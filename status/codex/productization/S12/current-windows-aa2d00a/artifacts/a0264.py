"""Native ordinary coordinator idle/recovery only; no strategy/workflow permission.

Uses public init-profile/configure-paper with the original owning store/receipt.
Explicit SOFTWARE_IDLE serialization inputs never promote engineering research.
"""
from contextlib import closing
from datetime import datetime,timezone
import hashlib,json,os,re,sqlite3,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1];ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tools'),str(BASE),str(BASE.parent)]
from application.config import load_config,product_namespace
from application.datasets.catalog import canonical,read_local
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.supervision import config_hash,process_health
from application.platform.runtime_identity import read_runtime_identity
from application.paper.inventory import current_target,fixed_profile
from application.paper.producer import _guard
from application.qualification import _sanitize
from storage.paper_selection import open_paper_selections
from tools.verify_paper_product import PublicFixture,owns_pid
from tools.verify_headless_product import NativeHeadlessFlow,terminate_verified_pid,_token
from tests.product.test_paper_runtime_v02 import simulation_fixture
from tests.application.test_product_assessment_binding import risk_fixture
from tests.validation.test_paper_promotion_policy import policy_fixture
from local_windows_qualification_awake import awake_request

ROLES=('coordinator','control','research','runtime')
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()

def make_idle_view(output,data,config,operations,package,facts,report,guard):
    view=object.__new__(NativeHeadlessFlow)
    view.output=output;view.data=data;view.config=config;view.operations=operations
    view.executable=package/'R7.exe';view.package=package;view.identity=facts
    # This fixed redaction marker is never enrolled, sent or used for login.
    # Inherited command() requires a nonempty replacement input.
    view.password='R7_UNUSED_NON_CREDENTIAL_REDACTION_SENTINEL';view.sessions=[]
    view.commands=report['commands'];view.observation=report;view.guard=guard
    view.env={key:os.environ[key] for key in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if key in os.environ}
    view.env.update(PATH='',PYTHONUTF8='1')
    return view

def require_duplicate_denial(raw):
    if len(raw)>65536:raise ValueError('Bounded duplicate startup diagnostic required')
    lines=raw.decode('utf-8').strip().splitlines()
    value=json.loads(lines[-1]) if lines else {}
    if value.get('schema_version')!='r7-startup-diagnostic-v0.2' or value.get('error_kind')!='OWNER_SCOPE_BUSY':
        raise ValueError('Exact duplicate coordinator owner-scope diagnostic required')
    return value

def require_idle_runtime_summary(raw,generation):
    if len(raw)>65536:raise ValueError('Bounded ordinary idle runtime summary required')
    lines=raw.decode('utf-8').strip().splitlines();value=json.loads(lines[-1]) if lines else {}
    expected=dict(status='STOPPED',namespace='LOCAL_RESEARCH',mode='REAL_TIME',market_source='NOT_CONNECTED',
        request_accounting='COMPLETE',run_failures={},process_generation=generation,financial_authority='NONE',capital='NONE')
    if (not isinstance(value,dict) or any(value.get(key)!=item for key,item in expected.items())
            or any(type(value.get(key)) is not int or value[key]!=0 for key in ('provider_requests','provider_responses'))):
        raise ValueError('Actual same-generation idle zero-request runtime summary required')
    return value

def run(revision,attempt='first',idle_attempt='first'):
    from run_current_checkpoint import qualification_output
    if not re.fullmatch('[0-9a-f]{40}',revision) or not re.fullmatch('first|retry[0-9]{2}',idle_attempt):raise ValueError('Exact executable and fresh attempt required')
    qpath=qualification_output(revision,attempt);q=json.loads((qpath/'checkpoint.json').read_bytes())
    automatic=json.loads((BASE/('unattended-'+revision[:7]+'-first')/'checkpoint.json').read_bytes())
    portable=json.loads((BASE/('portable-'+revision[:7]+'-first')/'checkpoint.json').read_bytes())
    if not all(row.get('passed') is True and row.get('revision')==revision for row in (q,automatic,portable)):
        raise ValueError('Actual complete owning/portable/unattended prerequisite required')
    package=PROJECT/portable['installation_ref'];facts=verify_distribution(package);profile=fixed_profile(current_target())
    def guard():_guard(ROOT,revision,package,facts,profile)
    guard();original_path=qpath/'product.json';original=load_config(original_path);data=original.local_data_root
    if (automatic['owning_profile']['config_hash']!=config_hash(original) or automatic['identity']!=facts
            or portable['identity']!=facts or not original.diagnostic_only or original.paper_runtime_enabled):
        raise ValueError('Original actual diagnostic owning subject required')
    output=BASE/('ordinary-idle-'+revision[:7]+'-'+idle_attempt);create_private_directory(output)
    report=dict(revision=revision,identity=facts,passed=False,scope='NATIVE_ORDINARY_COORDINATOR_IDLE_RECOVERY_ONLY',
        helper_hash=sha(Path(__file__).read_bytes()),
        started_at=datetime.now(timezone.utc).isoformat(),commands=[],sessions=[],cases=[],
        qualification_attempt=attempt,idle_attempt=idle_attempt,workflow_authorized=False,operator_policies='UNSELECTED',policy_serializations='SOFTWARE_IDLE_TEST_ONLY',
        strategy_promotion='NONE',paper_runs='NONE',positive_paper_lifecycle='NOT_RUN',forward='NOT_STARTED',live='NOT_STARTED',
        additional_public_requests=0,cumulative_public_requests=8,private_requests=0,credentials='NONE',
        provider_mutation=0,capital='NONE',github_compute='NOT_USED',host_settings='UNCHANGED',master='IN_PROGRESS')
    view=make_idle_view(output,data,output/'ordinary-idle-profile.json',output/'operations.json',package,facts,report,guard)
    baseline_original=sha(original_path.read_bytes());baseline_inputs={};selected_generation=None
    def rows(query,parameters=()):
        with closing(sqlite3.connect(original.database_path.as_uri()+'?mode=ro',uri=True)) as db:
            db.row_factory=sqlite3.Row
            return [dict(row) for row in db.execute(query,parameters)]
    baseline_lifecycle=rows('SELECT strategy_id,strategy_version,current_lifecycle_state FROM strategy_versions ORDER BY strategy_id,strategy_version')
    def idle():
        from application.paper.public_market import load_market_profile
        if load_market_profile(load_config(view.config)) is not None:raise ValueError('Idle verification must not select a public acquisition feed')
        if rows('SELECT run_id FROM paper_process_runs LIMIT 1'):raise ValueError('Idle verification started a Paper run')
        if rows('SELECT strategy_id,strategy_version,current_lifecycle_state FROM strategy_versions ORDER BY strategy_id,strategy_version')!=baseline_lifecycle:
            raise ValueError('Idle verification changed engineering strategy lifecycle')
        with open_paper_selections(original.database_path) as reader:selection=reader.current()
        if selection is None or selection.as_dict()['owner']['workflow_authorized'] is not False:
            raise ValueError('Idle selection must never acquire workflow authority')
        if selected_generation is not None and selection.generation!=selected_generation:raise ValueError('Idle selection generation changed')
        if sha(original_path.read_bytes())!=baseline_original:raise ValueError('Original qualified configuration changed')
        for ref,commitment in baseline_inputs.items():
            if sha(read_local(data,ref,65536))!=commitment:raise ValueError('Software-only idle policy changed')
    def snapshot(owned):
        values={role:PublicFixture.health(view,role,owned) for role in ROLES}
        current=read_runtime_identity(load_config(view.config))
        if any(current.identity[key]!=values['runtime'][key] for key in ('pid','generation','process_generation_id','config_hash')):
            raise ValueError('Actual ordinary runtime identity differs')
        idle();return values
    def ready(owned,before=None,runtime_only=False):
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            if owned.process.poll() is not None:raise ValueError('Actual ordinary coordinator exited before readiness')
            try:
                values=snapshot(owned)
                if before is not None:
                    if runtime_only:
                        if any(_token(values[role])!=_token(before[role]) for role in ROLES if role!='runtime'):raise ValueError('Unaffected ordinary role changed')
                        changed=('runtime',)
                    else:changed=ROLES
                    if any(values[role]['generation']<=before[role]['generation'] or values[role]['process_generation_id']==before[role]['process_generation_id'] for role in changed):
                        raise ValueError('Actual ordinary successor generation missing')
                return values
            except (ValueError,RuntimeError,OSError,sqlite3.Error):time.sleep(.15)
        raise ValueError('Bounded ordinary idle readiness not observed')
    def stop(session,before,label):
        receipt=view.command(label,['stop-product','--config',view.config,'--role','coordinator'])
        if receipt.get('status')!='COOPERATIVE_STOP_REQUESTED' or receipt.get('process_generation_id')!=before['coordinator']['process_generation_id']:
            raise ValueError('Exact ordinary coordinator stop required')
        owned=session['owned'];code=owned.wait(timeout=20);session['stream'].flush()
        last=json.loads(session['log'].read_bytes().strip().splitlines()[-1])
        if (code!=0 or not owned.termination_report.reaped or last.get('all_owned_trees_reaped') is not True
                or last.get('status')!='STOPPED' or last.get('financial_authority')!='NONE'
                or last.get('exposure_status')!='NOT_ASSERTED' or last.get('host_settings')!='UNCHANGED'
                or set(last.get('roles',{}))!={'control','research','runtime'} or last.get('schedule') is not None
                or any(row.get('status')!='STOPPED' or row.get('forced_stop') is not False or row.get('exit_code')!=0 or row.get('tree_reaped') is not True for row in last['roles'].values())):
            raise ValueError('Graceful ordinary idle stop/reaping not confirmed')
        session['result']=last;view._close_session(session)
        service_logs=[]
        for role,state in last['roles'].items():
            launches=state['launches']
            if type(launches) is not int or not 1<=launches<=3:raise ValueError('Bounded actual service launch inventory required')
            for number in range(1,launches+1):
                ref='worker-logs/coordinator-'+before['coordinator']['process_generation_id']+'-'+role+'-'+str(number)+'.log'
                raw=read_local(data,ref,4*1024*1024)
                if role=='runtime' and number==launches:
                    report.setdefault('actual_idle_runtime_summaries',[]).append(require_idle_runtime_summary(raw,before['runtime']['generation']))
                retained='service-'+session['label']+'-'+role+'-'+str(number)+'.log'
                safe=_sanitize(raw.decode('utf-8',errors='replace'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').encode()
                write_private_new(output/retained,safe)
                service_logs.append(dict(original_ref=ref,original_hash=sha(raw),retained_ref=retained,retained_hash=sha(safe)))
        report.setdefault('service_logs',[]).extend(service_logs)
        if any(process_health(load_config(view.config),role).get('state')!='STOPPED' for role in ROLES):
            raise ValueError('Every actual ordinary role must stop')
        idle()
    with awake_request():
        try:
            args=['init-profile','--config',view.config,'--data-root',data,'--instance-id',original.product_instance_id,
                '--port',original.control_api_port,'--enable-paper-runtime']
            if original.cloud_root is not None:args+=['--cloud-root',original.cloud_root]
            view.command('new-public-idle-profile',args)
            configured=load_config(view.config)
            if (product_namespace(configured)!='LOCAL_RESEARCH' or configured.diagnostic_only or not configured.paper_runtime_enabled
                    or configured.database_path!=original.database_path or configured.product_instance_id!=original.product_instance_id):
                raise ValueError('Public same-store ordinary capability profile required')
            simulation=simulation_fixture();simulation.update(namespace='LOCAL_RESEARCH',mode='REAL_TIME',policy_id='SOFTWARE_IDLE_NOT_OPERATOR_POLICY')
            risk=risk_fixture();risk['namespace']='LOCAL_RESEARCH';risk['policy']['version']='SOFTWARE_IDLE_NOT_OPERATOR_POLICY'
            promotion=policy_fixture('LOCAL_RESEARCH');promotion.update(policy_id='SOFTWARE_IDLE_NOT_FOR_PROMOTION',validation_policy_version='SOFTWARE_IDLE_NOT_OPERATOR_POLICY')
            refs={}
            for name,document in (('simulation',simulation),('risk',risk),('promotion',promotion)):
                ref='software-idle-'+revision[:7]+'-'+name+'.json';raw=(canonical(document)+'\n').encode()
                write_private_new(data/ref,raw);refs[name]=ref;baseline_inputs[ref]=sha(raw)
            inputs=dict(schema_version='r7-local-paper-inputs-v0.2',submission_id='engineering-unattended-'+revision[:7],
                simulation_policy_ref=refs['simulation'],risk_policy_ref=refs['risk'],promotion_policy_ref=refs['promotion'],
                paper_policy_ref='software-idle-no-workflow',actor='software-idle-verifier',workflow_authorized=False,
                account_ref='SOFTWARE_IDLE_NO_REAL_ACCOUNT',qualification_receipt_ref=q['result']['receipt_ref'])
            selection_path=output/'software-idle-inputs.json';write_private_new(selection_path,(canonical(inputs)+'\n').encode())
            selected=view.command('normal-configure-paper-idle',['configure-paper','--config',view.config,'--selection-profile',selection_path])
            if selected.get('status')!='ORDINARY_PAPER_CONFIGURED' or selected.get('workflow_authorized') is not False:raise ValueError('Normal idle-only selection required')
            selected_generation=selected['config_generation'];report['selection_generation']=selected_generation
            report['owning_profile']=dict(original_config_hash=config_hash(original),idle_config_hash=config_hash(configured),
                original_config_ref=original_path.relative_to(PROJECT).as_posix(),
                original_data_root_ref=data.relative_to(PROJECT).as_posix(),
                original_canonical_ref=original.database_path.relative_to(PROJECT).as_posix(),
                original_product_instance_id=original.product_instance_id,
                same_original_data_root=True,same_original_receipt_ref=q['result']['receipt_ref'],workflow_authorized=False)
            operations=dict(schema_version='r7-local-operations-v0.2',workflow_authorized=True,actor='software-idle-verifier',
                roles=['control','research','runtime'],scan_inbox=False,research_policy_ids=[],queue_reports=False,
                interval_seconds=5,restart_budget=2,restart_backoff_seconds=1)
            write_private_new(view.operations,(canonical(operations)+'\n').encode())
            first=view._launch('coordinator-ordinary-first');before=ready(first['owned']);report['initial_roles']=before
            view.command('ordinary-duplicate-denied',['run-product','--config',view.config,'--operations-profile',view.operations,'--maximum-cycles','1'],expected=2)
            report['duplicate_denial']=require_duplicate_denial((output/'ordinary-duplicate-denied.log').read_bytes())
            if {role:_token(value) for role,value in snapshot(first['owned']).items()}!={role:_token(value) for role,value in before.items()}:
                raise ValueError('Duplicate start changed original ordinary roles')
            actual=PublicFixture.health(view,'runtime',first['owned'])
            terminate_verified_pid(first['owned'],actual['pid'])
            successor=ready(first['owned'],before,runtime_only=True);report['runtime_successor_roles']=successor
            stop(first,successor,'ordinary-stop-first')
            second=view._launch('coordinator-ordinary-restarted');restarted=ready(second['owned'],successor);report['restarted_roles']=restarted
            stop(second,restarted,'ordinary-stop-restarted')
            report['passed']=True
        except BaseException as error:report.update(passed=False,error_type=type(error).__name__)
        finally:
            cleanup_errors=[]
            for session in reversed(view.sessions):
                try:view._close_session(session)
                except BaseException as error:cleanup_errors.append(type(error).__name__)
            report['cleanup_errors']=cleanup_errors;report['all_owned_trees_reaped']=all(session['closed'] for session in view.sessions)
            if cleanup_errors or not report['all_owned_trees_reaped']:report['passed']=False
            try:guard();report['source_and_package_unchanged']=True
            except BaseException as error:report.update(passed=False,source_and_package_unchanged=False,guard_error_type=type(error).__name__)
            report['helper_unchanged']=sha(Path(__file__).read_bytes())==report['helper_hash']
            if not report['helper_unchanged']:report['passed']=False
            report['finished_at']=datetime.now(timezone.utc).isoformat();view.persist()
    write_private_new(output/'checkpoint.json',(canonical(report)+'\n').encode())
    print(json.dumps({key:value for key,value in report.items() if key not in ('commands','sessions','initial_roles','runtime_successor_roles','restarted_roles')}),flush=True)
    return 0 if report['passed'] else 2
if __name__=='__main__':raise SystemExit(run(*sys.argv[1:]))
