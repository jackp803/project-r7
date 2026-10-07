"""Prepare fresh scoped launchers; do not rewrite previous attempt evidence."""
from pathlib import Path
project=Path(__file__).resolve().parent.parent
base=project/'artifacts'
def new(name, source):
    path=base/name
    assert not path.exists()
    compile(source,name,'exec')
    path.write_text(source,encoding='utf-8',newline='\n')
ui=(base/'s13_recovery_ui_qualify_v2.py').read_text(encoding='utf-8')
assert ui.count("['run','build'],['run','test:browser']")==1
ui=ui.replace("['run','build'],['run','test:browser']","['run','build']")
ui=ui.replace("commands=[],passed=False,execution='LOCAL'","commands=[],passed=False,qualification_scope='FRONTEND_ONLY',browser_status='NOT_RUN_PENDING_SERIAL_BROWSER',execution='LOCAL'")
ui=ui.replace("S13 recovery UI adds strict restoration health DTO", "S13 guarded service and UI link increment; frontend-only qualification preserves strict restoration health DTO")
new('s13_service_ui_frontend.py',ui)
full=(base/'s13_recovery_qualify.py').read_text(encoding='utf-8')
full=full.replace("scope='S13 private full product-data", "scope='S13 exact native control/research service subject, owner permissions, shared scope lock provisioning, Unicode pinned config, actual research child config binding and UI root/descendant reparse denial; retained private full product-data")
new('s13_service_qualify.py',full)
pipeline=(base/'s13_recovery_candidate_pipeline.py').read_text(encoding='utf-8')
pipeline=pipeline.replace("s13_recovery_qualify.py", "s13_service_qualify.py")
pipeline=pipeline.replace(" ('native-smoke'", " ('native-service-denial',[str(python),str(base/'s13_native_service_denial.py'),str(package),str(base/f'r7-native-S13-service-denial-{short}')],300),\n ('native-smoke'")
pipeline=pipeline.replace("initial_browser_status='PASS' if ui['passed'] else 'NOT_RUN_FIXTURE_STARTUP_MEMORY_PRESSURE;SEPARATE_BROWSER_QUALIFICATION_REQUIRED'", "initial_browser_status='NOT_RUN_PENDING_SERIAL_BROWSER',qualification_scope='S13_SERVICE_SUBJECT_AND_RETAINED_WINDOWS_RECOVERY',ubuntu_service_acceptance='NOT_RUN'")
pipeline=pipeline.replace("assert ui['source_before']==", "assert ui['qualification_scope']=='FRONTEND_ONLY' and ui['browser_status']=='NOT_RUN_PENDING_SERIAL_BROWSER'\nassert ui['source_before']==")
new('s13_service_candidate_pipeline.py',pipeline)
browser=(base/'s13_serial_browser_qualify.py').read_text(encoding='utf-8')
browser=browser.replace("The earlier seven-fixture startup failure remains a distinct retained attempt.","This run intentionally stages frontend/native build before serial fixtures; earlier failure evidence is not relabelled.")
browser=browser.replace("assert initial_report['source_before']", "assert initial_report['qualification_scope'] == 'FRONTEND_ONLY'\nassert initial_report['browser_status'] == 'NOT_RUN_PENDING_SERIAL_BROWSER'\nassert initial_report['source_before']")
browser=browser.replace("status='NOT_RUN_FIXTURE_STARTUP_MEMORY_PRESSURE', browser_cases_executed=0,\n        results_sha256=digest(initial / 'browser-results.json')", "status='NOT_RUN_PENDING_SERIAL_BROWSER', browser_cases_executed=0, qualification_scope='FRONTEND_ONLY'")
new('s13_service_serial_browser_qualify.py',browser)
print('Fresh scoped frontend/full/native/serial-browser launchers prepared')
