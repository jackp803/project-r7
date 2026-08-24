# E6 Current Task

- task_id: `E6-20260824-013`
- issued_at: `2026-08-24T17:08:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e6-gate-b-paper-runtime-durability-v2-20260824`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`, `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`, ADR-0005, ADR-0006, ADR-0007, accepted Gate B in-memory chain through PR #55, blocker PR #56, lifecycle contract PR #57, accepted E5 lifecycle projection producer PR #58

## Objective

Implement only the renewed E6-owned **durable Paper runtime persistence / restart / audit slice** required by Gate B, now consuming the accepted E5 `position-lifecycle-projection-v0.1` producer output rather than inventing lifecycle precedence.

Bounded intent:

```text
canonical E4/E5 runtime objects
+ canonical profiled Position projections from E5
-> E6 durable SQLite append-only journal + mechanical current indexes
-> database close/reopen
-> exact restart-safe recovery/readback
-> immutable/idempotent/conflict-safe audit behavior
```

Stop at E6 durability/recovery storage. Do **not** implement Paper runtime scheduling/orchestration, E4/E5 domain behavior, E7 E2E/release approval, provider/private APIs, dashboard expansion, strategy lifecycle promotion, PAPER/SHADOW/LIVE authorization, or approved-local execution.

## Accepted prerequisites

```text
PR #55 merge = d6302eb89b9319bfd00d5c26e315bd2fe1923b65
in-memory ordinary EXIT / EMERGENCY_EXIT / verified full PROTECTION_STOP -> canonical TradeResult = MATERIALIZED / executable NOT_RUN

PR #56 merge = 649ae522b71f3992e48b81882662b6d7d0222324
prior E6 durability attempt = BLOCKED / CONTRACT_OR_SEMANTIC_GAP

PR #57 merge = 5b203ea2e4a235dfb4575626f15e2409b6674c59
profile = position-lifecycle-projection-v0.1
Position lifecycle durability contract/rule = RESOLVED STATIC

PR #58 merge = f5bbeaf1daef1fdeda28ea6d12482b3b26018cc8
E5 lifecycle projection producer = MATERIALIZED / executable NOT_RUN
```

No prerequisite `NOT_RUN` is PASS. Gate B remains BLOCKED and PAPER remains unauthorized.

## Required inspection before editing

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E6_PLATFORM.md`;
- `contracts/README.md`, `contracts/SHARED_CONTRACTS_V1.md`;
- `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md` and ADR-0007;
- protection/close/funding profiles and ADR-0005/0006;
- current E5 `src/position/lifecycle_projection.py` read-only;
- current E4/E5 canonical runtime shapes read-only as needed;
- current `src/storage/**`, migrations, `src/platform/**` public storage/service boundary;
- existing `tests/storage/**`, `tests/platform/**`, `tests/registry/**`;
- PR #55 integration definitions, PR #56 blocker evidence, PR #58 producer tests/evidence;
- `status/RELEASE_GATES.md`, `status/INTEGRATION_STATUS.md`.

### Contract-first blocker rule

If safe durable recovery still requires a new shared serialized field, enum, lifecycle meaning, authority meaning, profile revision, or cross-module DTO not already defined by accepted contracts, stop:

```text
BLOCKED / CONTRACT_OR_SEMANTIC_GAP
next_owner = E7
```

E6 may define storage-internal tables, migrations, indexes, row metadata, repository/service APIs, errors and recovery views. It must not redefine canonical E4/E5/E7 objects or turn an E6-local DTO into a shared contract.

## Required durable object coverage

Persist exact canonical payload/identity or exact canonical reference for the current Gate B Paper runtime graph at minimum:

```text
strategy_id + strategy_version reference
RiskDecision
ApprovedTradePlan
profiled Position projections (`position-lifecycle-projection-v0.1`)
PositionAction
OrderRequest
OrderResult observations / reconciliation state needed for recovery
Fill
FundingAllocationEvidence
TradeResult
```

Preserve stable identifiers exactly where present:

```text
risk_decision_id
trade_plan_id
position_id
lifecycle_projection_id
lifecycle_revision
previous_lifecycle_projection_id
position_action_id
order_request_id
client_order_id
broker_order_id
fill_id
funding_evidence_id
trade_result_id
```

Never regenerate canonical IDs on persistence or restart.

## Position lifecycle projection durability

This is the key remediation from PR #56/#57/#58.

### 1. Persist exact E5 profiled projections

A restart-authoritative Position projection must declare:

```text
schema_version = contracts-v0.1
position_lifecycle_projection_profile_version = position-lifecycle-projection-v0.1
```

E6 must validate/persist the exact serialized projection produced by E5. E6 must not call E5 state transitions during restart and must not allocate or repair lifecycle revisions/IDs.

### 2. Current lifecycle projection selection

For one `position_id`, current projection may advance only through the highest contiguous, conflict-free lifecycle revision satisfying the shared rules:

