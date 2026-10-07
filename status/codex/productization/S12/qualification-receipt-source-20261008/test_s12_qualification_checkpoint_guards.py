"""Actual isolated public checkpoint guard regressions; no real metadata changes."""
from contextlib import ExitStack
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
import record_s12_qualification_receipt_source_checkpoint as tool
from s09_owner_worker_native_regression import BASE,REPO,sha

class CheckpointGuards(unittest.TestCase):
 def fixture(self,root):
  repo=root/'repo';base=root/'artifacts';base.mkdir();repo.mkdir()
  for name in tool.SOURCE:
   target=repo/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((REPO/name).read_bytes())
  for name in list(tool.TOOLS)+list(tool.LOGS)+tool.PROOFS:
   (base/name).write_bytes((BASE/name).read_bytes())
  target=repo/'status/codex/productization/S12/qualification-receipt-source-20261008';target.parent.mkdir(parents=True)
  doc=repo/'docs/product/v0_2/QUALIFICATION_RECEIPT_STORAGE_IMPLEMENTATION.md';doc.parent.mkdir(parents=True)
  metadata=repo/'coordination/CODEX';metadata.mkdir(parents=True)
  for name in ['PROGRESS.json','HANDOFF.md']:(metadata/name).write_bytes((REPO/'coordination/CODEX'/name).read_bytes())
  review=dict(critical=0,important=0,reviewer_execution='NONE',
   reviewed_raw_sha256={n:h for n,h in tool.TOOLS.items() if n not in ['s12_qualification_receipt_source_regression.py','s12_qualification_receipt_after_replace_regression.py']},
   historical_driver_review='2_IMPORTANT_REPAIRED_IN_FRESH_BOUND_LAUNCHER;OLDER_OUTCOMES_OBSERVATIONAL_ONLY',
   retainer_raw_sha256=sha(Path(tool.__file__).read_bytes()))
  (base/'S12-qualification-receipt-storage-checkpoint-review.json').write_text(json.dumps(review),encoding='utf-8')
  bound=json.loads((base/tool.PROOFS[-1]).read_bytes())
  return repo,base,target,doc,metadata,bound
 def invoke(self,fixture,extra=None):
  repo,base,target,doc,metadata,bound=fixture
  with ExitStack() as stack:
   for name,value in [('REPO',repo),('BASE',base),('TARGET',target),('MANIFEST',target.parent/'qualification-receipt-source-artifact-hashes-20261008.json'),('DOC',doc)]:stack.enter_context(patch.object(tool,name,value))
   stack.enter_context(patch.object(tool,'GUARD_LOGS',{}))
   stack.enter_context(patch.object(tool,'revision_fact',return_value=bound['source_before']))
   stack.enter_context(patch.object(tool,'_revision',return_value=bound['implementation_hash']))
   stack.enter_context(patch('s12_qualification_receipt_bound_regression.capture_inputs',return_value=bound['input_hashes_before']))
   if extra:stack.enter_context(extra)
   tool.main()
 def test_omitted_retainer_review_is_rejected_before_publication(self):
  with tempfile.TemporaryDirectory(prefix='r7-s12-checkpoint-review-',dir=BASE) as tmp:
   f=self.fixture(Path(tmp));reviewpath=f[1]/'S12-qualification-receipt-storage-checkpoint-review.json'
   review=json.loads(reviewpath.read_bytes());review.pop('retainer_raw_sha256');reviewpath.write_text(json.dumps(review),encoding='utf-8')
   old=(f[4]/'PROGRESS.json').read_bytes()
   with self.assertRaises(AssertionError):self.invoke(f)
   self.assertFalse(f[2].exists());self.assertEqual((f[4]/'PROGRESS.json').read_bytes(),old)
 def test_duplicate_storage_rows_cannot_claim_owner_backup_pass(self):
  with tempfile.TemporaryDirectory(prefix='r7-s12-checkpoint-sequence-',dir=BASE) as tmp:
   f=self.fixture(Path(tmp));proofpath=f[1]/tool.PROOFS[-1];proof=json.loads(proofpath.read_bytes());proof['commands'][1]=dict(proof['commands'][0]);proofpath.write_text(json.dumps(proof),encoding='utf-8')
   old=(f[4]/'PROGRESS.json').read_bytes()
   with self.assertRaises(AssertionError):self.invoke(f)
   self.assertFalse(f[2].exists());self.assertEqual((f[4]/'PROGRESS.json').read_bytes(),old)
 def test_corrupted_published_snapshot_leaves_both_metadata_files_unchanged(self):
  with tempfile.TemporaryDirectory(prefix='r7-s12-checkpoint-bytes-',dir=BASE) as tmp:
   f=self.fixture(Path(tmp));old={n:(f[4]/n).read_bytes() for n in ['PROGRESS.json','HANDOFF.md']};original=tool.publish
   def substituted(path,raw):
    original(path,raw)
    if path.name=='source-checkpoint.json':path.write_bytes(b'corrupted public checkpoint\n')
   with self.assertRaises(AssertionError):self.invoke(f,patch.object(tool,'publish',side_effect=substituted))
   for n,raw in old.items():self.assertEqual((f[4]/n).read_bytes(),raw,'Metadata changed before retained snapshots were verified')

if __name__=='__main__':unittest.main(verbosity=2)
