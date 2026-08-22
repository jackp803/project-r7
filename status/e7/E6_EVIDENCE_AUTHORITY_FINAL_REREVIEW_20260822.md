# E7 Final Targeted Re-Review — E6 Lifecycle Evidence Authority / PR #16

- Task: `E7-20260822-007`
- Date: `2026-08-22`
- Review branch: `agent/e7-e6-evidence-authority-rereview-20260822`
- Review-time `main`: `29b5fa3a011554e472a11b35f216a21eb816d4d1`
- PR: `#16 platform: integrate early Slice 2 registry and evidence persistence`
- Exact corrected E6 source/tests/docs revision: `df39836adabd04c77cc4f0d0b531ea10408866ab`
- Observed PR head: `e7d1f3d9a99043107824a3c64d1d37663db8ff53`
- Correction pin -> observed PR head delta: `coordination/E6/STATUS.md`, `status/E6_EARLY_SLICE2_HANDOFF.md`, `status/E6_STATUS.md` only
- Executable verification: `NOT_RUN`
- Tests/migrations executed: `NO`
- GitHub project compute: `NOT_USED`

## Executive disposition

`E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` is **NOT CLOSED**.

The correction successfully moves lifecycle promotion checks into `SQLiteRegistryStore.append_transition(...)` and revalidates durable E2/E3-looking evidence inside the transaction before lifecycle history/projection mutation. Edge shape, canonical payload validation, identity/content binding, local-evidence metadata checks, current-state/revision checks, atomic update, rollback, SQL forbidden-edge guards, and append-only history all remain coherent.

However, the authoritative persistence surface still allows a caller with direct access to the exported storage/registry APIs to manufacture the durable evidence or lifecycle projection that those checks trust. Promotion authority is therefore still based on caller-controlled durable records rather than trustworthy producer provenance.

```text
E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001   BLOCKING / NOT CLOSED
raw-store evidence provenance             BLOCKING / FAIL
E6-EVIDENCE-CONTRACT-001                  CLOSED / PASS STATIC / NO REGRESSION
PR #16 source disposition                 FAIL / BLOCKED
PR #16 merge recommendation               DO NOT MERGE
```

This is a source/security boundary finding, not an executable-test result.

## 1. What the correction fixes correctly

### Exact lifecycle vocabulary / edge shape

The reviewed source still exposes only:

```text
DRAFT
BACKTESTING
REJECTED
CANDIDATE
```

with exactly:

