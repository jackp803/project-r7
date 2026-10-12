"""Reexecute the actual public normal FIXTURE flow on the qualified 13d package.

Current clean Git metadata and exact native executable identities are separate.
The existing immutable normal-flow mechanics are reused; no factory/state injection.
"""
import json,os,re,sys
from pathlib import Path
import s09_native_forward_ui_flow as old
from s09_owner_worker_native_regression import BASE,REPO,OwnedProof,sha,stamp,capture_qualification
from s09_normal_fixture_source_qualify import inputs
from s09_local_paper_control_native_regression import read_input
from application.qualification import revision_fact
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory
from local_windows_qualification_awake import awake_request

EXECUTABLE_REVISION='13d7375d6297c8df94124e95856821df6dee7f09'
OBSERVER=BASE/'record_s09_current_tty.py'

class CurrentFlow(old.NativeFlow):
    def __init__(self,source,phase,scenario):
        assert re.fullmatch('[0-9a-f]{40}',source) and phase in ('prepare','resume')
        assert scenario in ('positive','oos-loss','insufficient-oos')
        self.revision=source;self.executable_revision=EXECUTABLE_REVISION;self.phase=phase;self.scenario=scenario
        revision_fact(REPO,source,True)
        self.output=BASE/f'r7-native-S09-current-user-flow-{EXECUTABLE_REVISION[:7]}-{scenario}'
        self.proof=self.output/'native-normal-fixture-flow.json'
        self.package=BASE/f'r7-native-windows-S15-negative-intake-{EXECUTABLE_REVISION[:7]}/dist/R7'
        self.identity=verify_distribution(self.package)
        assert self.identity['executable_revision']==EXECUTABLE_REVISION
        manifest=json.loads(read_input(self.package/'distribution.json',8*1024**2))
        self.executable=self.package/manifest['entrypoint']
        self.build_path=BASE/f'S15-negative-intake-{EXECUTABLE_REVISION[:7]}-native-build.json'
        build_raw=read_input(self.build_path,8*1024**2);build=json.loads(build_raw)
        assert build['passed'] and build['native_build_identity']==self.identity
        assert build['source_before']==build['source_after']==dict(revision=EXECUTABLE_REVISION,worktree='CLEAN')
        self.qualification=BASE/f'r7-productization-S09-normal-fixture-qualified-{EXECUTABLE_REVISION[:7]}'
        q,context,qualified_hashes=capture_qualification(self.qualification,EXECUTABLE_REVISION)
        assert {str(path):digest for path,digest in qualified_hashes.items()}==build['source_qualification_hashes']
        assert q['tests_run']==build['full_source_execution_instances']==2108
        assert context['inputs_unchanged'] and context['awake_request']['restored']
        assert context['implementation_hash']==self.identity['implementation_hash']
        self.sources=build['source_input_hashes']
        assert len(self.sources)==637 and self.sources==context['source_input_hashes']==inputs()
        self.execution=self.execution_hashes()
        assert self.execution[str(self.build_path)]==sha(build_raw)
        assert all(self.execution[str(path)]==digest for path,digest in qualified_hashes.items())
        self.guard()
        self.environment={key:os.environ[key] for key in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if key in os.environ}
        self.environment.update(PATH='',PYTHONUTF8='1')
        self.config_path=self.output/'private-fixture/product.json'
        self.data=self.config_path.parent/'data';self.cloud=self.config_path.parent/'synthetic-cloud'
        self.control=None;self.control_log=None;self.control_generation=None;self.owner=None
        if phase=='prepare':
            assert not os.path.lexists(self.output)
            create_private_directory(self.output);create_private_directory(self.config_path.parent)
            self.value=dict(passed=False,phase='PREPARATION',source_revision=source,executable_revision=EXECUTABLE_REVISION,
                source_before=revision_fact(REPO,source,True),native_build_identity=self.identity,
                full_python_revision=EXECUTABLE_REVISION,full_python_execution_instances=2108,
                source_input_hashes=self.sources,execution_input_hashes=self.execution,
                native_build_proof_sha256=sha(build_raw),scenario=scenario,
                commands=[],control_sessions=[],browser=[],native_authentication='TTY_ENROLLMENT_PENDING',
                provider_requests=0,credentials='NONE',synthetic_local_login='EPHEMERAL_TEST_ONLY',capital='NONE',github_compute='NOT_USED',
                ordinary_paper='NOT_RUN',production_profile='PROPOSED_NOT_ACTIVE',real_cloud='NOT_RUN',real_forward='NOT_RUN',
                ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',
                scope='CURRENT_PUBLIC_FROZEN_FIXTURE_RESEARCH_PAPER_OWNER_AND_PACKAGED_UI;NO_ORDINARY_RELEASE_REAL_FORWARD_OR_WHOLE_MASTER_CREDIT')
            self.owner=OwnedProof(self.proof).__enter__();self.owner.persist(self.value)
            retained=self.output/'execution-inputs';retained.mkdir()
            for name,digest in self.execution.items():
                path=Path(name)
                if path.parent!=BASE:continue
                raw=read_input(path,128*1024**2);assert sha(raw)==digest
                with OwnedProof(retained/path.name) as proof:
                    proof.stream.write(raw);proof.stream.flush();proof.require_owned()
            self.value['execution_inputs_retained_at']='execution-inputs'
        else:
            self.value=json.loads(read_input(self.proof,8*1024**2))
            assert self.value['phase']=='AWAITING_OBSERVED_NATIVE_TTY' and self.value['passed'] is False
            assert self.value['source_revision']==source and self.value['executable_revision']==EXECUTABLE_REVISION
            assert self.value['native_build_identity']==self.identity and self.value['source_input_hashes']==self.sources
            assert self.value['execution_input_hashes']==self.execution
            assert sha(read_input(self.config_path,65536))==self.value['initial_profile_sha256']
            tty_raw=read_input(self.output/'observed-native-tty-enrollment.json',8192);tty=json.loads(tty_raw)
            assert tty['status']=='OWNER_CONFIGURED' and tty['namespace']=='FIXTURE'
            assert tty['native_build_identity']==self.identity and tty['config_sha256']==self.value['initial_profile_sha256']
            assert tty['actual_tool_tty'] is True and tty['password_echoed'] is False and tty['exit_code']==0
            assert tty['command']=='PUBLIC_ENROLL_OWNER' and tty['credentials']=='NONE'
            assert tty['observer_sha256']==self.execution[str(OBSERVER)]
            self.value.update(native_authentication='OBSERVED_ACTUAL_NATIVE_PUBLIC_CLI_TTY_ENROLLMENT',tty_evidence_sha256=sha(tty_raw),phase='RUNNING')
        self.guard()

    def execution_hashes(self):
        values=old.execution_hashes('dd533694df21bd3608e58408d14b5b05255b4d21')
        values.pop(str(BASE/'S09-forward-ui-dd53369-native-build.json'))
        for path in (Path(__file__),OBSERVER,self.build_path,self.qualification/'qualification.json',self.qualification/'qualification-context.json'):
            values[str(path)]=sha(read_input(path,8*1024**2))
        return values

    def guard(self):
        revision_fact(REPO,self.revision,True)
        assert inputs()==self.sources and self.execution_hashes()==self.execution
        assert verify_distribution(self.package)==self.identity

    def resume(self):
        assert len(os.environ['R7_SYNTHETIC_PASSWORD'])>=12
        with OwnedProof(self.output/'native-normal-fixture-outcome.json') as proof:
            self.owner=proof
            try:
                with awake_request() as awake:
                    self.start_control('control-research')
                    enqueued=self.browser('research-enqueue')
                    worker=self.call('04-research-worker',['research-worker','--config',self.config_path,'--once'],timeout=300,expected_status='JOB_FINISHED')
                    assert worker['tree_reaped'] and worker['parent_pid']!=worker['child_pid']
                    actual=self.browser('research-result');assert actual['research_job_id']==enqueued['research_job_id']
                    self.stop_control()
                    if self.scenario=='positive':
                        self.positive(actual)
                    else:
                        self.call('05-configure-paper',['configure-paper','--config',self.config_path,'--selection-profile',self.data/'fixture-inputs/paper-selection.json'],expected_status='FIXTURE_PAPER_CONFIGURED')
                        self.start_control('control-paper-denied');denied=self.browser('paper-denied')
                        assert denied['paper_runs_before']==denied['paper_runs_after']==0
                        assert denied['lifecycle']==actual['lifecycle'] and denied['denial']=='CURRENT_OWNER_EVIDENCE_REQUIRED'
                        self.stop_control()
                        self.value.update(phase='COMPLETE',normal_native_fixture_flow='PASS',native_research_child='ACTUAL_STANDARD_CHILD',
                            research_lifecycle=actual['lifecycle'],sealed_oos=actual['sealed_oos'],native_paper_start='DENIED_BEFORE_RUN_CREATION',
                            native_paper_worker='NOT_STARTED',real_elapsed_ns=0,cloud_acknowledged=0)
                assert awake['restored'];self.value['awake_request']=awake
                self.guard()
                self.value.update(passed=True,execution_inputs_unchanged=True,package_identity_unchanged=True,
                    source_inputs_unchanged=True,source_after=revision_fact(REPO,self.revision,True),finished_at_utc=stamp())
            except BaseException:
                self.value.update(passed=False,phase='FAILED',finished_at_utc=stamp())
                raise
            finally:
                try:self.stop_control()
                except BaseException:
                    self.value.update(passed=False,phase='FAILED')
                    raise
                finally:proof.persist(self.value);self.owner=None
        print(json.dumps(dict(passed=self.value['passed'],scenario=self.scenario,commands=len(self.value['commands']),browser_stages=len(self.value['browser']),normal_native_fixture_flow=self.value.get('normal_native_fixture_flow','FAILED'))),flush=True)

if __name__=='__main__':
    source,phase,scenario=sys.argv[1:]
    flow=CurrentFlow(source,phase,scenario)
    if phase=='prepare':flow.prepare()
    else:
        flow.resume()
        raise SystemExit(0 if flow.value['passed'] else 1)
