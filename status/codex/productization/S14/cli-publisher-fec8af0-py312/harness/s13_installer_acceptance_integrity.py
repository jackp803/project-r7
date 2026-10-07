"""Fresh installer increment guard; old reviewed primary verifier remains unchanged."""
import hashlib,json
from s13_acceptance_integrity import validate_primary_artifacts as _primary,require_artifact,require_sequence,digest,publish_retention_manifest
from s13_ssh_acceptance_integrity import validate_ssh_report
from application.datasets.catalog import read_local

COMMANDS=['install-dry','uninstall-dry','install-apply','uninstall-apply','invalid-commitment']
PIPELINE=['native-build','native-service-denial','native-installer-denial','native-ssh-access','native-smoke',
    'native-research','native-cloud','native-restore','full-source']
HARNESSES={'s13_native_installer_denial_v2.py','s13_installer_package_binding.py','s13_run_bound_installer_denial_v3.py'}

def read_bound_report(folder,name,verified,project):
    raw=read_local(folder,name,256*1024)
    expected='sha256:'+hashlib.sha256(raw).hexdigest()
    path=require_artifact(folder,name,expected)
    reference=path.relative_to(project).as_posix()
    if reference in verified and verified[reference]!=expected:
        raise ValueError('Previously validated report changed')
    value=json.loads(raw)
    verified[reference]=expected
    return value

def validate_harness_commitments(folder,mapping,verified,project):
    if not isinstance(mapping,dict) or set(mapping)!=HARNESSES:
        raise ValueError('Exact three execution harness commitments required')
    for name,expected in mapping.items():
        path=require_artifact(folder,name,expected)
        verified[path.relative_to(project).as_posix()]=expected

def validate_installer_report(folder,report,identity,verified,project):
    if (report['identity']!=identity or report['passed'] is not True or report['native_ubuntu']!='NOT_RUN'
            or report['systemd']!='NOT_RUN' or report['runtime']!='NOT_STARTED' or report['credentials']!='NONE'
            or report['actual_provider_requests']!=0 or report['capital']!='NONE' or report['github_compute']!='NOT_USED'
            or report['product_path']!='EMPTY' or report['pythonpath']!='UNSET'
            or report['package_identity_checks']!='BEFORE_AND_AFTER_EACH_COMMAND_AND_AT_COMPLETION'):
        raise ValueError('Exact Windows installer denial boundary differs')
    require_sequence(report['commands'],COMMANDS)
    require_sequence(report['scenarios'],['unsupported-Windows-'+name+'-denied' for name in COMMANDS])
    if not all(row['passed'] is True for row in report['scenarios']):raise ValueError('Installer denial scenario did not pass')
    for row in report['commands']:
        if (row['passed'] is not True or row['tree_reaped'] is not True or row['exit_code']!=2 or row['expected_exit_code']!=2
                or row['log']!=row['name']+'.log'):
            raise ValueError('Exact owned native denial command differs')
        path=require_artifact(folder,row['log'],row['log_sha256'])
        if path.read_text(encoding='utf-8').strip()!='R7: local configuration or startup validation failed':
            raise ValueError('Actual native denial stdout differs')
        verified[path.relative_to(project).as_posix()]=row['log_sha256']

