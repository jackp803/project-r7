"""Exact independent-review inventories and bound actual regression proof."""
from s13_acceptance_integrity import require_artifact
from s13_installer_acceptance_integrity import read_bound_report
from application.qualification import parse_result

SOURCE_FILES=frozenset(('src/application/cloud/paper_feedback.py','src/application/cloud/public_feedback.py',
 'src/storage/paper_feedback.py','src/storage/migrations/0017_paper_feedback_outbox.sql','contracts/paper_feedback_v0_2.schema.json',
 'src/application/cloud/rclone_bridge.py','tests/product/test_paper_feedback_bridge.py','tests/product/test_paper_feedback_outbox.py',
 'tests/product/test_paper_feedback_projection.py','tests/product/test_paper_feedback_schema.py','tests/product/test_public_feedback_dispatch.py',
 'docs/product/v0_2/PAPER_FEEDBACK_IMPLEMENTATION.md'))
HARNESS_FILES=frozenset(('s14_feedback_candidate_pipeline.py','s14_feedback_bound_installer.py','s14_feedback_source_qualify.py',
 's14_feedback_ui_frontend.py','s14_feedback_serial_browser_qualify.py','test_s14_feedback_harness_integrity.py','run_s14_feedback_harness_integrity.py'))
RETENTION_FILES=frozenset(('s14_feedback_accept.py','s14_feedback_acceptance_core.py','prepare_s14_feedback_acceptance_core.py',
 's14_feedback_review_integrity.py','test_s14_feedback_review_integrity.py','run_s14_review_integrity.py'))

def validate_review(review,*,kind,repo,base,bound,project):
 if kind=='source':root,names,key=repo,SOURCE_FILES,'kind'
 elif kind=='harness':root,names,key=base,HARNESS_FILES,'review_kind'
 elif kind=='retention':root,names,key=base,RETENTION_FILES,'review_kind'
 else:raise ValueError('Explicit review subject required')
 if (not isinstance(review,dict) or review.get(key)!='INDEPENDENT_READ_ONLY_SOURCE_REVIEW'
  or review.get('reviewer')!='qualification_review' or review.get('execution')!='NONE'
  or type(review.get('critical')) is not int or type(review.get('important')) is not int
  or review['critical']!=0 or review['important']!=0 or not isinstance(review.get('reviewed_files'),dict)
  or set(review['reviewed_files'])!=names):raise ValueError('Exact independent review commitments required')
 for name,expected in review['reviewed_files'].items():
  path=root/name;require_artifact(path.parent,path.name,expected)
  bound[path.relative_to(project).as_posix()]=expected
 if kind in ('harness','retention'):
  stem,count=('S14-feedback-harness-integrity-runner-GREEN',6) if kind=='harness' else ('S14-feedback-harness-review-binding-GREEN-v2',5)
  regression=read_bound_report(base,stem+'.json',bound,project)
  if (regression!=review.get('regression') or regression.get('tests_run')!=count or regression.get('passed') is not True
   or regression.get('tree_reaped') is not True or regression.get('errors')!=0 or regression.get('failures')!=0
   or kind=='harness' and regression.get('wrapper_sha256')!=review['reviewed_files']['s14_feedback_bound_installer.py']):
   raise ValueError('Actual independent review regression subject differs')
  path=require_artifact(base,stem+'.log',regression.get('log_sha256'))
  result=parse_result(path.read_text(encoding='utf-8'),returncode=0)
  if (not result.passed or result.tests_run!=count or result.failures or result.errors or result.skipped
   or result.expected_failures or result.unexpected_successes):raise ValueError('Actual regression log does not match complete passing inventory')
  bound[path.relative_to(project).as_posix()]=regression['log_sha256']
