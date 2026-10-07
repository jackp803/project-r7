"""Fresh browser-results hash capture and retention-time byte commitment checks."""
from pathlib import Path
base=Path(__file__).resolve().parent
browser=(base/'s13_service_serial_browser_qualify.py').read_text(encoding='utf-8')
old="item.update(browser_stats=stats, observed_cases=names, errors_count=len(actual.get('errors', [])))"
assert browser.count(old)==1
browser=browser.replace(old,old+"\n            item['browser_results_sha256'] = digest(output / f'{profile}-browser-results.json')")
new=base/'s13_service_serial_browser_qualify_v2.py';assert not new.exists();compile(browser,str(new),'exec');new.write_text(browser,encoding='utf-8',newline='\n')
collector=(base/'s13_service_accept.py').read_text(encoding='utf-8')
collector=collector.replace("S13-service-launcher-review.json","S13-service-launcher-review-v2.json")
start=collector.index("phase_counts=")
collector=collector[:start]+'''from s13_acceptance_integrity import validate_primary_artifacts
initial=project/f'artifacts/r7-productization-S13-recovery-ui-qualified-{short}-safe-logs'
frontend=load(initial/'ui-qualification.json')
integrity=validate_primary_artifacts(root,revision,source,full,ui_root,ui,initial,frontend,build_root,build,
    native_roots,dict(smoke=smoke,research=research,cloud=cloud,restore=restore),denial_root,denial,
    project/'artifacts/s13_service_serial_browser_qualify_v2.py')
assert integrity['source_commands']==33 and integrity['native_scenarios']==36 and integrity['native_commands']==40
''' +collector[start:]
old="original=file.read_bytes()\n    raw=original if binary"
new="original=file.read_bytes()\n    original_ref=file.relative_to(project).as_posix()\n    expected=integrity['verified_artifact_hashes'].get(original_ref)\n    if expected is not None and hash_bytes(original)!=expected:raise ValueError('Verified evidence changed before copying')\n    raw=original if binary"
assert collector.count(old)==1;collector=collector.replace(old,new)
collector=collector.replace("transformation='NONE' if binary else 'UTF8_REPLACEMENT_DECODE/CRLF_TO_LF/LOCAL_PATH_SANITIZATION'", "integrity='RECORDED_OR_LOADED_REPORT_HASH_VERIFIED' if expected is not None else 'COLLECTION_HASH_ONLY;SUPPLEMENTAL_NOT_USED_FOR_PASS',transformation='NONE' if binary else 'UTF8_REPLACEMENT_DECODE/CRLF_TO_LF/LOCAL_PATH_SANITIZATION'")
collector=collector.replace("'s13_service_serial_browser_qualify.py'","'s13_service_serial_browser_qualify_v2.py'")
collector=collector.replace("'s13_prepare_service_accept.py','s13_service_accept.py'", "'s13_prepare_service_accept.py','s13_service_accept_v2.py','s13_prepare_service_integrity_v2.py','s13_acceptance_integrity.py','s13_acceptance_integrity_tests.py','run_s13_integrity_tests.py'")
collector=collector.replace("pending=['S13 native", "evidence_integrity={k:v for k,v in integrity.items() if k!='verified_artifact_hashes'},\n    pending=['S13 native")
new=base/'s13_service_accept_v2.py';assert not new.exists();compile(collector,str(new),'exec');new.write_text(collector,encoding='utf-8',newline='\n')
print('Prepared fresh browser hash capture and collector integrity gates; not executed')
