# E7 Status

- task_id: `E7-20260822-005`
- agent: `E7`
- state: `DONE / BLOCKED_WAITING_E6_CORRECTION`
- branch: `agent/e7-e6-lifecycle-rereview-20260822`
- review_target: `PR #16 platform: integrate early Slice 2 registry and evidence persistence`
- reviewed_e6_revision: `aab1639d6db1f94e915d1c4af3041be28e9a4b94`
- observed_pr_head: `42c5d56996e0c4ff0e96edfc591726d9f9f34963`
- implementation_pin_to_pr_head_delta: `coordination/E6/STATUS.md + status/E6_EARLY_SLICE2_HANDOFF.md + status/E6_STATUS.md only`
- review_time_main: `6de6c45cd3db3e1c449725c8a7721c133f3296fc`
- review_artifact: `status/e7/E6_LIFECYCLE_TARGETED_REREVIEW_20260822.md`
- summary: `The E6 correction successfully adds the exact early-Slice-2 edge allowlist to SQLiteRegistryStore and an independent forbidden-edge SQL trigger, preserving concurrency/rollback and prior evidence validators. However E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001 remains BLOCKING because direct callers of the exported SQLiteRegistryStore can legally chain DRAFT -> BACKTESTING -> CANDIDATE without the E2 compatibility and E3 ValidationDecision/BacktestResult evidence gates enforced by StrategyPlatformService. Edge shape is now constrained, but promotion/evidence authority is still bypassable at the authoritative persistence surface.`

## Finding dispositions

- `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`: `BLOCKING / NOT CLOSED / E6 OWNER`
- `E6-EVIDENCE-CONTRACT-001`: `CLOSED / PASS STATIC / NO REGRESSION`

## Targeted lifecycle dispositions

- early_lifecycle_vocabulary: `PASS / DRAFT|BACKTESTING|REJECTED|CANDIDATE ONLY`
- early_lifecycle_edge_allowlist: `PASS / EXACT THREE EDGE PAIRS`
- direct_store_forbidden_pair_rejection: `PASS / STATIC ONLY`
- forbidden_pair_no_row_state_revision_mutation: `PASS / STATIC TEST DEFINITIONS`
- sqlite_forbidden_edge_insert_trigger: `PASS / STATIC ONLY`
- lifecycle_history_append_only: `PASS / STATIC ONLY`
- concurrency_state_revision_checks: `PASS / STATIC ONLY`
- atomic_history_projection_update: `PASS / STATIC ONLY`
- rollback_behavior: `PASS / STATIC ONLY`
- direct_store_evidence_authority: `FAIL / BLOCKING`
- direct_store_draft_to_backtesting_without_e2_evidence: `POSSIBLE / BLOCKING`
- direct_store_backtesting_to_candidate_without_e3_evidence: `POSSIBLE / BLOCKING`
- service_edge_allowlist_duplication: `NON_BLOCKING_HARDENING / CURRENTLY MATCHES CENTRAL SET`

## Remaining blocking source condition

The correction defines:

```text
EARLY_LIFECYCLE_TRANSITIONS = {
  DRAFT -> BACKTESTING,
  BACKTESTING -> REJECTED,
  BACKTESTING -> CANDIDATE,
}
```

and `SQLiteRegistryStore.append_transition(...)` rejects every other pair before mutation.

That closes direct service-forbidden edge attempts such as one-step `DRAFT -> CANDIDATE`.

It does **not** close service evidence-authority bypass.

Public/reachable surfaces still include:

```text
registry.LifecycleTransitionRecord
storage.SQLiteRegistryStore
RegistryStore.append_transition(...)
SQLiteRegistryStore.append_transition(...)
```

The store validates only edge shape plus current state/revision/resulting revision. It does not require the evidence that `StrategyPlatformService` requires for those legal edges.

Therefore a direct store caller can perform:

```text
DRAFT -> BACKTESTING
BACKTESTING -> CANDIDATE
```

without:

- verified E2 compatibility `PASS / LOCAL_EXECUTION` metadata for DRAFT -> BACKTESTING;
- stored/bound E3 ValidationDecision `decision=PASS`;
- bound parent BacktestResult;
- `PASS / LOCAL_EXECUTION` source revision/environment/command/result reference on ValidationDecision and BacktestResult.

The deterministic legal-edge test definitions themselves construct direct `LifecycleTransitionRecord` objects with no service evidence authority and advance the store through the legal edge pairs.

Thus the authoritative lifecycle projection and registry revision can still reach `CANDIDATE` without the service promotion gates.

The SQL edge trigger does not prevent this because both chained edge pairs are legal shapes.

Required E6 correction outcome:

- direct persistence callers must not advance `DRAFT -> BACKTESTING` without the accepted E2 compatibility authority;
- direct persistence callers must not advance `BACKTESTING -> CANDIDATE` without the accepted bound E3 ValidationDecision + BacktestResult authority;
- service-authorized legal transitions must remain possible;
- forbidden pairs must remain rejected;
- any failed evidence authorization must leave transition rows, lifecycle state, and registry revision unchanged.

Do not expand lifecycle states while correcting this issue.

## Corrected edge / migration acceptance

Accepted statically at `aab1639d...`:

