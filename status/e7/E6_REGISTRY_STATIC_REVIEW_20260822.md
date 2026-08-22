# E7 Static / Integration Review — E6 Early Slice 2 Registry Persistence

- Task: `E7-20260822-003`
- Date: 2026-08-22
- Review branch: `agent/e7-e6-registry-review-20260822`
- PR: `#16 platform: integrate early Slice 2 registry and evidence persistence`
- Reviewed E6 source/tests/docs revision: `207f6f87dd984c9dea5e4360e2f605e2c94b2bcf`
- Observed PR head: `df15109dcb8594b1182bf6fc09cb5ad6681d74b5`
- Implementation-pin -> PR-head delta: `coordination/E6/STATUS.md` only
- Review-time `main`: `82c52a1f1ce8f9bc7edf8cea139cd1b3fd2cf384`
- Executable verification: `NOT_RUN`
- GitHub project compute: `NOT_USED`

## Executive disposition

The accepted E6 evidence-contract correction remains intact and the synchronized PR scope is otherwise coherent, but PR #16 is **BLOCKED from merge** by a lifecycle-authority defect in the persistence boundary.

```text
E6-EVIDENCE-CONTRACT-001                  CLOSED / PASS STATIC
E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001   BLOCKING / FAIL
inbox / immutable strategy identity       PASS STATIC
append-only lifecycle audit               PASS STATIC
execution-audit scope separation          PASS STATIC
repository synchronization                PASS / NON-BLOCKING
PR #16 merge recommendation                DO NOT MERGE
```

The blocking condition is independent of executable evidence. No project test or migration was run in GitHub.

## 1. Synchronization / repository scope

E6 synchronization merge:

```text
e3ad9b28ee819fa99aa3933c146e9e9fe02151e2
```

The merge has two parents:

```text
4a845ff79ba48abb6122191a2cf8df7d52544475  accepted E6 correction baseline
bac41e860b5582f7a87d8992c803ce081dafcb35  then-current main
```

This is a non-destructive merge preserving both histories; no force rewrite/destructive rebase evidence was found.

PR #16 changed-file scope is limited to E6 registry/storage/tests/docs/status:

```text
coordination/E6/STATUS.md
docs/platform/E6_REGISTRY_PERSISTENCE_LIFECYCLE_SKELETON.md
src/registry/**
src/storage/**
status/E6_EARLY_SLICE2_HANDOFF.md
status/E6_STATUS.md
tests/registry/**
tests/storage/**
```

No PR file is under:

```text
contracts/**
src/market_data/**
src/strategy/**
src/backtest/**
src/brokers/**
src/execution/**
src/risk/**
src/position/**
.github/workflows/**
```

No real credential/secret material or unrelated feature expansion was found in the reviewed scope.

At review time:

```text
PR #16 mergeable = true
E6 branch vs latest main = ahead 36 / behind 2
```

The two main-only commits after E6's synchronization modify only:

```text
coordination/E6/TASK.md
coordination/E7/TASK.md
```

Therefore no additional E6 resynchronization is required merely because of those coordination-only commits. Repository synchronization is not the blocker in this review.

## 2. `E6-EVIDENCE-CONTRACT-001`

**Disposition: `CLOSED / PASS STATIC`**

The accepted critical blobs remain exactly unchanged at the synchronized implementation revision:

```text
src/registry/contract_validation.py
  blob = 954d21c021c0885554ee650acced17610d958a0e

src/registry/service_base.py
  blob = 3889ac156358f58c5fc3380865ad73844b874c3c

src/registry/service.py
  blob = 3184452956e1540be44d5ea779be87ed573fbcae
```

The public package export resolves `StrategyPlatformService` from `registry.service`, not directly from `service_base`.

### BacktestResult gate

Before persistence, the public service calls `validate_backtest_result_contract()` and `validate_verification_metadata()`.

The validator requires the current `contracts-v0.1` identity/reproducibility fields:

```text
schema_version
backtest_result_id
strategy_id
strategy_version
strategy_content_hash
runtime_version
dataset_id
dataset_hash
dataset_start
dataset_end
cost_model_version
created_at
```

and core metrics:

```text
total_trades
wins
losses
breakeven
gross_pnl
net_pnl
total_fees
profit_factor
expectancy
max_drawdown
max_consecutive_losses
```

It validates exact shared schema, non-empty identity fields, RFC3339 UTC timestamps, integer metric types, and decimal-string financial interchange shapes. Invalid/incomplete evidence fails before persistence even when callers supply synthetic `PASS / LOCAL_EXECUTION` metadata.

