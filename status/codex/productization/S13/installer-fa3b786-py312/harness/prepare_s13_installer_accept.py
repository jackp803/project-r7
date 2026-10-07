"""Historical v2 collector generator, superseded before any acceptance execution."""
raise SystemExit('Historical v2 generator is disabled; use the independently reviewed s13_installer_accept.py')
from pathlib import Path
import ast
base=Path(__file__).resolve().parent;text=(base/'s13_ssh_accept.py').read_text(encoding='utf-8')
def change(old,new):
    global text
    assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
change("full['tests_run']==1850","full['tests_run']==1890")
change("len(pipeline['commands'])==8","len(pipeline['commands'])==9")
change("for name,expected in ssh_source_review['reviewed_source_hashes'].items():assert hash_bytes((root/name).read_bytes())==expected",
    "# The earlier SSH CLI review is historical; current CLI is bound by installer review.\nfor name,expected in ssh_source_review['reviewed_source_hashes'].items():\n    if name!='src/application/cli.py':assert hash_bytes((root/name).read_bytes())==expected")
anchor="assert ui['initial_attempt']['status']=='NOT_RUN_PENDING_SERIAL_BROWSER'"
addition="""installer_review=load(project/'artifacts/S13-service-installer-independent-source-review.json')
assert installer_review['remaining_critical']==installer_review['remaining_important']==0
for name,expected in installer_review['reviewed_source_hashes'].items():assert hash_bytes((root/name).read_bytes())==expected
installer_harness_review=load(project/'artifacts/S13-service-installer-independent-harness-review.json')
assert installer_harness_review['remaining_critical']==installer_harness_review['remaining_important']==0
for name,expected in installer_harness_review['harness_hashes'].items():assert hash_bytes((project/'artifacts'/name).read_bytes())==expected
"""
change(anchor,addition+anchor)
change('from s13_ssh_acceptance_integrity import validate_primary_artifacts,publish_retention_manifest',
    'from s13_installer_acceptance_integrity import validate_primary_artifacts,publish_retention_manifest')
