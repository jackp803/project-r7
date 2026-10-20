"""Bounded native execution helper. Disposable offline Windows portable upgrade flow.
Root reviews/runs; no old7d downgrade-refusal, full qualification or finance claim.
"""
import argparse
from contextlib import closing
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.error import URLError

BASE=Path(__file__).resolve().parent
PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from application.config import load_config
from application.qualification import _sanitize
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new,require_private
from application.platform.restoration import restoration_status
from application.platform.supervision import _local_path,process_health,config_hash
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from verify_paper_product import PublicFixture

OLD_REV='7d821f29837e95e46bcd5fe32f14d536a28c9aa8'
OLD_IMPL='sha256:e3e79dc1b293a2cb26dbe64df22bf79f815c5810ccf473da76e9f568cf446fc1'
OLD_BUILD='sha256:0edb13bb6df357fb251b23618ba50b25c2ad1fbfe69aa7940486a83da8b4c3f4'
PENDING=('0020_product_funding_publication.sql','0021_product_stop_cleanup_claim.sql',
    '0022_product_trade_finalization.sql','0023_product_entry_decision.sql','0024_product_original_exit.sql')


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while raw:=stream.read(1024*1024):digest.update(raw)
    return 'sha256:'+digest.hexdigest()


def closure(root):
    _local_path(root);result={};size=0
    for path in sorted(root.rglob('*')):
        _local_path(path)
        if path.is_file():
            info=path.stat()
            if info.st_nlink!=1:raise ValueError('Single-link closure required')
            size+=info.st_size
            if size>512*1024**2 or len(result)>=4096:raise ValueError('Bounded closure required')
            result[path.relative_to(root).as_posix()]=sha(path)
        elif not path.is_dir():raise ValueError('Regular closure required')
    return result


def subject(package,build_path,build_hash,manifest_hash,exe_hash,revision):
    _local_path(build_path)
    if build_path.stat().st_size>65536:raise ValueError('Bounded build metadata required')
    for path,expected in ((build_path,build_hash),(package/'distribution.json',manifest_hash),(package/'R7.exe',exe_hash)):
        _local_path(path)
        if not re.fullmatch('sha256:[0-9a-f]{64}',expected) or sha(path)!=expected:
            raise ValueError('Explicit subject hash mismatch')
    if build_path.stat().st_size>65536:raise ValueError('Bounded build metadata required')
    build=json.loads(build_path.read_bytes());facts=verify_distribution(package)
    if (facts['executable_revision']!=revision or build.get('identity')!=facts or
            build.get('source',{}).get('revision')!=revision or build['source'].get('worktree')!='CLEAN'
            or build['source'].get('implementation_hash')!=facts['implementation_hash']):
        raise ValueError('Actual exact clean build binding required')
    return facts


def install_copy(source,target,scope):
    _local_path(target)
    if target.exists() or target.parent!=scope or scope.parent!=PROJECT/'installations':
        raise ValueError('Fresh exact disposable installation required')
    original=closure(source)
    if any(Path(name).name in ('product.json','local-auth.sqlite','restored-product.json') for name in original):
        raise ValueError('Portable package must not copy local configuration/authentication')
    create_private_directory(target)
    for name in original:
        path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
        with (source/name).open('rb') as incoming,path.open('xb') as outgoing:
            shutil.copyfileobj(incoming,outgoing,1024*1024)
    if closure(target)!=original or verify_distribution(target)!=verify_distribution(source):
        raise ValueError('Disposable installed bytes differ')
    return original