def validate_primary_artifacts(*args,**kwargs):
    result=_primary(*args,**kwargs);repo,revision,source=args[:3];project=repo.parent.parent
    verified=result['verified_artifact_hashes'];identity=args[9]['identity']
    ssh=project/f'artifacts/r7-native-S13-ssh-access-{revision[:7]}'
    installer=project/f'artifacts/r7-native-S13-installer-denial-{revision[:7]}-bound-v3'
    for folder,name,validator in ((ssh,'native-ssh-access.json',validate_ssh_report),(installer,'native-installer-denial.json',validate_installer_report)):
        report=read_bound_report(folder,name,verified,project)
        validator(folder,report,identity,verified,project)
    context=read_bound_report(source,'qualification-context.json',verified,project)
    read_bound_report(source,'hardware-observations.json',verified,project)
    if context['launcher_hash']!=digest(project/'artifacts/s13_installer_qualify.py') or context['configuration']['expected_revision']!=revision:
        raise ValueError('Actual installer qualification launcher differs')
    data=read_bound_report(project/'artifacts',f'S13-recovery-{revision[:7]}-serial-pipeline.json',verified,project)
    require_sequence(data['commands'],PIPELINE,key='label')
    if data['passed'] is not True or data['revision']!=revision or data['worktree']!='CLEAN':raise ValueError('Exact serial installer pipeline differs')
    for row in data['commands']:
        if row['passed'] is not True or row['tree_reaped'] is not True or row['exit_code']!=0:raise ValueError('Actual pipeline command failed')
        path=require_artifact(project/'artifacts',row['log'],row['log_sha256']);verified[path.relative_to(project).as_posix()]=row['log_sha256']
    # The original pipeline's unbound v1 installer result is retained history.
    # Only v3 binds all three harnesses before and after execution.
    observed=read_bound_report(project/'artifacts',f'S13-service-installer-bound-v3-{revision[:7]}-pipeline.json',verified,project)
    if (observed['passed'] is not True or observed['revision']!=revision or observed['identity']!=identity
            or observed['worktree']!='CLEAN' or observed['unbound_v1']!='RETAINED_HISTORY;NOT_USED_FOR_PASS'
            or observed['v2_postexecution_hashes']!='RETAINED_HISTORY;NOT_USED_FOR_PASS'
            or observed['harness_binding']!='BEFORE_AND_AFTER_EXECUTION'
            or observed['scope']!='BOUND_V3_STABLE_EXECUTION_HARNESSES_AND_PACKAGE_REPLACEMENT_FOR_PRIOR_DENIAL_ATTEMPTS'):
        raise ValueError('Bound installer replacement qualification differs')
    require_sequence(observed['commands'],['native-installer-denial-bound-v3'],key='label')
    validate_harness_commitments(project/'artifacts',observed['harness_hashes'],verified,project)
    row=observed['commands'][0]
    if row['passed'] is not True or row['tree_reaped'] is not True or row['exit_code']!=0:raise ValueError('Bound native denial did not pass')
    path=require_artifact(project/'artifacts',row['log'],row['log_sha256']);verified[path.relative_to(project).as_posix()]=row['log_sha256']
    wrapper=project/'artifacts/S13-service-wrapper-windows-git-sh'
    proof=read_bound_report(wrapper,'qualification.json',verified,project)
    if (proof['passed'] is not True or proof['scope']!='ACTUAL_WINDOWS_GIT_SH_WITH_SYNTHETIC_EXECUTABLE_ONLY'
            or proof['native_ubuntu']!='NOT_RUN' or proof['actual_systemctl']!='NOT_RUN'):
        raise ValueError('Explicit Windows synthetic wrapper scope required')
    require_sequence(proof['commands'],['install-service-syntax','install-service-literal-argv','uninstall-service-syntax','uninstall-service-literal-argv'])
    for row in proof['commands']:
        if (row['passed'] is not True or row['tree_reaped'] is not True or row['exit_code']!=0
                or row['literal_arguments_preserved'] is not True or row['product_path']!='EMPTY' or row['cwd']!='OUTSIDE_PACKAGE'):
            raise ValueError('Literal bounded wrapper execution failed')
        name='install-service.sh' if row['name'].startswith('install-') else 'uninstall-service.sh'
        if row['wrapper_sha256']!=digest(repo/'packaging/linux'/name):raise ValueError('Actual executed wrapper bytes changed')
        log=require_artifact(wrapper,row['log'],row['log_sha256']);verified[log.relative_to(project).as_posix()]=row['log_sha256']
    result.update(native_scenarios=result['native_scenarios']+15,native_commands=result['native_commands']+15,
        ssh_access_scenarios=10,ssh_access_commands=10,installer_denial_scenarios=5,installer_denial_commands=5,
        real_ssh='NOT_RUN;LOCAL_PUBLIC_ENDPOINT_ONLY',native_ubuntu_installation='NOT_RUN',unbound_installer_v1='NOT_USED_FOR_PASS',
        postexecution_only_installer_v2='NOT_USED_FOR_PASS',installer_execution_harnesses='EXACT_THREE_BOUND_BEFORE_AND_AFTER_EXECUTION',
        windows_git_sh_synthetic_wrapper_commands=4)
    return result
