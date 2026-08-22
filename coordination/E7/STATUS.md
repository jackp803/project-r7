# E7 Status

- task_id: `E7-20260822-003`
- agent: `E7`
- state: `DONE / BLOCKED_WAITING_E6_CORRECTION`
- branch: `agent/e7-e6-registry-review-20260822`
- review_target: `PR #16 platform: integrate early Slice 2 registry and evidence persistence`
- reviewed_e6_revision: `207f6f87dd984c9dea5e4360e2f605e2c94b2bcf`
- observed_pr_head: `df15109dcb8594b1182bf6fc09cb5ad6681d74b5`
- implementation_pin_to_pr_head_delta: `coordination/E6/STATUS.md only`
- review_time_main: `82c52a1f1ce8f9bc7edf8cea139cd1b3fd2cf384`
- review_artifact: `status/e7/E6_REGISTRY_STATIC_REVIEW_20260822.md`
- summary: `PR #16 preserves the accepted E6 evidence-contract correction and coherent inbox/evidence/SQLite early Slice 2 scope, but is BLOCKED because the public persistence boundary exposes generic lifecycle transition authority. SQLiteRegistryStore.append_transition validates current state/revision but not the allowed early-Slice-2 edge set, while the migration constrains only state vocabulary. A direct store caller can therefore bypass StrategyPlatformService evidence gates and move authoritative state through service-forbidden edges such as DRAFT -> CANDIDATE.`

## Finding dispositions

- `E6-EVIDENCE-CONTRACT-001`: `CLOSED / PASS STATIC`
- `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`: `BLOCKING / FAIL / E6 OWNER`

## Review dispositions

- evidence_contract_validation: `PASS / STATIC ONLY`
- validation_decision_binding: `PASS / STATIC ONLY`
- candidate_requires_bound_backtest_and_validation_decision: `PASS / STATIC ONLY`
- caller_pass_local_execution_metadata_bypass: `BLOCKED BY CANONICAL VALIDATORS / PASS STATIC`
- default_compatibility_boundary: `FAIL-CLOSED NOT_RUN / PASS STATIC`
- inbox_identity_idempotency_conflict_handling: `PASS / STATIC ONLY`
- immutable_strategy_content: `PASS / STATIC ONLY`
- lifecycle_service_cap: `PASS / DRAFT -> BACKTESTING -> REJECTED|CANDIDATE`
- lifecycle_persistence_edge_cap: `FAIL / BLOCKING`
- lifecycle_append_only_history: `PASS / STATIC ONLY`
- sqlite_implementation_detail: `PASS / NO SHARED-CONTRACT CHANGE`
- slice3_execution_audit_persistence: `ABSENT / PASS STATIC`
- provider_native_quantity_persistence: `ABSENT / PASS STATIC`
- provider_quantity_reinterpreted_as_canonical_btc: `NO / PASS STATIC`
- repository_scope: `PASS / E6 REGISTRY-STORAGE-TEST-DOC-STATUS ONLY`
- repository_synchronization: `PASS / NON-DESTRUCTIVE / CURRENT BEHIND-2 IS COORDINATION-ONLY`
- pr_16_merge_recommendation: `BLOCKED / DO NOT MERGE`

## Accepted evidence-contract baseline preservation

Critical accepted blobs remain unchanged:

```text
src/registry/contract_validation.py
  954d21c021c0885554ee650acced17610d958a0e

src/registry/service_base.py
  3889ac156358f58c5fc3380865ad73844b874c3c

src/registry/service.py
  3184452956e1540be44d5ea779be87ed573fbcae
```

The public `registry.StrategyPlatformService` comes from `registry.service`, whose evidence-ingest wrapper validates canonical BacktestResult / ValidationDecision shape and verification enum metadata before persistence.

BacktestResult validation requires the current contracts-v0.1 identity/reproducibility/core metric set, UTC timestamps, exact schema, integer counts, and decimal-string financial interchange values.

ValidationDecision validation requires exact canonical fields, decision enum, reason-code sequence shape, UTC decision time, exact strategy binding, and exact stored BacktestResult binding.

`mark_candidate()` requires a stored E3 ValidationDecision with `decision=PASS`, valid parent BacktestResult, exact strategy/content binding, and `PASS / LOCAL_EXECUTION` metadata with source revision/environment/command/result reference on both decision and backtest evidence.

A BacktestResult alone cannot authorize CANDIDATE.

Synthetic `PASS` fixtures in tests remain test input only and are not project executable evidence.

## Blocking source condition

### `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`