def remove_disposable(target,scope,expected,external_roots):
    # No recursive shell/path substitution. Validate exact absolute owned target,
    # all ancestors/reparse points and complete bytes before bounded leaf removal.
    _local_path(target)
    if (not target.is_absolute() or target.parent!=scope or scope.parent!=PROJECT/'installations'
            or target.resolve()!=target or not target.is_relative_to((PROJECT/'installations').resolve())):
        raise ValueError('Disposable removal containment required')
    protected=PROJECT/'installations/windows-7d821f2-clean'
    if target==protected or target.is_relative_to(protected) or protected.is_relative_to(target):
        raise ValueError('Original operator installation is protected')
    for external in external_roots:
        resolved=external.resolve()
        if target.is_relative_to(resolved) or resolved.is_relative_to(target):
            raise ValueError('Removal must be disjoint from external data and backup')
    if closure(target)!=expected:raise ValueError('Changed installation preserved for inspection')
    for name in expected:
        path=target/name;_local_path(path);path.unlink()
    for path in sorted((p for p in target.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
        _local_path(path);path.rmdir()
    target.rmdir()
    if target.exists():raise ValueError('Disposable removal incomplete')


class LocalDiagnosticControl(PublicFixture):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.owned=[]
        self.observation.pop('passed',None)
        self.observation['result_scope']='OBSERVATIONS_ONLY;OUTER_RESULT_DECIDES'

    def _spawn(self,*args,**kwargs):
        if len(self.owned)>=32:raise ValueError('Bounded owned process inventory required')
        owned=spawn_owned(*args,**kwargs)
        self.owned.append(owned)
        return owned

    def command(self,label,args,*,timeout=300,expected=0,argv=None,env=None,json_result=False):
        self.guard();raw_path=self.output/(label+'.raw');log=self.output/(label+'.log')
        owned=None;code=None;cleanup=None
        try:
            with raw_path.open('xb') as stream:
                owned=self._spawn(argv or [str(self.executable),*map(str,args)],cwd=self.output,
                    limits=ResourceLimits(timeout),stdout=stream,stderr=subprocess.STDOUT,env=env or self.env)
                code=owned.wait()
        finally:
            try:
                if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=5)
            finally:
                text=_sanitize(raw_path.read_text(encoding='utf-8',errors='replace'),ROOT)
                text=text.replace(self.password,'<SYNTHETIC_TEST_INPUT>').replace(str(self.output),'<PRIVATE_FIXTURE_ROOT>')
                write_private_new(log,text.encode('utf-8'));raw_path.unlink()
                self.commands.append(dict(command=label,exit_code=code,expected_exit_code=expected,
                    tree_reaped=bool(cleanup and cleanup.reaped),log=log.name,log_hash=sha(log)))
                self.persist()
        self.guard()
        if code!=expected or not cleanup or not cleanup.reaped:raise ValueError('Actual native public command failed')
        return json.loads(text) if expected==0 or json_result else None

    def start_control(self,label):
        self.guard();self.control_log=self.output/(label+'.log');self.control_stream=self.control_log.open('xb')
        self.control=self._spawn([str(self.executable),'serve','--config',str(self.config)],cwd=self.output,
            limits=ResourceLimits(180),stdout=self.control_stream,stderr=subprocess.STDOUT,env=self.env)
        cfg=load_config(self.config);self.origin='http://127.0.0.1:'+str(cfg.control_api_port)
        deadline=time.monotonic()+35
        while time.monotonic()<deadline:
            if self.control.process.poll() is not None:raise ValueError('Diagnostic control exited early')
            try:
                self.health('control',self.control)
                with self.opener.open(self.origin+'/api/v1/auth/status',timeout=1) as response:
                    if response.geturl()!=self.origin+'/api/v1/auth/status':raise ValueError('Loopback redirect refused')
                    auth=json.loads(response.read(2048))
                if auth!=dict(configured=False,namespace='LOCAL_RESEARCH',enrollment='LOCAL_CLI_ONLY'):
                    raise ValueError('Fresh unenrolled ordinary profile required')
                if process_health(cfg,'runtime')['status']!='NOT_STARTED':raise ValueError('Runtime must remain unstarted')
                return
            except (URLError,OSError,ValueError):time.sleep(.1)
        raise ValueError('Diagnostic control readiness deadline')


def ledger(config):
    path=load_config(config).database_path
    # Live owner stores need not have the exact protected backup-copy ACL.
    # The normal backup/preflight paths enforce their own sealed privacy.
    _local_path(path)
    if not path.is_file() or path.stat().st_nlink!=1:raise ValueError('Single-link owner store required')
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=1)) as db:
        db.execute('PRAGMA query_only=ON');db.execute('PRAGMA trusted_schema=OFF')
        rows=db.execute('SELECT migration_name FROM schema_migrations ORDER BY migration_name LIMIT 65').fetchall()
    if len(rows)>64:raise ValueError('Finite migration ledger required')
    return tuple(row[0] for row in rows)


