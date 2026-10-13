"""Fixed native Paper observations through actual public product commands.

Every invocation creates fresh private FIXTURE data outside the installation.
Unimplemented native observations are retained as NOT_RUN and fail the group;
source tests, old demos and an exit code never substitute for native evidence.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import build_opener, HTTPRedirectHandler, HTTPCookieProcessor, ProxyHandler, Request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from application.config import load_config
from application.datasets.catalog import read_local
from application.paper.inventory import NATIVE_ASSERTIONS,current_target
from application.paper.qualification import artifact_bytes
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new,require_private
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.platform.supervision import process_health,config_hash
from application.qualification import _sanitize
from registry.product_assessment import canonical
from storage.paper_process import open_paper_process_journal
from storage.runtime import open_paper_runtime_journal
from native_console import enroll


def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args):raise ValueError('Native fixture redirect denied')


def owns_pid(owned,pid):
    """An actual supervisor PID must belong to this private kernel scope."""
    if os.name!='nt':return os.getpgid(pid)==owned.process.pid
    import ctypes
    from ctypes import wintypes as w
    class Pids(ctypes.Structure):
        _fields_=[('assigned',w.DWORD),('listed',w.DWORD),('pids',ctypes.c_size_t*256)]
    result=Pids()
    if not owned._job.kernel.QueryInformationJobObject(owned._job.handle,3,ctypes.byref(result),ctypes.sizeof(result),None):
        raise ValueError('Actual native owned PID inventory unavailable')
    return pid in list(result.pids)[:result.listed]


class PublicFixture:
    def __init__(self,package,output,scenario,*,expected_identity=None):
        self.package,self.output,self.scenario=package,output,scenario
        self.identity=verify_distribution(package)
        if expected_identity is not None and self.identity!=expected_identity:
            raise ValueError('Native scenario changed the original group subject')
        manifest=json.loads((package/'distribution.json').read_bytes())
        self.executable=package/manifest['entrypoint']
        create_private_directory(output)
        self.config=output/'product.json';self.data=output/'data';self.cloud=output/'synthetic-cloud'
        # Deliberate repeated keyboard input catches OS-console coalescing.
        self.password='a'*12+secrets.token_hex(24)
        self.env={k:os.environ[k] for k in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if k in os.environ}
        self.env.update(PATH='',PYTHONUTF8='1')
        self.commands=[];self.browser=[];self.control=None;self.control_stream=None;self.control_log=None
        self.observation=dict(scenario=scenario,identity=self.identity,passed=False,commands=self.commands,
            browser=self.browser,provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
            namespace='FIXTURE',real_forward='NOT_ISSUED',ordinary_paper='NOT_QUALIFIED')
        self.opener=build_opener(ProxyHandler({}),NoRedirect())

    def guard(self):
        if verify_distribution(self.package)!=self.identity:raise ValueError('Native installation changed')

    def persist(self):
        # This actual attempt remains mutable until completed; final hashes are
        # bound by the owning producer after the command and all children exit.
        path=self.output/'observations.json'
        raw=(canonical(self.observation)+'\n').encode('utf-8')
        if not path.exists():write_private_new(path,raw)
        else:
            require_private(path)
            with path.open('wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())

    def command(self,label,args,*,timeout=300,expected=0,argv=None,env=None):
        self.guard();raw_path=self.output/(label+'.raw');log=self.output/(label+'.log')
        with raw_path.open('xb') as stream:
            owned=spawn_owned(argv or [str(self.executable),*map(str,args)],cwd=self.output,
                limits=ResourceLimits(timeout),stdout=stream,stderr=subprocess.STDOUT,env=env or self.env)
            code=owned.wait()
        text=_sanitize(raw_path.read_text(encoding='utf-8',errors='replace'),ROOT)
        text=text.replace(self.password,'<SYNTHETIC_TEST_INPUT>').replace(str(self.output),'<PRIVATE_FIXTURE_ROOT>')
        write_private_new(log,text.encode('utf-8'));raw_path.unlink()
        self.commands.append(dict(command=label,exit_code=code,expected_exit_code=expected,
            tree_reaped=owned.termination_report.reaped,log=log.name,log_hash=sha(log.read_bytes())))
        self.persist();self.guard()
        if code!=expected or not owned.termination_report.reaped:raise ValueError('Actual native public command failed')
        return json.loads(text) if expected==0 else None

    def health(self,role,owned):
        config=load_config(self.config);health=process_health(config,role)
        try:
            with closing(sqlite3.connect((config.local_data_root/'process-supervision.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
                row=db.execute('SELECT identity_json,state,generation,process_generation_id FROM process_sessions WHERE role=?',(role,)).fetchone()
            identity=json.loads(row[0])
        except (OSError,ValueError,TypeError,sqlite3.Error) as error:
            raise ValueError('Actual native supervisor observation unavailable') from error
        if (health['status']!='RECENT_HEARTBEAT' or not owns_pid(owned,health['pid'])
                or health['config_hash']!=config_hash(config)
                or row[1]!='RUNNING' or row[2]!=health['generation'] or row[3]!=health['process_generation_id']
                or any(identity.get(k)!=v for k,v in self.identity.items())
                or any(identity.get(k)!=health[k] for k in ('pid','generation','process_generation_id','config_hash','product_instance_id'))):
            raise ValueError('Exact actual native supervisor observation required')
        return health

    def start_control(self,label):
        self.guard();self.control_log=self.output/(label+'.log')
        self.control_stream=self.control_log.open('xb')
        self.control=spawn_owned([str(self.executable),'serve','--config',str(self.config)],cwd=self.output,
            limits=ResourceLimits(600),stdout=self.control_stream,stderr=subprocess.STDOUT,env=self.env)
        deadline=time.monotonic()+35;config=load_config(self.config)
        self.origin=f'http://127.0.0.1:{config.control_api_port}'
        while time.monotonic()<deadline:
            if self.control.process.poll() is not None:raise ValueError('Native control exited before readiness')
            try:
                self.health('control',self.control)
                with self.opener.open(self.origin+'/api/v1/auth/status',timeout=1) as response:
                    if response.geturl()!=self.origin+'/api/v1/auth/status':raise ValueError('Unexpected native URL')
                    auth=json.loads(response.read(2048))
                if auth!=dict(configured=True,namespace='FIXTURE',enrollment='LOCAL_CLI_ONLY'):
                    raise ValueError('Actual enrolled native FIXTURE required')
                return
            except (URLError,OSError,ValueError):time.sleep(.1)
        raise ValueError('Actual native control readiness deadline')

    def stop_control(self):
        if self.control is None:return
        owned=self.control;graceful=False
        try:
            self.command('stop-'+self.control_log.stem,['stop-product','--config',self.config,'--role','control'],timeout=45)
            code=owned.wait(timeout=10)
            graceful=code==0 and process_health(load_config(self.config),'control')['state']=='STOPPED'
            if not graceful:raise ValueError('Native managed control stop unconfirmed')
        finally:
            cleanup=terminate_owned(owned,deadline_seconds=5)
            self.control_stream.close();self.control_stream=None;self.control=None
            raw=self.control_log.read_bytes()
            sanitized=_sanitize(raw.decode('utf-8',errors='replace'),ROOT).replace(self.password,'<SYNTHETIC_TEST_INPUT>')
            self.control_log.write_text(sanitized,encoding='utf-8')
            self.commands.append(dict(command=self.control_log.stem,tree_reaped=cleanup.reaped,
                managed_stop=graceful,forced_cleanup=not graceful,log=self.control_log.name,log_hash=sha(self.control_log.read_bytes())))
            self.persist()
            if not cleanup.reaped:raise ValueError('Native control tree not reaped')

    def rendered(self,stage):
        self.health('control',self.control)
        node=Path('C:/Program Files/nodejs/node.exe') if os.name=='nt' else Path('/usr/bin/node')
        env={**self.env,'R7_SYNTHETIC_PASSWORD':self.password}
        result=self.command('browser-'+stage,[],argv=[str(node),str(ROOT/'tools/paper_native_browser.mjs'),
            str(ROOT),self.origin,stage,str(self.output),self.scenario],env=env,timeout=60)
        if (result['passed'] is not True or result['remote_requests']!=0 or result['namespace']!='FIXTURE'
                or sha(read_local(self.output,result['screenshot'],8*1024*1024))!=result['screenshot_sha256']):
            raise ValueError('Actual rendered native browser observation invalid')
        self.browser.append(result);self.persist();self.health('control',self.control)
        return result

    def journal(self,run):
        with open_paper_process_journal(load_config(self.config).database_path,require_existing=True) as journal:
            return journal.recover(run)

    def run(self):
        try:
            with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
            self.command('init',['init-profile','--config',self.config,'--data-root',self.data,'--cloud-root',self.cloud,
                '--instance-id','pqr-public-'+self.scenario,'--port',port,'--execution-mode','FIXTURE'])
            generated=self.command('prepare',['prepare-fixture','--config',self.config,'--scenario',self.scenario])
            if generated['execution_evidence']!='NOT_RUN':raise ValueError('Fresh unexecuted fixture input required')
            self.command('research-selection',['configure-research','--config',self.config,'--selection-profile',self.data/'fixture-inputs/selection.json'])
            self.observation['enrollment']=enroll(self.executable,self.config,self.password,env=self.env)
            self.start_control('control-research');enqueued=self.rendered('research-enqueue')
            research=self.command('research-worker',['research-worker','--config',self.config,'--once'])
            if (research['status']!='JOB_FINISHED' or not research['tree_reaped'] or
                    research['parent_pid']==research['child_pid']):raise ValueError('Actual independent native research child required')
            actual=self.rendered('research-result')
            if actual['research_job_id']!=enqueued['research_job_id']:raise ValueError('Research job changed')
            self.stop_control()
            self.command('paper-selection',['configure-paper','--config',self.config,'--selection-profile',self.data/'fixture-inputs/paper-selection.json'])
            self.start_control('control-paper')
            if self.scenario!='positive':
                denied=self.rendered('paper-denied')
                if denied['paper_runs_after']!=0 or not denied['registry_subject_unchanged']:
                    raise ValueError('Negative native case changed owner state')
            else:
                started=self.rendered('paper-start');run=started['run_id']
                first=self.command('paper-worker-first',['paper-worker','--config',self.config,'--maximum-ticks','2'])
                protected=self.journal(run);position=protected.state['runtime']['position']
                if (first['run_failures'] or protected.process_generation!=1 or
                        position['lifecycle_state']!='OPEN_PROTECTED'):raise ValueError('Actual native protected position missing')
                paused=self.rendered('paper-pause')
                if paused['position']!=position:raise ValueError('Native pause altered original position')
                second=self.command('paper-worker-successor',['paper-worker','--config',self.config,'--maximum-ticks','4'])
                finished=self.rendered('paper-closed');closed=self.journal(run)
                from decimal import Decimal
                if (second['run_failures'] or second['process_generation']!=first['process_generation']+1
                        or closed.binding!=protected.binding or closed.state['runtime']['exit_anchor']!=protected.state['runtime']['exit_anchor']
                        or closed.state['runtime']['position']['position_id']!=position['position_id']
                        or Decimal(closed.state['runtime']['position']['actual_quantity'])!=0
                        or finished['forward']['real_elapsed_ns']!=0):raise ValueError('Native successor/flat original binding failed')
                with open_paper_runtime_journal(load_config(self.config).database_path,require_existing=True) as journal:
                    graph=journal.recover(position_id=position['position_id'])
                if (graph.status!='READY' or len(graph.fills)!=2 or
                        graph.trade_result.payload!=closed.state['runtime']['closed_trades'][0]):
                    raise ValueError('Actual native canonical ACK/fill/TradeResult graph missing')
                self.observation.update(native_direction=position['side'],canonical_fills=len(graph.fills),canonical_trades=1,
                    original_protection_preserved=True,real_elapsed_ns=0)
            self.observation.update(passed=True,lifecycle=actual['lifecycle'],sealed_oos=actual['sealed_oos'])
        finally:
            self.stop_control();self.persist();self.guard()
        return self.observation


class NativeExpiryFlow(PublicFixture):
    """Fixed fresh public native cases; faults change unexecuted inputs only."""
    CASES=('intake-faults','discovery-expired','enqueue-expired','research-checkpoint-expired',
           'pre-entry-expired','protected-expired','checkpoint-cancel')

    def __init__(self,package,output,native_case,*,expected_identity=None):
        if native_case not in self.CASES:raise ValueError('Fixed native expiry case required')
        super().__init__(package,output,'positive',expected_identity=expected_identity)
        self.native_case=native_case;self.csrf=None;self.requests=[]
        self.opener=build_opener(ProxyHandler({}),NoRedirect(),HTTPCookieProcessor(CookieJar()))
        self.observation.update(case=native_case,requests=self.requests)

    def start_control(self,label):
        super().start_control(label)
        actual=self.health('control',self.control)
        self.api_control_identity={key:actual[key] for key in ('pid','generation','process_generation_id','config_hash')}

    def require_api_control(self):
        actual=self.health('control',self.control)
        if any(actual[key]!=value for key,value in self.api_control_identity.items()):
            raise ValueError('Actual native control identity changed')

    @staticmethod
    def forward_elapsed(payload):
        forward=payload.get('forward_observations')
        if not isinstance(forward,dict) or type(forward.get('real_elapsed_ns')) is not int:
            raise ValueError('Actual Paper read port forward observations required')
        return forward['real_elapsed_ns']

    def request(self,method,path,body=None,*,expected=200):
        if not path.startswith('/api/v1/'):raise ValueError('Fixed loopback product API required')
        self.require_api_control()
        headers={'Origin':self.origin}
        if body is not None:headers['Content-Type']='application/json'
        if self.csrf is not None:headers['x-r7-csrf']=self.csrf
        request=Request(self.origin+path,data=None if body is None else canonical(body).encode(),headers=headers,method=method)
        try:response=self.opener.open(request,timeout=15)
        except HTTPError as error:response=error
        with response:
            raw=response.read(1024*1024+1);status=response.code
            if response.geturl()!=self.origin+path or len(raw)>1024*1024:raise ValueError('Bounded native response required')
        self.require_api_control()
        # Authentication bodies, cookies and CSRF never enter evidence.
        self.requests.append(dict(method=method,path=path,status=status,actual_at=datetime.now(timezone.utc).isoformat()))
        self.persist()
        if status!=expected:raise ValueError('Actual native API status mismatch: '+path+':'+str(status))
        return json.loads(raw)

    def view(self,path):return self.request('GET','/api/v1/'+path)['data']

    def login(self):
        grant=self.request('POST','/api/v1/auth/login',dict(command_id='login-'+secrets.token_hex(12),
            expected_revision=0,username='native-fixture-owner',password=self.password))
        if grant['namespace']!='FIXTURE' or grant['actor']!='native-fixture-owner':raise ValueError('Actual isolated native actor required')
        self.csrf=grant['csrf_token']

    def setup(self):
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        self.command('init',['init-profile','--config',self.config,'--data-root',self.data,'--cloud-root',self.cloud,
            '--instance-id','pqr-04-'+self.native_case,'--port',port,'--execution-mode','FIXTURE'])
        temporal={'pre-entry-expired':'paper-expire-before-entry','protected-expired':'paper-expire-after-protection'}.get(self.native_case,
            'none' if self.native_case=='intake-faults' else 'research-expire-before-robustness')
        self.generated=self.command('prepare',['prepare-fixture','--config',self.config,'--scenario','positive','--temporal-case',temporal])
        if self.generated['execution_evidence']!='NOT_RUN':raise ValueError('Fresh native unexecuted inputs required')
        self.command('research-selection',['configure-research','--config',self.config,'--selection-profile',self.data/'fixture-inputs/selection.json'])
        self.observation['enrollment']=enroll(self.executable,self.config,self.password,env=self.env)
        self.start_control('control-research');self.login()

    def scan(self,*,body=None):
        if body is None:body=dict(command_id='scan-'+secrets.token_hex(12),expected_revision=self.view('overview')['scan_revision'])
        receipt=self.request('POST','/api/v1/research/scan',body)
        # Observation of the actual formal owner receipt; never a database write.
        uri=(self.data/'control-settings.sqlite').as_uri()+'?mode=ro'
        with closing(sqlite3.connect(uri,uri=True)) as db:
            row=db.execute('SELECT summary_json FROM control_scan_receipts WHERE command_id=?',(body['command_id'],)).fetchone()
        if row is None:raise ValueError('Actual native scan receipt missing')
        summary=json.loads(row[0]);self.observation.setdefault('scans',[]).append(summary);self.persist()
        return body,receipt,summary

    def submission(self):return self.view('submissions/'+self.generated['submission_id'])['payload']

    def enqueue(self):
        body=dict(command_id='enqueue-'+secrets.token_hex(12),expected_revision=self.submission()['revision'],
            submission_id=self.generated['submission_id'],policy_id=self.generated['policy_id'])
        receipt=self.request('POST','/api/v1/research/runs',body,expected=202)
        return body,receipt,receipt['effect_ref'].removeprefix('research-job:')

    def research(self):
        result=self.command('research-worker',['research-worker','--config',self.config,'--once'],timeout=180)
        if result['status']!='JOB_FINISHED' or not result['tree_reaped'] or result['parent_pid']==result['child_pid']:
            raise ValueError('Actual independent native research child required')
        return result

    def wait_original_expiry(self):
        from application.fixtures.temporal import utc
        document=json.loads(read_local(self.data,'fixture-inputs/temporal.json',65536))
        upper=utc(document['validity']['until']);started=datetime.now(timezone.utc);deadline=time.monotonic()+125
        if (upper-started).total_seconds()>120:raise ValueError('Original bounded native expiry required')
        while datetime.now(timezone.utc)<=upper:
            self.health('control',self.control)
            if time.monotonic()>=deadline:raise ValueError('Actual native expiry wait deadline')
            time.sleep(min(.25,max(.01,(upper-datetime.now(timezone.utc)).total_seconds())))
        self.observation['expiry_wait']=dict(original_validity=document['validity'],clock='ACTUAL_UTC',
            actual_started_at=started.isoformat(),actual_finished_at=datetime.now(timezone.utc).isoformat())
        self.persist()

    def intake_faults(self):
        folder=self.cloud/'inbox/strategies'/self.generated['submission_id'];manifest=folder/'manifest.json';payload=folder/'strategy.json'
        original=artifact_bytes(self.cloud,manifest.relative_to(self.cloud).as_posix())
        definition=artifact_bytes(self.cloud,payload.relative_to(self.cloud).as_posix())
        def write(path,raw):
            require_private(path)
            # Exact fresh authored fault inputs only; accepted snapshots remain immutable.
            with path.open('wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        write(manifest,b'{');malformed=self.scan()[2]
        if malformed['blocked']!=1 or self.submission()['receipt'] is not None:raise ValueError('Malformed submission accepted')
        unsupported=json.loads(original);unsupported['schema_version']='r7-package-unsupported-v999'
        write(manifest,canonical(unsupported).encode());self.scan()
        if self.submission()['latest_observation']['reason']!='UNSUPPORTED_PACKAGE_VERSION':raise ValueError('Unsupported package not denied')
        write(manifest,original);payload.unlink();self.scan()
        if self.submission()['latest_observation']['state']!='INCOMPLETE_SYNC':raise ValueError('Partial sync not retained')
        retry=self.scan()[2]
        if retry['results'][0]['state']!='SYNC_RETRY_WAIT':raise ValueError('Actual bounded sync retry missing')
        write_private_new(payload,definition);time.sleep(5.1)
        body,receipt,_=self.scan();accepted=self.submission()
        if accepted['receipt'] is None:raise ValueError('Completed actual sync not accepted')
        before=self.view('overview')['scan_revision'];replay=self.scan(body=body)[1]
        if replay!=receipt or self.view('overview')['scan_revision']!=before:raise ValueError('Completed scan replay changed effects')
        conflict=json.loads(original);conflict['created_by']='SYNTHETIC FIXTURE changed authored input'
        write(manifest,canonical(conflict).encode());self.scan();observed=self.submission()
        if observed['latest_observation']['state']!='CONFLICT' or observed['receipt']!=accepted['receipt']:
            raise ValueError('Conflicting submission changed accepted receipt')
        write(manifest,original);self.scan()
        if len(self.view('strategies')['items'])!=1:raise ValueError('Idempotent scan duplicated actual strategy')
        self.observation.update(original_receipt_preserved=True,completed_same_id_idempotent=True,
            malformed_denied=True,unsupported_denied=True,partial_retry_completed=True,conflict_denied=True)

    def retained_checkpoint_observations(self):
        paths=sorted((self.data/'fixture-observations').glob('*.json'))
        rows=[]
        for path in paths:
            raw=artifact_bytes(self.data,path.relative_to(self.data).as_posix())
            row=json.loads(raw);rows.append(row)
            target=self.output/path.name;write_private_new(target,raw)
        self.observation['checkpoint_observations']=rows;self.persist()
        return rows

    def cancel_checkpoint(self,run):
        self.guard();raw_path=self.output/'research-worker.raw'
        owned=None;cleanup=None;code=None;failure=None
        try:
            with raw_path.open('xb') as stream:
                owned=spawn_owned([str(self.executable),'research-worker','--config',str(self.config),'--once'],cwd=self.output,
                    limits=ResourceLimits(180),stdout=stream,stderr=subprocess.STDOUT,env=self.env)
                deadline=time.monotonic()+60
                while not list((self.data/'fixture-observations').glob('*-start.json')):
                    if owned.process.poll() is not None or time.monotonic()>=deadline:raise ValueError('Native actual checkpoint not reached')
                    time.sleep(.1)
                job=self.view('research/runs/'+run);started=time.monotonic()
                self.request('POST','/api/v1/research/runs/'+run+'/cancel',dict(command_id='cancel-'+secrets.token_hex(12),expected_revision=job['revision']))
                code=owned.wait(timeout=15)
                self.observation['cancel_elapsed_seconds']=time.monotonic()-started
        except Exception as error:
            failure=type(error).__name__;raise
        finally:
            try:
                if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=5)
            finally:
                if raw_path.exists():
                    raw=artifact_bytes(self.output,raw_path.name)
                    text=_sanitize(raw.decode('utf-8',errors='replace'),ROOT).replace(str(self.output),'<PRIVATE_FIXTURE_ROOT>').replace(self.password,'<SYNTHETIC_TEST_INPUT>')
                    log=self.output/'research-worker.log';write_private_new(log,text.encode());raw_path.unlink()
                    self.commands.append(dict(command='research-worker',exit_code=code,tree_reaped=cleanup is not None and cleanup.reaped,
                        error_type=failure,log=log.name,log_hash=sha(log.read_bytes())))
                    self.persist()
        if code!=0 or not cleanup.reaped:raise ValueError('Actual native canceled child failed or not reaped')
        result=json.loads(text)
        if not result['tree_reaped'] or result['parent_pid']==result['child_pid']:raise ValueError('Actual canceled native child required')
        rows=self.retained_checkpoint_observations()
        if len(rows)!=1 or 'actual_finished_at' in rows[0]:raise ValueError('Canceled expiry observation falsely completed')

    def paper_expiry(self):
        self.scan();_,_,job=self.enqueue();self.research()
        actual=self.view('research/runs/'+job)['payload']
        strategy=self.view('strategies')['items'][0]
        if strategy['current_lifecycle_state']!='CANDIDATE' or actual['evidence']['sealed_oos']!='PASS':raise ValueError('Actual native candidate required')
        self.stop_control();self.csrf=None
        self.command('paper-selection',['configure-paper','--config',self.config,'--selection-profile',self.data/'fixture-inputs/paper-selection.json'])
        self.start_control('control-paper');self.login()
        policies=[p for p in self.view('policies')['items'] if p['kind']=='PAPER']
        if len(policies)!=1:raise ValueError('Actual explicit fixture Paper policy required')
        receipt=self.request('POST','/api/v1/paper/runs',dict(command_id='paper-'+secrets.token_hex(12),
            expected_revision=strategy['registry_revision'],**strategy['identity'],policy_id=policies[0]['policy_id']))
        run=receipt['effect_ref'].removeprefix('paper:')
        first=self.command('paper-worker-first',['paper-worker','--config',self.config,'--maximum-ticks','2'])
        current=self.journal(run);runtime=current.state['runtime']
        if first['run_failures']:raise ValueError('Actual native expiry Paper worker failed')
        from application.fixtures.temporal import utc
        temporal=json.loads(read_local(self.data,'fixture-inputs/temporal.json',65536))
        upper=utc(temporal['validity']['until'])
        if self.native_case=='pre-entry-expired':
            if runtime['position'] is not None or utc(runtime['forward']['observed_at'])<upper:
                raise ValueError('Expired submission created exposure or expiry not observed')
            with closing(sqlite3.connect(load_config(self.config).database_path.as_uri()+'?mode=ro',uri=True)) as db:
                # Canonical ACK/fill graph must be absent, not fabricated flat.
                counts={kind:db.execute('SELECT COUNT(*) FROM paper_runtime_objects WHERE object_kind=?',(kind,)).fetchone()[0]
                    for kind in ('ORDER_REQUEST','FILL')}
                counts['ORDER_RESULT']=db.execute('SELECT COUNT(*) FROM paper_order_result_observations').fetchone()[0]
            if any(counts.values()):raise ValueError('Expired pre-entry created canonical effects')
            self.observation.update(expired_preentry_no_position=True,canonical_effect_counts=counts)
        else:
            position=runtime['position']
            if position is None or position['lifecycle_state']!='OPEN_PROTECTED' or utc(runtime['forward']['observed_at'])>=upper:
                raise ValueError('Actual pre-expiry protection missing')
            view=self.view('paper/runs/'+run)
            self.request('POST','/api/v1/paper/runs/'+run+'/pause',dict(command_id='pause-'+secrets.token_hex(12),expected_revision=view['revision']))
            second=self.command('paper-worker-successor',['paper-worker','--config',self.config,'--maximum-ticks','4'])
            closed=self.journal(run);finished=self.view('paper/runs/'+run)['payload']
            from decimal import Decimal
            if (second['run_failures'] or second['process_generation']!=first['process_generation']+1
                    or closed.binding!=current.binding or closed.state['runtime']['exit_anchor']!=runtime['exit_anchor']
                    or closed.state['runtime']['position']['position_id']!=position['position_id']
                    or Decimal(closed.state['runtime']['position']['actual_quantity'])!=0
                    or self.forward_elapsed(finished)!=0 or utc(closed.state['runtime']['forward']['observed_at'])<upper):
                raise ValueError('Expired successor abandoned original protection or expiry not observed')
            with open_paper_runtime_journal(load_config(self.config).database_path,require_existing=True) as journal:
                graph=journal.recover(position_id=position['position_id'])
            if graph.status!='READY' or len(graph.fills)!=2 or graph.trade_result.payload!=closed.state['runtime']['closed_trades'][0]:
                raise ValueError('Expired actual canonical exit graph missing')
            self.observation.update(original_protection_preserved=True,canonical_fills=2,canonical_trades=1,
                native_direction=position['side'],real_elapsed_ns=0,original_binding_preserved=True)
        self.observation.update(paper_run_id=run,original_validity=temporal['validity'],clock='SYNTHETIC_UTC_SECONDS',
            actual_first_worker_observed_at=runtime['forward']['observed_at'])

    def run(self):
        try:
            self.setup()
            if self.native_case=='intake-faults':self.intake_faults()
            elif self.native_case in ('pre-entry-expired','protected-expired'):self.paper_expiry()
            elif self.native_case=='discovery-expired':
                self.wait_original_expiry();self.scan();submission=self.submission()
                if submission['receipt'] is not None or submission['latest_observation']['state']!='EXPIRED' or self.view('strategies')['items']:
                    raise ValueError('Discovery expiry created accepted effects')
                self.observation['expired_discovery_no_receipt_or_strategy']=True
            else:
                self.scan();original=self.submission()['receipt'];body,receipt,run=self.enqueue()
                if self.native_case=='enqueue-expired':
                    self.wait_original_expiry()
                    if self.request('POST','/api/v1/research/runs',body,expected=202)!=receipt:raise ValueError('Expired exact completed enqueue changed receipt')
                    changed={**body,'expected_revision':body['expected_revision']+1}
                    self.request('POST','/api/v1/research/runs',changed,expected=409)
                    self.request('POST','/api/v1/research/runs',{**body,'command_id':'new-'+secrets.token_hex(12)},expected=503)
                    if len(self.view('research/runs')['items'])!=1:raise ValueError('Expired enqueue added a job')
                    self.research()
                elif self.native_case=='checkpoint-cancel':self.cancel_checkpoint(run)
                else:
                    self.research();rows=self.retained_checkpoint_observations()
                    from application.fixtures.temporal import utc
                    if len(rows)!=2 or not any('actual_finished_at' in r and utc(r['actual_finished_at'])>=utc(r['original_validity']['until']) for r in rows):
                        raise ValueError('Actual original research expiry not observed')
                job=self.view('research/runs/'+run)['payload'];expected='CANCELED' if self.native_case=='checkpoint-cancel' else 'EXPIRED'
                if job['state']!=expected or self.submission()['receipt']!=original:raise ValueError('Expiry/cancel changed original evidence')
                evidence=job['evidence']
                if self.native_case=='enqueue-expired':
                    if job['owner_run_id'] is not None or job['outcome'] is not None or evidence is not None:
                        raise ValueError('Expired queued submission executed research')
                else:
                    stages={row['stage'] for row in evidence['attempts'] if row['status']=='COMPLETE'}
                    if not {'development_replay','e6_backtest_persistence'}.issubset(stages) or any(stage in stages for stage in ('robustness','sealed_oos','e6_product_assessment')):
                        raise ValueError('Expired/canceled research lost development or fabricated final evidence')
                self.observation.update(research_state=job['state'],research_evidence=evidence,original_receipt_preserved=True)
            self.observation['passed']=True
        finally:self.stop_control();self.persist();self.guard()
        return self.observation


def verify(package,output,group):
    package,output=Path(package).resolve(),Path(output)
    if (not output.is_absolute() or output.exists() or output.resolve().is_relative_to(package)
            or group not in NATIVE_ASSERTIONS or group=='PQR-02'):
        raise ValueError('Fixed native group and fresh external private output required')
    identity=verify_distribution(package);target=current_target();create_private_directory(output)
    report=dict(group=group,target=target,identity=identity,passed=False,observations=[],
        provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
    assertions=[];artifacts=[]
    try:
        if group=='PQR-03':
            for scenario in ('positive','oos-loss','insufficient-oos'):
                report['observations'].append(PublicFixture(package,output/scenario,scenario,expected_identity=identity).run())
            if not all(row['passed'] for row in report['observations']):raise ValueError('Fresh native flows incomplete')
            report['passed']=True
        elif group=='PQR-04':
            for case in NativeExpiryFlow.CASES:
                flow=NativeExpiryFlow(package,output/case,case,expected_identity=identity)
                try:report['observations'].append(flow.run())
                except Exception:
                    partial=dict(flow.observation);partial['passed']=False
                    report['observations'].append(partial)
                    raise
            if not all(row['passed'] for row in report['observations']):raise ValueError('Fresh native expiry flows incomplete')
            report['passed']=True
        else:
            # This fails closed until every concrete native scenario below has
            # an actual fixed driver. It cannot issue eligibility from old tests.
            report['remaining_native_observations']=list(NATIVE_ASSERTIONS[group])
            report['reason']='NATIVE_GROUP_IMPLEMENTATION_IN_PROGRESS'
        if verify_distribution(package)!=identity:raise ValueError('Native group subject changed')
    except Exception as error:
        report.update(passed=False,reason='ACTUAL_NATIVE_GROUP_FAILED',error_type=type(error).__name__)
    # Failed native attempts retain the same protected artifact closure. They
    # cannot establish PASS, but their actual logs/cleanup facts remain bound.
    try:
        for path in sorted(output.rglob('*')):
            if (path.suffix in ('.log','.png') or path.name=='observations.json'
                    or path.parent.parent==output and path.parent.name in NativeExpiryFlow.CASES
                    and path.suffix=='.json' and path.name.endswith(('-start.json','-finish.json'))):
                ref=path.relative_to(output).as_posix()
                artifacts.append(dict(ref=ref,hash=sha(artifact_bytes(output,ref))))
                if len(artifacts)>126:raise ValueError('Bounded native artifact inventory required')
    except Exception as error:
        report.update(passed=False,reason='ACTUAL_NATIVE_GROUP_FAILED',error_type=type(error).__name__)
    observation='native-observations.json';raw=(canonical(report)+'\n').encode('utf-8')
    write_private_new(output/observation,raw)
    artifacts.insert(0,dict(ref=observation,hash=sha(raw)))
    assertions=[dict(assertion_id=name,status='PASS' if report['passed'] else 'NOT_RUN',
        evidence_ref=observation,evidence_hash=sha(raw)) for name in NATIVE_ASSERTIONS[group]]
    write_private_new(output/'pqr-result.json',(canonical(dict(assertions=assertions,artifacts=artifacts))+'\n').encode('utf-8'))
    print(json.dumps(dict(group=group,passed=report['passed'],target=target,provider_requests=0)))
    return 0 if report['passed'] else 2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--group',choices=tuple(g for g in NATIVE_ASSERTIONS if g!='PQR-02'),required=True)
    args=parser.parse_args()
    try:return verify(args.package_root,args.output,args.group)
    except Exception:
        print('Native Paper group failed; retain the actual local attempt',file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
