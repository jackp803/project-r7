"""Current Windows headless diagnostic services through actual public commands.

No credential enrollment, browser, network acquisition, Paper workflow or host
startup/security/sleep changes. Previously captured approved public bytes are
copied as inputs only; this driver never writes a product database or result.
"""
import argparse
from contextlib import closing
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import stat
import subprocess
import sys
import time

TOOLS=Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:sys.path.insert(0,str(TOOLS))
from verify_paper_product import PublicFixture,ROOT,owns_pid,sha
from application.config import load_config,product_namespace
from application.datasets.catalog import canonical,decode,read_local,DatasetCatalog
from application.datasets.public_capture import public_capture_inventory
from application.platform.private_files import create_private_directory,require_private,write_private_new,_filesystem_path
from application.platform.product_backup import _opened_source
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned,process_alive
from application.platform.supervision import process_health,_local_path
from application.qualification import _sanitize

ROLES=('coordinator','control','research')
CAPTURE='datasets/btc-4h-20260801-20261018'
CAPTURE_MANIFEST='sha256:d5a0ae299c78045ff87e321fad7cab50fa73ebb6565f4a4e7f7b439d9cb41f18'
SCOPE='CURRENT_WINDOWS_SOFTWARE_DAEMON_DIAGNOSTIC_ONLY'


def operations_document():
    return dict(schema_version='r7-local-operations-v0.2',workflow_authorized=True,actor='fixturelocal',
        roles=['control','research'],scan_inbox=False,research_policy_ids=[],queue_reports=False,
        interval_seconds=5,restart_budget=2,restart_backoff_seconds=1)


def _token(value):
    return value['pid'],value['generation'],value['process_generation_id']


def require_control_restart(before,after):
    if (any(_token(before[role])!=_token(after[role]) for role in ('coordinator','research'))
            or after['control']['generation']<=before['control']['generation']
            or after['control']['process_generation_id']==before['control']['process_generation_id']
            or after['control']['pid']==before['control']['pid']):
        raise ValueError('Actual isolated control successor not confirmed')


def terminate_verified_pid(owned,pid):
    """Terminate one confirmed member handle, never a program-name/PID guess."""
    if os.name!='nt' or type(pid) is not int or pid<=0 or not owns_pid(owned,pid):
        raise ValueError('Actual Windows owned PID required')
    import ctypes
    from ctypes import wintypes as w
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
    kernel.IsProcessInJob.argtypes=[w.HANDLE,w.HANDLE,ctypes.POINTER(w.BOOL)];kernel.IsProcessInJob.restype=w.BOOL
    kernel.TerminateProcess.argtypes=[w.HANDLE,w.UINT];kernel.TerminateProcess.restype=w.BOOL
    kernel.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];kernel.WaitForSingleObject.restype=w.DWORD
    kernel.CloseHandle.argtypes=[w.HANDLE]
    handle=kernel.OpenProcess(0x100001|0x1000,False,pid)
    if not handle:raise ValueError('Owned crash handle unavailable')
    try:
        inside=w.BOOL()
        # Membership is checked on this same kernel handle, closing PID reuse.
        if (not owned._job or not kernel.IsProcessInJob(handle,owned._job.handle,ctypes.byref(inside)) or not inside.value
                or not kernel.TerminateProcess(handle,73) or kernel.WaitForSingleObject(handle,5000)!=0):
            raise ValueError('Actual single owned process crash unconfirmed')
    finally:kernel.CloseHandle(handle)


