"""Public frozen FIXTURE flow; actual TTY enrollment is a separate observed step.

No injected app/service/runtime factory, state/result/approval write or CLI override.
Source owner imports below only verify durable observations and package identity.
"""
from pathlib import Path
from contextlib import contextmanager
import json,os,socket,subprocess,sys,time
from s09_owner_worker_native_regression import BASE,PROJECT,REPO,OwnedProof,sha,stamp,capture_qualification
from s09_normal_fixture_source_qualify import inputs
from s09_local_paper_control_native_regression import read_input
from s13_native_access_integrity import require_owned_generation,build_loopback_opener
from local_windows_qualification_awake import awake_request
from application.qualification import revision_fact,_sanitize
from application.platform.distribution import verify_distribution
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.supervision import _local_path
from application.platform.private_files import create_private_directory
from application.config import load_config
from storage.paper_process import open_paper_process_journal
from storage.runtime import open_paper_runtime_journal
from storage.paper_feedback import PaperFeedbackOutbox
from application.cloud.safe_files import read_bounded

NODE=Path('C:/Program Files/nodejs/node.exe')
EDGE=Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
BROWSER=BASE/'s09_native_normal_fixture_browser.mjs'

def execution_hashes(revision):
    paths=[Path(__file__),BROWSER,BASE/'s09_owner_worker_native_regression.py',
      BASE/'s09_normal_fixture_source_qualify.py',BASE/'s09_local_paper_control_native_regression.py',
      BASE/'s13_native_access_integrity.py',BASE/'local_windows_qualification_awake.py',NODE,EDGE]
    qualified=BASE/f'r7-productization-S09-normal-fixture-qualified-{revision[:7]}'
    paths.extend([qualified/'qualification.json',qualified/'qualification-context.json'])
    for folder in [REPO/'ui/node_modules/@playwright/test',REPO/'ui/node_modules/playwright',REPO/'ui/node_modules/playwright-core']:
        _local_path(folder)
        paths.extend(sorted(path for path in folder.rglob('*') if path.is_file()))
    return {str(path):sha(read_input(path,128*1024**2)) for path in paths}

