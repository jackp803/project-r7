# E6 Current Task

- task_id: `E6-20260824-010`
- issued_at: `2026-08-24T16:04:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e6-gate-b-paper-runtime-durability-20260824`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`, `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`, ADR-0005, ADR-0006, accepted Gate A evidence PR #33, accepted Gate B static integration chain through PR #55

## Objective

Implement only the first E6-owned **durable Paper runtime persistence / restart / audit slice** required by Gate B.

The current in-memory execution/position/result chain is already statically materialized through accepted E4/E5/E7 work. This task must persist and recover the exact canonical runtime truth without recomputing identities or inventing domain state.

Bounded intent:

```text
canonical E4/E5 runtime objects / observations
-> E6 durable SQLite runtime journal + exact projections/indexes
-> process close/reopen
-> exact restart-safe recovery/readback
-> immutable/idempotent audit behavior
```

Stop at E6 durability/recovery storage. Do **not** implement Paper runtime scheduling, E4/E5 domain behavior, E7 E2E/release approval, provider/private APIs, dashboard expansion, later strategy lifecycle promotion, PAPER/SHADOW/LIVE authorization, or approved-local execution.

## Accepted prerequisites

```text
PR #55 merge = d6302eb89b9319bfd00d5c26e315bd2fe1923b65
ordinary EXIT in-memory -> canonical TradeResult = MATERIALIZED / executable NOT_RUN
EMERGENCY_EXIT in-memory -> canonical TradeResult = MATERIALIZED / executable NOT_RUN
verified full PROTECTION_STOP -> canonical TradeResult = MATERIALIZED / executable NOT_RUN
funding producer -> consumer = MATERIALIZED / executable NOT_RUN

Current remaining Gate B structural blocker:
Restart/persistence preserves required state = BLOCKED / E6 IMPLEMENTATION GAP
Paper E2E closes to TradeResult and persists audit = BLOCKED / E6 DURABILITY + APPROVED-LOCAL E2E EVIDENCE
```

No prerequisite `NOT_RUN` is PASS. Gate B remains BLOCKED and PAPER remains unauthorized.

## Required inspection before editing

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E6_PLATFORM.md`;
- `contracts/README.md` and current canonical execution/position/result profiles;
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`;
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`;
- `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`;
- ADR-0005 / ADR-0006;
- current `src/storage/**`, migrations and `tests/storage/**`;
- existing early Slice 2 Registry/public storage boundary and tests;
- current E4/E5 canonical object shapes read-only as needed;
- accepted E7 PR #55 integration/safety definitions and `status/RELEASE_GATES.md` / `status/INTEGRATION_STATUS.md`.

### Contract-first blocker rule

If durable recovery requires a new shared serialized field, enum, authority meaning, lifecycle meaning, or cross-module DTO that is not already defined, stop:

```text
BLOCKED / CONTRACT_OR_SEMANTIC_GAP
next_owner = E7
```

E6 may define storage-internal schemas, indexes, migrations, repository/service APIs, errors and local recovery views under its own ownership. It must not redefine canonical E4/E5/E7 objects or promote an E6-local recovery DTO into a shared contract.

## Required durable object coverage

Persist the exact canonical payload/identity or exact canonical reference for the current Gate B Paper runtime graph at minimum:

```text
strategy_id + strategy_version reference
RiskDecision
ApprovedTradePlan
Position observations including lifecycle/reconciliation projection
PositionAction
OrderRequest
OrderResult observations / reconciliation state needed for recovery
Fill
FundingAllocationEvidence
TradeResult
```

Preserve identifiers and lineage including, where present:

```text
risk_decision_id
trade_plan_id
position_id
position_action_id
order_request_id
client_order_id
broker_order_id
fill_id
funding_evidence_id
trade_result_id
```

Do not regenerate any of these IDs on storage or restart.

## Required persistence semantics

### 1. Canonical payload preservation

- Store exact canonical serialized data, plus storage-owned metadata such as row IDs, payload hashes, created/persisted timestamps and indexes only where useful.
- Storage metadata must not alter canonical object identity.
- Do not derive `Position.actual_quantity`, lifecycle, protection state, funding zero, PnL, order status or TradeResult from other rows during persistence/recovery.
- Do not treat missing data as zero, flat, protected, closed, healthy or reconciled.