```text
DRAFT       -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

`EARLY_LIFECYCLE_TRANSITIONS` and `is_early_lifecycle_transition_allowed(...)` contain no later lifecycle states.

### Persistence transaction ordering

`SQLiteRegistryStore.append_transition(...)` now:

1. rejects non-allowed edge pairs;
2. starts `BEGIN IMMEDIATE`;
3. reloads authoritative strategy state;
4. checks persisted current lifecycle state;
5. checks `expected_registry_revision`;
6. checks `resulting_registry_revision == current + 1`;
7. calls `require_transition_authority(...)` inside the transaction;
8. only then inserts lifecycle history;
9. updates the authoritative projection with matching state/revision predicates;
10. requires exactly one projection row updated;
11. commits;
12. rolls back on exception.

This is the correct ordering for the bounded persistence gate itself.

### DRAFT -> BACKTESTING durable-row checks

`require_backtesting_authority(...)` requires a stored compatibility row for the exact strategy identity, checker prefix `E2`, `PASS / LOCAL_EXECUTION`, and non-empty:

- `source_revision`;
- `environment`;
- `command`;
- `result_ref`.

A transition-record field by itself cannot satisfy this gate.

### BACKTESTING -> CANDIDATE durable-row checks

`require_candidate_authority(...)` requires a transition-selected stored `VALIDATION_DECISION` and validates:

- evidence type `VALIDATION_DECISION`;
- producer `E3`;
- decision `PASS`;
- exact strategy identity;
- exact strategy content hash;
- complete `PASS / LOCAL_EXECUTION` metadata;
- canonical ValidationDecision JSON shape through the accepted validator;
- stored decision ID/schema/decision matching canonical payload;
- stored parent evidence ID;
- parent evidence type `BACKTEST_RESULT`;
- parent producer `E3`;
- exact parent identity/content binding;
- complete parent local-PASS metadata;
- canonical BacktestResult JSON shape through the accepted validator;
- stored BacktestResult ID/schema matching canonical payload;
- exact ValidationDecision -> BacktestResult canonical ID binding.

Malformed, mismatched, wrong-type, wrong-parent, FAIL/BLOCKED/NOT_RUN, non-local, and incomplete metadata paths fail closed at this helper layer.

### SQL lifecycle edge guard / append-only history

`0001_strategy_registry.sql` retains the `BEFORE INSERT` lifecycle-edge trigger allowing only the same three edge pairs and retains UPDATE/DELETE append-only triggers on lifecycle history.

These protections are valid but only constrain lifecycle-event shape/history; they do not establish producer provenance.

## 2. BLOCKING — raw-store evidence provenance is caller controlled

### 2.1 Public/reachable writer surface

The repository exports or exposes:

```text
registry.CompatibilityEvidence
registry.ValidationEvidenceRecord
registry.StrategyVersionRecord
registry.LifecycleTransitionRecord
storage.SQLiteRegistryStore
storage.connect
RegistryStore.save_compatibility(...)
RegistryStore.save_validation_evidence(...)
RegistryStore.append_transition(...)
```

The concrete `SQLiteRegistryStore` implements those writer methods directly.

### 2.2 Synthetic E2 authority can be manufactured

`SQLiteRegistryStore.save_compatibility(...)` accepts a caller-constructed `CompatibilityEvidence` and commits its fields directly. It does not require an E2-owned capability/token, service-issued provenance object, signature, immutable producer receipt, trusted writer identity, or other non-caller-forgeable provenance.

Therefore a direct caller can construct durable-looking evidence such as:

```text
checker           = "E2_TEST_FIXTURE"  # starts with E2
status            = "PASS"
verification_kind = "LOCAL_EXECUTION"
source_revision   = "caller-value"
environment       = "caller-value"
command           = "caller-value"
result_ref        = "caller-value"
```

and persist it through the public store method.

`require_backtesting_authority(...)` subsequently treats those field values as sufficient durable authority.

The new deterministic test helper `_to_backtesting(...)` demonstrates this exact authority model: it calls `store.save_compatibility(...)` with synthetic local-PASS evidence and then successfully calls `store.append_transition(DRAFT -> BACKTESTING)`.

That test is useful evidence of the bypass, not positive security evidence.

### 2.3 Synthetic E3 promotion authority can be manufactured

`SQLiteRegistryStore.save_validation_evidence(...)` similarly accepts a caller-constructed `ValidationEvidenceRecord` and commits it directly. The writer does not establish trusted E3 provenance.

A direct caller can therefore create, in order:

1. a canonical-looking BacktestResult payload bound to the registered strategy;
2. a `ValidationEvidenceRecord` declaring:
   - `evidence_type = BACKTEST_RESULT`;
   - `producer = E3`;
   - `PASS / LOCAL_EXECUTION` metadata;
3. a canonical-looking ValidationDecision payload referencing that BacktestResult;
4. a second `ValidationEvidenceRecord` declaring:
   - `evidence_type = VALIDATION_DECISION`;
   - `producer = E3`;
   - `decision = PASS`;
   - `parent_evidence_id` pointing at the caller-created BacktestResult;
   - caller-supplied complete local-PASS metadata;
5. `append_transition(BACKTESTING -> CANDIDATE, primary_evidence_id=<caller-created decision>)`.

Because the canonical JSON can be made internally consistent, every current `require_candidate_authority(...)` content/binding check can pass even though no authoritative E3 producer path created the evidence.

Canonical contract validation proves shape/semantic consistency. It does not prove producer provenance.

### 2.4 Direct initial-state construction bypass

There is an even earlier reachable persistence bypass.

`StrategyVersionRecord` is public and caller-constructible. `SQLiteRegistryStore.register_strategy(...)` inserts the record's caller-supplied:

```text
current_lifecycle_state
registry_revision
```

directly into `strategy_versions`.

The SQL table constrains `current_lifecycle_state` only to the four recognized enum values and `registry_revision >= 0`; it does not require a newly registered strategy to start at exactly `DRAFT / revision 0`.

A caller can therefore construct and register a strategy record already declaring `current_lifecycle_state="CANDIDATE"`, bypassing lifecycle transition history and E2/E3 promotion authority entirely.

This is within the explicit TASK requirement to inspect direct record construction and equivalent raw-store interfaces.

### 2.5 Public raw connection can mutate lifecycle projection directly

`storage.__all__` publicly exports `connect`, and `connect(...)` returns the raw SQLite connection.

The migration's immutable-content trigger protects strategy semantic fields, but it does not prevent a direct SQL update of:

```text
strategy_versions.current_lifecycle_state
strategy_versions.registry_revision
```

The lifecycle history append-only triggers do not govern direct projection updates.

A caller with this exported raw persistence surface can therefore mutate the authoritative lifecycle projection without any lifecycle row or evidence authorization.

This is an additional reachable authority bypass under the repository's current exported persistence surface.

## 3. Raw-store provenance disposition

**Disposition: `BLOCKING / FAIL`**

The repository currently treats durable field values as authority even though the same public persistence surface lets an arbitrary caller manufacture those durable field values.

The distinction is:

```text
canonical validity     != producer provenance
row durability         != trusted provenance
string "E2..."         != E2 authority
string producer="E3"   != E3 authority
PASS/LOCAL_EXECUTION    != verified local execution merely because caller wrote it
```

For this TASK, these surfaces are authoritative because they can change the same persisted registry/lifecycle state consumed by the system. They cannot be dismissed as test-only internals while simultaneously serving as the persistence authority boundary.

Required correction outcome is architectural, but bounded:

- promotion-relevant compatibility/validation evidence must become writable only through a trusted producer/service authority path or carry non-caller-forgeable provenance validated by persistence;
- direct construction/public raw-store methods must not be able to manufacture promotion authority;
- initial strategy registration must fail closed unless lifecycle state/revision are the permitted initial values;
- authoritative lifecycle projection must not be directly mutable through an exported raw connection without the lifecycle authority path;
- the existing canonical validators, three-edge lifecycle cap, concurrency semantics, rollback, and append-only audit behavior must remain intact.

E7 does not prescribe a particular implementation mechanism in this review and does not modify E6 code.

## 4. Normal StrategyPlatformService regression review

**PASS / STATIC ONLY**

The public `StrategyPlatformService` now calls the same lifecycle-authority helpers before delegating to the existing base service. This is same-or-stricter than the accepted service-level behavior.

Evidence ingest remains protected by:

```text
validate_backtest_result_contract(...)
validate_validation_decision_contract(...)
validate_verification_metadata(...)
```

before base persistence.

Accepted critical blobs remain:

```text
src/registry/contract_validation.py
  954d21c021c0885554ee650acced17610d958a0e

