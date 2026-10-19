"""Archive explicit public checkpoint helpers/designs/reviews, never private stores."""
import hashlib,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1];ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.paper.qualification import artifact_bytes
from application.qualification import _sanitize
names='''run_current_checkpoint.py
run_owning_with_memory.py
verify_portable_checkpoint.py
verify_unattended_checkpoint.py
verify_qualified_backup_checkpoint.py
index_current_qualification.py
bind_current_acceptance_records.py
write_current_launch_guide.py
retain_current_checkpoint.py
test_current_acceptance_bindings.py
test_current_index_helper.py
test_current_launch_guide.py
test_explicit_qualification_attempt.py
test_qualified_backup_checkpoint_helper.py
test_retain_current_checkpoint.py
test_portable_checkpoint_helper.py
acceptance-v02-draft.json
legacy-150-draft.json
acceptance-disposition-advisory.json
acceptance-cloud-trade-expanded-map.json
acceptance-research-expanded-map.json
acceptance-str-expanded-map.json
final-acceptance-record-plan.json
strategy-coverage-completion-design.json
research-coverage-completion-design.json
legacy-local-gap-design.json
k05-authority-and-local-plan.json
adapter-runtime-boundary-review.json
current-acceptance-bindings-final-review.json
current-acceptance-bindings-source-regressions.log
current-index-helper-refactor-regressions.log
current-index-helper-refactor-review.json
current-index-helper-review.json
current-index-helper-source-regressions.log
current-launch-guide-final-review.json
current-launch-guide-source-regressions.log
explicit-qualification-attempt-review.json
explicit-qualification-attempt-source-regressions.log
qualified-backup-helper-final-review.json
qualified-backup-helper-source-regressions.log
retain-current-checkpoint-final2-review.json
retain-current-checkpoint-source-regressions.log
unattended-helper-final-review.json
portable-helper-final-review.json
owning-memory-observer-review.json
owning-memory-observer-final-review.json
owning-memory-observer-final2-review.json
windows-abi-no-skip-review.json
ctypes-no-skip-inventory.log
build-dffb0a3-first/checkpoint.json
build-dffb0a3-first/native-build-execution.json
build-dffb0a3-first/native-build.log
retain_checkpoint_preparation.py'''.splitlines()
captured=[(name,artifact_bytes(BASE,name)) for name in names]
target=ROOT/'status/codex/productization/S12/checkpoint-preparation-20261019';target.mkdir();(target/'artifacts').mkdir();bindings=[]
for number,(name,raw) in enumerate(captured,1):
    ref=f'artifacts/a{number:04d}'+Path(name).suffix
    safe=_sanitize(raw.decode('utf-8-sig'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').replace('\r','').encode()
    (target/ref).write_bytes(safe)
    bindings.append(dict(original_ref=name,original_hash='sha256:'+hashlib.sha256(raw).hexdigest(),retained_ref=ref,retained_hash='sha256:'+hashlib.sha256(safe).hexdigest()))
value=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',kind='BOUNDED_PREPARATION_AND_STATIC_REVIEW;NOT_QUALIFICATION',
    prior_executable='dffb0a3c8284f34f6bf6c09b51bd6ce96aed155a',prior_native_build='PASS',prior_full_owning='NOT_STARTED',
    next_candidate_reason='NO_SKIPPED_SOURCE_INVENTORY;SAME_PRODUCTION_ABI_REPAIR',
    source_delta_tests=dict(tests=15,failures=0,errors=0,skipped=0),
    design_execution='NONE',mapping_semantic_pass='NOT_INFERRED',provider_requests_additional=0,
    provider_requests_cumulative=8,private_requests=0,credentials='NONE',capital='NONE',master='IN_PROGRESS',artifacts=bindings)
(target/'disposition.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(retained_files=len(bindings))))