- `src/registry/models.py` defines only the three early edge pairs;
- `SQLiteRegistryStore.append_transition(...)` uses the shared Python edge predicate before transaction/mutation;
- authoritative current-state equality is still checked;
- expected registry revision is still checked;
- resulting revision must still equal current + 1;
- history insert and projection update remain inside the same transaction;
- projection update still requires matching state/revision and exactly one row;
- exception path still rolls back;
- SQL `BEFORE INSERT` trigger rejects every edge pair outside the same three-pair set;
- SQL UPDATE/DELETE triggers keep lifecycle history append-only.

PR #16 remains pre-merge and project migrations remain `NOT_RUN`; the edited `0001` is treated as the pre-merge baseline migration, not evidence of an executed upgrade.

## Test-definition review

Static definitions now cover:

- all three allowed direct-store edges;
- `DRAFT -> CANDIDATE` rejection;
- `DRAFT -> REJECTED` rejection;
- forbidden transitions out of CANDIDATE;
- forbidden transitions out of REJECTED;
- self-transition rejection;
- no transition-row/state/revision mutation after forbidden pair rejection;
- forbidden direct-SQL lifecycle INSERT rejection;
- migration idempotency;
- immutable strategy content;
- append-only lifecycle history;
- restart persistence.

Missing for full finding closure:

- direct-store `DRAFT -> BACKTESTING` must fail when verified E2 compatibility authority is absent;
- direct-store `BACKTESTING -> CANDIDATE` must fail when bound E3 ValidationDecision/BacktestResult local evidence is absent;
- service-authorized transition tests must prove the corrected persistence authorization cannot be caller-forged.

No test or migration was executed in GitHub.

## `E6-EVIDENCE-CONTRACT-001` regression disposition

Critical accepted blobs remain unchanged:

```text
src/registry/contract_validation.py
  954d21c021c0885554ee650acced17610d958a0e

src/registry/service.py
  3184452956e1540be44d5ea779be87ed573fbcae

src/registry/service_base.py
  3889ac156358f58c5fc3380865ad73844b874c3c
```

Preserved:

- complete canonical BacktestResult validation before persistence;
- complete canonical ValidationDecision validation before persistence;
- exact strategy/content/BacktestResult parent binding;
- exact decision enum and reason-code structure;
- invalid/unknown required type/state fails closed;
- caller `PASS / LOCAL_EXECUTION` metadata cannot bypass payload validators;
- BacktestResult alone cannot authorize CANDIDATE through the service;
- service `mark_candidate()` still requires bound E3 ValidationDecision + parent BacktestResult with local-execution evidence metadata.

Synthetic PASS fixtures remain test-only and are not project executable evidence.

## Scope / lifecycle / execution separation

- lifecycle states beyond CANDIDATE: `ABSENT`
- generic later lifecycle transition authority: `ABSENT`
- ApprovedTradePlan persistence: `ABSENT`
- OrderRequest persistence: `ABSENT`
- OrderResult persistence: `ABSENT`
- Fill persistence: `ABSENT`
- Position execution-audit persistence: `ABSENT`
- OKX provider-native `sz` persistence: `ABSENT`
- execution reconciliation persistence: `ABSENT`
- Demo execution facts: `ABSENT`
- provider quantity reinterpreted as canonical BTC: `NO`
- shared-contract changes: `NONE`
- E1/E2/E3/E4/E5 production edits: `NONE`
- workflow/CI additions: `NONE`
- real credentials/secrets: `NONE FOUND`

## Repository / synchronization state

E6 synchronization merge:

```text
c3d756b46af547b4ea0bb36aa653cc8b9081163f
```

Parents:

```text
df15109dcb8594b1182bf6fc09cb5ad6681d74b5
06752b83c18f6579b06c1f3b7e1d5837a2d6949a
```

Non-destructive two-parent merge; no force rewrite/destructive rebase evidence found.

Current review state:

```text
PR #16 mergeable = TRUE
E6 branch vs latest main = ahead 46 / behind 2
latest-main-only delta = coordination/E6/TASK.md + coordination/E7/TASK.md
meaningful production/shared-contract drift = NONE
```

Coordination-only drift is not a resynchronization blocker.

Correction pin -> observed PR head changes only:

```text
coordination/E6/STATUS.md
status/E6_EARLY_SLICE2_HANDOFF.md
status/E6_STATUS.md
```

No material code/test change exists after the reviewed correction pin.

## Merge / verification / release state

- pr_16_source_disposition: `FAIL / BLOCKED`
- pr_16_merge_recommendation: `DO NOT MERGE`
- executable_verification: `NOT_RUN`
- project_tests_executed: `NO`
- migrations_executed: `NO`
- provider_requests: `NOT_SENT`
- github_compute: `NOT_USED`
- codex_ticket: `NONE / NOT_APPLICABLE WITHOUT LOCAL REPRODUCTION`
- gate_a: `BLOCKED / UNCHANGED`
- gate_b: `BLOCKED / UNCHANGED`
- gate_c: `BLOCKED / UNCHANGED`
- gate_d: `BLOCKED / UNCHANGED`

## Completion / next owner

E7 completed only `E7-20260822-005` and stops here.

Next owner: `E6` for a bounded correction of the remaining direct-store evidence-authority bypass under the existing early Slice 2 lifecycle scope.

E7 does not merge PR #16, does not modify E6 production code, does not run project tests/migrations, and does not start another task automatically.
