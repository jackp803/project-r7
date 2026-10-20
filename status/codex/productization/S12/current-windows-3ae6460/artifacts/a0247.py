"""Bounded actual execution helper: current native future-schema negative only.
The single schema fault is produced through actual trusted test migration owner.
No manually inserted receipts/financial facts or old7d guard claim.
"""
import argparse
from contextlib import ExitStack,closing
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import sys

BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from application.config import load_config
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.scope_lock import ProcessScopeLock,operational_lock_root
from application.platform.supervision import PROCESS_ROLES,process_health
from application.platform.processes import terminate_owned
from storage._sqlite_registry import _connect,_apply_migrations
from strategy.v02.capabilities import _source_revision

FUTURE='9999_future_schema_guard_fixture.sql'
SQL=("-- r7-migration-transaction: atomic\n"
     "CREATE TABLE r7_disposable_future_schema_probe (fixture_marker TEXT NOT NULL);\n")


def run(args):
    # Pin existing successful helper before importing any of its code; never edit it.
    path=BASE/'verify_plat08_crossversion_native.py'
    import hashlib
    def digest(path):return 'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()
    if digest(path)!=args.support_helper_sha256:raise ValueError('Pinned support helper changed')
    spec=importlib.util.spec_from_file_location('plat08_verified_support',path)
    support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)
    if os.name!='nt' or not re.fullmatch('[a-z0-9][a-z0-9-]{0,47}',args.attempt):
        raise ValueError('Bounded fresh Windows attempt required')
    if not re.fullmatch('[0-9a-f]{40}',args.revision) or args.revision==support.OLD_REV:
        raise ValueError('Exact current new native revision required; old7d excluded')
    output=BASE/('plat08-future-'+args.attempt)
    if output.exists():raise ValueError('Preserve previous attempt')
    identity=support.subject(args.package,args.build_result,args.build_sha256,
        args.manifest_sha256,args.exe_sha256,args.revision)
    # Test input writer must match sealed current binary source, not a different
    # historical/working implementation. This is a file commitment, no Git command.
    if _source_revision(ROOT/'src')!=identity['implementation_hash']:
        raise ValueError('Actual source input owner differs from current target')
    create_private_directory(output)
    report=dict(passed=False,scope='CURRENT_WINDOWS_NATIVE_FUTURE_SCHEMA_NEGATIVE_ONLY',
        identity=identity,provider_requests=0,financial_authority='NONE',paper='NOT_STARTED',
        old7d_guard='NOT_CLAIMED',schema_input='ACTUAL_TRUSTED_TEST_MIGRATION_OWNER',
        startup_overall_zero_database_mutation='NOT_CLAIMED_SUPERVISION_MAY_RECORD_FAILURE',
        errors=[],cleanup_errors=[],helper_hash=digest(Path(__file__)),support_helper_hash=args.support_helper_sha256)
    flow=None;done=False
    def guard():
        if (digest(path)!=args.support_helper_sha256 or _source_revision(ROOT/'src')!=identity['implementation_hash']
                or support.subject(args.package,args.build_result,args.build_sha256,
                    args.manifest_sha256,args.exe_sha256,args.revision)!=identity):
            raise ValueError('Frozen actual subject/input producer changed')
    try:
        flow=support.LocalDiagnosticControl(args.package,output/'native-control',
            'CURRENT_NATIVE_FUTURE_SCHEMA_REFUSAL',expected_identity=identity)
        flow.observation['namespace']='LOCAL_RESEARCH'
        with socket.socket() as selected:selected.bind(('127.0.0.1',0));port=selected.getsockname()[1]
        initialized=flow.command('fresh-normal-profile',['init-profile','--config',flow.config,
            '--data-root',flow.data,'--instance-id','future-'+args.attempt,'--port',str(port)],timeout=60)
        if initialized['status']!='PROFILE_CREATED':raise ValueError('Actual profile init required')
        config=load_config(flow.config)
        if (config.database_path!=flow.data/'canonical.sqlite3' or not config.diagnostic_only
                or config.paper_runtime_enabled or config.cloud_root is not None):
            raise ValueError('Exact fresh diagnostic source required')
        flow.start_control('normal-current-initialize');before=support.ledger(flow.config)
        flow.stop_control();guard()
        if not before or FUTURE in before:raise ValueError('Actual normal current baseline required')
        if process_health(config,'control').get('state')!='STOPPED':raise ValueError('Actual normal stop required')
        scripts=output/'private-future-schema-input';create_private_directory(scripts)
        write_private_new(scripts/FUTURE,SQL.encode('utf-8'))
        # Exactly one disposable schema fault, produced by real migration owner.
        # No hand ledger INSERT, arbitrary supplied SQL, DML or positive authority.
        with ExitStack() as locks:
            for role in PROCESS_ROLES:
                locks.enter_context(ProcessScopeLock(role+':'+config.product_instance_id,
                    lock_root=operational_lock_root(config)))
            with closing(_connect(config.database_path,require_existing=True)) as db:
                _apply_migrations(db,migrations_dir=scripts)
        if support.ledger(flow.config)!=before+(FUTURE,):raise ValueError('Actual future migration receipt missing')
        report['fixture_producer']=dict(module='storage._sqlite_registry._apply_migrations',
            script=FUTURE,script_hash=digest(scripts/FUTURE),original_ledger=before,
            future_ledger=before+(FUTURE,),source_implementation=identity['implementation_hash'])
        backup=output/'future-source-normal-backup'
        if flow.command('normal-backup-future-source',['backup-product-data','--config',flow.config,
                '--destination',backup],timeout=90)['status']!='PRODUCT_DATA_BACKUP_VERIFIED':
            raise ValueError('Genuine normal backup prerequisite failed')
        if flow.command('normal-verify-future-backup',['verify-product-backup','--config',flow.config,
                '--destination',backup],timeout=90)['status']!='PRODUCT_DATA_BACKUP_VERIFIED':
            raise ValueError('Genuine normal verify prerequisite failed')
        sealed_source=support.closure(flow.data);sealed_backup=support.closure(backup)
        config_hash=digest(flow.config);canonical_hash=digest(config.database_path)
        refused=flow.command('native-preflight-future-refused',['preflight-product-upgrade',
            '--config',flow.config,'--backup',backup],expected=2,json_result=True,timeout=90)
        if (refused.get('status')!='BLOCKED' or refused.get('reason_codes')!=['UPGRADE_PREFLIGHT_SCHEMA_UNSUPPORTED']
                or refused.get('financial_authority')!='NONE' or refused.get('database_mutations')!=0
                or refused.get('owner_starts')!=0):raise ValueError('Actual typed native refusal required')
        target=output/'must-not-create-restored-generation'
        flow.command('native-complete-restore-future-refused',['restore-product-data',
            '--config',flow.config,'--backup',backup,'--destination',target],expected=2,timeout=90)
        if (target.exists() or support.closure(flow.data)!=sealed_source or support.closure(backup)!=sealed_backup
                or digest(flow.config)!=config_hash):raise ValueError('Preflight/restore refusal changed input')
        # Native serve has a generic sanitized startup diagnostic. Do not invent
        # a MIGRATION_COMPATIBILITY code that it does not publicly disclose.
        flow.command('native-writer-future-start-refused',['serve','--config',flow.config],
            expected=2,timeout=60)
        if digest(config.database_path)!=canonical_hash or support.ledger(flow.config)!=before+(FUTURE,):
            raise ValueError('Native failed startup changed canonical source')
        if support.closure(backup)!=sealed_backup or target.exists() or digest(flow.config)!=config_hash:
            raise ValueError('Native startup changed sealed backup/config/restore target')
        after=support.closure(flow.data)
        report.update(preflight=refused,source_hashes_before_start=sealed_source,
            source_hashes_after_start=after,sealed_backup_hashes=sealed_backup,
            canonical_hash_before_and_after=canonical_hash,config_hash=config_hash,
            preflight_restore_all_source_unchanged=True,startup_canonical_unchanged=True,
            startup_diagnostic='GENERIC_SANITIZED_EXIT2_LOG_RETAINED_NO_TYPED_MIGRATION_CODE')
        # Report actual differences, rather than claiming whole-source zero writes.
        report['source_files_changed_during_startup']=sorted(name for name in set(sealed_source)|set(after)
            if sealed_source.get(name)!=after.get(name))
        guard();done=True
    except Exception as error:report['errors'].append(type(error).__name__+':'+str(error))
    finally:
        if flow is not None:
            try:
                if flow.control is not None:flow.stop_control()
            except Exception as error:report['cleanup_errors'].append(type(error).__name__)
            for owned in flow.owned:
                try:
                    cleanup=terminate_owned(owned,deadline_seconds=5)
                    if not cleanup.reaped:raise ValueError('Owned tree not reaped')
                except Exception as error:report['cleanup_errors'].append(type(error).__name__)
            if flow.control_stream is not None:flow.control_stream.close()
        try:
            guard()
            if done and (digest(config.database_path)!=canonical_hash or support.closure(backup)!=sealed_backup
                    or support.closure(flow.data)!=after or target.exists() or digest(flow.config)!=config_hash):
                raise ValueError('Final preserved byte checks changed')
        except Exception as error:report['errors'].append('FINAL_GUARD:'+type(error).__name__)
        if digest(Path(__file__))!=report['helper_hash']:report['errors'].append('HELPER_CHANGED')
        report['passed']=done and not report['errors'] and not report['cleanup_errors']
        write_private_new(output/'native-future-refusal-result.json',(json.dumps(report,indent=2)+'\n').encode())
    return 0 if report['passed'] else 2


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--attempt',required=True);parser.add_argument('--revision',required=True)
    for name in ('package','build-result'):parser.add_argument('--'+name,type=lambda value:Path(value).absolute(),required=True)
    for name in ('build-sha256','manifest-sha256','exe-sha256','support-helper-sha256'):
        parser.add_argument('--'+name,required=True)
    return run(parser.parse_args())


if __name__=='__main__':raise SystemExit(main())