### 2. Immutable object/idempotency rules

For immutable identity-bearing objects such as RiskDecision, ApprovedTradePlan, PositionAction, OrderRequest, Fill, FundingAllocationEvidence and TradeResult:

```text
same canonical ID + identical canonical payload
-> idempotent replay / no second financial fact

same canonical ID + different canonical payload
-> durable conflict / fail closed
```

Do not use last-write-wins for canonical financial/runtime identity.

For `Fill`, a repeated identical `fill_id` is idempotent; the same `fill_id` with changed quantity/price/lineage/time/fee is corruption/conflict.

For `TradeResult`, once a final canonical result is stored it is immutable. A later write must not silently rewrite historical PnL, fees, funding binding, exit reasons, quantity or identity.

### 3. Funding evidence conflict rules

Implement the accepted `funding-allocation-v0.1` durable behavior.

Canonical lineage key:

```text
(
  funding_evidence_profile_version,
  trade_plan_id,
  position_id,
  symbol,
  interval_start,
  interval_end,
  interval_semantics
)
```

Required behavior:

```text
same funding_evidence_id + identical identity material
-> idempotent replay

same funding_evidence_id + different identity material/payload
-> corruption/conflict / fail closed

different funding_evidence_id for the same exact lineage key
-> reconciliation conflict / fail closed / never last-write-wins

existing durable TradeResult bound to funding_evidence_id A
+ later conflicting evidence B for the same lineage
-> no silent TradeResult rewrite
```

`calculated_at` is non-financial observation metadata. Do not manufacture a new financial allocation merely because a later equivalent observation has a newer calculated_at. Preserve the first canonical evidence object; a separate storage-owned observation/audit record may represent later duplicate observation metadata if useful.

### 4. Observation/projection behavior

OrderResult and Position may have multiple authoritative observations over time.

- Preserve append-only observation history sufficient for audit/restart.
- A current projection/index may advance only from coherent later authoritative observations.
- A stale historical observation may be retained for audit but must not silently replace a newer current projection.
- Equal observation identity/time with conflicting payload must fail closed.
- Recovery must expose the exact stored current canonical observation, not recompute it from Fill totals or symbol-level net exposure.

If current shared semantics are insufficient to choose a safe current projection in a specific case, store append-only truth and stop with a bounded blocker rather than inventing precedence.

### 5. Restart recovery

Provide an E6-owned public storage/service surface that can close and reopen the SQLite database and recover exact Paper runtime state by stable lineage such as `position_id` and/or `trade_plan_id`.

Recovery must be able to return/read the exact stored canonical objects needed for later E7 integration, including open/in-flight and closed cases.

At minimum define deterministic behavior for:

- restart with an open Position and protection/close Order state;
- restart after partial Fill / nonterminal Order state;
- restart with reconciliation-required/ambiguous state preserved as such;
- restart after full close with FundingAllocationEvidence + TradeResult persisted;
- incomplete/corrupt/conflicting graph fails closed rather than inventing missing state.

An E6-local recovery bundle/view is allowed as an E6 storage API. It is not a new shared domain contract and must contain/read exact canonical serialized payloads rather than rewritten copies.

### 6. Atomicity / audit

Use transactions so a bounded runtime write either commits coherently or rolls back without half-updating current projections.

Preserve durable auditability of:

- object kind;
- canonical identity;
- canonical payload hash;
- lineage keys/indexes needed for exact lookup;
- immutable creation/persistence record;
- observation ordering where applicable;
- conflict/rejection reason in sanitized E6-local error/audit form when retained.

Do not store credentials or provider-private secrets.

### 7. Preserve existing early Registry behavior

Do not weaken or expand the accepted early Slice 2 Registry lifecycle:

```text
DRAFT -> BACKTESTING -> REJECTED | CANDIDATE
```

Do not enable `PAPER`, `APPROVED`, `SHADOW`, `LIVE` or later lifecycle transitions in this task.

