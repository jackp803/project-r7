"""Fixed native Paper observations through actual public product commands.

Every invocation creates fresh private FIXTURE data outside the installation.
Unimplemented native observations are retained as NOT_RUN and fail the group;
source tests, old demos and an exit code never substitute for native evidence.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from application.config import load_config
from application.datasets.catalog import read_local
from application.paper.inventory import NATIVE_ASSERTIONS,current_target
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
    def __init__(self,package,output,scenario):
        self.package,self.output,self.scenario=package,output,scenario
        self.identity=verify_distribution(package)
        manifest=json.loads((package/'distribution.json').read_bytes())
        self.executable=package/manifest['entrypoint']
        create_private_directory(output)
        self.config=output/'product.json';self.data=output/'data';self.cloud=output/'synthetic-cloud'
        self.password=secrets.token_hex(24)
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


def verify(package,output,group):
    package,output=Path(package).resolve(),Path(output)
    if (not output.is_absolute() or output.exists() or output.resolve().is_relative_to(package)
            or group not in NATIVE_ASSERTIONS or group=='PQR-02'):
        raise ValueError('Fixed native group and fresh external private output required')
    identity=verify_distribution(package);target=current_target();create_private_directory(output)
    report=dict(group=group,target=target,identity=identity,passed=False,observations=[],
        provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
    assertions=[]
    try:
        if group=='PQR-03':
            for scenario in ('positive','oos-loss','insufficient-oos'):
                report['observations'].append(PublicFixture(package,output/scenario,scenario).run())
            if not all(row['passed'] for row in report['observations']):raise ValueError('Fresh native flows incomplete')
            report['passed']=True
        else:
            # This fails closed until every concrete native scenario below has
            # an actual fixed driver. It cannot issue eligibility from old tests.
            report['remaining_native_observations']=list(NATIVE_ASSERTIONS[group])
            report['reason']='NATIVE_GROUP_IMPLEMENTATION_IN_PROGRESS'
    except Exception as error:
        report.update(reason='ACTUAL_NATIVE_GROUP_FAILED',error_type=type(error).__name__)
    observation='native-observations.json';raw=(canonical(report)+'\n').encode('utf-8')
    write_private_new(output/observation,raw)
    artifacts=[dict(ref=observation,hash=sha(raw))]
    for path in sorted(output.rglob('*')):
        if path.is_file() and (path.suffix=='.log' or path.suffix=='.png' or path.name=='observations.json'):
            artifacts.append(dict(ref=path.relative_to(output).as_posix(),hash=sha(path.read_bytes())))
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