Owner: `E6`

Service-level transition authority is correct:

```text
DRAFT -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

But persistence does not enforce those edges.

Public/reachable surfaces include:

- `registry.LifecycleTransitionRecord`;
- `storage.SQLiteRegistryStore`;
- `RegistryStore.append_transition(...)`;
- `SQLiteRegistryStore.append_transition(...)`.

`SQLiteRegistryStore.append_transition()` checks current persisted state, expected registry revision, and resulting revision, but contains no allowlist for legal `(previous_state, new_state)` pairs.

`0001_strategy_registry.sql` constrains state values to:

```text
DRAFT
BACKTESTING
REJECTED
CANDIDATE
```

but does not constrain legal edge pairs on INSERT.

Therefore a direct caller can construct a matching-revision `LifecycleTransitionRecord` such as `DRAFT -> CANDIDATE` and bypass the service's E2 compatibility / E3 evidence gates. Other service-forbidden edges among the four states are likewise representable.

Append-only UPDATE/DELETE triggers protect historical rows after insertion but do not prevent insertion of an unauthorized edge.

Required E6 correction: enforce the exact early Slice 2 transition allowlist at the persistence boundary and/or migration trigger level, and add deterministic direct-store tests proving forbidden edges cannot mutate the authoritative lifecycle projection. Do not add later lifecycle states while fixing this issue.

## Inbox / persistence accepted boundaries

Accepted statically:

- same identity + same immutable content is idempotent;
- same identity + conflicting content fails closed;
- immutable strategy content is protected by SQLite trigger;
- secret-like intake fields fail before persistence;
- default unwired E2 compatibility is `NOT_RUN`, not PASS;
- lifecycle history is append-only against UPDATE/DELETE;
- concurrency checks bind current state and registry revision;
- SQLite remains an E6 implementation detail.

## Slice 3 / execution separation

PR #16 does not add persistence for:

- `ApprovedTradePlan`;
- `OrderRequest`;
- `OrderResult`;
- `Fill`;
- OKX provider-native `sz`;
- provider order/fill identity;
- execution reconciliation;
- Demo execution facts;
- position/execution audit state.

No provider contract quantity is stored or reinterpreted as canonical BTC quantity.

## Repository / synchronization state

E6 synchronization merge:

```text
e3ad9b28ee819fa99aa3933c146e9e9fe02151e2
```

Parents:

```text
4a845ff79ba48abb6122191a2cf8df7d52544475
bac41e860b5582f7a87d8992c803ce081dafcb35
```

This preserves both accepted E6 history and then-current main; no destructive rewrite was found.

At review time:

```text
PR #16 mergeable = TRUE
E6 branch vs latest main = ahead 36 / behind 2
latest-main-only delta = coordination/E6/TASK.md + coordination/E7/TASK.md
meaningful production/shared-contract drift = NONE
```

Coordination-only drift is not a resynchronization blocker. The lifecycle persistence defect is the only blocking source condition identified by this review.

## Test-definition review

Static definitions appropriately cover evidence contract fail-closed behavior, strategy inbox/idempotency/conflicts, service lifecycle gating, immutable persistence, append-only history, and restart persistence.

Missing for the blocking finding:

- direct `SQLiteRegistryStore.append_transition()` rejection of service-forbidden edges;
- persistence/migration proof that `DRAFT -> CANDIDATE`, `DRAFT -> REJECTED`, `CANDIDATE -> DRAFT`, `REJECTED -> CANDIDATE`, and equivalent forbidden edges cannot update authoritative state.

No tests or migrations were executed in GitHub.

## Verification / release state

- executable_verification: `NOT_RUN`
- migrations_executed: `NO`
- project_tests_executed: `NO`
- provider_requests: `NOT_SENT`
- github_compute: `NOT_USED`
- codex_ticket: `NONE / NOT_APPLICABLE WITHOUT LOCAL REPRODUCTION`
- gate_a: `BLOCKED / UNCHANGED`
- gate_b: `BLOCKED / UNCHANGED`
- gate_c: `BLOCKED / UNCHANGED`
- gate_d: `BLOCKED / UNCHANGED`

## Next action

`E6` should correct only `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` and return an exact revised source/test revision for bounded E7 static re-review.

Do **not** merge PR #16 yet. Do not expand lifecycle scope. Do not infer Gate A/PAPER/APPROVED/SHADOW/LIVE readiness from the accepted evidence-contract portion.

E7 stops here and waits for PM/E6. No PR merge, E6 implementation change, project execution, migration, or next task is started automatically.