class NativeHeadlessFlow(PublicFixture):
    def __init__(self,package,output,*,research_input_root=None):
        super().__init__(Path(package),Path(output),'headless-local-diagnostic')
        self.research_input_root=None if research_input_root is None else Path(research_input_root).absolute()
        self.operations=self.output/'operations.json';self.sessions=[]
        self.observation.update(namespace='LOCAL_RESEARCH',scope=SCOPE,passed=False,sessions=[],cases=[],
            financial_policies='NONE',paper='NOT_STARTED',auth_enrollment='NOT_PERFORMED',browser='NOT_REQUIRED',
            provider_requests=0,provider_responses=0,private_requests=0,host_startup='UNCHANGED',sleep='UNCHANGED',security='UNCHANGED')

    def _mkdir(self,path):
        if not path.is_relative_to(self.output) or path==self.output:raise ValueError('Private exact fixture descendant required')
        current=self.output;require_private(current,directory=True)
        for part in path.relative_to(self.output).parts:
            current/=part;_local_path(current)
            if not current.exists():create_private_directory(current)
            require_private(current,directory=True)

    @staticmethod
    def _hash_file(path):
        digest=hashlib.sha256();size=0
        with _opened_source(path) as stream:
            while chunk:=stream.read(1024*1024):
                size+=len(chunk)
                if size>64*1024*1024:raise ValueError('Bounded approved input required')
                digest.update(chunk)
        return 'sha256:'+digest.hexdigest()

    def _copy_inputs(self):
        source=self.research_input_root
        if source is None or not source.is_absolute() or source.is_relative_to(self.output) or self.output.is_relative_to(source):
            raise ValueError('Explicit disjoint previously captured public input root required')
        base=source/CAPTURE;_local_path(base)
        paths={};pending=[base]
        while pending:
            directory=pending.pop();_local_path(directory)
            for entry in _filesystem_path(directory).iterdir():
                path=directory/entry.name;_local_path(path);information=entry.lstat()
                if stat.S_ISDIR(information.st_mode):pending.append(path)
                elif stat.S_ISREG(information.st_mode) and information.st_nlink==1:
                    paths[path.relative_to(source).as_posix()]=path
                else:raise ValueError('Approved capture cannot contain filesystem aliases')
                if len(paths)+len(pending)>64:raise ValueError('Bounded approved capture required')
        allowed,hashes,dataset=public_capture_inventory(source,CAPTURE,paths)
        if (len(allowed)!=28 or set(paths)!=allowed or dataset!=CAPTURE+'/dataset.json'
                or DatasetCatalog(source).load(dataset).manifest_hash!=CAPTURE_MANIFEST):
            raise ValueError('Exact complete approved public capture required')
        for name,schema in (('engineering-cost.json','r7-replay-cost-policy-v0.2'),('engineering-split.json','r7-split-policy-v0.2')):
            raw=read_local(source,name,65536);document=decode(raw)
            if document.get('schema_version')!=schema or document.get('namespace')!='LOCAL_RESEARCH':
                raise ValueError('Same-namespace explicit engineering diagnostic input required')
            hashes[name]=sha(raw);allowed.add(name)
        for relative in sorted(allowed):
            target=self.data/relative;self._mkdir(target.parent)
            count=0;digest=hashlib.sha256()
            with _opened_source(source/relative) as incoming:
                descriptor=os.open(_filesystem_path(target),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(descriptor,'wb') as outgoing:
                    while chunk:=incoming.read(1024*1024):
                        count+=len(chunk)
                        if count>64*1024*1024:raise ValueError('Bounded public input copy required')
                        outgoing.write(chunk);digest.update(chunk)
                    outgoing.flush();os.fsync(outgoing.fileno())
            require_private(target)
            if 'sha256:'+digest.hexdigest()!=hashes[relative] or self._hash_file(source/relative)!=hashes[relative]:
                raise ValueError('Approved public source changed while copied')
        summary=decode(read_local(self.data,CAPTURE+'/acquisition.json',65536))
        self.source_inputs={source/relative:hashes[relative] for relative in allowed}
        self.observation['research_input']=dict(scope='PREVIOUS_CAPTURE_INPUT_ONLY;NO_NEW_PROVIDER_CALLS',
            manifest_hash=CAPTURE_MANIFEST,public_capture_files=28,engineering_policy_files=2,
            prior_capture_requests=summary['provider_requests'],prior_capture_responses=summary['provider_responses'],
            files=[dict(relative_path=relative,sha256=hashes[relative]) for relative in sorted(allowed)])
        return dataset

    def _setup(self):
        if self.research_input_root is None:raise ValueError('Explicit approved public research input root required')
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        self.command('init-headless',['init-profile','--config',self.config,'--data-root',self.data,
            '--instance-id','native-headless-diagnostic','--port',port,'--execution-mode','LOCAL_RESEARCH'])
        self._mkdir(self.data/'worker-logs')
        dataset=self._copy_inputs()
        selection=dict(schema_version='r7-owner-selections-v0.2',cloud_root_id=None,research_policies={
            'engineering-development-only':dict(dataset_ref=dataset,split_policy_ref='engineering-split.json',cost_policy_ref='engineering-cost.json',
                selection_mode='DIAGNOSTIC_DEVELOPMENT_ONLY',requested_dataset_profile='okx-btc-4h',
                requested_validation_profile='diagnostic',requested_robustness_profile='diagnostic')})
        path=self.output/'engineering-selection.json';write_private_new(path,(canonical(selection)+'\n').encode())
        result=self.command('select-headless-diagnostic',['configure-research','--config',self.config,'--selection-profile',path])
        if result.get('status')!='RESEARCH_CONFIGURED' or result.get('namespace')!='LOCAL_RESEARCH':raise ValueError('Normal diagnostic research selection missing')
        write_private_new(self.operations,(canonical(operations_document())+'\n').encode())
        config=load_config(self.config)
        if product_namespace(config)!='LOCAL_RESEARCH' or not config.diagnostic_only or config.paper_runtime_enabled or config.cloud_root is not None:
            raise ValueError('Headless test cannot acquire Paper or cloud authority')
        self.config_before=sha(self.config.read_bytes());self.operations_before=sha(self.operations.read_bytes())

    def _snapshot(self,owned):
        self.guard()
        if sha(self.config.read_bytes())!=self.config_before or sha(self.operations.read_bytes())!=self.operations_before:
            raise ValueError('Native headless configuration changed')
        return {role:self.health(role,owned) for role in ROLES}

    def _wait_ready(self,owned,*,before=None,control_restart=False):
        end=time.monotonic()+40
        while time.monotonic()<end:
            if owned.process.poll() is not None:raise ValueError('Actual native coordinator exited before readiness')
            try:
                current=self._snapshot(owned)
                if control_restart:require_control_restart(before,current)
                elif before is not None and any(current[role]['generation']<=before[role]['generation'] or
                        current[role]['process_generation_id']==before[role]['process_generation_id'] for role in ROLES):
                    raise ValueError('Actual recovered service generations missing')
                return current
            except (ValueError,OSError,sqlite3.Error):time.sleep(.1)
        raise ValueError('Actual bounded coordinator/service readiness not observed')

    def _launch(self,label):
        self.guard();log=self.output/(label+'.log');stream=log.open('xb')
        session=dict(label=label,log=log,stream=stream,owned=None,closed=False)
        self.sessions.append(session)
        session['owned']=spawn_owned([str(self.executable),'run-product','--config',str(self.config),
            '--operations-profile',str(self.operations),'--maximum-cycles','500'],cwd=self.output,
            limits=ResourceLimits(180),stdout=stream,stderr=subprocess.STDOUT,env=self.env)
        return session

    def _contender(self,owned,before):
        label='second-coordinator-denied'
        self.command(label,['run-product','--config',self.config,'--operations-profile',self.operations,'--maximum-cycles','1'],expected=2)
        raw=(self.output/(label+'.log')).read_bytes()
        if len(raw)>65536:raise ValueError('Bounded native denial diagnostic required')
        lines=raw.decode('utf-8').strip().splitlines()
        diagnostic=json.loads(lines[-1]) if lines else {}
        if (diagnostic.get('schema_version')!='r7-startup-diagnostic-v0.2' or diagnostic.get('error_kind')!='OWNER_SCOPE_BUSY'
                or any(_token(self._snapshot(owned)[role])!=_token(before[role]) for role in ROLES)):
            raise ValueError('Exact native scope denial without generation mutation required')
        self.observation['cases'].append(dict(case='SECOND_COORDINATOR_DENIED',diagnostic=diagnostic,original_tokens_unchanged=True))

    def _crash_role(self,owned,role,before):
        self.guard();actual=self.health(role,owned)
        if _token(actual)!=_token(before[role]):raise ValueError('Owned role incarnation changed before requested crash')
        terminate_verified_pid(owned,actual['pid'])
        self.observation['cases'].append(dict(case='ACTUAL_'+role.upper()+'_PROCESS_CRASH',pid=actual['pid'],
            generation=actual['generation'],process_generation_id=actual['process_generation_id'],method='VERIFIED_OWNED_KERNEL_TERMINATE_PROCESS',
            observed_at=datetime.now(timezone.utc).isoformat()))

    @staticmethod
    def _dead(pids):
        end=time.monotonic()+10
        while time.monotonic()<end:
            if not any(process_alive(pid) for pid in pids):return
            time.sleep(.1)
        raise ValueError('Actual owned child PIDs did not die after coordinator crash/stop')

    def _finish(self,session,*,graceful):
        owned=session['owned'];code=owned.wait(timeout=15)
        if not owned.termination_report or not owned.termination_report.reaped:raise ValueError('Actual native owned tree not reaped')
        session['stream'].flush()
        if graceful:
            raw=session['log'].read_bytes()
            if len(raw)>1024*1024:raise ValueError('Bounded native coordinator result required')
            lines=raw.decode('utf-8',errors='replace').strip().splitlines();result=json.loads(lines[-1]) if lines else {}
            if (code!=0 or result.get('status')!='STOPPED' or result.get('all_owned_trees_reaped') is not True
                    or result.get('financial_authority')!='NONE' or result.get('exposure_status')!='NOT_ASSERTED'
                    or result.get('host_settings')!='UNCHANGED' or result.get('schedule') is not None
                    or set(result.get('roles',{}))!={'control','research'}
                    or any(value.get('status')!='STOPPED' or value.get('forced_stop') is not False or value.get('tree_reaped') is not True
                           or value.get('exit_code')!=0 for value in result['roles'].values())):
                raise ValueError('Actual graceful coordinator/child stop unconfirmed')
            session['result']=result
        elif code==0:raise ValueError('Actual coordinator crash must have nonzero exit')
        self._close_session(session)

    def _close_session(self,session):
        if session['closed']:return
        owned=session['owned'];cleanup=None
        try:
            if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=5)
        finally:
            session['stream'].close()
            raw=session['log'].read_bytes()
            if len(raw)>1024*1024:raise ValueError('Bounded native coordinator log required')
            text=_sanitize(raw.decode('utf-8',errors='replace'),ROOT).replace(str(self.output),'<PRIVATE_NATIVE_ROOT>')
            if self.password:text=text.replace(self.password,'<SYNTHETIC_UNUSED_INPUT>')
            session['log'].write_text(text,encoding='utf-8')
            reaped=bool(cleanup and cleanup.reaped)
            self.observation['sessions'].append(dict(label=session['label'],log=session['log'].name,
                log_hash=sha(session['log'].read_bytes()),tree_reaped=reaped,result=session.get('result'),
                termination_reason=getattr(cleanup,'reason',None)))
            session['closed']=reaped;self.persist()
        if not session['closed']:raise ValueError('Native coordinator cleanup not confirmed')

    def _stop(self,session,before,label):
        receipt=self.command(label,['stop-product','--config',self.config,'--role','coordinator'])
        if (receipt.get('status')!='COOPERATIVE_STOP_REQUESTED' or receipt.get('process_generation_id')!=before['coordinator']['process_generation_id']
                or receipt.get('financial_authority')!='NONE' or receipt.get('exposure_status')!='NOT_ASSERTED'):
            raise ValueError('Exact actual cooperative coordinator stop receipt required')
        self._finish(session,graceful=True)
        self._dead([before[role]['pid'] for role in ROLES])
        config=load_config(self.config)
        stopped={role:process_health(config,role) for role in ROLES}
        if any(value.get('state')!='STOPPED' or _token(value)!=_token(before[role]) for role,value in stopped.items()):
            raise ValueError('Actual stopped role identities differ')
        again=self.command(label+'-repeat',['stop-product','--config',self.config,'--role','coordinator'])
        if again.get('status')!='NO_CURRENT_PROCESS' or any(_token(process_health(config,role))!=_token(before[role]) for role in ROLES):
            raise ValueError('Repeated stop mutated actual stopped owner identities')
        self.observation['cases'].append(dict(case='GRACEFUL_COORDINATOR_AND_CHILDREN_STOPPED',repeat_status=again['status'],exposure_status='NOT_ASSERTED'))

    def _assert_idle(self):
        for name,table in (('queue.sqlite','research_queue_jobs'),('canonical.sqlite3','paper_process_runs')):
            path=self.data/name;_local_path(path)
            with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
                if db.execute('SELECT count(*) FROM '+table).fetchone()[0]!=0:raise ValueError('Diagnostic daemon invented research jobs or Paper runs')
        if process_health(load_config(self.config),'runtime').get('status')!='NOT_STARTED':raise ValueError('Diagnostic daemon started runtime')

    def _exercise(self):
        first=self._launch('coordinator-first');before=self._wait_ready(first['owned'])
        self.observation['initial_roles']={role:{key:value for key,value in health.items() if key in
            ('pid','generation','process_generation_id','role','config_hash','build_hash','implementation_hash','status')} for role,health in before.items()}
        self._contender(first['owned'],before)
        self._crash_role(first['owned'],'control',before)
        successor=self._wait_ready(first['owned'],before=before,control_restart=True)
        self.observation['cases'].append(dict(case='CONTROL_RESTARTED_WITH_RESEARCH_COORDINATOR_UNCHANGED',
            old_control_generation=before['control']['generation'],new_control_generation=successor['control']['generation']))
        self._assert_idle();self._stop(first,successor,'stop-first-coordinator')
        second=self._launch('coordinator-crash');second_roles=self._wait_ready(second['owned'],before=successor)
        self._crash_role(second['owned'],'coordinator',second_roles)
        self._dead([second_roles[role]['pid'] for role in ROLES])
        self._finish(second,graceful=False)
        third=self._launch('coordinator-recovered');third_roles=self._wait_ready(third['owned'],before=second_roles)
        self._assert_idle();self._stop(third,third_roles,'stop-recovered-coordinator')
        self.observation['cases'].append(dict(case='COORDINATOR_CRASH_TREE_REAPED_AND_FRESH_GENERATIONS_RECOVERED',
            coordinator_generation_before=second_roles['coordinator']['generation'],coordinator_generation_after=third_roles['coordinator']['generation']))
        if any(self._hash_file(path)!=expected for path,expected in self.source_inputs.items()):raise ValueError('Approved public input source changed')
        self.guard()

    def _cleanup_all(self):
        failed=False
        for session in self.sessions:
            if not session['closed']:
                try:self._close_session(session)
                except BaseException:failed=True
        if failed:raise ValueError('One or more exact native owned handles remain unconfirmed')

    def run(self):
        passed=False
        try:
            self._setup();self._exercise();passed=True
        finally:
            try:self._cleanup_all()
            except BaseException:
                passed=False
                raise
            finally:
                self.observation['passed']=passed
                try:self.persist()
                except BaseException:
                    self.observation['passed']=False
                    raise
        return self.observation


def verify(package,output,*,research_input_root=None):
    try:
        if os.name!='nt':raise ValueError('Current Windows diagnostic driver required')
        result=NativeHeadlessFlow(package,output,research_input_root=research_input_root).run()
        return 0 if result['passed'] else 2
    except Exception:
        print('Native headless diagnostic verification failed; retain the private attempt',file=sys.stderr)
        return 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--research-input-root',type=Path,required=True)
    args=parser.parse_args()
    raise SystemExit(verify(args.package_root,args.output,research_input_root=args.research_input_root))
