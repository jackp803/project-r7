"""Actual frozen CLI setup checks; no research, authentication or Paper claim.

Fresh synthetic inputs contain only namespace labels. These exercise selection
shape and local availability, not policy validity or qualification authority.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
from tempfile import TemporaryDirectory

from s09_owner_worker_native_regression import OwnedProof, BASE, REPO, sha, stamp
from s09_local_paper_control_native_regression import read_input
from application.qualification import revision_fact, _sanitize
from application.platform.distribution import verify_distribution
from application.platform.processes import ResourceLimits, spawn_owned, terminate_owned
from application.platform.supervision import _local_path


def main():
    package=Path(sys.argv[1]); output=Path(sys.argv[2]); revision=sys.argv[3]
    revision_fact(REPO,revision,True)
    identity=verify_distribution(package)
    assert identity['executable_revision']==revision
    manifest=json.loads(read_input(package/'distribution.json',8*1024**2))
    executable=package/manifest['entrypoint']
    environment={key:os.environ[key] for key in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if key in os.environ}
    environment.update(PATH='',PYTHONUTF8='1')
    _local_path(output)
    assert not os.path.lexists(output)
    output.mkdir()
    launcher_before=sha(read_input(Path(__file__),1024**2))
    commands=[]; scenarios=[]

    def call(label,args,*,expected_status=None,rejected=False):
        revision_fact(REPO,revision,True)
        assert verify_distribution(package)==identity
        log=output/(label+'.log'); owned=None
        started=stamp()
        try:
            with OwnedProof(log) as log_owner:
                owned=spawn_owned([str(executable),*map(str,args)],cwd=output,
                    limits=ResourceLimits(90),stdout=log_owner.stream,stderr=subprocess.STDOUT,env=environment)
                code=owned.wait(); cleanup=terminate_owned(owned,deadline_seconds=5)
                log_owner.require_owned(); log_owner.stream.seek(0)
                raw=log_owner.stream.read(4*1024**2+1); assert len(raw)<=4*1024**2
                sanitized=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace('\r\n','\n').encode()
                log_owner.stream.seek(0);log_owner.stream.write(sanitized);log_owner.stream.truncate()
                log_owner.stream.flush();log_owner.require_owned()
                assert cleanup.reaped
                if rejected:
                    assert code!=0, 'Actual native setup unexpectedly accepted forbidden input'
                    result=None
                else:
                    assert code==0, 'Actual native setup command failed'
                    result=json.loads(raw)
                    if expected_status is not None: assert result['status']==expected_status
                commands.append(dict(label=label,exit_code=code,expected_rejection=rejected,
                    tree_reaped=cleanup.reaped,started_at_utc=started,finished_at_utc=stamp(),
                    log=log.name,log_sha256=sha(sanitized),passed=True))
                return result
        finally:
            if owned is not None: assert terminate_owned(owned,deadline_seconds=5).reaped
            revision_fact(REPO,revision,True)
            assert verify_distribution(package)==identity

    with TemporaryDirectory(prefix='R7 native public setup 中文 ',dir=output) as temporary:
        root=Path(temporary); config=root/'config.json'; data=root/'local data'; cloud=root/'cloud simulation'
        profile=root/'operator selection.json'
        init=call('01-init',['init-profile','--config',config,'--data-root',data,'--cloud-root',cloud,
            '--instance-id','native-public-setup'])
        assert init['runtime']=='NOT_STARTED' and not data.exists() and not cloud.exists()
        scenarios.append(dict(id='FIRST_RUN_EXPLICIT_DISJOINT_ROOTS',passed=True))
        data.mkdir(); cloud.mkdir()
        (cloud/'.r7-root.json').write_text(json.dumps({'root_id':'synthetic-native-folder'}),encoding='utf-8')
        refs={key+'_ref':key+'.json' for key in ('dataset','split_policy','cost_policy','research_policy','robustness_policy','risk_policy')}
        for reference in refs.values():
            (data/reference).write_text(json.dumps({'namespace':'LOCAL_RESEARCH'}),encoding='utf-8')
        policy=dict(refs,family_id='native-setup-only',seed=42,requested_dataset_profile='synthetic',
            requested_validation_profile='diagnostic',requested_robustness_profile='diagnostic')
        selection=dict(schema_version='r7-owner-selections-v0.2',cloud_root_id='synthetic-native-folder',
            research_policies={'selected-test':policy})
        profile.write_text(json.dumps(selection),encoding='utf-8')
        args=['configure-research','--config',config,'--selection-profile',profile]
        first=call('02-configure',args,expected_status='RESEARCH_CONFIGURED')
        assert first['validation_scope']=='SELECTION_SHAPE_LOCAL_REFERENCES_AND_NAMESPACE'
        assert first['cloud']=='LOCAL_STAGING_SELECTED' and first['paper']=='NOT_STARTED'
        assert first['provider_requests']==0 and first['credentials']=='NONE' and first['capital']=='NONE'
        destination=data/'owner-selections.json'; original=read_input(destination,65536)
        scenarios.append(dict(id='PUBLIC_NATIVE_LOCAL_SELECTION',passed=True))
        repeated=call('03-identical-retry',args,expected_status='ALREADY_CONFIGURED')
        assert repeated['selection_hash']==first['selection_hash'] and read_input(destination,65536)==original
        scenarios.append(dict(id='IMMUTABLE_IDENTICAL_RETRY',passed=True))
        policy['seed']=43; profile.write_text(json.dumps(selection),encoding='utf-8')
        call('04-different-selection',args,rejected=True)
        assert read_input(destination,65536)==original
        scenarios.append(dict(id='DIFFERENT_SELECTION_DENIED',passed=True))
        policy['seed']=42; profile.write_text(json.dumps(selection),encoding='utf-8')
        cloud_profile=cloud/'cloud-selection.json';cloud_profile.write_bytes(profile.read_bytes())
        call('05-cloud-origin',['configure-research','--config',config,'--selection-profile',cloud_profile],rejected=True)
        assert read_input(destination,65536)==original
        scenarios.append(dict(id='CLOUD_ORIGIN_SELECTION_DENIED',passed=True))
        alias=root/'operator-hardlink.json';os.link(cloud_profile,alias)
        call('06-cloud-hardlink',['configure-research','--config',config,'--selection-profile',alias],rejected=True)
        assert read_input(destination,65536)==original
        scenarios.append(dict(id='ACTUAL_WINDOWS_CLOUD_HARDLINK_DENIED',passed=True))
        profile.write_text(json.dumps(dict(selection,qualified_release='PASS')),encoding='utf-8')
        call('07-unknown-authority',args,rejected=True)
        assert read_input(destination,65536)==original
        scenarios.append(dict(id='CALLER_AUTHORITY_FIELD_DENIED',passed=True))
        profile.write_text(json.dumps(selection),encoding='utf-8');(data/refs['risk_policy_ref']).unlink()
        call('08-missing-local-input',args,rejected=True)
        assert read_input(destination,65536)==original
        scenarios.append(dict(id='MISSING_SELECTED_INPUT_DENIED',passed=True))
        fresh_cloud=root/'uncreated cloud'
        for label,path in [('09-cloud-config',fresh_cloud/'nested'/'config.json'),('10-equal-cloud-config',fresh_cloud)]:
            call(label,['init-profile','--config',path,'--data-root',root/'uncreated data','--cloud-root',fresh_cloud],rejected=True)
            assert not fresh_cloud.exists() and not (root/'uncreated data').exists()
        scenarios.append(dict(id='CONFIG_INSIDE_OR_EQUAL_CLOUD_DENIED_BEFORE_WRITE',passed=True))
        overlap_config=root/'overlap.json';overlap_data=root/'overlap data'
        call('11-overlapping-roots',['init-profile','--config',overlap_config,'--data-root',overlap_data,
            '--cloud-root',overlap_data/'nested'],rejected=True)
        assert not overlap_config.exists() and not overlap_data.exists()
        scenarios.append(dict(id='OVERLAPPING_ROOTS_DENIED_BEFORE_WRITE',passed=True))
        assert not list(data.rglob('*.sqlite'))
    assert not Path(temporary).exists()
    revision_fact(REPO,revision,True)
    assert verify_distribution(package)==identity
    assert sha(read_input(Path(__file__),1024**2))==launcher_before
    proof=dict(passed=True,executable_revision=revision,native_build_identity=identity,
        scope='ACTUAL_FROZEN_PUBLIC_RESEARCH_SETUP_SELECTION_SHAPE_AND_NAMESPACE_ONLY',
        scenarios=scenarios,commands=commands,launcher_sha256_before=launcher_before,launcher_sha256_after=launcher_before,
        private_fixture_removed=True,native_authentication='NOT_INVOKED',research='NOT_STARTED',paper='NOT_STARTED',
        product_path='EMPTY',pythonpath='UNSET',node='UNAVAILABLE_ON_PATH',
        live='NOT_STARTED',provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',ubuntu='NOT_RUN')
    with OwnedProof(output/'native-public-setup.json') as owner: owner.persist(proof)
    print(json.dumps(dict(passed=True,scenarios=len(scenarios),commands=len(commands),paper='NOT_STARTED')),flush=True)
    return 0


if __name__=='__main__': raise SystemExit(main())
