from pathlib import Path
import hashlib,json
base=Path(__file__).resolve().parent
expected={
 's14_feedback_candidate_pipeline.py':'dc8b8affacfecf9ddbb0d24aab32a74095ccd94197b6ad2e16bd34c9a815c498',
 's14_feedback_bound_installer.py':'29537cfc12b75dec90964fc27c811b96997dd62c767e18030d97eb25d279475d',
 's14_feedback_source_qualify.py':'90f816fa1a9a783f3bb82dd523bb2dc13f260d9eb01498e29d0354e42be225dc',
 's14_feedback_ui_frontend.py':'b88b5e8b06b74e9cfc719b8a46f28d2da45bf3fd4cd6cc75d1177e1a161d682d',
 's14_feedback_serial_browser_qualify.py':'816112fd91f235acf5fad653e379f3bf88f589be55a2300bf788bb290d9ca084',
 'test_s14_feedback_harness_integrity.py':'703bc459024e5ffd306104c03d304f206e809e4beec173bed3fafc38d4cf4b7d',
 'run_s14_feedback_harness_integrity.py':'2930c66d2ca0d1bcc0bce3f9c03e5fe13bb32ef78ef439b8a0518f781010dcfa',
}
for name,digest in expected.items():assert hashlib.sha256((base/name).read_bytes()).hexdigest()==digest,name
result=json.loads((base/'S14-feedback-harness-integrity-runner-GREEN.json').read_bytes())
assert result['passed'] and result['tests_run']==6 and result['tree_reaped']
assert hashlib.sha256((base/'S14-feedback-harness-integrity-runner-GREEN.log').read_bytes()).hexdigest()=='c0c58b52e836dfb6706185e8ab3abb4307cfa189fa2ee69345984bf0322b2fcc'
facts=dict(reviewer='qualification_review',review_kind='INDEPENDENT_READ_ONLY_SOURCE_REVIEW',critical=0,important=0,execution='NONE',
 reviewed_files={name:'sha256:'+digest for name,digest in expected.items()},regression=result,
 resolved_findings=['Bound installer failure cleanup propagates nonzero exit','All14 external pipeline dependencies including SSH helper are bound',
 'Integrity runner failure cleanup propagates nonzero exit'],preexecution_generator_syntax='REPAIRED_BEFORE_ANY_QUALIFICATION_STAGE;BROKEN_DRAFT_RETAINED',
 native_execution='NOT_RUN_YET',cloud='NOT_RUN',forward='NOT_RUN',ubuntu='NOT_RUN')
target=base/'S14-paper-feedback-independent-harness-review.json';assert not target.exists()
target.write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n');print('Retained7 independent harness commitments and actual6 regressions')
