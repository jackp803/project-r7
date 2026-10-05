"""Fresh private database restoration; source data is never replaced.

This scope restores the verified seven-store database bundle only. Dataset,
accepted-snapshot and policy restoration requires the complete user-data bundle.
The resulting profile is inhibited and disconnected, never activation evidence.
"""
from contextlib import ExitStack,closing
from dataclasses import asdict,replace
from datetime import datetime,timezone
import hashlib,json,math,os,sqlite3,time,uuid
from pathlib import Path
from application.platform.backup import (_destination,_deadline,_profile_current,
    _verify_database_backup_snapshot,_database_facts)
from application.platform.paths import overlapping
from application.platform.private_files import create_private_directory,write_private_new,require_private
from application.platform.scope_lock import ProcessScopeLock,operational_lock_root
from application.platform.supervision import config_hash
from application.research.evidence import capture_provenance,stamp

class RestoreError(RuntimeError):pass

def _verify_within_deadline(config,backup,end,*,product_data=False):
    _deadline(end)
    return _verify_database_backup_snapshot(config,backup,timeout_seconds=min(30,max(1,math.ceil(end-time.monotonic()))),
        _include_settings=product_data)

def _restore_connection(path,end):
    _deadline(end)
    db=sqlite3.connect(path,timeout=min(2,max(0.001,end-time.monotonic())))
    try:
        db.row_factory=sqlite3.Row
        db.set_progress_handler(lambda:int(time.monotonic()>=end),1000)
        db.execute('PRAGMA trusted_schema=OFF');db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA synchronous=FULL')
        if db.execute('PRAGMA synchronous').fetchone()[0]!=2:raise RestoreError('RESTORE_FULL_DURABILITY_REQUIRED')
        _deadline(end)
        return db
    except BaseException:
        db.close()
        raise


def _fence_app_store(path,role,at,end):
    with closing(_restore_connection(path,end)) as db:
        tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        db.execute('BEGIN IMMEDIATE')
        if role=='intake' and 'app_submissions' in tables:
            db.execute("UPDATE app_submissions SET lease_generation=lease_generation+1,revision=revision+1,lease_deadline=?,owner_id='RESTORED_LEASE_FENCED' WHERE state='CLAIMED'",(at,))
        if role=='queue' and 'research_queue_jobs' in tables:
            db.execute("INSERT INTO research_queue_events(run_id,state,generation,revision,observed_at) SELECT run_id,'FAILED',generation+1,revision+1,? FROM research_queue_jobs WHERE state IN ('QUEUED','RUNNING','CANCEL_REQUESTED')",(at,))
            db.execute("UPDATE research_queue_jobs SET state='FAILED',revision=revision+1,generation=generation+1,updated_at=?,lease_deadline=?,owner_id='RESTORED_LEASE_FENCED',reason_codes_json='[\"RESTORED_RECONCILIATION_REQUIRED\"]' WHERE state IN ('QUEUED','RUNNING','CANCEL_REQUESTED')",(at,at))
        if role=='research' and 'research_attempts' in tables:
            output='{"reason_codes":["RESTORED_RECONCILIATION_REQUIRED"]}'
            db.execute("UPDATE research_attempts SET status='FAILED',ended_at=?,lease_deadline=?,output_json=?,output_hash=?,reason_codes_json='[\"RESTORED_RECONCILIATION_REQUIRED\"]' WHERE status='RUNNING'",
                (at,at,output,'sha256:'+hashlib.sha256(output.encode()).hexdigest()))
        if role=='auth' and 'local_sessions' in tables:
            db.execute('UPDATE local_sessions SET revoked=1,revision=revision+1,reauth_deadline=NULL')
        if role=='supervision' and 'process_sessions' in tables:
            db.execute("UPDATE process_sessions SET state='FAILED'")
            db.execute("UPDATE process_session_history SET state='FAILED',ended_at=? WHERE ended_at IS NULL",(at,))
            db.execute('UPDATE process_generation_counters SET generation=generation+1')
        db.commit()
        _deadline(end)