class NativeFlow:
    def __init__(self,revision,phase):
        self.revision=revision;self.phase=phase;short=revision[:7]
        self.output=BASE/f'r7-native-S09-normal-fixture-user-flow-{short}-edge-pinned'
        self.proof=self.output/'native-normal-fixture-flow.json'
        self.package=BASE/f'r7-native-windows-S09-normal-fixture-{short}'/'dist/R7'
        revision_fact(REPO,revision,True)
        self.identity=verify_distribution(self.package)
        assert self.identity['executable_revision']==revision
        manifest=json.loads(read_input(self.package/'distribution.json',8*1024**2))
        self.executable=self.package/manifest['entrypoint']
        report,context,qualification_hashes=capture_qualification(BASE/f'r7-productization-S09-normal-fixture-qualified-{short}',revision)
        assert report['tests_run']==2101 and len(context['source_input_hashes'])==636
        assert self.identity['implementation_hash']==context['implementation_hash']
        self.sources=context['source_input_hashes'];assert inputs()==self.sources
        self.execution=execution_hashes(revision)
        for path,expected in qualification_hashes.items():assert self.execution[str(path)]==expected
        self.environment={key:os.environ[key] for key in ['SystemRoot','WINDIR','SystemDrive','TEMP','TMP'] if key in os.environ}
        self.environment.update(PATH='',PYTHONUTF8='1')
        self.config_path=self.output/'private-fixture'/'product.json'
        self.data=self.config_path.parent/'data';self.cloud=self.config_path.parent/'synthetic-cloud'
        self.control=None;self.control_log=None;self.control_generation=None
        if phase=='prepare':
            _local_path(self.output);assert not os.path.lexists(self.output)
            create_private_directory(self.output);create_private_directory(self.config_path.parent)
            self.value=dict(passed=False,phase='PREPARATION',executable_revision=revision,native_build_identity=self.identity,
              source_tests=report['tests_run'],source_input_hashes=self.sources,execution_input_hashes=self.execution,
              commands=[],control_sessions=[],browser=[],native_authentication='TTY_ENROLLMENT_PENDING',
              provider_requests=0,credentials='NONE',synthetic_local_login='EPHEMERAL_TEST_ONLY',capital='NONE',github_compute='NOT_USED',
              ordinary_paper='NOT_RUN',production_profile='PROPOSED_NOT_ACTIVE',real_cloud='NOT_RUN',real_forward='NOT_RUN',
              ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',scope='ACTUAL_FROZEN_PUBLIC_FIXTURE_CLI_NATIVE_RESEARCH_CHILD_NATIVE_PAPER_WORKER_AND_PACKAGED_BROWSER;NO_ORDINARY_OR_REAL_FORWARD_ACCEPTANCE')
            self.owner=OwnedProof(self.proof).__enter__();self.owner.persist(self.value)
            retained=self.output/'execution-inputs';retained.mkdir()
            for name,commitment in self.execution.items():
                path=Path(name)
                if path.parent!=BASE:continue
                raw=read_input(path,128*1024**2);assert sha(raw)==commitment
                with OwnedProof(retained/path.name) as owner:
                    owner.stream.write(raw);owner.stream.flush();owner.require_owned()
            self.value['execution_inputs_retained_at']='execution-inputs'
        else:
            raw=read_input(self.proof,8*1024**2);self.value=json.loads(raw)
            assert self.value['phase']=='AWAITING_OBSERVED_NATIVE_TTY' and not self.value['passed']
            assert self.value['native_build_identity']==self.identity and self.value['source_input_hashes']==self.sources
            assert self.value['execution_input_hashes']==self.execution
            assert sha(read_input(self.config_path,65536))==self.value['initial_profile_sha256']
            self.owner=None
            tty_raw=read_input(self.output/'observed-native-tty-enrollment.json',8192)
            tty=json.loads(tty_raw)
            assert tty['status']=='OWNER_CONFIGURED' and tty['namespace']=='FIXTURE' and tty['native_build_identity']==self.identity
            assert tty['actual_tool_tty'] is True and tty['password_echoed'] is False and tty['exit_code']==0
            assert tty['command']=='PUBLIC_ENROLL_OWNER' and tty['credentials']=='NONE'
            assert tty['config_sha256']==self.value['initial_profile_sha256']
            self.value['native_authentication']='OBSERVED_ACTUAL_NATIVE_PUBLIC_CLI_TTY_ENROLLMENT'
            self.value['tty_evidence_sha256']=sha(tty_raw)
            self.value['phase']='RUNNING'
        self.guard()
    def guard(self):
        revision_fact(REPO,self.revision,True)
        assert inputs()==self.sources and execution_hashes(self.revision)==self.execution
        assert verify_distribution(self.package)==self.identity
    def persist(self):
        if self.owner is not None:self.owner.persist(self.value)
        else:
            # Continue with a distinct immutable outcome proof, preserving preparation.
            pass
    def call(self,label,args,timeout=180,expected_status=None,rejected=False,expected_rejection=None,argv=None,env=None):
        self.guard();log=self.output/(label+'.log');owned=None;started=stamp()
        try:
            with OwnedProof(log) as owner:
                owned=spawn_owned(argv if argv is not None else [str(self.executable),*map(str,args)],cwd=self.output,
                  limits=ResourceLimits(timeout),stdout=owner.stream,stderr=subprocess.STDOUT,env=self.environment if env is None else env)
                code=owned.wait();cleanup=terminate_owned(owned,deadline_seconds=5)
                owner.require_owned();owner.stream.seek(0);raw=owner.stream.read(8*1024**2+1);assert len(raw)<=8*1024**2
                text=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n')
                secret=os.environ.get('R7_SYNTHETIC_PASSWORD')
                if secret:text=text.replace(secret,'<SYNTHETIC_PASSWORD>')
                sanitized=text.encode();owner.stream.seek(0);owner.stream.write(sanitized);owner.stream.truncate();owner.stream.flush();owner.require_owned()
            result=dict(label=label,started_at_utc=started,finished_at_utc=stamp(),exit_code=code,
              tree_reaped=cleanup.reaped,expected_rejection=rejected,log=log.name,log_sha256=sha(sanitized),passed=cleanup.reaped and (code!=0 if rejected else code==0))
            self.value['commands'].append(result);self.persist();print(json.dumps(result),flush=True)
            assert result['passed'],'Actual public native command failed'
            if rejected:
                assert expected_rejection is not None and code==expected_rejection[0] and text.strip()==expected_rejection[1]
                return None
            value=json.loads(raw)
            if expected_status is not None:assert value['status']==expected_status
            return value
        finally:
            if owned is not None:assert terminate_owned(owned,deadline_seconds=5).reaped
            self.guard()
    def browser(self,stage):
        assert self.control is not None
        assert require_owned_generation(self.control,self.config_path,self.identity,self.control_generation)==self.control_generation
        config=load_config(self.config_path);origin=f'http://127.0.0.1:{config.control_api_port}'
        env=self.environment.copy();env['R7_SYNTHETIC_PASSWORD']=os.environ['R7_SYNTHETIC_PASSWORD']
        result=self.call('browser-'+stage,[],argv=[str(NODE),str(BROWSER),str(REPO),origin,stage,str(self.output)],env=env)
        assert result['passed'] is True and result['remote_requests']==0 and result['namespace']=='FIXTURE'
        assert result['screenshot']==stage+'.png'
        assert sha(read_input(self.output/result['screenshot'],8*1024**2))==result['screenshot_sha256']
        self.value['browser'].append(result);self.persist()
        assert require_owned_generation(self.control,self.config_path,self.identity,self.control_generation)==self.control_generation
        return result
    def start_control(self,label):
        self.guard();config=load_config(self.config_path)
        self.control_log=OwnedProof(self.output/(label+'.log')).__enter__()
        self.control=spawn_owned([str(self.executable),'serve','--config',str(self.config_path)],cwd=self.output,
          limits=ResourceLimits(600),stdout=self.control_log.stream,stderr=subprocess.STDOUT,env=self.environment)
        end=time.monotonic()+30
        while time.monotonic()<end:
            try:
                generation=require_owned_generation(self.control,self.config_path,self.identity)
                with build_loopback_opener().open(f'http://127.0.0.1:{config.control_api_port}/api/v1/auth/status',timeout=1) as response:
                    status=json.loads(response.read(2049))
                assert status==dict(configured=True,namespace='FIXTURE',enrollment='LOCAL_CLI_ONLY')
                self.control_generation=generation;return
            except Exception:
                if self.control.process.poll() is not None:raise
                time.sleep(.1)
        raise AssertionError('Owned native control readiness deadline expired')
    def stop_control(self):
        if self.control is None:return
        cleanup=terminate_owned(self.control,deadline_seconds=5);assert cleanup.reaped
        self.control_log.require_owned();self.control_log.stream.seek(0);raw=self.control_log.stream.read(8*1024**2+1);assert len(raw)<=8*1024**2
        sanitized=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').encode()
        self.control_log.stream.seek(0);self.control_log.stream.write(sanitized);self.control_log.stream.truncate();self.control_log.stream.flush();self.control_log.require_owned()
        self.value['control_sessions'].append(dict(generation=self.control_generation,tree_reaped=True,
          stop='FORCED_OWNED_CONTROL_TREE_CLEANUP;NO_GRACEFUL_CONTROL_STOP_CREDIT',log=self.control_log.path.name,log_sha256=sha(sanitized)))
        self.control_log.__exit__();self.control_log=None;self.control=None;self.control_generation=None;self.guard();self.persist()
    def prepare(self):
        with socket.socket() as candidate:
            candidate.bind(('127.0.0.1',0));port=candidate.getsockname()[1]
        self.call('01-init',['init-profile','--config',self.config_path,'--data-root',self.data,'--cloud-root',self.cloud,
          '--instance-id','native-normal-fixture-'+self.revision[:7],'--port',str(port),'--execution-mode','FIXTURE'],expected_status='PROFILE_CREATED')
        generated=self.call('02-prepare-fixture',['prepare-fixture','--config',self.config_path,'--scenario','positive'])
        assert generated['namespace']=='FIXTURE' and generated['execution_evidence']=='NOT_RUN'
        self.call('03-configure-research',['configure-research','--config',self.config_path,'--selection-profile',self.data/'fixture-inputs/selection.json'],expected_status='RESEARCH_CONFIGURED')
        assert not (self.data/'local-auth.sqlite').exists()
        self.value['initial_profile_sha256']=sha(read_input(self.config_path,65536))
        self.value['phase']='AWAITING_OBSERVED_NATIVE_TTY';self.persist();self.owner.__exit__();self.owner=None
        print(json.dumps(dict(status='AWAITING_NATIVE_TTY',config=str(self.config_path),executable=str(self.executable))),flush=True)
    def journal(self,run):
        with open_paper_process_journal(load_config(self.config_path).database_path,require_existing=True) as journal:return journal.recover(run)
    def resume(self):
        assert len(os.environ['R7_SYNTHETIC_PASSWORD'])>=12
        outcome=self.output/'native-normal-fixture-outcome.json'
        with OwnedProof(outcome) as owner:
            self.owner=owner
            try:
                with awake_request() as awake:
                    self.start_control('control-research')
                    enqueued=self.browser('research-enqueue')
                    research=self.call('04-research-worker',['research-worker','--config',self.config_path,'--once'],timeout=300,expected_status='JOB_FINISHED')
                    assert research['tree_reaped'] is True and research['parent_pid']!=research['child_pid']
                    actual=self.browser('research-result');assert actual['research_job_id']==enqueued['research_job_id']
                    self.stop_control()
                    self.call('05-configure-paper',['configure-paper','--config',self.config_path,'--selection-profile',self.data/'fixture-inputs/paper-selection.json'],expected_status='FIXTURE_PAPER_CONFIGURED')
                    self.start_control('control-paper-start')
                    started=self.browser('paper-start');run=started['run_id'];initial=self.journal(run);assert initial.process_generation==0
                    first=self.call('06-paper-worker',['paper-worker','--config',self.config_path,'--maximum-ticks','2'],expected_status='STOPPED')
                    assert first['ticks']==2 and first['run_failures']=={} and first['observation_clock']=='SYNTHETIC_UTC_SECONDS'
                    protected=self.journal(run);position=protected.state['runtime']['position']
                    assert protected.process_generation==1 and position['lifecycle_state']=='OPEN_PROTECTED'
                    self.stop_control()
                    backup=self.config_path.parent/'private-backup';target=self.config_path.parent/'restored'
                    self.call('07-backup',['backup-product-data','--config',self.config_path,'--destination',backup],expected_status='PRODUCT_DATA_BACKUP_VERIFIED')
                    self.call('08-verify-backup',['verify-product-backup','--config',self.config_path,'--destination',backup])
                    self.call('09-restore',['restore-product-data','--config',self.config_path,'--backup',backup,'--destination',target])
                    restored=load_config(target/'restored-product.json');assert restored.cloud_root is None and restored.diagnostic_only and not restored.paper_runtime_enabled
                    with open_paper_process_journal(restored.database_path,require_existing=True) as journal:copied=journal.recover(run)
                    assert copied.state==protected.state and copied.binding==protected.binding and copied.revision==protected.revision
                    assert copied.process_generation==protected.process_generation+1 and self.journal(run)==protected
                    self.call('10-restored-worker-denied',['paper-worker','--config',target/'restored-product.json','--maximum-ticks','2'],rejected=True,
                      expected_rejection=(2,'R7: local configuration or startup validation failed'))
                    with open_paper_process_journal(restored.database_path,require_existing=True) as journal:
                        assert journal.recover(run)==copied
                    assert self.journal(run)==protected
                    from application.platform.restoration import require_valid_restoration
                    restoration=require_valid_restoration(restored)
                    assert restoration['status']=='RESTORED_INHIBITED' and restoration['runtime_new_exposure']=='INHIBITED'
                    self.value['restored_worker_denial']=dict(exit_code=2,diagnostic='SANITIZED_GENERIC_VALIDATION_REJECTION',
                      exact_cause='NOT_DISCLOSED_BY_PUBLIC_CLI;NO_SPECIFIC_CAUSE_CREDIT',copied_journal_unchanged=True,source_journal_unchanged=True,
                      typed_restore_status=restoration['status'],new_exposure=restoration['runtime_new_exposure'])
                    self.start_control('control-paper-resume')
                    paused=self.browser('paper-pause');assert paused['run_id']==run and paused['position']==position
                    second=self.call('11-paper-worker-restarted',['paper-worker','--config',self.config_path,'--maximum-ticks','4'],expected_status='STOPPED')
                    assert second['ticks']==4 and second['run_failures']=={} and second['process_generation']==first['process_generation']+1
                    finished=self.browser('paper-closed');assert finished['run_id']==run
                    closed=self.journal(run);assert closed.binding==protected.binding
                    assert closed.state['runtime']['position']['position_id']==position['position_id']
                    assert closed.state['runtime']['position']['opened_at']==position['opened_at']
                    assert closed.state['runtime']['forward']['real_elapsed_ns']==0
                    with open_paper_runtime_journal(load_config(self.config_path).database_path,require_existing=True) as canonical:
                        graph=canonical.recover(position_id=position['position_id'])
                    assert graph.status=='READY' and len(graph.fills)==2 and graph.trade_result.payload==closed.state['runtime']['closed_trades'][0]
                    self.stop_control()
                    self.call('12-queue-research-feedback',['queue-research-feedback','--config',self.config_path,'--namespace','FIXTURE','--run-id',actual['owner_run_id']])
                    staged=0
                    for i in range(10):
                        row=self.call(f'13-stage-{i:02d}',['publish-fixture-outbox','--config',self.config_path,'--limit','1'],expected_status='LOCAL_STAGED')
                        assert row['attempted']<=1 and row['cloud_acknowledged']==0 and row['remote_verification']=='NOT_RUN'
                        staged+=row['local_staged']
                        if row['attempted']==0:break
                    assert staged>=3
                    with open_paper_process_journal(load_config(self.config_path).database_path,require_existing=True) as journal:
                        outbox=PaperFeedbackOutbox(journal);pending=outbox.pending(10)
                        publications=outbox.publications();assert len(publications)>=1 and all(row['state']=='LOCAL_STAGED' for row in publications)
                    self.value['paper_publications']=[]
                    for operation,bundle,artifact in pending:
                        feedback=json.loads(bundle.payloads['feedback.json'])
                        for name,raw in bundle.payloads.items():assert read_bounded(self.cloud,bundle.logical_path+'/'+name,262144)==raw
                        manifest=read_bounded(self.cloud,bundle.logical_path+'/manifest.json',262144)
                        receipt=json.loads(manifest);assert receipt['operation_id']==operation and receipt['artifact_hash']==artifact
                        assert feedback['observation']['actual_elapsed_seconds']==0 and feedback['assessment']['status']=='BLOCKED'
                        assert feedback['performance'] is None and feedback['live']['status']=='NOT_RUN'
                        self.value['paper_publications'].append(dict(operation_id=operation,artifact_hash=artifact,
                          payload_hashes={name:sha(raw) for name,raw in bundle.payloads.items()},manifest_hash=sha(manifest),state='LOCAL_STAGED',assessment='BLOCKED',performance='OPT_OUT'))
                    assert self.value['paper_publications'] and self.journal(run)==closed
                    self.value.update(phase='COMPLETE',normal_native_fixture_flow='PASS',native_research_child='ACTUAL_STANDARD_CHILD',
                      native_paper_worker='PUBLIC_SEPARATE_PROCESS',canonical_fills=2,canonical_closed_trades=1,
                      backup_restore='EXACT_PROTECTED_STATE_PRESERVED_AND_RESTORED_START_DENIED',real_elapsed_ns=0,cloud_acknowledged=0)
                assert awake['restored'] is True;self.value['awake_request']=awake;self.guard()
                self.value.update(passed=True,execution_inputs_unchanged=True,package_identity_unchanged=True);owner.persist(self.value)
            finally:
                self.stop_control();owner.persist(self.value);self.owner=None
        print(json.dumps(dict(passed=self.value['passed'],commands=len(self.value['commands']),browser_stages=len(self.value['browser']),normal_native_fixture_flow=self.value.get('normal_native_fixture_flow','FAILED'))),flush=True)

def main():
    revision,phase=sys.argv[1:];assert phase in ('prepare','resume')
    flow=NativeFlow(revision,phase)
    flow.prepare() if phase=='prepare' else flow.resume()
if __name__=='__main__':main()