src/registry/service_base.py
  3889ac156358f58c5fc3380865ad73844b874c3c
```

`src/registry/service.py` changed intentionally to call the new lifecycle-authority helpers; the evidence validators remain in place and are not weakened.

## 5. E6-EVIDENCE-CONTRACT-001 regression disposition

**`CLOSED / PASS STATIC / NO REGRESSION`**

Preserved:

- complete canonical BacktestResult required-field/type/time/decimal validation;
- complete canonical ValidationDecision required-field/enum/reason-code/time validation;
- exact strategy version/content binding;
- exact ValidationDecision -> BacktestResult ID binding in the normal service path;
- unsupported enum/type fails closed;
- caller-supplied verification metadata cannot bypass canonical payload validators;
- BacktestResult alone cannot authorize CANDIDATE through `StrategyPlatformService`.

Important distinction: this accepted finding is about canonical evidence contract validation. It does not solve the separate raw-store writer-provenance defect identified above.

## 6. Test-definition review

Static definitions in `tests/storage/test_lifecycle_evidence_authority.py` cover many content/transaction failure modes correctly:

- missing compatibility;
- wrong checker;
- non-PASS compatibility;
- non-local verification kind;
- missing local evidence metadata;
- missing primary ValidationDecision;
- wrong evidence type;
- FAIL/BLOCKED/NOT_RUN decision values;
- wrong strategy identity/content hash;
- missing/wrong BacktestResult parent;
- malformed canonical payload;
- mismatched canonical BacktestResult ID;
- non-local/missing metadata on decision/backtest;
- no lifecycle row/state/revision mutation on rejected cases;
- valid service-authorized backtesting/candidate paths.

But the tests do not establish trusted provenance. In fact:

- `_to_backtesting(...)` manufactures synthetic E2 local-PASS compatibility through the raw store and treats it as valid authority;
- `_save_valid_backtest(...)` and `_save_decision(...)` manufacture caller-created E3-looking durable evidence through raw store methods;
- there is no test asserting that raw-store synthetic PASS evidence cannot authorize promotion;
- there is no test rejecting `register_strategy(...)` with non-DRAFT initial lifecycle state/revision;
- there is no test preventing direct raw-connection projection mutation.

No test was executed in GitHub. Synthetic PASS values remain fixture strings only and are not project executable evidence.

## 7. SQL / concurrency / rollback disposition

```text
edge allowlist                         PASS / STATIC ONLY
SQL forbidden lifecycle INSERT        PASS / STATIC ONLY
lifecycle UPDATE/DELETE append-only    PASS / STATIC ONLY
current-state concurrency check        PASS / STATIC ONLY
expected revision check                PASS / STATIC ONLY
resulting revision check               PASS / STATIC ONLY
atomic lifecycle event + projection    PASS / STATIC ONLY
exception rollback                     PASS / STATIC ONLY
producer/writer provenance             FAIL / BLOCKING
initial lifecycle registration guard   FAIL / BLOCKING
raw projection write guard             FAIL / BLOCKING
```

## 8. Slice / lifecycle / execution scope

No regression or scope expansion found in PR #16 changed-file scope:

- no `contracts/**` change;
- no E1/E2/E3/E4/E5 production change;
- no `.github/workflows` / CI addition;
- no real credential/secret material found;
- no ApprovedTradePlan persistence;
- no OrderRequest persistence;
- no OrderResult persistence;
- no Fill persistence;
- no Position execution-audit persistence;
- no OKX provider-native `sz` persistence;
- no provider order/fill/reconciliation persistence;
- no Demo execution facts;
- no PAPER / READY_FOR_APPROVAL / APPROVED / SHADOW / LIVE / DEGRADED / RETIRED lifecycle state.

Provider-native quantity is not reinterpreted as canonical BTC quantity in this PR.

## 9. Repository / synchronization state

Correction pin -> observed PR head changes only:

```text
coordination/E6/STATUS.md
status/E6_EARLY_SLICE2_HANDOFF.md
status/E6_STATUS.md
```

No production/test blob changed after the reviewed correction pin.

At review time:

```text
latest main = 29b5fa3a011554e472a11b35f216a21eb816d4d1
E6 branch vs latest main = ahead 57 / behind 2
latest-main-only delta = coordination/E6/TASK.md + coordination/E7/TASK.md
meaningful production/shared-contract drift = NONE
PR #16 GitHub mergeable = FALSE at review time
```

The latest-main drift is coordination-only and does not invalidate this exact source review. GitHub's current `mergeable=false` is a secondary repository condition; PR #16 is already source-blocked by the authority bypass, so no merge is recommended regardless.

E6 synchronization merge `d94a64a1abaf70850167b3e6aec7af120f40ffa6` was inspected as a normal merge of then-current main into the E6 branch; no destructive E7 action is taken here.

## 10. Final recommendation

`PR #16`: **DO NOT MERGE**.

Owner: **E6**.

Exact remaining condition: a caller with direct access to the exported E6 persistence surface can manufacture promotion authority or lifecycle projection without trustworthy E2/E3 producer provenance. The accepted canonical validators and new in-transaction durable-row checks do not distinguish trusted producer output from caller-created rows carrying the same strings/payloads.

A future bounded E6 correction must close all reachable authoritative persistence bypasses while preserving the accepted early Slice 2 lifecycle and evidence semantics, then return an exact revision for E7 re-review.

## Verification / release state

```text
Executable verification: NOT_RUN
Project tests executed: NO
Migrations executed: NO
Backtests executed: NO
Provider requests: NOT_SENT
GitHub project compute: NOT_USED
Codex ticket: NONE
Gate A: BLOCKED / UNCHANGED
Gate B: BLOCKED / UNCHANGED
Gate C: BLOCKED / UNCHANGED
Gate D: BLOCKED / UNCHANGED
```

E7 stops after this task. No PR merge, E6 implementation edit, test/migration execution, lifecycle advancement, or next task is started automatically.
