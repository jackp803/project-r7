"""Native complete owning-store backup/restore; receipt history is not authority."""
from contextlib import closing
from datetime import datetime,timezone
import hashlib,json,os,re,sqlite3,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tools'),str(BASE),str(BASE.parent)]
from application.config import load_config
from application.datasets.catalog import read_local
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.platform.restoration import require_valid_restoration
from application.platform.product_backup import _safe_backup_relative,_file_facts
from application.platform.supervision import config_hash,_local_path
from application.paper.inventory import current_target,fixed_profile
from application.paper.producer import _guard
from application.qualification import _sanitize
from application.datasets.public_capture import public_capture_inventory
from application.datasets.catalog import decode,DatasetCatalog
from verify_headless_product import CAPTURE,CAPTURE_MANIFEST
from storage.qualification import open_qualification_receipts
from local_windows_qualification_awake import awake_request
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()

def require_same_captured_file(roots,row,deadline):
    ref=row['relative_path'];_safe_backup_relative(ref)
    for root in roots:
        if _file_facts(root/ref,deadline)!={key:row[key] for key in ('bytes','sha256')}:
            raise ValueError('Actual four-way file equality failed')

def run(revision,qualification_attempt='first'):
    if not re.fullmatch('[0-9a-f]{40}',revision):raise ValueError('Exact subject required')
    from run_current_checkpoint import qualification_output
    qualified=qualification_output(revision,qualification_attempt);q=json.loads((qualified/'checkpoint.json').read_bytes())
    portable=json.loads((BASE/('portable-'+revision[:7]+'-first')/'checkpoint.json').read_bytes())
    automatic=json.loads((BASE/('unattended-'+revision[:7]+'-first')/'checkpoint.json').read_bytes())
    if not all(v['passed'] for v in (q,portable,automatic)) or not automatic['all_owned_tree_reaped']:raise ValueError('Actual stopped prerequisites required')
    package=PROJECT/portable['installation_ref'];facts=verify_distribution(package);profile=fixed_profile(current_target())
    def guard():_guard(ROOT,revision,package,facts,profile)
    guard();config_path=qualified/'product.json';config=load_config(config_path);data=config.local_data_root
    owning_profile=dict(config_ref=config_path.relative_to(PROJECT).as_posix(),data_root_ref=data.relative_to(PROJECT).as_posix(),
        canonical_ref=config.database_path.relative_to(PROJECT).as_posix(),product_instance_id=config.product_instance_id,config_hash=config_hash(config))
    if (automatic.get('owning_profile')!=owning_profile or automatic.get('revision')!=revision or automatic.get('identity')!=facts
            or portable.get('revision')!=revision or portable.get('identity')!=facts or q.get('revision')!=revision
            or q['result'].get('executable_revision')!=revision or q['result'].get('build_hash')!=facts['build_hash']):
        raise ValueError('Same actual qualified diagnostic profile and package required')
    output=BASE/('qualified-backup-'+revision[:7]+'-first')
    if output.exists():raise ValueError('Fresh attempt required')
    create_private_directory(output);receipt_ref=q['result']['receipt_ref']
    report=dict(revision=revision,identity=facts,passed=False,commands=[],started_at=datetime.now(timezone.utc).isoformat(),
        scope='ACTUAL_NATIVE_SAME_QUALIFIED_ORDINARY_AND_DIAGNOSTIC_STORE_BACKUP_RESTORE',receipt_ref=receipt_ref,
        helper_hash=sha(Path(__file__).read_bytes()),additional_provider_requests=0,owning_profile=owning_profile,
        credentials='NONE',private_requests=0,provider_mutation=0,capital='NONE',github_compute='NOT_USED',master='IN_PROGRESS')
    env={k:os.environ[k] for k in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if k in os.environ};env.update(PATH='',PYTHONUTF8='1')
    handles=[]
    def command(label,args,expected=0):
        guard();raw=output/(label+'.raw');log=output/(label+'.log');owned=None;cleanup=None;code=None
        error=None
        try:
            with raw.open('xb') as stream:
                owned=spawn_owned([str(package/'R7.exe'),*map(str,args)],cwd=output,env=env,
                    limits=ResourceLimits(120),stdout=stream,stderr=subprocess.STDOUT)
                handles.append((label,owned));code=owned.wait()
        except BaseException as caught:error=caught
        finally:
            if owned is not None:
                try:cleanup=terminate_owned(owned,deadline_seconds=5)
                except BaseException as caught:error=error or caught
            row=dict(command=label,exit_code=code,expected_exit_code=expected,tree_reaped=bool(cleanup and cleanup.reaped))
            try:
                if raw.stat().st_size>8*1024*1024:raise ValueError('Bounded native output required')
                text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n')
                write_private_new(log,text.encode());raw.unlink();row.update(log_ref=log.name,log_hash=sha(log.read_bytes()))
            except BaseException as caught:row['log_retention_error_type']=type(caught).__name__;error=error or caught
            if error is not None:row['error_type']=type(error).__name__
            report['commands'].append(row)
        if error is not None:raise error
        if code!=expected or not cleanup or not cleanup.reaped:raise ValueError('Actual backup command failed')
        guard();return json.loads(text.strip().splitlines()[-1])
    def receipt(path,immutable=False):
        with open_qualification_receipts(path,namespace='LOCAL_RESEARCH',immutable=immutable) as reader:return reader.get(receipt_ref)
    def captured(bundle):
        value=json.loads(read_local(bundle/'databases','manifest.json',2*1024*1024))
        return bundle/'databases'/next(row['artifact'] for row in value['databases'] if row['logical_name']=='canonical')
    def state(root):
        facts={}
        tables={'queue.sqlite':[('research_queue_jobs','run_id')],
            'research.sqlite':[('research_runs','run_id'),('research_attempts','attempt_id'),('research_feedback_publications','operation_id')]}
        for name,queries in tables.items():
            with closing(sqlite3.connect((root/name).as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
                db.execute('PRAGMA query_only=ON')
                for table,ordering in queries:
                    rows=list(db.execute('SELECT * FROM '+table+' ORDER BY '+ordering+' LIMIT 257'))
                    if len(rows)>256:raise ValueError('Bounded actual diagnostic history required')
                    facts[name+'/'+table]=sha(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode())
        return facts
    with awake_request():
        try:
            observed=command('original-software-before',['_paper-release-observe','--config',config_path,'--receipt-ref',receipt_ref,'--mode','software'])
            original=receipt(config.database_path)
            if original is None or not original.passed or original.subject.executable_revision!=revision:raise ValueError('Actual owning receipt required')
            previous_state=state(data);profile_bytes_hash=sha(config_path.read_bytes())
            with closing(sqlite3.connect((data/'queue.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
                db.execute('PRAGMA query_only=ON');jobs=list(db.execute('SELECT run_id,owner_run_id,state,outcome_json FROM research_queue_jobs'))
            expected_job=automatic['actual_owner_report']['job'];expected_report=automatic['actual_owner_report']['publication']
            if len(jobs)!=1 or tuple(jobs[0][:3])!=(expected_job['run_id'],expected_job['owner_run_id'],'COMPLETE') or jobs[0][3]!=expected_job['outcome_json']:
                raise ValueError('Actual completed diagnostic job missing from SAME owning store')
            with closing(sqlite3.connect((data/'research.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
                db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
                outbox=[dict(row) for row in db.execute('SELECT * FROM research_feedback_publications')]
                if db.execute("SELECT count(*) FROM research_attempts WHERE status='RUNNING'").fetchone()[0]:raise ValueError('Nonterminal diagnostic attempt cannot establish immutable restore equality')
            if len(outbox)!=1 or any(outbox[0].get(key)!=value for key,value in expected_report.items()):raise ValueError('Actual diagnostic outbox lineage differs')
            backup=output/'qualified-product-backup';restored=output/'restored-qualified-product';rebackup=output/'restored-product-rebackup'
            created=command('backup-owning-store',['backup-product-data','--config',config_path,'--destination',backup])
            verified=command('verify-owning-backup',['verify-product-backup','--config',config_path,'--destination',backup])
            if created!=verified or verified['status']!='PRODUCT_DATA_BACKUP_VERIFIED':raise ValueError('Actual full backup not verified')
            if receipt(captured(backup),True)!=original:raise ValueError('Captured actual receipt differs')
            restored_result=command('restore-owning-store',['restore-product-data','--config',config_path,'--backup',backup,'--destination',restored])
            restored_config_path=restored/'restored-product.json';restored_config=load_config(restored_config_path)
            fence=require_valid_restoration(restored_config)
            if (restored_result['status']!='PRODUCT_DATA_RESTORE_STAGED' or fence['status']!='RESTORED_INHIBITED'
                    or restored_config.cloud_root is not None or not restored_config.diagnostic_only or restored_config.paper_runtime_enabled
                    or fence['restore_generation_id']!=restored_result['restore_generation_id']):raise ValueError('Restoration inhibition missing')
            if receipt(restored_config.database_path)!=original or state(restored)!=previous_state:raise ValueError('Restored immutable histories differ')
            denied=command('restored-software-denied',['_paper-release-observe','--config',restored_config_path,'--receipt-ref',receipt_ref,'--mode','software'],2)
            if denied.get('error_kind')!='VALIDATION' or denied.get('reason_code')!='LOCAL_STARTUP_VALIDATION_FAILED':raise ValueError('Expected sanitized restored admission denial missing')
            repeated=command('backup-restored-store',['backup-product-data','--config',restored_config_path,'--destination',rebackup])
            verified_again=command('verify-restored-rebackup',['verify-product-backup','--config',restored_config_path,'--destination',rebackup])
            if repeated!=verified_again or receipt(captured(rebackup),True)!=original:raise ValueError('Actual restored rebackup differs')
            manifest=json.loads(read_local(backup,'manifest.json',2*1024*1024));second=json.loads(read_local(rebackup,'manifest.json',2*1024*1024))
            final_rows={row['relative_path']:row for row in second['files']}
            source_rows={row['relative_path']:row for row in manifest['files']}
            paths={ref:data/ref for ref in source_rows if ref.startswith(CAPTURE+'/')}
            capture_refs,capture_hashes,dataset_ref=public_capture_inventory(data,CAPTURE,paths)
            capture=decode(read_local(data,CAPTURE+'/acquisition.json',65536))
            if set(paths)!=capture_refs or DatasetCatalog(data).load(dataset_ref).manifest_hash!=CAPTURE_MANIFEST:raise ValueError('Actual audited public capture closure differs')
            required={f'qualification/{original.execution_id}/{artifact["ref"]}':artifact['hash']
                for member in original.execution_evidence['members'] for artifact in member['artifacts']}
            if any(ref not in source_rows or source_rows[ref]['sha256']!=expected for ref,expected in required.items()):raise ValueError('Actual owning receipt artifact closure missing')
            for suffix in ('preflight.json','result.json'):
                if f'qualification/{original.execution_id}/{suffix}' not in source_rows:raise ValueError('Typed actual qualification metadata missing')
            public_count=0;qualification_count=0
            audit_deadline=time.monotonic()+120
            for row in manifest['files']:
                ref=row['relative_path'];_safe_backup_relative(ref)
                if final_rows.get(ref)!=row:raise ValueError('Rebackup captured file commitment differs')
                require_same_captured_file((data,backup/'files',restored,rebackup/'files'),row,audit_deadline)
                public_count+=ref.startswith('datasets/btc-4h-20260801-20261018/')
                qualification_count+=ref.startswith('qualification/'+original.execution_id+'/')
            if public_count!=len(capture_refs):raise ValueError('Actual public closure incomplete')
            after=command('original-software-after',['_paper-release-observe','--config',config_path,'--receipt-ref',receipt_ref,'--mode','software'])
            if after!=observed or receipt(config.database_path)!=original or state(data)!=previous_state or sha(config_path.read_bytes())!=profile_bytes_hash:
                raise ValueError('Original source identity/history changed')
            report.update(passed=True,backup=verified,restore=restored_result,restoration_fence=fence,rebackup=verified_again,
                four_way_equal_files=len(manifest['files']),public_capture_files=public_count,qualification_files=qualification_count,
                actual_receipt_equal_across_four_stores=True,source_diagnostic_histories_unchanged=True,restored_native_software_admission='DENIED',
                actual_qualification_declared_artifacts=len(required),capture_manifest_hash=CAPTURE_MANIFEST,
                capture_actual_public_requests=capture['provider_requests'],capture_actual_public_responses=capture['provider_responses'],
                restored_history_authority='NONE',ordinary_paper_selection='NOT_ASSESSED_BY_BACKUP_HELPER',
                paper='NOT_COMMANDED_BY_BACKUP_HELPER',forward='NO_OBSERVATION_PERFORMED_BY_BACKUP_HELPER')
        except BaseException as error:report.update(passed=False,error_type=type(error).__name__)
        finally:
            report['owned_cleanup']=[]
            for label,handle in handles:
                try:
                    cleanup=terminate_owned(handle,deadline_seconds=5);report['owned_cleanup'].append(dict(command=label,reaped=cleanup.reaped))
                except BaseException as error:report['owned_cleanup'].append(dict(command=label,reaped=False,error_type=type(error).__name__))
            report['all_owned_tree_reaped']=bool(handles) and all(row['reaped'] for row in report['owned_cleanup'])
            if not report['all_owned_tree_reaped']:report['passed']=False
            try:guard();report['source_and_package_unchanged']=True
            except BaseException as error:report.update(passed=False,guard_error_type=type(error).__name__)
            report['finished_at']=datetime.now(timezone.utc).isoformat()
    write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps(dict(revision=revision,passed=report['passed'],error_type=report.get('error_type'),scope=report['scope'])),flush=True)
    return 0 if report['passed'] else 2
if __name__=='__main__':raise SystemExit(run(*sys.argv[1:]))
