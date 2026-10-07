"""Integrate the independently reviewed bounded supervisor bytes only."""
import hashlib,json
from pathlib import Path

base=Path(__file__).resolve().parent
repo=base.parent/'workspaces/project-r7-productization-master-20261002'
development=base/'S12-runtime-supervision-development'
expected={
    'platform/supervision.py':'ab9edc20fc7307e11b7ded01573a83da153947c24924b688955255dff7a137ac',
    'migrations/0008_runtime_process_supervision.sql':'377a455959843dc8add08927d01c8537ac77708611aec582b4b6d0b8dc1a41c2',
    'test_runtime_process_supervision.py':'215d0b2df36374f733dad5c4e1807ec1c0763c18c4d2ac5f8bfdff97238df7a7',
}
destinations={
    'platform/supervision.py':'src/application/platform/supervision.py',
    'migrations/0008_runtime_process_supervision.sql':'src/application/migrations/0008_runtime_process_supervision.sql',
    'test_runtime_process_supervision.py':'tests/application/test_runtime_process_supervision.py',
}
supplemental={
    'run_s12_runtime_supervision_development.py':'b2d71a5e245c50ebae34c742ac26a2d702385eb897608daa4bf2a865dd6cbb04',
    's12_runtime_supervision_harness_integrity.py':'8e99793100c0b5b14ad112040020589fc31adb1e9d681c62194da8e2fc203116',
    'test_s12_runtime_supervision_harness_integrity.py':'6ad816a72b36b7814578644d1d38efceea9c1c3d0740fbfc49a08ba2092c0b86',
    'S12-runtime-supervision-increment-plan.md':'000128e42f017615df53ee66de87b4b1632cf054d5bf3d3a09bca874e10b6796',
    'S12-qualified-paper-release-profile-proposal.md':'5af8ff6bc569140e047277f9f43eb2b17b18900d36a5e7f9892ca5f9b18b56e3',
}
for name,sha in expected.items():
    assert hashlib.sha256((development/name).read_bytes()).hexdigest()==sha
for name,sha in supplemental.items():
    assert hashlib.sha256((base/name).read_bytes()).hexdigest()==sha
legacy=repo/'src/application/migrations/0006_process_supervision.sql'
assert hashlib.sha256(legacy.read_bytes()).hexdigest()=='5c0dcbda40205770e9f110125058cde44590567779eebabf881fdd3eb42beb8e'
for label,count in (('S12-runtime-supervision-reviewed-GREEN',18),
    ('S12-runtime-supervision-reviewed-regression-GREEN',34),('S12-runtime-supervision-harness-GREEN',4)):
    proof=json.loads((base/(label+'.json')).read_bytes())
    assert proof['passed'] and proof['tests_run']==count and proof['failures']==proof['errors']==proof['skipped']==0
    assert proof['inputs_unchanged'] and proof['tree_reaped'] and proof['harness_binding']=='BEFORE_AND_AFTER_EXECUTION'
    assert proof['execution_input_sha256_before']==proof['execution_input_sha256_after']
    assert 'sha256:'+hashlib.sha256((base/(label+'.log')).read_bytes()).hexdigest()==proof['log_sha256']
review=dict(reviewer='/root/qualification_review',kind='INDEPENDENT_BOUNDED_READ_ONLY_SUPERVISOR_MIGRATION_AND_HARNESS_REVIEW',
    remaining_critical=0,remaining_important=0,reviewer_execution='NONE',
    reviewed_files={**{'development/'+name:'sha256:'+sha for name,sha in expected.items()},
        **{name:'sha256:'+sha for name,sha in supplemental.items()},
        'src/application/migrations/0006_process_supervision.sql':'sha256:'+hashlib.sha256(legacy.read_bytes()).hexdigest()},
    resolved_important=['Reject unknown unnamed UNIQUE constraints and altered receipt-backed shapes using exact owned SQLite schemas including automatic indexes',
        'Bind the exact development and harness inventory before/after execution and deny PASS on changed input/source or unreaped trees'],
    actual_tests='SEPARATE_CODEX_LOCAL_RUNS:18_SUPERVISOR_MIGRATION+34_EXISTING_REGRESSION+4_HARNESS',
    subprocess_scope='PREINTEGRATION_CHILDREN_USE_COMMITTED_SOURCE;INTEGRATED_CHILD_VERIFICATION_PENDING',
    profile_proposal_review='0_CRITICAL_OR_IMPORTANT_WORDING_FINDINGS;PROPOSED_NOT_ACTIVE',
    native='NOT_RUN_FOR_NEW_ROLES',ubuntu='NOT_RUN',whole_branch='NOT_REVIEWED')
review_path=base/'S12-runtime-supervision-independent-review.json'
assert not review_path.exists()
review_path.write_text(json.dumps(review,indent=2)+'\n',encoding='utf-8',newline='\n')
for name,target in destinations.items():
    path=repo/target
    if name!='platform/supervision.py':assert not path.exists()
    path.write_bytes((development/name).read_bytes())
doc=repo/'docs/product/v0_2/RUNTIME_PROCESS_SUPERVISION_IMPLEMENTATION.md'
assert not doc.exists()
doc.write_text('''# Runtime and cloud process supervision

The existing local ProcessSupervisor now supports control, research, runtime and cloud roles. Each actual owner holds its existing host lifetime lock and records an independent generation, UUID, configuration digest, process identity and heartbeat in process-supervision.sqlite. Configuration drift, stolen generations, stale/future heartbeats and restart reconciliation remain inhibited. No additional database is introduced.

Migration 0006 remains unchanged. Additive migration 0008 atomically rebuilds only the two role-constrained tables, preserving legacy rows and all history. The initializer validates exact table declarations and all automatic/explicit indexes and triggers against the owned old/new schemas, rejecting unknown constraints before a destructive table rebuild. A receipt commits to the UTF-8/LF migration semantics; matching receipts still require the recognized target schema. Every operation uses a bounded SQLite transaction; no network or worker computation holds it.

Eighteen source regressions cover new-role ownership and heartbeat, configuration and generation fences, unknown-role denial, read-only unstarted health, exact legacy preservation/idempotence, complete rollback, changed migration receipts, unknown columns/indexes/triggers/unnamed UNIQUE constraints, altered target constraints, nested transactions, LF/CRLF packaging and an active legacy control owner surviving the additive migration. The active legacy test explicitly controls only initialization with the unchanged legacy script and observes the real lifetime lock and heartbeat.

Development verification passed18 new tests,34 existing supervisor/control/backup regressions and4 external execution-input integrity tests. Reported results are Codex local executions; independent review was read-only and found0 remaining Critical/Important after two findings were repaired. Integrated subprocess verification, exact-clean full source and native qualification are still pending at this source checkpoint.

A supervisor generation is not an E6 PAPER run lease, qualified software release, human financial consent, provider capability or restoration clearance. Supporting runtime/cloud role names does not start normal workers or change UI runtime readiness. Normal worker composition, qualified-release issuer/store/current-owner adapter and restoration integration remain separate S12 work. The proposed production qualification profile is not active until PM/E6 acceptance. Native Ubuntu and real cloud/data/forward/provider commissioning remain NOT_RUN.
''',encoding='utf-8',newline='\n')
print(json.dumps(dict(integrated_files=4,source_tests=18,existing_regression=34,harness_tests=4,
    state='SOURCE_ONLY;EXACT_CLEAN_QUALIFICATION_PENDING',financial_authority='NONE')))