```text
revision 0 = GENESIS
revision n+1 = exact previous revision + 1
previous_lifecycle_projection_id = exact stored revision n ID
broker anchors nondecreasing
same revision + same ID + identical payload = idempotent replay
same revision + changed payload/ID = conflict
same ID + changed payload = corruption/conflict
revision gap = cannot advance
predecessor mismatch = branch/conflict
higher lifecycle revision with older broker anchor = stale/invalid
```

Do not use SQLite row order, auto-increment, insertion sequence, `persisted_at`, process arrival order or last-write-wins as lifecycle authority.

### 3. Newer raw E4 broker truth without E5 re-attestation

If E6 stores a newer E4 broker observation whose `broker_state_observed_at` is later than the latest accepted E5 lifecycle projection anchor, E6 must not copy the old lifecycle state onto the newer broker facts.

Persist the evidence separately if needed and expose a bounded E6-local diagnostic/recovery state indicating fresh E5 interpretation/REATTESTATION is required. Do not synthesize a canonical Position projection.

### 4. Legacy Position handling

Legacy Positions without `position-lifecycle-projection-v0.1` may be stored as historical/raw evidence if useful, but are not Gate B restart-authoritative current Position projections.

Do not backfill revision 0 from storage order. Safe profile entry is an E5 responsibility from a fresh E4 observation.

## Immutable object / idempotency rules

For immutable identity-bearing objects including RiskDecision, ApprovedTradePlan, PositionAction, OrderRequest, Fill, FundingAllocationEvidence and TradeResult:

```text
same canonical ID + identical canonical payload
-> idempotent replay / no second financial fact

same canonical ID + different canonical payload
-> durable conflict / fail closed
```

For Fill:

```text
same fill_id + identical payload -> idempotent
same fill_id + changed quantity/price/time/fee/lineage -> conflict
```

For TradeResult, once stored it is immutable. Later persistence must never silently rewrite PnL, fees, funding binding, exit reasons, quantities or identity.

## Funding evidence durable conflict rules

Use the accepted `funding-allocation-v0.1` lineage key:

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
same funding_evidence_id + identical canonical payload
-> idempotent replay

same funding_evidence_id + changed identity material/payload
-> corruption/conflict / fail closed

different funding_evidence_id for the same exact lineage key
-> reconciliation conflict / fail closed / never last-write-wins

