"""Prepare service-scope retention from reviewed recovery collector, no execution."""
from pathlib import Path
base=Path(__file__).resolve().parent
old=(base/'s13_recovery_accept_v2.py').read_text(encoding='utf-8')
source=old.replace('Retain exact-clean successful scoped recovery evidence','Retain exact-clean successful scoped service-subject and Windows recovery evidence')
source=source.replace("full['tests_run']>=1789","full['tests_run']==1828")
source=source.replace("len(pipeline['commands'])==6","len(pipeline['commands'])==7")
source=source.replace("previous_qualified_executable_revision='7f50cbf4fdb339ac50ea98f0880de05e8546fb8a'", "previous_qualified_executable_revision='86643c4b0444db2cfb33ce071618c1e3f708ad37'")
source=source.replace("scope='SCOPED_PRIVATE_RECOVERY_AND_RETAINED_OFFLINE_BRIDGE'", "scope='GUARDED_SERVICE_SOURCE_AND_SCOPED_WINDOWS_RECOVERY;UBUNTU_SERVICE_NOT_RUN'")
source=source.replace("target=root/f'status/codex/productization/S13/recovery-{short}-py312'", "target=root/f'status/codex/productization/S13/service-{short}-py312'")
source=source.replace("manifest=root/f'status/codex/productization/S13/recovery-artifact-hashes-{short}.json'", "manifest=root/f'status/codex/productization/S13/service-artifact-hashes-{short}.json'")
start=source.index("browser_review=load(project/'artifacts/S13-independent-serial-browser-review.json')")
end=source.index('phase_counts=',start)
source=source[:start]+'''service_review=load(project/'artifacts/S13-service-independent-review-v2.json')
assert service_review['remaining_critical']==service_review['remaining_important']==0
for name,expected in service_review['reviewed_source_hashes'].items():assert hash_bytes((root/name).read_bytes())==expected
browser_review=load(project/'artifacts/S13-service-launcher-review.json')
assert browser_review['remaining_critical']==browser_review['remaining_important']==0
for name,expected in browser_review['harness_hashes'].items():assert hash_bytes((project/'artifacts'/name).read_bytes())==expected
denial_root=project/f'artifacts/r7-native-S13-service-denial-{short}'
denial=load(denial_root/'native-service-denial.json')
assert denial['passed'] and denial['identity']==identity
assert len(denial['commands'])==len(denial['scenarios'])==3
assert all(c['passed'] and c['tree_reaped'] and c['exit_code']==2 for c in denial['commands'])
assert all(c['passed'] for c in denial['scenarios'])
assert ui['initial_attempt']['status']=='NOT_RUN_PENDING_SERIAL_BROWSER'
assert ui['initial_attempt']['qualification_scope']=='FRONTEND_ONLY'
''' +source[end:]
source=source.replace("'native-smoke.json','native-selected-research.json','native-S14.json','native-recovery.json'", "'native-smoke.json','native-selected-research.json','native-S14.json','native-recovery.json','native-service-denial.json'")
source=source.replace("top(initial,'initial-browser-startup-NOT_RUN')", "top(initial,'frontend-only')\ntop(denial_root,'native-service-denial')")
start=source.index("for pattern in ('S13-cloud-long-path-*.log'")
end=source.index("measurements=load(",start)
source=source[:start]+'''for pattern in ('S13-service-*.log','S13-control-asset-junction-*.log',f'S13-recovery-{short}-*.log'):
    for file in sorted((project/'artifacts').glob(pattern)):
        retain(file,'development/'+file.name)
        summary=file.with_suffix('.json')
        if summary.is_file():retain(summary,'development/'+summary.name)
retain(project/'artifacts/S13-independent-recovery-review.json','review/retained-recovery-harness-review.json')
retain(project/'artifacts/S13-independent-long-path-review.json','review/retained-long-path-review.json')
retain(project/'artifacts/S13-service-independent-review-v2.json','review/service-source-review.json')
retain(project/'artifacts/S13-service-launcher-review.json','review/service-launcher-review.json')
for name in ('s13_service_ui_frontend.py','s13_service_candidate_pipeline.py','s13_service_serial_browser_qualify.py',
    's13_native_service_denial.py','s13_service_qualify.py','s13_prepare_service_qualification.py',
    's13_prepare_service_accept.py','s13_service_accept.py','s13_record_service_reviews.py',
    'run_bounded_unittest.py','run_bounded_suite_unittest.py','s13_native_recovery_probe.py',
    's13_native_research_probe.py','s14_native_probe.py','s13_refresh_authoring_examples_v5.py',
    's13_retain_withdrawn_service_5f42a84.py'):
    retain(project/'artifacts'/name,'harness/'+name)
''' +source[end:]
source=source.replace("schema_version='r7-scoped-recovery-qualification-v0.2'", "schema_version='r7-scoped-service-qualification-v0.2'")
source=source.replace("initial_seven_fixture_attempt='NOT_RUN_MEMORY_PRESSURE;RETAINED_SEPARATELY'", "initial_frontend_scope='FRONTEND_ONLY;BROWSER_PENDING_UNTIL_SERIAL_RUN'")
source=source.replace("smoke['scenario_count']+1+cloud['scenario_count']+restore['scenario_count']", "smoke['scenario_count']+1+cloud['scenario_count']+restore['scenario_count']+len(denial['scenarios'])")
source=source.replace("len(smoke['commands'])+1+len(cloud['commands'])+restore['command_count']", "len(smoke['commands'])+1+len(cloud['commands'])+restore['command_count']+len(denial['commands'])")
source=source.replace("smoke=smoke['scenario_count'],selected_research=1", "windows_service_platform_denial=3,smoke=smoke['scenario_count'],selected_research=1")
source=source.replace("S13 native Ubuntu packages/service/install/reboot/SSH qualification", "S13 native service install/uninstall/SSH code and actual Ubuntu package/systemd/reboot qualification")
source=source.replace("progress['long_path_remediation'].update(status='PASS',source_checkpoint=revision,full_source='PASS',native='SCOPED_WINDOWS_PASS',browser='SERIAL_SAME11CASES_PASS',evidence_ref=ref+'/disposition.json')", "progress['service_increment'].update(status='SCOPED_WINDOWS_AND_SOURCE_PASS;UBUNTU_SERVICE_NOT_RUN',source_checkpoint=revision,full_source='PASS',native='SCOPED_WINDOWS_PASS',browser='SERIAL_SAME11CASES_PASS',evidence_ref=ref+'/disposition.json')")
source=source.replace("phase='EXACT_CLEAN_COMPLETE_PRIVATE_RECOVERY_QUALIFICATION'", "phase='EXACT_CLEAN_SERVICE_SUBJECT_AND_WINDOWS_RECOVERY_QUALIFICATION'")
source=source.replace("progress['pending_recovery_checkpoint']=", "progress['service_qualified_checkpoint']=")
source=source.replace("scope='QUALIFIED_PRIVATE_RECOVERY_ONLY'", "scope='SERVICE_SOURCE_AND_WINDOWS_RECOVERY_ONLY;UBUNTU_NOT_RUN'")
source=source.replace("native_package_scope='PRIVATE_RECOVERY_AND_RETAINED_OFFLINE_BRIDGE'", "native_package_scope='SERVICE_PLATFORM_DENIAL_AND_RETAINED_PRIVATE_RECOVERY_OFFLINE_BRIDGE'")
source=source.replace("S13 scoped recovery executable", "S13 scoped service/recovery executable")
source=source.replace("(earlier simultaneous startupNOT_RUN due actual memory pressure retained separately)", "(frontend-only preparation followed by exact serial browser qualification)")
source=source.replace("across smoke/research/offline bridge/private recovery PASS", "across service platform denial/smoke/research/offline bridge/private recovery PASS;actual Ubuntu service/kernel/installNOT_RUN")
source=source.replace("scenarios=smoke['scenario_count']", "scenarios=smoke['scenario_count']")
path=base/'s13_service_accept.py';assert not path.exists()
compile(source,str(path),'exec')
path.write_text(source,encoding='utf-8',newline='\n')
print('Prepared service retention collector; not executed or claiming qualification')
