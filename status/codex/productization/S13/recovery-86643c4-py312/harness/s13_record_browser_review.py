from pathlib import Path
import hashlib,json
project=Path(__file__).resolve().parent.parent
folder=project/'artifacts'
file=folder/'s13_serial_browser_qualify.py'
record=dict(schema_version='r7-bounded-independent-review-record-v0.2',reviewer='/root/qualification_review',
    review_type='INDEPENDENT_READ_ONLY_SOURCE_AND_ASSERTION_INSPECTION',
    harness_sha256='sha256:'+hashlib.sha256(file.read_bytes()).hexdigest(),
    critical_findings=0,initial_important_findings=2,remaining_important_findings=0,
    resolved=['Ignored browser assets are bound to actual complete native UI inventory and candidate revision; rechecked before and after every fixture',
        'Actual root and descendant reparse/link entries are denied before hashing/traversal'],
    unchanged_cases=11,profiles=7,assertions='UNCHANGED',retries=0,workers=1,
    local_asset_guard_regression=dict(result='PASS',tests_run=5,skipped=0,actual_windows_root_junction=True,
        log='S13-serial-browser-build-guard-v2-GREEN.log'),
    limitations=['Reviewer did not execute tests or inspect private fixtures',
        'Source/assertion review only; runtime qualification and full product/platform acceptance are separate'])
(folder/'S13-independent-serial-browser-review.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
initial=folder/'r7-productization-S13-recovery-ui-qualified-86643c4-safe-logs'
report=json.loads((initial/'ui-qualification.json').read_bytes())
stats=json.loads((initial/'browser-results.json').read_bytes())['stats']
assert len(report['commands'])==5 and all(c['passed'] for c in report['commands']) and not report['passed']
assert stats['expected']==stats['unexpected']==stats['skipped']==stats['flaky']==0
disposition=dict(schema_version='r7-failed-browser-startup-disposition-v0.2',
    executable_revision=report['source_before']['revision'],frontend_commands_passed=5,frontend_unit_tests_passed=15,
    browser='NOT_RUN',cases_executed=0,fixture_startup='FAILED_EXISTING_RESOURCE_ADMISSION',
    observed_resource_reason='RESEARCH_MEMORY_PRESSURE',available_memory_bytes=4615544832,
    minimum_available_memory_bytes=5060439859,physical_memory_bytes=33736265728,
    source_of_resource_values='Original06-test-browser.log;actualtypedResearchResourceError',
    collector='FAILED_SCREENSHOT_COPY_AFTER_BROWSER_STARTUP_DENIAL;ORIGINAL_REPORT_RETAINED_UNALTERED',
    product_threshold_changes='NONE',attempt_replaced=False,
    original_report_sha256='sha256:'+hashlib.sha256((initial/'ui-qualification.json').read_bytes()).hexdigest(),
    original_browser_results_sha256='sha256:'+hashlib.sha256((initial/'browser-results.json').read_bytes()).hexdigest())
(folder/'S13-initial-browser-86643c4-disposition.json').write_text(json.dumps(disposition,indent=2)+'\n',encoding='utf-8',newline='\n')
print('Independentreview and original failedbrowserattempt dispositions recorded outsideGit')
