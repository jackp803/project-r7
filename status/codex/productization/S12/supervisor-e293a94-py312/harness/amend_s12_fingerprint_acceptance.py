"""Keep the fresh scoped collector and its reproducible generator aligned."""
from pathlib import Path

def amend(code):
    assert "full['tests_run']==1940" in code
    code=code.replace('1940','1942').replace('1693','1695')
    code=code.replace("'S12-runtime-supervision-integrated-GREEN'","'S12-runtime-supervision-integrated-fingerprint-GREEN'")
    code=code.replace("'S12-runtime-supervision-independent-retention-review.json'",
                      "'S12-runtime-supervision-independent-retention-fingerprint-review.json'")
    code=code.replace('S12-runtime-supervision-retention-review-GREEN-v2','S12-runtime-supervision-retention-fingerprint-GREEN')
    needle="'s12_runtime_supervision_review_integrity.py','test_s12_runtime_supervision_review_integrity.py','run_s12_runtime_supervision_review_integrity.py')"
    assert code.count(needle)==1
    code=code.replace(needle,needle[:-1]+",'amend_s12_fingerprint_acceptance.py')")
    anchor='for reference,expected in integrity[\'verified_artifact_hashes\'].items():'
    assert code.count(anchor)==1
    block="""fingerprint_review=load(base,'S12-runtime-supervision-fingerprint-independent-review.json')
fingerprint_names=('src/strategy/v02/capabilities.py','tests/strategy/test_v02_capabilities.py',
 'docs/product/v0_2/SOURCE_IDENTITY_TRAVERSAL_REMEDIATION.md')
fingerprint_external=('S12-source-fingerprint-remediation-plan.md','benchmark_s12_fresh_fingerprint.py',
 'run_s12_fingerprint_remediation.py','s12_fingerprint_proof.py','test_s12_fingerprint_proof.py','run_s12_fingerprint_proof.py')
fingerprint_files={path.relative_to(project).as_posix():path for path in
 (*[repo/name for name in fingerprint_names],*[base/name for name in fingerprint_external])}
validate_review_inventory(fingerprint_review,kind='INDEPENDENT_BOUNDED_READ_ONLY_FRESH_SOURCE_IDENTITY_AND_DIAGNOSTIC_PROOF_REVIEW',
 files=fingerprint_files,bound=bound,project=project)
fingerprint_inputs={path.relative_to(project).as_posix():path for path in
 (base/'run_s12_fingerprint_remediation.py',base/'s12_fingerprint_proof.py',repo/'src/strategy/v02/capabilities.py',
 repo/'tests/strategy/test_v02_capabilities.py',repo/'tests/strategy/test_source_resource_commitment.py',
 repo/'tests/application/test_native_distribution.py',repo/'tests/product/test_trading_protection_monitor_v02.py')}
for stem,count in (('S12-runtime-supervision-fingerprint-remediation-reviewed-safety',21),
 ('S12-runtime-supervision-fingerprint-remediation-reviewed-product-case',1)):
 proof=validate_primary_proof(base,stem,count,inputs=fingerprint_inputs,
  input_fields=('input_sha256_before','input_sha256_after'),bound=bound,project=project)
 assert proof['test_result_passed'] is True and proof['source_before']==proof['source_after']
 assert proof['implementation_hash_before']==proof['implementation_hash_after']==identity['implementation_hash']
fingerprint_guard_inputs={name:base/name for name in ('run_s12_fingerprint_proof.py','test_s12_fingerprint_proof.py',
 'run_s12_fingerprint_remediation.py','s12_fingerprint_proof.py')}
validate_primary_proof(base,'S12-runtime-supervision-fingerprint-proof-GREEN',2,inputs=fingerprint_guard_inputs,
 input_fields=('input_sha256_before','input_sha256_after'),bound=bound,project=project)
benchmark=load(base,'S12-runtime-supervision-fingerprint-interleaved-benchmark.json')
benchmark_paths=(base/'benchmark_s12_fresh_fingerprint.py',base/'s12_capabilities.before-fingerprint-remediation.py',repo/'src/strategy/v02/capabilities.py')
benchmark_inputs={path.relative_to(project).as_posix():path for path in benchmark_paths}
assert benchmark['harness_binding']=='BEFORE_AND_AFTER_EXECUTION' and benchmark['input_sha256_before']==benchmark['input_sha256_after']
assert set(benchmark['input_sha256_before'])==set(benchmark_inputs) and benchmark['source_before']==benchmark['source_after']
assert len(benchmark['rows'])==80 and benchmark['identities_equal_on_identical_source'] is True and benchmark['cross_call_cache']=='NONE'
for label in ('old','new'):
 assert sum(row['algorithm']==label for row in benchmark['rows'])==40
assert all(row['implementation_hash']==identity['implementation_hash'] and row['seconds']>0 for row in benchmark['rows'])
for ref,path in benchmark_inputs.items():
 expected=benchmark['input_sha256_before'][ref];require_artifact(path.parent,path.name,expected);bound[ref]=expected
failed_root=base/'r7-productization-S12-runtime-supervision-qualified-4ea0f61'
failed=load(failed_root,'qualification.json')
assert failed['passed'] is False and failed['tests_run']==1701 and len(failed['commands'])==32
assert failed['source_before']==failed['source_after']==dict(revision='4ea0f61c62984eaca1cbfae8b745cffb9cdec901',worktree='CLEAN')
assert failed['commands'][-1]['returncode']==124 and failed['commands'][-1]['tree_reaped'] is True
assert all(row['passed'] is True and row['tree_reaped'] is True for row in failed['commands'][:-1])
for row in failed['commands']:
 path=require_artifact(failed_root,row['log'],'sha256:'+row['log_sha256']);bound[path.relative_to(project).as_posix()]='sha256:'+row['log_sha256']
for name in ('qualification-context.json','hardware-observations.json'):load(failed_root,name)
load(base,'S12-runtime-supervision-4ea0f61-serial-pipeline.json')
"""
    code=code.replace(anchor,block+anchor)
    needle="labels={source:'full-source',browser:'browser'"
    assert code.count(needle)==1
    code=code.replace(needle,"labels={failed_root:'failed-source',source:'full-source',browser:'browser'")
    needle="destination=target/relative;assert len(str(destination))<250"
    assert code.count(needle)==1
    code=code.replace(needle,"""destination=target/relative
 if len(str(destination))>=250:
  relative=Path('short-names')/(hashlib.sha256(reference.encode('utf-8')).hexdigest()[:24]+path.suffix)
  destination=target/relative
 assert len(str(destination))<250""")
    needle="*retention_names,'s13_acceptance_integrity.py'"
    assert code.count(needle)==1
    code=code.replace(needle,"""*fingerprint_external,'s12_capabilities.before-fingerprint-remediation.py','s12_test_capabilities.before-fingerprint-remediation.py',
 'run_s12_fingerprint_remediation.before-owned-pass-fix.py','profile_s12_product_timeout.py','record_s12_fingerprint_review.py',
 'record_s12_fingerprint_source_checkpoint.py','s12_runtime_supervision_accept.before-fingerprint-remediation.py',
 'prepare_s12_runtime_supervision_acceptance.before-fingerprint-remediation.py',
 *retention_names,'s13_acceptance_integrity.py'""")
    needle="independent_retention_review=dict(critical=0,important=0),"
    assert code.count(needle)==1
    code=code.replace(needle,"""independent_retention_review=dict(critical=0,important=0),
 independent_fingerprint_review=dict(critical=0,important=0),
 prior_candidate_4ea0f61='FAIL;PRODUCT_900_SECOND_TIMEOUT;1701_COMPLETED_SOURCE_TESTS;BROWSER_NOT_RUN',
 historical_proof_sidecars='HISTORY_ONLY;PASS_USES_FRESH_REVIEWED_BOUND_PROOFS',""")
    return code

if __name__=='__main__':
    import ast
    base=Path(__file__).resolve().parent
    collector=base/'s12_runtime_supervision_accept.py'
    generator=base/'prepare_s12_runtime_supervision_acceptance.py'
    code=amend(collector.read_text(encoding='utf-8'));ast.parse(code)
    generation=generator.read_text(encoding='utf-8')
    needle="collector.write_text(code,encoding='utf-8',newline='\\n')"
    assert generation.count(needle)==1
    generation=generation.replace(needle,"from amend_s12_fingerprint_acceptance import amend\ncode=amend(code)\n"+needle)
    ast.parse(generation)
    collector.write_text(code,encoding='utf-8',newline='\n')
    generator.write_text(generation,encoding='utf-8',newline='\n')
    print('Amended scoped collector:1942/33,247+1695;fresh21/1/2/52 proof and failed4ea history')
