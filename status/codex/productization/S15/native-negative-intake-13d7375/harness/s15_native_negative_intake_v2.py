"""Actual native public CLI/API negative intake; isolated synthetic inputs only.

Source metadata descendants are bound separately from the frozen executable.
No database writes, service injection, candidate/PASS or approval construction.
"""
import json,os,sys
from pathlib import Path
import s09_native_forward_ui_flow as old
from s09_normal_fixture_source_qualify import inputs
from s09_owner_worker_native_regression import BASE,REPO,OwnedProof,sha,stamp
from s09_local_paper_control_native_regression import read_input
from application.qualification import revision_fact
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory
from local_windows_qualification_awake import awake_request

BROWSER=BASE/'s15_native_negative_intake_browser_v2.mjs'

class NegativeFlow(old.NativeFlow):
    def __init__(self,source,executable,phase):
        self.revision=source;self.executable_revision=executable;self.scenario='positive';self.phase=phase
        revision_fact(REPO,source,True)
        self.output=BASE/f'r7-native-S15-negative-intake-{source[:7]}'
        self.proof=self.output/'preparation.json'
        self.package=BASE/f'r7-native-windows-S15-negative-intake-{executable[:7]}'/'dist/R7'
        self.identity=verify_distribution(self.package)
        assert self.identity['executable_revision']==executable
        manifest=json.loads(read_input(self.package/'distribution.json',8*1024**2))
        self.executable=self.package/manifest['entrypoint']
        raw=read_input(BASE/f'S15-negative-intake-{executable[:7]}-native-build.json',8*1024**2)
        build=json.loads(raw)
        assert build['passed'] and build['native_build_identity']==self.identity
        self.sources=build['source_input_hashes'];assert len(self.sources)==637 and inputs()==self.sources
        self.execution=self.execution_hashes()
        self.environment={key:os.environ[key] for key in ['SystemRoot','WINDIR','SystemDrive','TEMP','TMP'] if key in os.environ}
        self.environment.update(PATH='',PYTHONUTF8='1')
        self.config_path=self.output/'private-fixture/product.json'
        self.data=self.config_path.parent/'data';self.cloud=self.config_path.parent/'synthetic-cloud'
        self.control=None;self.control_log=None;self.control_generation=None
        self.owner=None
        if phase=='prepare':
            assert not os.path.lexists(self.output)
            create_private_directory(self.output);create_private_directory(self.config_path.parent)
            self.value=dict(passed=False,phase='PREPARATION',source_revision=source,executable_revision=executable,
                started_at_utc=stamp(),native_build_identity=self.identity,source_input_hashes=self.sources,
                execution_input_hashes=self.execution,native_build_proof_sha256=sha(raw),
                compatibility='EXACT_SAME_637_SOURCE_INPUTS;SOURCE_METADATA_DESCENDANT_SEPARATE_FROM_NATIVE_EXECUTABLE',
                commands=[],control_sessions=[],browser=[],native_authentication='TTY_ENROLLMENT_PENDING',
                provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',real_cloud='NOT_RUN',
                ordinary_paper='NOT_RUN',real_forward='NOT_RUN',ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',
                scope='WINDOWS_NATIVE_PUBLIC_NEGATIVE_INTAKE_ONLY;NO_WHOLE_MASTER_OR_PROFIT_ACCEPTANCE')
            self.owner=OwnedProof(self.proof).__enter__()
        else:
            self.value=json.loads(read_input(self.proof,8*1024**2))
            assert self.value['phase']=='AWAITING_OBSERVED_NATIVE_TTY'
            assert self.value['native_build_identity']==self.identity and self.value['execution_input_hashes']==self.execution
            assert sha(read_input(self.config_path,65536))==self.value['initial_profile_sha256']
            tty_raw=read_input(self.output/'observed-native-tty-enrollment.json',8192)
            tty=json.loads(tty_raw)
            assert tty['actual_tool_tty'] and not tty['password_echoed'] and tty['exit_code']==0
            assert tty['config_sha256']==self.value['initial_profile_sha256'] and tty['native_build_identity']==self.identity
            self.value.update(native_authentication='OBSERVED_ACTUAL_NATIVE_PUBLIC_CLI_TTY_ENROLLMENT',tty_evidence_sha256=sha(tty_raw))
        self.guard()
    def execution_hashes(self):
        values=old.execution_hashes('dd533694df21bd3608e58408d14b5b05255b4d21')
        path=BASE/f'S15-negative-intake-{self.executable_revision[:7]}-native-build.json'
        values[str(path)]=sha(read_input(path,8*1024**2))
        for path in (Path(__file__),BROWSER):values[str(path)]=sha(read_input(path,2*1024**2))
        return values
    def guard(self):
        revision_fact(REPO,self.revision,True)
        assert inputs()==self.sources and self.execution_hashes()==self.execution
        assert verify_distribution(self.package)==self.identity
    def prepare(self):
        super().prepare()
        # Continue preparation through separate owned proof; original init proof stays intact.
        with OwnedProof(self.output/'inputs.json') as owner:
            self.owner=owner
            definition=self.cloud/'inbox/strategies/r7-synthetic-fixture-input/strategy.json'
            expired_definition=json.loads(read_input(definition,256*1024))
            expired_definition['strategy_id']='r7-negative-expired-subject'
            expired_definition.pop('content_hash',None)
            expired_input=self.output/'expired-authoring-input.json'
            with OwnedProof(expired_input) as source_owner:source_owner.persist(expired_definition)
            for name in ('partial','malformed','unsupported','expired'):
                args=['author-package','--definition',expired_input if name=='expired' else definition,'--destination',self.cloud/'inbox/strategies'/('negative-'+name),
                    '--submission-id','negative-'+name,'--dataset-profile','synthetic-fixture',
                    '--validation-profile','synthetic-fixture','--robustness-profile','synthetic-fixture']
                if name=='expired':args+=['--valid-from','2026-10-02T00:00:00Z','--valid-until','2026-10-02T04:00:00Z']
                self.call('author-'+name,args,expected_status='AUTHORING_PACKAGE_CREATED')
            folder=self.cloud/'inbox/strategies'
            self.partial=read_input(folder/'negative-partial/strategy.json',256*1024)
            (self.output/'partial-original.json').write_bytes(self.partial)
            (folder/'negative-partial/strategy.json').write_bytes(self.partial[:17])
            (folder/'negative-malformed/manifest.json').write_bytes(b'{"broken":')
            path=folder/'negative-unsupported/manifest.json'
            manifest=json.loads(read_input(path,65536));manifest['package_schema_version']='r7-strategy-package-v9.9'
            path.write_text(json.dumps(manifest),encoding='utf-8')
            self.value['synthetic_input_hashes']={str(path.relative_to(self.cloud)):sha(read_input(path,256*1024))
                for path in sorted(folder.rglob('*.json'))}
            self.value['phase']='AWAITING_OBSERVED_NATIVE_TTY';owner.persist(self.value);self.owner=None
        # The additional input commands are retained by inputs.json; prepare remains the auth binding.
    def browser_stage(self,stage):
        from s13_native_access_integrity import require_owned_generation
        assert self.control is not None
        assert require_owned_generation(self.control,self.config_path,self.identity,self.control_generation)==self.control_generation
        env=self.environment.copy();env['R7_SYNTHETIC_PASSWORD']=os.environ['R7_SYNTHETIC_PASSWORD']
        from application.config import load_config
        origin=f'http://127.0.0.1:{load_config(self.config_path).control_api_port}'
        result=self.call('browser-'+stage,[],argv=[str(old.NODE),str(BROWSER),str(REPO),origin,stage,str(self.output)],env=env)
        assert result['passed'] and result['remote_requests']==0
        assert sha(read_input(self.output/result['screenshot'],8*1024**2))==result['screenshot_sha256']
        assert require_owned_generation(self.control,self.config_path,self.identity,self.control_generation)==self.control_generation
        self.value['browser'].append(result);self.persist();return result
    def resume(self):
        initial=json.loads(read_input(self.output/'inputs.json',8*1024**2))
        self.value['commands']=initial['commands'];self.value['synthetic_input_hashes']=initial['synthetic_input_hashes']
        with OwnedProof(self.output/'outcome.json') as owner:
            self.owner=owner
            try:
                with awake_request() as awake:
                    self.start_control('control-negative-intake')
                    initial=self.browser_stage('initial')
                    path=self.cloud/'inbox/strategies/negative-partial/strategy.json'
                    path.write_bytes(read_input(self.output/'partial-original.json',256*1024))
                    recovered=self.browser_stage('partial-recovered')
                    path=self.cloud/'inbox/strategies/r7-synthetic-fixture-input/manifest.json'
                    manifest=json.loads(read_input(path,65536));manifest['research_hypothesis']+=' immutable mutation'
                    path.write_text(json.dumps(manifest),encoding='utf-8')
                    conflict=self.browser_stage('conflict')
                    self.stop_control()
                assert awake['restored'];self.value['awake_request']=awake
                cases=[dict(test_id='native.malformed',passed=initial['malformed']=='BLOCKED'),
                    dict(test_id='native.partial-sync',passed=initial['partial']=='INCOMPLETE_SYNC' and recovered['partial']=='INTAKE_ACCEPTED'),
                    dict(test_id='native.unsupported-version',passed=initial['unsupported']=='BLOCKED'),
                    dict(test_id='native.immutable-conflict',passed=conflict['latest_observation']=='CONFLICT' and conflict['receipt_unchanged']),
                    dict(test_id='native.expired-submission',passed=initial['expired']=='EXPIRED')]
                self.value.update(cases=cases,phase='COMPLETE',finished_at_utc=stamp(),
                    source_inputs_unchanged=True,execution_inputs_unchanged=True,native_distribution_unchanged=True,
                    paper_runs=0,trading_runtime='NOT_STARTED',expired_observed=initial['expired'])
                self.guard()
                self.value['passed']=all(row['passed'] for row in cases)
                owner.persist(self.value)
            except BaseException:
                self.value.update(passed=False,phase='FAILED')
                raise
            finally:
                try:self.stop_control()
                except BaseException:
                    self.value.update(passed=False,phase='FAILED')
                    raise
                finally:owner.persist(self.value);self.owner=None
        print(json.dumps(dict(passed=self.value['passed'],passed_cases=sum(row['passed'] for row in cases),total_cases=len(cases),expired=initial['expired'])),flush=True)

if __name__=='__main__':
    source,executable,phase=sys.argv[1:]
    flow=NegativeFlow(source,executable,phase)
    if phase=='prepare':
        flow.prepare()
    else:
        flow.resume()
        raise SystemExit(0 if flow.value['passed'] else 1)