persisted TradeResult bound to evidence A
+ later conflicting evidence B on same lineage
-> no silent TradeResult rewrite
```

`calculated_at` is non-financial observation metadata and must not create a second financial allocation for otherwise identical evidence.

## OrderResult / broker observation history

OrderResult and other mutable authoritative broker observations may have multiple observations over time.

- preserve append-only history sufficient for audit/restart;
- current projection/index advances only from coherent later authoritative observation time;
- stale historical observations remain auditable but cannot replace a newer current observation;
- equal observation identity/time with conflicting canonical payload fails closed;
- UNKNOWN / RECONCILIATION_REQUIRED / degraded truth must remain exactly that after restart;
- do not infer healthy/filled/flat state from other rows.

If shared semantics are insufficient for a specific mutable observation ordering case, stop with the contract-first blocker rather than inventing precedence.

## Canonical payload preservation

- Store exact canonical serialized data; storage-owned metadata such as payload hash, persisted timestamp, row identity and indexes may be additive only.
- Storage metadata must not alter canonical identity or domain meaning.
- Never derive `Position.actual_quantity`, lifecycle/protection state, funding zero, PnL, order status or TradeResult from other rows during persistence/recovery.
- Missing data never means zero, flat, protected, closed, healthy or reconciled.

## Restart recovery surface

Provide an E6-owned public storage/service surface that can close/reopen SQLite and recover exact Paper runtime state by stable lineage such as `position_id` and/or `trade_plan_id`.

At minimum recovery definitions must cover:

1. open Position with GENESIS/TRANSITION/REATTESTATION lifecycle history plus active protection/close order state;
2. partial Fill / nonterminal Order state;
3. UNKNOWN or RECONCILIATION_REQUIRED state preserved without promotion;
4. lifecycle projection gap/conflict reported fail-closed rather than silently selecting a branch;
5. newer raw broker observation beyond latest lifecycle anchor reported as requiring E5 re-attestation, without synthetic Position creation;
6. fully closed Position projection with FundingAllocationEvidence + immutable TradeResult;
7. incomplete/corrupt/conflicting graph fails closed.

An E6-local recovery bundle/view is allowed, but it must return/read exact canonical payloads and is not a new shared domain contract.

## Atomicity / audit

Use transactions so a bounded runtime write either commits coherently or rolls back without half-updating current indexes/projections.

Preserve durable auditability for:

```text
object kind
canonical identity
canonical payload hash
lineage keys/indexes
immutable creation/persistence record
observation ordering
lifecycle revision/predecessor chain
sanitized conflict/rejection reason where retained
```

Do not store credentials or provider-private secrets.

## Preserve existing Registry behavior

Do not weaken or expand the accepted early E6 Registry lifecycle:

```text
DRAFT -> BACKTESTING -> REJECTED | CANDIDATE
```

Existing `open_sqlite_platform(...)` / Strategy Registry behavior and migrations must remain compatible. Do not enable PAPER, APPROVED, SHADOW, LIVE or later lifecycle transitions in this task.

## Required deterministic E6 test definitions

Add/update E6-owned definitions under `tests/storage/**` and only strictly necessary `tests/platform/**` covering at minimum:

- additive migration creates Paper runtime durability schema without breaking existing Registry schema/data;
- exact round-trip for every required canonical object kind;
- same immutable ID + same payload idempotency;
- same immutable ID + changed payload conflict;
- Fill replay/conflict;
- profiled Position GENESIS/TRANSITION/REATTESTATION exact round-trip;
- contiguous lifecycle revisions mechanically advance current projection;
- duplicate lifecycle projection idempotency;
- same revision changed payload/ID conflict;
- revision gap/predecessor mismatch/broker-anchor regression fail closed;
- stale exact historical lifecycle replay never replaces current;
- newer raw broker observation without E5 re-attestation does not synthesize current Position;
- legacy unprofiled Position never becomes restart-authoritative by row order;
- OrderResult append-only observations/current projection do not regress;
- equal observation time conflicting OrderResult fails closed;
- funding same-ID replay, same-ID corruption, same-lineage different-ID conflict;
- persisted TradeResult retains exact `funding_evidence_id` and cannot be rewritten;
- database close/reopen recovers exact open/in-flight graph;
- close/reopen preserves ambiguous/reconciliation-required truth;
- close/reopen recovers exact closed projection + funding + TradeResult IDs/payloads;
- incomplete/conflicting graph fails closed;
- transaction rollback leaves no half-applied current projection;
- existing Strategy Registry/storage tests remain defined and compatible;
- no credentials/provider-private fields/lifecycle release authority introduced.

Use sanitized deterministic fixtures. E6 production must not import E4/E5 implementation classes merely to reconstruct domain truth.

## Writable scope

E6-owned only:

- `src/storage/**`;
- `src/platform/**` only if strictly required for bounded storage/service composition;
- `tests/storage/**`;
- `tests/platform/**` compatibility definitions only if required;
- `docs/platform/**`, `docs/operations/**` if needed;
- E6-specific `status/**` evidence/handoff;
- `coordination/E6/STATUS.md` on the target branch.

Forbidden:

- `contracts/**` / ADR changes;
- E1-E5 production code;
- E7 integration/release files;
- strategy lifecycle expansion beyond the accepted Registry subset;
- dashboard/UI expansion unrelated to durability;
- provider/private API/network/credentials;
- `.github/workflows/**` or GitHub CI/compute;
- PAPER/SHADOW/LIVE authority.

## Executable verification

This is implementation/test-definition work under the hard local-only policy. Unless a separate exact-revision Local Runner action is explicitly approved, record:

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

Do not use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud project execution, Computer Adapter, provider/private APIs or credentials. `NOT_RUN` is not PASS.

## Acceptance

### DONE

- additive E6 durable Paper runtime schema/service is materialized;
- canonical runtime identities/payloads survive database close/reopen exactly;
- E5 profiled Position lifecycle revision/predecessor/identity semantics are persisted mechanically without lifecycle inference;
- open/in-flight/ambiguous/reattestation-required and closed states recover fail-closed;
- immutable/idempotent/conflict semantics are durable;
- funding lineage conflict and TradeResult binding rules are enforced;
- existing early Registry behavior remains compatible;
- deterministic E6 storage/restart test definitions are materialized;
- no shared contract, E4/E5, provider, lifecycle-promotion or release scope is crossed;
- executable verification is approved-local evidence or explicit `NOT_RUN` with exact commands.

### BLOCKED

- accepted shared semantics remain insufficient for safe durable representation/recovery;
- record exact expected-vs-actual evidence and `next_owner = E7`;
- do not invent E6 lifecycle/order authority or last-write-wins workaround.

Do not declare Restart/persistence PASS, Paper E2E PASS, Gate B/PAPER_READY PASS, or any PAPER/SHADOW/LIVE authorization without later E7 review and approved-local evidence.

## Completion / mailbox rule

Commit/push bounded code/tests/evidence/status to `agent/e6-gate-b-paper-runtime-durability-v2-20260824`.

Worker-owned terminal STATUS must be written/pushed to `coordination/E6/STATUS.md` on that target branch, not main.

Then stop. Do not self-start E7 durability/E2E integration, approved-local verification, provider/private work, Gate C, PAPER, SHADOW or LIVE.