Existing `open_sqlite_platform(...)` / Strategy Registry behavior and its migration guarantees must remain compatible. Runtime durability may be implemented as additive E6 storage/migrations/services without turning SQLite details into a cross-module contract.

## Required deterministic test definitions

Add/update E6-owned tests under `tests/storage/**` and, only if necessary, `tests/platform/**` covering at minimum:

- additive migration creates Paper runtime durability schema without breaking existing Registry schema/data;
- exact round-trip for each required canonical object type;
- same canonical ID + same payload is idempotent;
- same canonical ID + changed payload fails closed;
- Fill replay/conflict behavior;
- Position/OrderResult append-only observations and current projection do not regress on stale observations;
- equal observation time/identity with conflicting payload fails closed;
- funding same-ID replay, same-ID corruption, and same-lineage different-ID conflict;
- durable TradeResult cannot be silently rewritten and retains exact `funding_evidence_id` binding;
- close database / reopen / recover exact open Position + action/order/fill state;
- close database / reopen / recover ambiguous/reconciliation-required state without converting it to healthy/flat/closed;
- close database / reopen / recover closed Position + funding evidence + TradeResult with exact IDs/payloads;
- incomplete/corrupt/conflicting runtime graph fails closed;
- transaction rollback leaves no half-applied projection;
- no credential/provider-private fields are required or persisted;
- existing Strategy Registry/storage tests remain defined and compatible;
- no lifecycle/release authority is created by persistence.

Use only sanitized deterministic fixtures. You may reuse canonical fixture shapes from accepted tests, but E6 production must not import E4/E5 implementation classes merely to reconstruct financial truth.

## Writable scope

E6-owned only:

- `src/storage/**`;
- `src/platform/**` only if strictly needed for the bounded storage/service composition surface;
- `tests/storage/**`;
- `tests/platform/**` compatibility definitions only if required;
- `docs/platform/**`, `docs/operations/**` only if needed;
- E6-specific `status/**` evidence/handoff;
- `coordination/E6/STATUS.md` on the target branch.

Forbidden:

- `contracts/**` / ADR changes;
- E1-E5 production code;
- E7 integration/release files;
- strategy lifecycle expansion beyond the accepted early Registry subset;
- dashboard/UI expansion unrelated to durability;
- provider/private API/network/credentials;
- GitHub Actions/CI/workflows;
- PAPER/SHADOW/LIVE authority.

## Executable verification

This is implementation/test-definition work under the hard local-only policy. Unless an exact-revision Local Runner action is separately approved by PM/Product Owner, record:

```text
local_verification = NOT_RUN
```

with exact future Windows PowerShell commands from repository root, at minimum:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud execution, Computer Adapter, provider/private APIs or credentials. `NOT_RUN` is not PASS.

## Acceptance

### DONE

- additive E6 durable Paper runtime schema/service is materialized;
- required canonical runtime identities/payloads survive database close/reopen exactly;
- open/in-flight/ambiguous and closed runtime states are recoverable without domain-state invention;
- immutable/idempotent/conflict semantics are fail-closed;
- funding lineage conflict and TradeResult binding rules are enforced durably;
- existing early Registry behavior is preserved;
- deterministic E6 storage/restart test definitions are materialized;
- no shared contract, E4/E5, provider, lifecycle-promotion or release scope is crossed;
- executable verification is approved-local evidence or explicit `NOT_RUN` with exact commands.

### BLOCKED

- accepted shared semantics are insufficient for safe durable representation/recovery;
- record exact expected-vs-actual evidence and `next_owner = E7`;
- do not invent a parallel cross-module contract or last-write-wins workaround.

Do not declare `Restart/persistence` PASS, Paper E2E PASS, Gate B/PAPER_READY PASS, or any PAPER/SHADOW/LIVE authorization without later E7 review and approved-local evidence.

## Completion / mailbox rule

Commit/push bounded code/tests/evidence/status to `agent/e6-gate-b-paper-runtime-durability-20260824`.

Worker-owned terminal STATUS must be written/pushed to `coordination/E6/STATUS.md` on that target branch, not main.

Then stop. Do not self-start E7 integration/E2E, approved-local verification, provider/private work, Gate C, PAPER, SHADOW or LIVE.