def _fence_financial_processes(path,token,now,end):
    # Existing E6 owner APIs append generations; no direct financial rewrite.
    with closing(_restore_connection(path,end)) as db:
        tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        dispatch=[];paper=[]
        if 'product_dispatch_runs' in tables:
            dispatch=db.execute('SELECT r.run_id,COALESCE(MAX(g.generation),0) FROM product_dispatch_runs r LEFT JOIN product_dispatch_generations g ON g.run_id=r.run_id GROUP BY r.run_id ORDER BY r.run_id LIMIT 1001').fetchmany(1001)
        if 'paper_process_runs' in tables and 'paper_process_generations' in tables:
            paper=db.execute('SELECT r.run_id,COALESCE(MAX(g.generation),0) FROM paper_process_runs r LEFT JOIN paper_process_generations g ON g.run_id=r.run_id GROUP BY r.run_id ORDER BY r.run_id LIMIT 1001').fetchmany(1001)
        if len(dispatch)+len(paper)>1000:raise RestoreError('RESTORE_PROCESS_INVENTORY_LIMIT')
    if dispatch:
        from storage.product_dispatch import ProductDispatchJournal
        # Verified current-schema copies need no migration. A bounded connection
        # enters the owning journal's actual public generation API.
        with ProductDispatchJournal(_restore_connection(path,end)) as journal:
            for run,generation in dispatch:
                _deadline(end)
                journal.begin_process(run,'restore:'+token,expected_generation=generation,now=now)
                _deadline(end)
    if paper:
        from storage.paper_process import PaperProcessJournal
        with PaperProcessJournal(_restore_connection(path,end)) as journal:
            for run,generation in paper:
                _deadline(end)
                journal.begin_process(run,'restore:'+token,expected_generation=generation,now=now)
                _deadline(end)

def restore_database_backup(config,backup,destination,*,config_path=None,timeout_seconds=30):
    return _restore_backup(config,backup,destination,config_path=config_path,timeout_seconds=timeout_seconds)


