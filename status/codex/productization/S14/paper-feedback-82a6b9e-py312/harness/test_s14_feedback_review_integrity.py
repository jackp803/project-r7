import copy,hashlib,importlib,json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

class ReviewBindingTests(unittest.TestCase):
 def setUp(self):
  self.guard=importlib.import_module('s14_feedback_review_integrity')
  temporary=TemporaryDirectory(dir=Path(__file__).parent);self.addCleanup(temporary.cleanup)
  self.project=Path(temporary.name);self.repo=self.project/'repo';self.base=self.project/'artifacts';self.base.mkdir()
  self.bound={};self.reviews=[]
  for kind,names,root in (('source',self.guard.SOURCE_FILES,self.repo),('harness',self.guard.HARNESS_FILES,self.base),('retention',self.guard.RETENTION_FILES,self.base)):
   self.assertEqual(len(names),dict(source=12,harness=7,retention=6)[kind]);mapping={}
   for name in names:
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'CONTROLLED_OWNER_FILE')
    mapping[name]='sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()
   value=dict(reviewer='qualification_review',critical=0,important=0,execution='NONE',reviewed_files=mapping)
   value['kind' if kind=='source' else 'review_kind']='INDEPENDENT_READ_ONLY_SOURCE_REVIEW'
   self.reviews.append(value)
  self.log=self.base/'S14-feedback-harness-integrity-runner-GREEN.log'
  self.log.write_bytes(b'Ran 6 tests in 0.001s\n\nOK\n')
  result=dict(tests_run=6,failures=0,errors=0,passed=True,tree_reaped=True,
   log_sha256='sha256:'+hashlib.sha256(self.log.read_bytes()).hexdigest(),
   wrapper_sha256=self.reviews[1]['reviewed_files']['s14_feedback_bound_installer.py'])
  self.reviews[1]['regression']=result
  self.sidecar=self.log.with_suffix('.json');self.sidecar.write_text(json.dumps(result),encoding='utf-8')
  retention_log=self.base/'S14-feedback-harness-review-binding-GREEN-v2.log'
  retention_log.write_bytes(b'Ran 5 tests in 0.001s\n\nOK\n')
  retention=dict(result,tests_run=5,log_sha256='sha256:'+hashlib.sha256(retention_log.read_bytes()).hexdigest())
  retention_log.with_suffix('.json').write_text(json.dumps(retention),encoding='utf-8');self.reviews[2]['regression']=retention
 def validate(self,review,kind):
  return self.guard.validate_review(review,kind=kind,repo=self.repo,base=self.base,bound=self.bound,project=self.project)
 def test_complete_exact_reviews_and_bound_regression_are_accepted(self):
  for kind,review in zip(('source','harness','retention'),self.reviews):self.validate(review,kind)
  self.assertIn(self.log.relative_to(self.project).as_posix(),self.bound)
  self.assertIn(self.sidecar.relative_to(self.project).as_posix(),self.bound)
 def test_empty_or_partial_source_and_harness_commitments_are_rejected(self):
  for kind,review in zip(('source','harness','retention'),self.reviews):
   for empty in (True,False):
    value=copy.deepcopy(review)
    if empty:value['reviewed_files']={}
    else:value['reviewed_files'].pop(next(iter(value['reviewed_files'])))
    with self.subTest(kind=kind,empty=empty),self.assertRaises(ValueError):self.validate(value,kind)
 def test_wrong_kind_and_extra_unreviewed_file_are_rejected(self):
  wrong=copy.deepcopy(self.reviews[0]);wrong['kind']='SELF_REVIEW'
  with self.assertRaises(ValueError):self.validate(wrong,'source')
  extra=copy.deepcopy(self.reviews[1]);extra['reviewed_files']['unreviewed.py']='sha256:'+'a'*64
  with self.assertRaises(ValueError):self.validate(extra,'harness')
 def test_replaced_or_missing_regression_log_cannot_be_supplemental_only(self):
  self.log.write_bytes(b'Ran 6 tests in 0.001s\n\nFAILED (failures=1)\n')
  with self.assertRaises(ValueError):self.validate(self.reviews[1],'harness')
  self.log.unlink()
  with self.assertRaises(ValueError):self.validate(self.reviews[1],'harness')
 def test_changed_sidecar_and_hash_consistent_failed_log_are_rejected(self):
  value=copy.deepcopy(self.reviews[1]);different=copy.deepcopy(value['regression']);different['tests_run']=99
  self.sidecar.write_text(json.dumps(different),encoding='utf-8')
  with self.assertRaises(ValueError):self.validate(value,'harness')
  self.log.write_bytes(b'Ran 6 tests in 0.001s\n\nFAILED (failures=1)\n')
  value['regression']['log_sha256']='sha256:'+hashlib.sha256(self.log.read_bytes()).hexdigest()
  self.sidecar.write_text(json.dumps(value['regression']),encoding='utf-8')
  with self.assertRaises(ValueError):self.validate(value,'harness')

if __name__=='__main__':unittest.main(verbosity=2)