change("integrity['native_scenarios']==46 and integrity['native_commands']==50","integrity['native_scenarios']==51 and integrity['native_commands']==55")
change("S13/ssh-{short}-py312","S13/installer-{short}-py312")
change("'native-service-denial.json','native-ssh-access.json'):","'native-service-denial.json','native-ssh-access.json','native-installer-denial.json'):")
anchor="retain(project/f'artifacts/S13-recovery-{short}-serial-pipeline.json','pipeline/serial-pipeline.json')"
addition="""installer_root=project/f'artifacts/r7-native-S13-installer-denial-{short}-bound-v2'
installer=load(installer_root/'native-installer-denial.json');top(installer_root,'native-installer-denial-bound-v2')
top(project/f'artifacts/r7-native-S13-installer-denial-{short}','unaccepted-native-installer-v1')
retain(project/f'artifacts/S13-service-installer-bound-{short}-pipeline.json','pipeline/bound-installer-v2.json')
"""
change(anchor,addition+anchor)
change("        if file.name.startswith('S13-service-installer-'):continue\n",'')
anchor="for name in ('s13_ssh_qualify.py'"
addition="""retain(project/'artifacts/S13-service-installer-independent-source-review.json','review/installer-source-review.json')
retain(project/'artifacts/S13-service-installer-independent-harness-review.json','review/installer-harness-review.json')
for name in ('prepare_s13_installer_pipeline.py','s13_installer_candidate_pipeline.py','s13_installer_qualify.py',
    's13_native_installer_denial.py','s13_native_installer_denial_v2.py','s13_installer_package_binding.py',
    's13_installer_package_binding_tests.py','run_s13_installer_binding_tests.py','prepare_s13_bound_installer_denial.py',
    's13_run_bound_installer_denial_v2.py','s13_installer_acceptance_integrity.py','s13_installer_acceptance_integrity_tests.py',
    'run_s13_installer_integrity_tests.py','prepare_s13_installer_accept.py','s13_installer_accept.py',
    's13_record_installer_checkpoint.py','s13_record_installer_harness_review.py','s13_service_wrapper_probe.py',
    's13_reproduce_original_asset_copy.py','run_s13_install_development.py'):
    retain(project/'artifacts'/name,'harness/'+name)
wrapper_root=project/'artifacts/S13-service-wrapper-windows-git-sh';top(wrapper_root,'windows-git-sh-fake-only')
"""
change(anchor,addition+anchor)
change("ssh_root:'native-ssh-access',","ssh_root:'native-ssh-access',installer_root:'native-installer-denial-bound-v2',")
change("previous_qualified_executable_revision='14aeb991aef9d92705cdf0a1151a2df2893e02bb'", "previous_qualified_executable_revision='9245c3c9cd6aa369f04ed6d7aa909225dbc15cd7'")
change("scope='SSH_PLAN_AND_NATIVE_PUBLIC_LOOPBACK_ACCESS_WITH_SCOPED_WINDOWS_RECOVERY;UBUNTU_AND_REAL_SSH_NOT_RUN'", "scope='BOUNDED_INSTALLER_SOURCE_AND_WINDOWS_DENIAL_WITH_RETAINED_SSH_PUBLIC_ACCESS_AND_RECOVERY;UBUNTU_ROOT_SYSTEMD_REAL_SSH_NOT_RUN'")
change("+len(ssh['scenarios']),", "+len(ssh['scenarios'])+len(installer['scenarios']),")
change("+len(ssh['commands']),", "+len(ssh['commands'])+len(installer['commands']),")
change("ssh_access_scenarios=10,ssh_access_commands=10,real_ssh='NOT_RUN',", "installer_denial_scenarios=5,installer_denial_commands=5,installer_binding='BEFORE_AND_AFTER_EACH_COMMAND_AND_COMPLETION',unbound_installer_v1='NOT_USED_FOR_PASS',ssh_access_scenarios=10,ssh_access_commands=10,real_ssh='NOT_RUN',")
change("pending=['S13 native service install/uninstall code and actual Ubuntu package/systemd/reboot/SSH qualification'", "pending=['S13 actual Ubuntu package/install/uninstall/systemd/reboot/SSH qualification'")
change("S13/ssh-artifact-hashes-{short}.json", "S13/installer-artifact-hashes-{short}.json")
change("next_step='Integrate bounded native install/uninstall tooling; continue", "next_step='Continue")
change("phase='EXACT_CLEAN_SSH_PUBLIC_ACCESS_AND_WINDOWS_RECOVERY_QUALIFICATION'", "phase='EXACT_CLEAN_INSTALLER_SOURCE_WINDOWS_DENIAL_AND_RETAINED_RECOVERY_QUALIFICATION'")
change("progress['ssh_qualified_checkpoint']=", "progress['installer_qualified_checkpoint']=")
change("scope='SSH_SOURCE_NATIVE_PUBLIC_ACCESS_AND_WINDOWS_RECOVERY;UBUNTU_REAL_SSH_NOT_RUN'", "scope='INSTALLER_SOURCE_WINDOWS_DENIAL_AND_RETAINED_RECOVERY;UBUNTU_SYSTEMD_NOT_RUN'")
anchor="progress['tests_executed'].append("
addition="""progress['service_admin_increment'].update(status='SOURCE_AND_SCOPED_WINDOWS_DENIAL_PASS;UBUNTU_ROOT_SYSTEMD_NOT_RUN',
    source_checkpoint=revision,full_source='PASS',native='SCOPED_WINDOWS_DENIAL_PASS',browser='SERIAL_SAME11CASES_PASS',evidence_ref=ref+'/disposition.json')
"""
change(anchor,addition+anchor)
change("native_package_scope='SERVICE_PLATFORM_DENIAL_AND_RETAINED_PRIVATE_RECOVERY_OFFLINE_BRIDGE'", "native_package_scope='WINDOWS_INSTALLER_SERVICE_DENIAL_SSH_PUBLIC_ACCESS_AND_RETAINED_RECOVERY'")
change('S13 scoped SSH/public-access/recovery executable', 'S13 scoped installer-source/Windows-denial/SSH/recovery executable')
change('commands across SSH plan/public access/service platform denial/', 'commands across bound-v2 installer denial/SSH plan/public access/service platform denial/')
change("f'Independent bounded source/harness review", "f'Unbound installer v1 is retained history and not used for PASS; five denial scenarios were rerun with before/after package checks. Independent bounded source/harness review")
ast.parse(text)
path=base/'s13_installer_accept.py';assert not path.exists();path.write_text(text,encoding='utf-8',newline='\n')
print('Prepared scoped installer collector with51 native scenarios/55 commands and boundv2 replacement evidence')