def _restore_backup(config,backup,destination,*,config_path=None,timeout_seconds=30,product_data=False):
    if type(timeout_seconds) is not int or not 5<=timeout_seconds<=300:raise RestoreError('BOUNDED_RESTORE_DEADLINE_REQUIRED')
    end=time.monotonic()+timeout_seconds
    try:
        target=_destination(config,destination);backup=_destination(config,backup)
        if overlapping(target,backup) or target.exists():raise RestoreError('FRESH_DISJOINT_RESTORE_GENERATION_REQUIRED')
        _profile_current(config,config_path)
        with ExitStack() as stack:
            for role in ('control','research','runtime','cloud'):
                stack.enter_context(ProcessScopeLock(role+':'+config.product_instance_id,lock_root=operational_lock_root(config)))
            bundle=None
            database_backup=backup
            if product_data:
                from application.platform.product_backup import _verified_manifest,_copy_file
                bundle,source_manifest,verified,manifest,raw_manifest=_verified_manifest(config,backup,end)
                database_backup=backup/'databases'
            else:
                verified,manifest,raw_manifest=_verify_within_deadline(config,backup,end)
                source_manifest=raw_manifest
            if sum(row['bytes'] for row in manifest['databases'])>16*1024**3:raise RestoreError('RESTORE_TRANSFER_BUDGET')
            create_private_directory(target)
            token=str(uuid.uuid4())
            progress=dict(schema_version='r7-private-restore-in-progress-v0.2',restore_generation_id=token,
                product_instance_id=config.product_instance_id,previous_config_hash=config_hash(config),status='IN_PROGRESS')
            write_private_new(target/'restore-in-progress.json',(json.dumps(progress,sort_keys=True)+'\n').encode())
            copied=[]
            for row in manifest['databases']:
                _deadline(end);source=database_backup/row['artifact'];require_private(source)
                relative=Path(row['relative_path'])
                if (relative.is_absolute() or relative.drive or '..' in relative.parts or '\\' in row['relative_path']
                        or not (target/relative).is_relative_to(target) or target/relative==target):
                    raise RestoreError('RESTORE_DESTINATION_CONTAINMENT_REQUIRED')
                path=target/relative
                for parent in reversed(path.parent.parents):
                    if parent.is_relative_to(target) and not parent.exists():create_private_directory(parent)
                if not path.parent.exists():create_private_directory(path.parent)
                write_private_new(path,b'');digest=hashlib.sha256();count=0
                with source.open('rb') as incoming,path.open('wb') as outgoing:
                    while chunk:=incoming.read(1024*1024):
                        _deadline(end);count+=len(chunk)
                        if count>row['bytes']:raise RestoreError('RESTORE_SOURCE_CHANGED')
                        digest.update(chunk);outgoing.write(chunk)
                    outgoing.flush();os.fsync(outgoing.fileno())
                require_private(path)
                if count!=row['bytes'] or 'sha256:'+digest.hexdigest()!=row['sha256']:raise RestoreError('RESTORE_SOURCE_CHANGED')
                copied.append((row['logical_name'],path))
            if _verify_within_deadline(config,database_backup,end,product_data=product_data)!=(verified,manifest,raw_manifest):
                raise RestoreError('RESTORE_SOURCE_CHANGED')
            if product_data:
                for row in bundle['files']:
                    _copy_file(backup/'files'/row['relative_path'],target/row['relative_path'],row,end)
                if _verified_manifest(config,backup,end)!=(bundle,source_manifest,verified,manifest,raw_manifest):
                    raise RestoreError('RESTORE_SOURCE_CHANGED')
            now=datetime.now(timezone.utc);at=stamp(now)
            for role,path in copied:
                _deadline(end);_fence_app_store(path,role,at,end);_fence_financial_processes(path,token,now,end);require_private(path)
                with closing(_restore_connection(path,end)) as db:
                    db.row_factory=None
                    _database_facts(db)
                _deadline(end)
            restored=replace(config,local_data_root=target,database_path=target/config.database_path.relative_to(config.local_data_root),
                cloud_root=None,diagnostic_only=True,paper_runtime_enabled=False)
            values={key:str(value) if isinstance(value,Path) else value for key,value in asdict(restored).items()}
            write_private_new(target/'restored-product.json',(json.dumps(values,ensure_ascii=False,indent=2)+'\n').encode())
            _profile_current(config,config_path);_deadline(end)
            scope='PRODUCT_DATA' if product_data else 'DATABASES_ONLY'
            user_data='COMPLETE_SUPPORTED_LOCAL_PROFILE' if product_data else 'PENDING'
            marker=dict(schema_version='r7-private-'+('product-data' if product_data else 'database')+'-restore-v0.2',restore_generation_id=token,restored_at=at,
                source_backup_id=verified['backup_id'],source_backup_manifest_sha256='sha256:'+hashlib.sha256(source_manifest).hexdigest(),
                product_instance_id=config.product_instance_id,previous_config_hash=config_hash(config),config_hash=config_hash(restored),
                database_count=len(copied),scope=scope,user_data_restore=user_data,
                reconciliation='REQUIRED',reauthorization='REQUIRED',runtime_new_exposure='INHIBITED',cloud='DISCONNECTED',
                financial_authority='NONE',source_provenance=capture_provenance())
            write_private_new(target/'restore-generation.json',(json.dumps(marker,ensure_ascii=False,indent=2)+'\n').encode())
        return dict(status='PRODUCT_DATA_RESTORE_STAGED' if product_data else 'DATABASE_RESTORE_STAGED',restore_generation_id=token,database_count=len(copied),
            scope=scope,user_data_restore=user_data,reconciliation='REQUIRED',reauthorization='REQUIRED',
            runtime_new_exposure='INHIBITED',financial_authority='NONE',cloud='DISCONNECTED')
    except RestoreError:raise
    except Exception:raise RestoreError('PRIVATE_DATABASE_RESTORE_FAILED') from None
