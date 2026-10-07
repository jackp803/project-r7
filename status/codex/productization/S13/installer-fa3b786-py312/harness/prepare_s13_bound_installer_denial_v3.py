from pathlib import Path
base=Path(__file__).resolve().parent
text=(base/'s13_run_bound_installer_denial_v2.py').read_text(encoding='utf-8')
def change(old,new):
    global text
    assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
change("denial-{short}-bound-v2'","denial-{short}-bound-v3'")
text=text.replace('S13-service-installer-bound-{short}-pipeline','S13-service-installer-bound-v3-{short}-pipeline')
change("started=stamp()", "binding_names=('s13_native_installer_denial_v2.py','s13_installer_package_binding.py',Path(__file__).name)\nbefore_hashes={name:'sha256:'+hashlib.sha256((base/name).read_bytes()).hexdigest() for name in binding_names}\nstarted=stamp()")
change("assert verify_distribution(package)==identity;revision_fact(repo,revision,True)", "assert verify_distribution(package)==identity;revision_fact(repo,revision,True)\nassert before_hashes=={name:'sha256:'+hashlib.sha256((base/name).read_bytes()).hexdigest() for name in binding_names}")
change('BOUND_V2_REPLACEMENT_FOR_UNBOUND_V1_INSTALLER_DENIAL_ONLY','BOUND_V3_STABLE_EXECUTION_HARNESSES_AND_PACKAGE_REPLACEMENT_FOR_PRIOR_DENIAL_ATTEMPTS')
change("unbound_v1='RETAINED_HISTORY;NOT_USED_FOR_PASS',", "unbound_v1='RETAINED_HISTORY;NOT_USED_FOR_PASS',v2_postexecution_hashes='RETAINED_HISTORY;NOT_USED_FOR_PASS',harness_binding='BEFORE_AND_AFTER_EXECUTION',")
change("label='native-installer-denial-bound-v2'","label='native-installer-denial-bound-v3'")
old="""harness_hashes={name:'sha256:'+hashlib.sha256((base/name).read_bytes()).hexdigest() for name in
        ('s13_native_installer_denial_v2.py','s13_installer_package_binding.py',Path(__file__).name)}"""
change(old,'harness_hashes=before_hashes')
path=base/'s13_run_bound_installer_denial_v3.py';assert not path.exists();path.write_text(text,encoding='utf-8',newline='\n')
print('Prepared immutable v3 with exact three execution-time harness commitments')