def run(args):
    if os.name!='nt':raise ValueError('Current Windows software flow only')
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,47}',args.attempt):raise ValueError('Finite fresh attempt name required')
    if not re.fullmatch('[0-9a-f]{40}',args.new_revision) or args.new_revision==OLD_REV:
        raise ValueError('Distinct exact new revision required')
    scope=(PROJECT/'installations'/('plat08-'+args.attempt)).absolute()
    output=(BASE/('plat08-native-'+args.attempt)).absolute()
    if output.exists() or scope.exists():raise ValueError('Preserve prior attempts; fresh scope required')
    subjects={}
    def guards():
        for label,revision in (('old',OLD_REV),('new',args.new_revision)):
            value=subject(getattr(args,label+'_package'),getattr(args,label+'_build_result'),
                getattr(args,label+'_build_sha256'),getattr(args,label+'_manifest_sha256'),
                getattr(args,label+'_exe_sha256'),revision)
            if label in subjects and subjects[label]!=value:raise ValueError('Input package changed')
            subjects[label]=value
        if (subjects['old']['implementation_hash']!=OLD_IMPL or subjects['old']['build_hash']!=OLD_BUILD):
            raise ValueError('Original sealed7d identity required')
    guards();create_private_directory(output)
    if not scope.parent.exists():raise ValueError('Existing project installations parent required')
    create_private_directory(scope)
    report=dict(passed=False,scope='CURRENT_WINDOWS_PORTABLE_UPGRADE_SOFTWARE_ONLY',
        started_at=datetime.now(timezone.utc).isoformat(),
        native_schema_refusal='NOT_RUN_SOURCE_REGRESSIONS_SEPARATE',execution='ACTUAL_ONLY_WHEN_ROOT_RUNS',old_identity=subjects['old'],new_identity=subjects['new'],
        provider_requests=0,private_requests=0,financial_authority='NONE',namespace='LOCAL_RESEARCH',
        paper='NOT_STARTED',real_forward='NOT_RUN',old7d_future_schema_refusal='NOT_IMPLEMENTED_NOT_CLAIMED',
        errors=[],cleanup_errors=[],removed=[],helper_hash=sha(Path(__file__)))
    flows=[];sealed={};success=False
    try:
        old_install=scope/'old';new_install=scope/'new'
        old_files=install_copy(args.old_package,old_install,scope);new_files=install_copy(args.new_package,new_install,scope)
        old=LocalDiagnosticControl(old_install,output/'old-control','PLAT08_OLD_NORMAL_DIAGNOSTIC',expected_identity=subjects['old'])
        flows.append(old);old.observation['namespace']='LOCAL_RESEARCH'
        with socket.socket() as bound:bound.bind(('127.0.0.1',0));port=bound.getsockname()[1]
        initialized=old.command('old-init',['init-profile','--config',old.config,'--data-root',old.data,
            '--instance-id','plat08-'+args.attempt,'--port',str(port)],timeout=60)
        if initialized['status']!='PROFILE_CREATED':raise ValueError('Actual original profile initialization required')
        cfg=load_config(old.config)
        if not cfg.diagnostic_only or cfg.paper_runtime_enabled or cfg.cloud_root is not None:
            raise ValueError('Ordinary nonfinancial profile required')
        old.start_control('old-normal-serve');old_names=ledger(old.config)
        if len(old_names)!=19 or old_names[-1]!='0019_paper_operational_selections.sql':
            raise ValueError('Actual sealed7d nineteen migrations required')
        old.stop_control();guards()
        backup=output/'old-normal-backup'
        if old.command('old-backup',['backup-product-data','--config',old.config,'--destination',backup],timeout=90)['status']!='PRODUCT_DATA_BACKUP_VERIFIED':
            raise ValueError('Actual old backup failed')
        old.command('old-verify',['verify-product-backup','--config',old.config,'--destination',backup],timeout=90)
        sealed={'source':closure(old.data),'backup':closure(backup),'config':sha(old.config)}
        report['sealed_old_input_hashes']=sealed
        new=LocalDiagnosticControl(new_install,output/'new-control','PLAT08_NEW_INHIBITED_CLONE',expected_identity=subjects['new'])
        flows.append(new);new.observation['namespace']='LOCAL_RESEARCH'
        preflight=new.command('new-preflight',['preflight-product-upgrade','--config',old.config,'--backup',backup],timeout=90)
        if (preflight['status']!='COMPATIBLE_FOR_INHIBITED_CLONE' or preflight['financial_authority']!='NONE'
                or (preflight['database_mutations'],preflight['owner_starts'])!=(0,0)
                or tuple(preflight['roles']['canonical']['pending'])!=PENDING):
            raise ValueError('Actual target preflight facts differ')
        if (any(preflight['target_provenance'].get(key)!=value for key,value in subjects['new'].items())
                or preflight['source_config_hash']!=config_hash(cfg)
                or preflight['backup_manifest_sha256']!=sha(backup/'manifest.json')
                or preflight['backup_id']!=json.loads((backup/'manifest.json').read_bytes())['backup_id']):
            raise ValueError('Actual target/config/backup subject binding differs')
        if closure(old.data)!=sealed['source'] or closure(backup)!=sealed['backup']:raise ValueError('Preflight mutated input')
        restored=output/'new-inhibited-clone'
        staged=new.command('new-restore',['restore-product-data','--config',old.config,'--backup',backup,
            '--destination',restored],timeout=90)
        if (staged['status']!='PRODUCT_DATA_RESTORE_STAGED' or staged['runtime_new_exposure']!='INHIBITED'
                or staged['financial_authority']!='NONE'):raise ValueError('Fresh inhibited restore required')
        new.config=restored/'restored-product.json';new.data=restored
        if ledger(new.config)!=old_names:raise ValueError('Restore must not apply canonical suffix')
        if restoration_status(load_config(new.config))['status']!='RESTORED_INHIBITED':raise ValueError('Restoration fence required')
        new.start_control('new-normal-serve-clone')
        if ledger(new.config)!=old_names+PENDING:raise ValueError('Normal new startup did not apply exact suffix')
        if restoration_status(load_config(new.config))['status']!='RESTORED_INHIBITED':raise ValueError('Startup must retain inhibition')
        new.stop_control()
        rebackup=output/'new-inhibited-rebackup'
        if new.command('new-rebackup',['backup-product-data','--config',new.config,'--destination',rebackup],timeout=90)['status']!='PRODUCT_DATA_BACKUP_VERIFIED':
            raise ValueError('New inhibited rebackup required')
        new.command('new-reverify',['verify-product-backup','--config',new.config,'--destination',rebackup],timeout=90)
        if (closure(old.data)!=sealed['source'] or closure(backup)!=sealed['backup'] or sha(old.config)!=sealed['config']):
            raise ValueError('Original external source/backup/config changed')
        report['new_rebackup_hashes']=closure(rebackup)
        report['new_restored_config_hash']=sha(new.config)
        guards();external=(output,old.data,backup,restored,rebackup)
        preserved=(closure(old.data),closure(backup),closure(restored),closure(rebackup),sha(old.config))
        for installation,files in ((old_install,old_files),(new_install,new_files)):
            remove_disposable(installation,scope,files,external);report['removed'].append(installation.name)
            if preserved!=(closure(old.data),closure(backup),closure(restored),closure(rebackup),sha(old.config)):
                raise ValueError('Portable removal changed external user data or backups')
        report.update(preflight=preflight,old_migrations=old_names,new_migrations=old_names+PENDING,
            original_source_unchanged=True,original_backup_unchanged=True,portable_removed=['old','new'])
        success=True
    except Exception as error:report['errors'].append(type(error).__name__+':'+str(error))
    finally:
        for flow in flows:
            try:
                if flow.control is not None:flow.stop_control()
                if any(not row.get('tree_reaped',False) for row in flow.commands):raise ValueError('Unreaped owned command')
            except Exception as error:report['cleanup_errors'].append(type(error).__name__)
            finally:
                for owned in flow.owned:
                    try:
                        cleanup=terminate_owned(owned,deadline_seconds=5)
                        report.setdefault('owned_cleanup',[]).append(dict(pid=owned.process.pid,reaped=cleanup.reaped))
                        if not cleanup.reaped:report['cleanup_errors'].append('OWNED_TREE_UNREAPED')
                    except Exception as error:report['cleanup_errors'].append(type(error).__name__)
                if flow.control_stream is not None:
                    flow.control_stream.close();flow.control_stream=None
        try:guards()
        except Exception as error:report['errors'].append('FINAL_GUARD:'+type(error).__name__)
        if sha(Path(__file__))!=report['helper_hash']:report['errors'].append('HELPER_CHANGED')
        report['passed']=success and not report['errors'] and not report['cleanup_errors']
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        write_private_new(output/'plat08-native-result.json',(json.dumps(report,indent=2)+'\n').encode())
    return 0 if report['passed'] else 2


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',required=True);parser.add_argument('--new-revision',required=True)
    for label in ('old','new'):
        for name in ('package','build-result'):parser.add_argument('--'+label+'-'+name,type=lambda x:Path(x).absolute(),required=True)
        for name in ('build-sha256','manifest-sha256','exe-sha256'):parser.add_argument('--'+label+'-'+name,required=True)
    return run(parser.parse_args())


if __name__=='__main__':raise SystemExit(main())
