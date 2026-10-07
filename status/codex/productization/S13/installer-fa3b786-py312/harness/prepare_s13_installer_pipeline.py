"""Fresh bounded installer qualification harnesses; never overwrite prior evidence."""
from pathlib import Path
base=Path(__file__).resolve().parent
def fresh(name,text):
    path=base/name;assert not path.exists();path.write_text(text,encoding='utf-8',newline='\n')
def replace(text,old,new):
    assert text.count(old)==1,(old,text.count(old));return text.replace(old,new)

qualifier=(base/'s13_ssh_qualify.py').read_text(encoding='utf-8')
qualifier=replace(qualifier,"scope='S13 SSH argv", "scope='S13 bounded root-only native service install/uninstall source and typed CLI, exclusive sealed Linux wrapper assets, private ownership receipt and no-replace quarantine removal; SSH argv")
qualifier=replace(qualifier,'S12 continuous composition/S13 installer and native Ubuntu/real SSH commissioning','S12 continuous composition and actual native Ubuntu install/systemd/real SSH commissioning')
fresh('s13_installer_qualify.py',qualifier)

pipeline=(base/'s13_ssh_candidate_pipeline.py').read_text(encoding='utf-8')
needle=" ('native-ssh-access',[str(python)"
assert pipeline.count(needle)==1
pipeline=pipeline.replace(needle," ('native-installer-denial',[str(python),str(base/'s13_native_installer_denial.py'),str(package),str(base/f'r7-native-S13-installer-denial-{short}')],300),\n"+needle)
pipeline=replace(pipeline,"base/'s13_ssh_qualify.py'","base/'s13_installer_qualify.py'")
pipeline=replace(pipeline,"qualification_scope='S13_SSH_PLANNER_PUBLIC_NATIVE_PROBE_AND_RETAINED_SERVICE_RECOVERY'", "qualification_scope='S13_BOUNDED_INSTALLER_SOURCE_AND_ACTUAL_WINDOWS_DENIAL_WITH_RETAINED_SSH_SERVICE_RECOVERY'")
fresh('s13_installer_candidate_pipeline.py',pipeline)

native=(base/'s13_native_service_denial.py').read_text(encoding='utf-8')
start=native.index("for name,arguments in [")
end=native.index("\n    log=",start)
native=native[:start]+'''for name,arguments in [('install-dry',['install-services',*common]),
                       ('uninstall-dry',['uninstall-services',*common]),
                       ('install-apply',['install-services',*common,'--apply','--operation-hash','sha256:'+'d'*64]),
                       ('uninstall-apply',['uninstall-services',*common,'--apply','--operation-hash','sha256:'+'d'*64]),
                       ('invalid-commitment',['install-services',*common,'--apply','--operation-hash','INVALID'])]:'''+native[end:]
native=native.replace('native-service-denial.json','native-installer-denial.json')
native=replace(native,"'control.log','research.log','export.log'","'install-dry.log','uninstall-dry.log','install-apply.log','uninstall-apply.log','invalid-commitment.log'")
native=replace(native,"scope='Actual Windows native platform denial only; Ubuntu service startup NOT_RUN'", "scope='Actual Windows frozen installer platform/commitment denial only; actual Ubuntu root/files/systemd NOT_RUN'")
fresh('s13_native_installer_denial.py',native)
print('Prepared9-stage installer pipeline and5 exact native denial scenarios')
