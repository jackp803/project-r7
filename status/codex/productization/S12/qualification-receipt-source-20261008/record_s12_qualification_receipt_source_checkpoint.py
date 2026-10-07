"""Persist only fixed public S12 storage checkpoint inputs; no database traversal."""
from pathlib import Path
import json,subprocess,sys
from s09_owner_worker_native_regression import OwnedProof,BASE,REPO,sha
from application.datasets.catalog import read_local
from application.qualification import _sanitize,parse_result,revision_fact
from strategy.v02.capabilities import _revision

SOURCE={
 'src/storage/qualification.py':'sha256:5a5784b35476662b00cf4dd1d98e8944516a9c1e0e85ac6eb8876c33c7d823a4',
 'src/storage/migrations/0018_product_qualification_receipts.sql':'sha256:6fda2f33ec790193651e1dd4b6a24ce9e872c4bae60794f3ca9552e7815f7c6d',
 'tests/storage/test_qualification_receipts.py':'sha256:a4fd09b68b71707c01b3ae572b4d3961391a7b52ce1ab5b4e7ba355152df4837'}
TOOLS={
 's12_qualification_receipt_source_regression.py':'sha256:7fc88ac8dd4724e2ec4b6f784fd1c3596c4d2bdf794e11d3dcaf58a26f3a0b63',
 's12_qualification_receipt_after_replace_regression.py':'sha256:adc0a44b68ccac66c9db94caad0fde09566d6faf3681873bb3017bd50d7dec43',
 's12_qualification_receipt_bound_regression.py':'sha256:752d2323a586d812c48de61605d4ae58263b0dfbe13bf021b3c74fd0b27790a1',
 'test_s12_qualification_regression_binding.py':'sha256:ac8c68b41f191aa039df7b04a43c09b5a8977eb21b58ca2e4c16683d7f20b26c',
 'S12-qualification-receipt-storage-implementation-draft.md':'sha256:fe880342f3aaed6d7dd4202953caadeb473786bd5d1bd467042e77dba1d77251',
 'test_s12_qualification_checkpoint_guards.py':'sha256:75b160cfa973b3ae2c7f815da3fa7bda91100b819429aa63d50a24c00516fd7e'}
LOGS={
 'S12-qualification-receipts-RED-20261008.log':(14,14,0,1),
 'S12-qualification-receipts-INITIAL-20261008.log':(14,0,8,1),
 'S12-qualification-receipts-GREEN-20261008.log':(15,0,0,0),
 'S12-qualification-receipts-replace-RED-20261008.log':(2,2,0,1),
 'S12-qualification-receipts-replace-GREEN-20261008.log':(17,0,0,0),
 'S12-qualification-receipts-storage-all-20261008.log':(194,0,0,0),
 'S12-qualification-receipts-owner-backup-20261008.log':(90,0,0,0),
 'S12-qualification-receipts-storage-all-20261008-after-replace.log':(196,0,0,0),
 'S12-qualification-receipts-owner-backup-20261008-after-replace.log':(90,0,0,0),
 'S12-qualification-receipts-storage-all-20261008-bound.log':(196,0,0,0),
 'S12-qualification-receipts-owner-backup-20261008-bound.log':(90,0,0,0),
 'S12-qualification-regression-binding-RED.log':(2,2,0,1),
 'S12-qualification-regression-binding-GREEN.log':(2,0,0,0)}
GUARD_LOGS={'S12-qualification-checkpoint-guards-RED.log':(3,3,0,1),
 'S12-qualification-checkpoint-guards-GREEN.log':(3,0,0,0)}
PROOFS=['S12-qualification-receipts-source-regression-20261008.json',
 'S12-qualification-receipts-source-regression-20261008-after-replace.json',
 'S12-qualification-receipts-source-regression-20261008-bound.json']
TARGET=REPO/'status/codex/productization/S12/qualification-receipt-source-20261008'
MANIFEST=REPO/'status/codex/productization/S12/qualification-receipt-source-artifact-hashes-20261008.json'
DOC=REPO/'docs/product/v0_2/QUALIFICATION_RECEIPT_STORAGE_IMPLEMENTATION.md'

