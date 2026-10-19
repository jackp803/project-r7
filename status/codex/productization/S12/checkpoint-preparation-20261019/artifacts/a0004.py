"""Actual installed normal coordinator: public-capture diagnostic flow only.

Uses the SAME successful owning qualification profile; never writes databases,
imports results, enrolls authentication or grants Paper/financial authority.
"""
from contextlib import closing
from datetime import datetime,timezone
import hashlib,json,os,re,sqlite3,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tools'),str(BASE),str(BASE.parent)]
from application.config import load_config,product_namespace
from application.datasets.catalog import canonical,decode
from application.platform.private_files import create_private_directory,write_private_new,require_private
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.platform.distribution import verify_distribution
from application.platform.supervision import _local_path,process_health,config_hash
from application.paper.inventory import fixed_profile,current_target
from application.paper.producer import _guard
from application.qualification import _sanitize
from application.cloud.feedback import validate_feedback_publication
from application.cloud.manifest import canonical_bytes
from verify_paper_product import owns_pid
from verify_headless_product import NativeHeadlessFlow,CAPTURE,CAPTURE_MANIFEST
from local_windows_qualification_awake import awake_request
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()

def run(revision,qualification_attempt='first'):
    if not re.fullmatch('[0-9a-f]{40}',revision):raise ValueError('Full subject required')
    from run_current_checkpoint import qualification_output
    qualifier=qualification_output(revision,qualification_attempt)
    qualification=json.loads((qualifier/'checkpoint.json').read_bytes())
    portable=json.loads((BASE/('portable-'+revision[:7]+'-first')/'checkpoint.json').read_bytes())
    if not qualification['passed'] or not portable['passed']:raise ValueError('Actual full owning and clean installed proof required')
    package=PROJECT/portable['installation_ref'];facts=verify_distribution(package);profile=fixed_profile(current_target())
    def guard():_guard(ROOT,revision,package,facts,profile)
    guard();config_path=qualifier/'product.json';config=load_config(config_path);data=config.local_data_root
    if (product_namespace(config)!='LOCAL_RESEARCH' or not config.diagnostic_only or config.paper_runtime_enabled
            or config.cloud_root!=qualifier/'local-inbox'):raise ValueError('Same ordinary diagnostic profile required')
    output=BASE/('unattended-'+revision[:7]+'-first')
    if output.exists():raise ValueError('Fresh attempt required')
    create_private_directory(output)
    report=dict(revision=revision,identity=facts,scope='NORMAL_NATIVE_AUTOMATIC_DIAGNOSTIC_INTAKE_RESEARCH_DURABLE_REPORT',
        passed=False,commands=[],started_at=datetime.now(timezone.utc).isoformat(),additional_public_requests=0,
        cumulative_actual_public_requests=8,cumulative_actual_public_responses=8,credentials='NONE',private_requests=0,
        provider_mutation=0,capital='NONE',github_compute='NOT_USED',strategy_origin='ENGINEERING_BASELINE_NOT_GPT',
        paper='NOT_STARTED',live='NOT_STARTED',forward='NOT_STARTED',publication='NOT_RUN',master='IN_PROGRESS',
        os_startup='UNCHANGED',sleep='UNCHANGED',security='UNCHANGED',helper_hash=sha(Path(__file__).read_bytes()))
    report['owning_profile']=dict(config_ref=config_path.relative_to(PROJECT).as_posix(),
        data_root_ref=data.relative_to(PROJECT).as_posix(),canonical_ref=config.database_path.relative_to(PROJECT).as_posix(),
        product_instance_id=config.product_instance_id,config_hash=config_hash(config))
    env={k:os.environ[k] for k in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if k in os.environ}
    env.update(PATH='',PYTHONUTF8='1');owned=None;stream=None;copier=None
    def command(label,args,expected=0,timeout=90):
        guard();raw=output/(label+'.raw');log=output/(label+'.log');process=None;cleanup=None
        with raw.open('xb') as incoming:
            try:
                process=spawn_owned([str(package/'R7.exe'),*map(str,args)],cwd=output,env=env,
                    limits=ResourceLimits(timeout),stdout=incoming,stderr=subprocess.STDOUT)
                code=process.wait()
            finally:
                if process is not None:cleanup=terminate_owned(process,deadline_seconds=5)
        text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n')
        write_private_new(log,text.encode());raw.unlink()
        report['commands'].append(dict(command=label,exit_code=code,expected_exit_code=expected,tree_reaped=bool(cleanup and cleanup.reaped),log_ref=log.name,log_hash=sha(log.read_bytes())))
        if code!=expected or not cleanup or not cleanup.reaped:raise ValueError('Actual normal native command failed')
        guard();return json.loads(text.strip().splitlines()[-1])
    def rows(name,query):
        path=data/name;_local_path(path)
        if not path.is_file():return []
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
            db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
            return [dict(row) for row in db.execute(query)]
    def observe():
        jobs=rows('queue.sqlite','SELECT run_id,submission_id,policy_id,owner_run_id,state,outcome_json FROM research_queue_jobs LIMIT 4')
        publications=rows('research.sqlite','SELECT * FROM research_feedback_publications LIMIT 4')
        if len(jobs)!=1 or jobs[0]['state']!='COMPLETE' or len(publications)!=1:return None
        job=jobs[0];row=publications[0]
        if row['run_id']!=job['owner_run_id'] or row['state']!='PENDING' or row['attempts']!=0:raise ValueError('Actual pending owner report required')
        raw=row['feedback_json'].encode();payloads={k:v.encode() for k,v in decode(row['payloads_json'].encode()).items()}
        validate_feedback_publication(row['logical_path'],payloads)
        if (raw!=payloads['feedback.json'] or sha(raw)!=row['feedback_hash']
                or row['artifact_hash']!=sha(canonical_bytes({name:sha(value) for name,value in payloads.items()}))
                or row['operation_id']!='r7-feedback-'+row['feedback_hash'][7:]):raise ValueError('Actual feedback bytes differ')
        document=decode(raw)
        if (document['namespace']!='LOCAL_RESEARCH' or document['performance_policy']!='OPT_OUT'
                or document['development']['status']!='EXECUTED'
                or any(document[key]['status']!='NOT_RUN' for key in ('robustness','sealed_oos','paper','live'))
                or any(document[key].get('performance') is not None for key in ('training','development','robustness','sealed_oos','paper','live'))
                or document['holdout_observed'] is not False or document['dataset']['manifest_hash']!=CAPTURE_MANIFEST
                or document['source']['executable_revision']!=revision or document['source']['implementation_hash']!=facts['implementation_hash']):
            raise ValueError('Diagnostic disclosure differs from actual stages')
        outcome=decode(job['outcome_json'].encode())
        if (outcome.get('status')!='BLOCKED' or outcome.get('strategy_lifecycle')!='BACKTESTING' or 'MISSING_PROMOTION_POLICY' not in outcome.get('reason_codes',[])
                or outcome.get('run_id')!=job['owner_run_id'] or document['run_id']!=job['owner_run_id']
                or job['submission_id']!=submission or job['policy_id']!='engineering-development-only'
                or document['strategy']['content_hash']!=report['authored']['strategy_content_hash']):
            raise ValueError('Unselected formal policy must retain actual blocked outcome')
        if len(rows('canonical.sqlite3','SELECT run_id FROM paper_process_runs LIMIT 1')):raise ValueError('Diagnostic flow started Paper')
        return dict(job=job,publication={k:row[k] for k in ('operation_id','run_id','feedback_hash','logical_path','artifact_hash','state','attempts')},feedback=document,payloads=payloads)
    with awake_request():
        try:
            command('software-before',['_paper-release-observe','--config',config_path,'--receipt-ref',qualification['result']['receipt_ref'],'--mode','software'])
            copier=object.__new__(NativeHeadlessFlow);copier.output=data;copier.data=data
            copier.research_input_root=BASE/'public-c62b11a-research/data';copier.observation={}
            def copy_directory(path):
                if path==data:require_private(data,directory=True)
                else:NativeHeadlessFlow._mkdir(copier,path)
            copier._mkdir=copy_directory
            dataset=copier._copy_inputs();report['research_input']=copier.observation['research_input']
            inbox=config.cloud_root;_local_path(inbox)
            if inbox.exists():raise ValueError('Fresh local-only handoff required')
            create_private_directory(inbox);write_private_new(inbox/'.r7-root.json',b'{"root_id":"engineering-local-inbox"}\n')
            create_private_directory(inbox/'inbox');create_private_directory(inbox/'inbox/strategies')
            definition=ROOT/'docs/strategy/authoring-v0.2/examples/four-hour/strategy.json'
            submission='engineering-unattended-'+revision[:7]
            report['authored']=command('author-actual-engineering-input',['author-package','--definition',definition,
                '--destination',inbox/'inbox/strategies'/submission,'--submission-id',submission,
                '--dataset-profile','okx-btc-4h','--validation-profile','diagnostic','--robustness-profile','diagnostic'])
            selection=dict(schema_version='r7-owner-selections-v0.2',cloud_root_id='engineering-local-inbox',research_policies={
                'engineering-development-only':dict(dataset_ref=dataset,split_policy_ref='engineering-split.json',cost_policy_ref='engineering-cost.json',
                    selection_mode='DIAGNOSTIC_DEVELOPMENT_ONLY',requested_dataset_profile='okx-btc-4h',requested_validation_profile='diagnostic',requested_robustness_profile='diagnostic')})
            selection_path=output/'research-selection.json';write_private_new(selection_path,(canonical(selection)+'\n').encode())
            selected=command('normal-configure-research',['configure-research','--config',config_path,'--selection-profile',selection_path])
            if selected['status']!='RESEARCH_CONFIGURED' or selected['namespace']!='LOCAL_RESEARCH':raise ValueError('Normal selection failed')
            operations=dict(schema_version='r7-local-operations-v0.2',workflow_authorized=True,actor='localdiagnostic',roles=['control','research'],
                scan_inbox=True,research_policy_ids=['engineering-development-only'],queue_reports=True,interval_seconds=5,restart_budget=2,restart_backoff_seconds=1)
            operations_path=output/'operations.json';write_private_new(operations_path,(canonical(operations)+'\n').encode())
            log=output/'actual-coordinator.log';stream=log.open('xb')
            owned=spawn_owned([str(package/'R7.exe'),'run-product','--config',str(config_path),'--operations-profile',str(operations_path),'--maximum-cycles','1500'],
                cwd=output,env=env,limits=ResourceLimits(240),stdout=stream,stderr=subprocess.STDOUT)
            began=time.monotonic();deadline=began+180;observed=None
            while time.monotonic()<deadline:
                if owned.process.poll() is not None:raise ValueError('Actual coordinator exited before automatic report')
                try:observed=observe()
                except sqlite3.Error:observed=None
                if observed is not None:break
                time.sleep(.25)
            if observed is None:raise ValueError('Automatic actual research/report not completed within checkpoint')
            report['automatic_completion_seconds']=time.monotonic()-began
            stable=canonical({key:observed[key] for key in ('job','publication','feedback')})
            end=time.monotonic()+12
            while time.monotonic()<end:
                time.sleep(.25)
                if owned.process.poll() is not None:raise ValueError('Coordinator died before idempotence proof')
            repeated=observe()
            if repeated is None or canonical({key:repeated[key] for key in ('job','publication','feedback')})!=stable:raise ValueError('Repeated automatic schedule changed logical effects')
            report['native_status']=command('actual-running-status',['product-status','--config',config_path])
            roles=report['native_status']['roles']
            if (any(roles[role].get('status')!='RECENT_HEARTBEAT' or not owns_pid(owned,roles[role]['pid']) for role in ('coordinator','control','research'))
                    or roles['runtime'].get('status')!='NOT_STARTED'):raise ValueError('Actual isolated role ownership missing')
            stop=command('normal-stop-coordinator',['stop-product','--config',config_path,'--role','coordinator'])
            if (stop.get('status')!='COOPERATIVE_STOP_REQUESTED' or stop.get('process_generation_id')!=roles['coordinator']['process_generation_id']
                    or stop.get('financial_authority')!='NONE'):raise ValueError('Exact normal coordinator stop token required')
            if owned.wait(timeout=15)!=0:raise ValueError('Normal coordinator stop failed')
            stream.flush();raw=log.read_bytes();result=decode(raw.strip().splitlines()[-1])
            if (result.get('status')!='STOPPED' or result.get('all_owned_trees_reaped') is not True
                    or result.get('schedule',{}).get('publication')!='LOCAL_DURABLE_OUTBOX_ONLY;REMOTE_NOT_CONFIGURED'
                    or set(result.get('roles',{}))!={'control','research'}
                    or any(row.get('forced_stop') is not False or row.get('exit_code')!=0 or row.get('tree_reaped') is not True for row in result['roles'].values())):
                raise ValueError('Actual normal owned stop/scheduling incomplete')
            report['coordinator_result']=result
            exported=output/'observed-owner-report';create_private_directory(exported)
            for name,payload in observed.pop('payloads').items():write_private_new(exported/name,payload)
            report['actual_owner_report']=observed;report['repeated_schedule']='SAME_ONE_JOB_ONE_REPORT_AFTER12_SECONDS'
            report['report_export']='NATIVE_OWNER_GENERATED_BYTES_READONLY_EXPORTED;OUTBOX_PENDING_ATTEMPTS0;PUBLICATION_NOT_RUN'
            command('software-after',['_paper-release-observe','--config',config_path,'--receipt-ref',qualification['result']['receipt_ref'],'--mode','software'])
            report['passed']=True
        except BaseException as error:report.update(passed=False,error_type=type(error).__name__)
        finally:
            if owned is not None:
                try:
                    cleanup=terminate_owned(owned,deadline_seconds=5);report['all_owned_tree_reaped']=cleanup.reaped
                    if not cleanup.reaped:report['passed']=False
                except BaseException as error:report.update(passed=False,cleanup_error_type=type(error).__name__)
            if stream is not None:
                try:
                    stream.close();log=output/'actual-coordinator.log'
                    text=_sanitize(log.read_text(encoding='utf-8',errors='replace'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n')
                    log.write_text(text,encoding='utf-8',newline='\n');report['coordinator_log_hash']=sha(log.read_bytes())
                except BaseException as error:report.update(passed=False,log_retention_error_type=type(error).__name__)
            if copier is not None and hasattr(copier,'source_inputs'):
                try:
                    report['public_source_unchanged']=all(copier._hash_file(path)==expected for path,expected in copier.source_inputs.items())
                    if not report['public_source_unchanged']:report['passed']=False
                except BaseException as error:report.update(passed=False,input_recheck_error_type=type(error).__name__)
            try:guard();report['source_and_package_unchanged']=True
            except BaseException as error:report.update(passed=False,guard_error_type=type(error).__name__)
            report['finished_at']=datetime.now(timezone.utc).isoformat()
    write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps(dict(revision=revision,passed=report['passed'],error_type=report.get('error_type'),scope=report['scope'])),flush=True)
    return 0 if report['passed'] else 2
if __name__=='__main__':raise SystemExit(run(*sys.argv[1:]))