The base service then additionally binds the BacktestResult to the registered immutable strategy content hash and exact `(strategy_id, strategy_version)`.

### ValidationDecision gate

Before persistence, the public service calls `validate_validation_decision_contract()` and `validate_verification_metadata()`.

Required fields include:

```text
schema_version
validation_decision_id
strategy_id
strategy_version
backtest_result_id
validation_policy_version
decision
reason_codes
decided_at
```

`decision` is fail-closed to:

```text
PASS | FAIL | BLOCKED | NOT_RUN
```

`reason_codes` must be a sequence of non-empty strings. The base service then requires a stored BacktestResult parent with exact strategy binding and exact `backtest_result_id` reference.

### Candidate gate

A BacktestResult alone cannot authorize CANDIDATE.

`mark_candidate()` requires:

- current state `BACKTESTING`;
- stored `VALIDATION_DECISION` evidence;
- exact strategy identity/content binding;
- producer `E3`;
- `decision=PASS`;
- ValidationDecision verification metadata = `PASS / LOCAL_EXECUTION` with source revision/environment/command/result reference;
- an attached BacktestResult parent;
- BacktestResult verification metadata = `PASS / LOCAL_EXECUTION` with the same required evidence metadata shape.

Test fixtures that contain `PASS` are explicitly labeled synthetic/local-test fixture inputs and are not project executable evidence.

## 3. Inbox / immutable identity / compatibility boundary

**Disposition: `PASS STATIC`**

Accepted behavior remains:

- strategy identity is `(strategy_id, strategy_version)`;
- same identity + same immutable content is idempotent;
- same identity + conflicting content fails with `IdentityConflict`;
- persisted strategy content is protected by a SQLite immutable-content trigger;
- secret-like keys are rejected during intake before persistence;
- unsupported shared schema fails before registry write.

The default `DeferredCompatibilityBoundary` returns:

```text
status = NOT_RUN
verification_kind = NOT_RUN
checker = E2_RUNTIME_NOT_WIRED
```

It cannot manufacture executable E2 compatibility PASS. `DRAFT -> BACKTESTING` requires explicit local E2 PASS metadata.

SQLite remains an E6 implementation detail; no shared-contract semantic change is introduced by using SQLite.

## 4. Blocking finding — `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`

**Disposition: `BLOCKING / FAIL`**  
**Owner: E6**

The service layer correctly caps allowed transitions to:

```text
DRAFT -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

and exposes no service-level approval/live/generic transition method.

However, that authority cap is **not enforced at the persistence boundary**.

### Publicly reachable bypass surface

The repository publicly exposes all pieces required to bypass `StrategyPlatformService._transition()`:

- `registry.__init__` exports `LifecycleTransitionRecord`;
- `storage.__init__` exports `SQLiteRegistryStore`;
- `RegistryStore` publicly defines `append_transition(...)`;
- `SQLiteRegistryStore.append_transition(...)` accepts caller-supplied `LifecycleTransitionRecord`.

### Missing edge validation in store

`SQLiteRegistryStore.append_transition()` verifies:

- strategy exists;
- current persisted state equals `transition.previous_state`;
- registry revision matches;
- resulting revision is exactly current + 1.

It does **not** verify the transition edge against the early Slice 2 allowlist.

Thus a caller with the current revision can construct a transition such as:

```text
previous_state = DRAFT
new_state      = CANDIDATE
```

and the store has no source-level rule rejecting the edge before inserting the audit record and updating the current-state projection.

That bypass skips the service's required E2 compatibility and E3 ValidationDecision/BacktestResult gates.

The same generic surface can also express other service-forbidden edges among the four enum values, for example `CANDIDATE -> DRAFT` or `REJECTED -> CANDIDATE`, provided the caller supplies matching current state/revision.

### Migration does not close the bypass

`0001_strategy_registry.sql` constrains both `previous_state` and `new_state` to the four early states:

```text
DRAFT
BACKTESTING
REJECTED
CANDIDATE
```

but does not constrain allowed **pairs/edges**.

The migration therefore caps the vocabulary but not transition authority.

Append-only triggers correctly prevent UPDATE/DELETE of historical transition rows after insertion, but they do not prevent an unauthorized edge from being inserted initially.

### Why this is blocking

The current TASK explicitly requires models, service transitions, persistence constraints, and migration not to expose generic lifecycle transition authority.

Because the store can mutate the authoritative lifecycle projection outside the service gate, the repository cannot currently guarantee that `CANDIDATE` was reached only through validated E2/E3 evidence.

This is a source/integration authority defect, not an executable-test result.

### Required E6 correction

E6 should close the edge at the persistence boundary without expanding lifecycle scope. Acceptable bounded correction patterns include:

1. enforce the same exact early-Slice-2 edge allowlist inside `SQLiteRegistryStore.append_transition()`; and/or
2. enforce legal transition pairs in SQLite with an INSERT trigger/CHECK-equivalent rule; and
3. add deterministic persistence-level tests proving direct store calls cannot create service-forbidden edges.

At minimum tests should cover direct rejection of:

```text
DRAFT -> CANDIDATE
DRAFT -> REJECTED
CANDIDATE -> DRAFT
REJECTED -> CANDIDATE
```

while preserving the three allowed edges.

No PAPER / READY_FOR_APPROVAL / APPROVED / SHADOW / LIVE / DEGRADED state should be added while fixing this finding.

## 5. Persistence / audit behavior outside the blocker

**Disposition: `PASS STATIC except lifecycle-edge authority finding above`**

Positive findings:

- strategy immutable content trigger is present;
- lifecycle history UPDATE/DELETE is blocked by append-only triggers;
- lifecycle projection update uses current-state + revision concurrency conditions;
- foreign keys bind registry/evidence/history records;
- validation evidence type is limited to `BACKTEST_RESULT | VALIDATION_DECISION`;
- validation decision enum is constrained at storage level;
- current lifecycle state vocabulary is limited to the four early states.

The persistence implementation contains no generic PAPER/APPROVED/SHADOW/LIVE vocabulary.

## 6. Slice 3 / execution-audit separation

**Disposition: `PASS STATIC`**

PR #16 does not add persistence schema/model/service surfaces for:

- `ApprovedTradePlan`;
- `OrderRequest`;
- `OrderResult`;
- `Fill`;
- provider-native OKX `sz`;
- provider order/fill identity;
- execution reconciliation;
- Demo execution facts;
- position/execution audit state.

The validation database contains strategy, compatibility, E3 validation evidence, intake receipts, and lifecycle transition records only.

No provider contract quantity is stored or reinterpreted as canonical BTC quantity.

Slice 3 execution-audit persistence remains deferred.

## 7. Deterministic test-definition review

**Executable result: `NOT_RUN`**

Static definitions appropriately cover:

### Evidence contract

- every required BacktestResult field fails closed when missing, even with synthetic local-PASS metadata;
- financial metric decimal interchange shape;
- UTC timestamp requirement;
- every required ValidationDecision field;
- invalid decision enum / malformed reason codes;
- BacktestResult alone cannot promote CANDIDATE.

### Strategy inbox

- default compatibility = NOT_RUN and cannot begin backtesting;
- explicit synthetic local E2 PASS path;
- static/declaration-style PASS is insufficient;
- idempotent same-content intake;
- conflicting immutable identity fails closed;
- unsupported schema and secret-like fields fail before persistence.

### Lifecycle service

- NOT_RUN evidence cannot promote;
- synthetic local-PASS fixtures demonstrate the intended candidate gate;
- service exposes no approval/live/generic transition method;
- rejection retains strategy history;
- wrong strategy content hash fails.

### SQLite persistence

- migration idempotence definition;
- immutable-content direct update rejection;
- lifecycle-history UPDATE/DELETE append-only behavior;
- state survives restart.

Missing for the blocking finding:

- a direct `SQLiteRegistryStore.append_transition()` illegal-edge rejection test;
- migration/store-level proof that service-forbidden early-state edges cannot update authoritative lifecycle state.

No test, migration, backtest, provider request, or GitHub Actions/CI job was executed by E7.

## 8. Merge / release recommendation

```text
PR #16 source disposition: BLOCKED
PR #16 merge recommendation: DO NOT MERGE
blocking owner: E6
blocking finding: E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001
E6-EVIDENCE-CONTRACT-001: CLOSED / PASS STATIC
Executable verification: NOT_RUN
Gate A RESEARCH_READY: BLOCKED / UNCHANGED
Gate B PAPER_READY: BLOCKED / UNCHANGED
Gate C SHADOW_READY: BLOCKED / UNCHANGED
Gate D LIVE_READY: BLOCKED / UNCHANGED
```

After E6 closes only the persistence-edge authority bypass and returns an exact corrected revision, E7 should perform a bounded static re-review. Coordination-only TASK commits on `main` do not require another synchronization cycle unless meaningful production/shared-contract drift or an actual merge conflict appears.

E7 does not merge PR #16, does not modify E6 code, does not execute migrations/tests, and does not start the correction automatically.