def rawjson(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def capture(path):return read_local(path.parent,path.name,8*1024**2)
def publish(path,raw):
 with OwnedProof(path) as p:
  p.stream.write(raw);p.stream.flush();p.require_owned();p.stream.seek(0)
  assert p.stream.read(8*1024**2+1)==raw

def main():
 assert revision_fact(REPO)=={'revision':'fb3c1c67abf60d7fc46d39e589b1538f45f13967','worktree':'DIRTY'}
 selfraw=capture(Path(__file__))
 source={n:capture(REPO/n) for n in SOURCE}
 assert {n:sha(v) for n,v in source.items()}==SOURCE
 tools={n:capture(BASE/n) for n in TOOLS}
 assert {n:sha(v) for n,v in tools.items()}==TOOLS
 reviewraw=capture(BASE/'S12-qualification-receipt-storage-checkpoint-review.json')
 review=json.loads(reviewraw)
 assert review['critical']==review['important']==0 and review['reviewer_execution']=='NONE'
 assert review.get('retainer_raw_sha256')==sha(selfraw)
 assert review['reviewed_raw_sha256']=={n:h for n,h in TOOLS.items() if n not in ['s12_qualification_receipt_source_regression.py','s12_qualification_receipt_after_replace_regression.py']}
 assert review['historical_driver_review']=='2_IMPORTANT_REPAIRED_IN_FRESH_BOUND_LAUNCHER;OLDER_OUTCOMES_OBSERVATIONAL_ONLY'
 captured={**tools,'checkpoint-review.json':reviewraw};observed=[];logsraw={}
 for name,expected in {**LOGS,**GUARD_LOGS}.items():
  raw=capture(BASE/name);logsraw[name]=raw
  result=parse_result(raw.decode('utf-8').replace('\r\n','\n'),returncode=expected[3])
  assert (result.tests_run,result.failures,result.errors,result.returncode)==expected
  assert result.skipped==result.expected_failures==result.unexpected_successes==0
  retained=_sanitize(raw.decode('utf-8'),REPO).replace('\r\n','\n').encode('utf-8')
  captured[name]=retained
  observed.append(dict(name=name,tests_run=result.tests_run,failures=result.failures,errors=result.errors,
   skipped=0,returncode=result.returncode,passed=result.passed,raw_sha256=sha(raw),retained_sha256=sha(retained),
   scope='OBSERVED_DIRTY_PRE_CANDIDATE;NO_EXACT_CLEAN_OR_NATIVE_QUALIFICATION_CREDIT'))
 for name in PROOFS:
  raw=capture(BASE/name);proof=json.loads(raw)
  assert proof['passed'] is True and proof['input_hashes_before']==proof['input_hashes_after']
  assert proof['source_before']==proof['source_after']==revision_fact(REPO)
  suffix=name.removeprefix('S12-qualification-receipts-source-regression-').removesuffix('.json')
  sequence=[(label,f'S12-qualification-receipts-{label}-{suffix}.log') for label in ['storage-all','owner-backup']]
  assert [(c['label'],c['log']) for c in proof['commands']]==sequence
  for item in proof['commands']:
   assert item['passed'] is True and item['returncode']==0 and item['tree_reaped'] is True
   assert item['log_sha256']==sha(logsraw[item['log']])
   assert (item['tests_run'],item['failures'],item['errors'],item['returncode'])==LOGS[item['log']]
  if name.endswith('-bound.json'):
   from s12_qualification_receipt_bound_regression import capture_inputs
   assert proof['input_hashes_before']==capture_inputs()
   assert proof['implementation_hash']==_revision()
   for n,h in SOURCE.items():assert proof['input_hashes_before']['repo/'+n]==h
   assert proof['input_hashes_before']['launcher/s12_qualification_receipt_bound_regression.py']==TOOLS['s12_qualification_receipt_bound_regression.py']
  captured[name]=_sanitize(raw.decode('utf-8'),REPO).replace('\r\n','\n').encode('utf-8')
 source_review=dict(critical=0,important=0,reviewer='/root/qualification_review',reviewer_execution='NONE',
  reviewed_raw_sha256=SOURCE,scope='THREE_BOUNDED_SOURCE_TEST_FILES;STORAGE_ONLY')
 captured['source-review.json']=rawjson(source_review)
 report=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',spec_baseline='r7-product-v0.2',
  source_before=revision_fact(REPO),implementation_hash=_revision(),source_review=source_review,observed=observed,
  new_cases=17,fresh_affected_regression=dict(tests_run=286,storage=196,owner_backup=90,failures=0,errors=0,skipped=0,owned_trees_reaped=True),
  initial_regression='284_PASS_BEFORE_REPLACE_REPAIR;HISTORICAL_ONLY',
  prior_after_replace_regression='286_OBSERVED_PASS;INCOMPLETE_INPUT_AND_CHILD_PACKAGE_BINDING;NO_CURRENT_QUALIFICATION_CREDIT',
  external_binding_guard_tests=2,external_binding_guard_red_failures=2,external_checkpoint_guard_tests=3,external_checkpoint_guard_red_failures=3,
  history_limitations='Intermediate source bytes were not retained. Historical logs record observed outcomes only; final reviewed commitments cover current three files.',
  exact_clean_qualification='PENDING',native='NOT_RUN_FOR_THIS_INCREMENT',owning_producer='NOT_IMPLEMENTED',
  ordinary_native_paper='NOT_RUN',production_profile='PROPOSED_NOT_ACTIVE',scope='INTERNAL_SOFTWARE_CHECK_RECORD_STORAGE_ONLY;NO_RELEASE_ADMISSION_AUTHORITY',
  failed_cleanup='8_EXACT_OWNED_FIXTURE_DIRS_PRESERVED_INSIDE_PROJECT;RECURSIVE_DELETE_AUTO_REVIEW_REJECTED;PRIVATE_DB_NOT_RETAINED',
  real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',ubuntu24='NOT_RUN',ubuntu26='NOT_RUN')
 captured['source-checkpoint.json']=rawjson(report)
 captured[Path(__file__).name]=selfraw
 assert not TARGET.exists() and not MANIFEST.exists() and not DOC.exists()
 TARGET.mkdir()
 for name,raw in captured.items():publish(TARGET/name,raw)
 publish(DOC,tools['S12-qualification-receipt-storage-implementation-draft.md'])
 manifest=dict(schema_version='r7-scoped-artifact-retention-v0.2',root=TARGET.relative_to(REPO).as_posix(),
  scope=report['scope'],files=[dict(name=name,sha256=sha(raw),bytes=len(raw)) for name,raw in sorted(captured.items())],
  implementation_doc=dict(path=DOC.relative_to(REPO).as_posix(),sha256=TOOLS['S12-qualification-receipt-storage-implementation-draft.md']))
 manifest_raw=rawjson(manifest)
 publish(MANIFEST,manifest_raw)
 for name,raw in captured.items():assert capture(TARGET/name)==raw
 assert capture(MANIFEST)==manifest_raw
 assert capture(DOC)==tools['S12-qualification-receipt-storage-implementation-draft.md']
 assert {n:sha(capture(REPO/n)) for n in SOURCE}==SOURCE
 ppath=REPO/'coordination/CODEX/PROGRESS.json';progress=json.loads(capture(ppath))
 assert progress['qualified_executable_revision']=='41fa2fe0d74435fed5831ed728af8b87c28883f0'
 progress.update(active_step='S12/S09/S13',next_step='Qualify the exact-clean qualification receipt storage candidate; then continue bounded owning fixed-check producer/current-release adapter and native PAPER fixture composition. Production profile PROPOSED_NOT_ACTIVE pending PM/E6 mapping acceptance; Ubuntu/full master/S15/S16 remain open.')
 progress['qualification_receipt_storage']=dict(status='SOURCE_STORAGE_COMPONENT_PASS;EXACT_CLEAN_QUALIFICATION_PENDING',
  implementation_hash=report['implementation_hash'],new_cases=17,regression_cases=286,storage=196,owner_backup=90,external_binding_guard_tests=2,
  failures=0,errors=0,skipped=0,independent_review='0_CRITICAL_0_IMPORTANT;BOUNDED_SOURCE_AND_EXTERNAL_CAPTURE;REVIEWER_EXECUTION_NONE',
  evidence_ref=TARGET.relative_to(REPO).as_posix()+'/source-checkpoint.json',manifest_ref=MANIFEST.relative_to(REPO).as_posix(),
  production_profile='PROPOSED_NOT_ACTIVE',owning_producer='NOT_IMPLEMENTED',ordinary_native_paper='NOT_RUN')
 ppath.write_bytes(rawjson(progress))
 handoff=REPO/'coordination/CODEX/HANDOFF.md';prior=capture(handoff)
 prefix=('S12 internal qualification receipt storage checkpoint:17 actual isolated canonical-store focused cases PASS; fresh affected storage196/owner-backup90=286PASS,0 failure/error/skip,owned trees reaped. Public facade is existing-store read-only; internal capability writer applies additive migration0018 to the same canonical E6 DB. Exact namespace/schema, strict bounded JSON/hash binding, restart replay/conflict, concurrent migration/append, actual SQL read-only and UPDATE/DELETE/INSERT OR REPLACE guards verified. Initial14missing-moduleFAIL,14with8Windows SQLite test-cleanupERROR,15PASS and reproduced2replaceFAIL histories retained. Independent bounded current source/capture/docs review0C/I,reviewerexecutionNONE. Two earlier external launcher binding findings reproduced2FAIL then2PASS;fresh full-input/package-pinned launcher reran286PASS,earlier regression proofs observational only. Source-check outcomes supply no release admission authority; owning fixed-check producer/adapter/native PAPER still pending. New exact-clean full source/native qualificationPENDING; accepted41fa remains historical,noPASS transfer. Production profilePROPOSED_NOT_ACTIVE; continue same master/branch,S12/S09/S13/S14/S15open,S16pending. Eight owned failed-cleanup fixture dirs safely preserved inside project after recursive-delete auto-review rejection; no private DB bytes retained in Git. Ubuntu/realcloud/data/forward/provider/capital/hostedcompute/mainmerge remain unexecuted.\n\n')
 handoff.write_bytes(prefix.encode()+prior)
 print(json.dumps(dict(retained_files=len(captured),focused=17,affected=286,qualification='PENDING',implementation_hash=report['implementation_hash'])))

if __name__=='__main__':main()
