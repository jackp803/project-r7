# E5 Current Task

- task_id: `E5-20260824-018`
- issued_at: `2026-08-24T14:56:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e5-gate-b-funding-consumer-20260824`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`, `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`, ADR-0005, ADR-0006, accepted Gate A PASS, accepted protection/close chain PR #37-#50, accepted funding contract PR #51, accepted E4 Paper funding producer PR #52

## Objective

Adapt only the E5-owned `trade-result-v0.1` finalization boundary so it consumes the canonical shared `funding-allocation-v0.1` `FundingAllocationEvidence` object produced by E4 and emits the required funding audit references.

Bounded chain:

```text
accepted E4-authoritative entry/exit Fill + final flat Position truth
+ exact E5 exit/protection authority
+ canonical funding-allocation-v0.1 evidence
-> fail-closed E5 funding validation
-> POSITION_CLOSED / CLOSED only after all closure evidence succeeds
-> canonical trade-result-v0.1 with funding evidence audit binding
```

Stop at E5 canonical consumer/TradeResult adaptation. Do **not** implement E4 funding production, E4 PROTECTION_STOP flat observation, E6 persistence/restart/audit, E7 Paper E2E, provider/private funding lookup, or PAPER/SHADOW/LIVE authorization.

## Accepted prerequisites

```text
PR #49 merge = a9edc5db9f31efb0c4a8a0c33d54766093c70392
E5 authoritative-flat + TradeResult builder = MATERIALIZED / executable NOT_RUN

PR #51 merge = 6950824f6e2e7842718fc29f5e0808f9d8e7b04e
funding-allocation-v0.1 shared contract = ACCEPTED

PR #52 merge = 844395fce0504573b5ee4932e3aca09101998080
E4 local Paper ZERO_CONFIRMED producer = MATERIALIZED / executable NOT_RUN
```

All executable Gate B evidence remains `NOT_RUN`; Gate B remains `BLOCKED`; PAPER remains unauthorized.

## Required inspection before editing

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E5_RISK_POSITION.md`;
- `contracts/README.md`;
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`;
- `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`;
- `docs/adr/ADR-0005*`, `docs/adr/ADR-0006-funding-allocation-evidence-boundary.md`;
- current `src/position/trade_result.py`, state machine and existing position tests;
- accepted E4 `src/execution/funding.py` and PR #52 handoff read-only only to verify the emitted serialized boundary;
- current `status/RELEASE_GATES.md` / accepted PR #50-#52 evidence.

### Contract-first blocker rule

If the accepted funding profile cannot be consumed safely without a new shared serialized field/enum/financial meaning, stop:

```text
BLOCKED / CONTRACT_OR_SEMANTIC_GAP
next_owner = E7
```

Do not modify `contracts/**`, ADRs, E4 code, E6 code, or invent a parallel shared Funding DTO.

## Required behavior

### 1. Canonical shared evidence boundary

For current Gate B finalization, `build_trade_result()` must require one canonical serialized `FundingAllocationEvidence` conforming to:

```text
schema_version = contracts-v0.1
funding_evidence_profile_version = funding-allocation-v0.1
```

The existing E5-private `FundingEvidence` helper is **not** the shared contract. It may remain only as clearly internal/legacy code if needed for migration, but it must not provide a fallback/bypass that can finalize a current Gate B TradeResult without canonical funding evidence.

Do not make E5 production import an E4 implementation class. Consume the shared serialized shape defined by E7.

### 2. Required canonical fields and exact lineage

Validate at minimum all required profile fields:

```text
schema_version
funding_evidence_profile_version
funding_evidence_id
source_kind
source
source_version
source_material_hash
source_record_count
source_complete_through
trade_plan_id
position_id
symbol
interval_start
interval_end
interval_semantics
status
funding_cost
cost_currency
calculated_at
```

Require exact binding:

```text
funding.trade_plan_id == ApprovedTradePlan.trade_plan_id
funding.position_id   == exit_authority.position_id == final Position.position_id
funding.symbol        == ApprovedTradePlan.symbol == final Position.symbol
funding.interval_start == canonical TradeResult.opened_at
funding.interval_end   == canonical TradeResult.closed_at / flat_position_observed_at
funding.interval_semantics == START_INCLUSIVE_END_EXCLUSIVE
```

No `trade_plan_id`-only matching is sufficient.

### 3. Source/profile/completeness validation

Fail closed unless:

- `schema_version` and funding profile version are supported exactly;
- `source_kind` is a profile-supported value (`PAPER_MODEL | BROKER_LEDGER`), with non-empty `source` and `source_version`;
- `source_material_hash` is a canonical SHA-256 digest shape;
- `source_record_count` is a non-negative integer;
- `source_complete_through >= interval_end`;
- `calculated_at >= interval_end`;
- all timestamps are RFC3339 UTC `Z` at the serialized boundary;
- the exact interval is non-empty and matches final position/TradeResult truth.

Do not infer source completeness, provider truth or funding zero inside E5. E4 remains the source authority.

The only currently materialized real Gate B producer is the E4 local `PAPER_MODEL / R7_PAPER_FUNDING_MODEL / paper-zero-funding-v0.1` ZERO_CONFIRMED producer. Structural `INCLUDED` validation may be preserved under the shared profile, but must not be reported as a materialized E4 runtime INCLUDED producer unless such a producer actually exists later.

### 4. ZERO_CONFIRMED / INCLUDED and currency semantics

Preserve the accepted profile exactly:

```text
ZERO_CONFIRMED:
  source_record_count = 0
  funding_cost = 0
  cost_currency = USDT

INCLUDED:
  source_record_count >= 1
  funding_cost = finite signed Decimal-string
  cost_currency = USDT
```

Signed meaning remains:

```text
positive funding_cost = cost
negative funding_cost = credit
```

No implicit currency conversion. Missing evidence, unsupported currency, malformed/non-finite cost, contradictory status/count/cost, partial/incomplete source truth or unknown required semantics must block TradeResult finalization.

### 5. Canonical evidence identity integrity

Recompute and validate `funding_evidence_id` from exactly the 17 profile identity-bearing fields:

```text
schema_version
funding_evidence_profile_version
source_kind
source
source_version
source_material_hash
source_record_count
source_complete_through
trade_plan_id
position_id
symbol
interval_start
interval_end
interval_semantics
status
funding_cost
cost_currency
```

Use sorted compact UTF-8 JSON + SHA-256 + `fundev_` prefix as defined by the contract.

Reject evidence when the supplied ID does not match the canonical material. `calculated_at` is not identity-bearing.

Do not attempt to recompute E4's `source_material_hash` from provider-private/raw source records inside E5; validate its required shape and use the canonical evidence identity/boundary.

### 6. Conflict boundary remains fail-closed without inventing persistence

This task validates one supplied canonical evidence object's internal consistency and identity. Do not invent an E5 persistence store or last-write-wins conflict resolver.

The contract's cross-replay rule remains:

```text
different funding_evidence_id values for the same exact lineage interval
-> reconciliation conflict
-> no finalization until resolved
```

Durable duplicate/conflict discovery is a later E6 persistence/replay responsibility and later E7 integration requirement. Do not claim that system-level conflict detection is implemented in this task merely because one object validates.

### 7. TradeResult audit binding

Every current Gate B `trade-result-v0.1` finalized with canonical funding evidence must emit:

```text
funding_evidence_profile_version = funding-allocation-v0.1
funding_evidence_id = exact consumed canonical evidence ID
funding_evidence_status = exact canonical evidence status
```

For `INCLUDED`, retain exact canonical `funding_cost` under existing serialization. For `ZERO_CONFIRMED`, existing accepted serialization may omit the TradeResult `funding_cost` field or emit zero only if current profile rules allow it; the evidence profile/id references are mandatory so zero remains auditable.

Existing PnL formula remains unchanged:

```text
net_pnl = gross_pnl - total_fees - funding_cost_effective
```

Actual Fill prices already embody realized execution price; do not add a second slippage charge.

### 8. TradeResult deterministic identity

Update deterministic TradeResult identity material so the exact canonical funding evidence binding is represented without making audit-only `calculated_at` change financial identity.

Required properties:

- same entry/exit/authority/funding allocation identity material -> same `trade_result_id`;
- later funding `calculated_at` only, with the same valid `funding_evidence_id`, must not create a different financial TradeResult identity;
- changed `funding_evidence_id`, status or cost material must change TradeResult identity or fail closed as appropriate;
- corrupted funding evidence ID/material must fail before lifecycle closure/result emission.

### 9. Preserve all existing closure safety

Do not weaken any PR #49 behavior:

- `OrderStatus.FILLED != flat Position proof`;
- exact same-position `actual_quantity=0 + CONSISTENT` final truth required;
- flat observation at/after latest exit Fill;
- exact entry OrderRequest identity + Fill binding;
- exact exit/protection authority and Fill lineage;
- quantity conservation;
- partial/under/over-close cannot finalize;
- duplicate/cross-set Fill IDs cannot finalize;
- missing fee cannot become zero;
- unsupported fee currency fails closed;
- `POSITION_CLOSED` occurs only after all evidence validation succeeds;
- E5 does not submit/query/rewrite E4 broker truth.

### 10. No scope absorption

Known separate blocker remains outside this task:

```text
PROTECTION_STOP -> same-position residual/flat Position truth
= BLOCKED / E4 IMPLEMENTATION_GAP
```

Do not modify E4/PaperBroker or hand-construct system-level protection flat truth here.

Do not implement E6 persistence/restart/audit or full Paper E2E.

## Required deterministic test definitions

Add/update E5-owned tests covering at minimum:

- canonical ZERO_CONFIRMED evidence accepted for ordinary EXIT finalization;
- canonical ZERO_CONFIRMED evidence accepted for EMERGENCY_EXIT finalization;
- canonical funding evidence profile/id refs emitted in TradeResult;
- exact E4 PR #52 serialized shape is consumable without importing E4 implementation code into E5 production;
- canonical funding ID is recomputed and mismatch/corruption fails closed;
- exact plan/position/symbol/interval mismatch fails closed;
- unsupported schema/profile/source kind fails closed;
- empty source/source_version fails closed;
- incomplete/stale completeness watermark or premature calculated_at fails closed;
- malformed source hash fails closed;
- ZERO_CONFIRMED count/cost contradiction fails closed;
- INCLUDED signed-cost semantics remain Decimal and fee/PnL formula remains unchanged where represented by valid canonical fixtures;
- unsupported currency fails closed;
- missing canonical funding evidence fails closed and cannot infer zero;
- E5-private legacy FundingEvidence cannot bypass the canonical Gate B boundary;
- calculated_at-only change with same canonical evidence identity does not change TradeResult identity;
- changed funding evidence identity/financial material changes result identity or fails closed;
- all existing authoritative-flat, Fill-lineage, duplicate, quantity, fee and lifecycle tests remain defined.

Use sanitized/fake deterministic fixtures only. E5 production must not import `src.execution.funding`; actual E4 -> E5 callable integration remains a later E7-owned integration definition.

## Writable scope

E5-owned only:

- `src/position/**`;
- `tests/position/**`;
- E5-owned `tests/safety/**` only if required;
- `docs/position/**` only if needed;
- E5-specific `status/**` handoff/evidence;
- `coordination/E5/STATUS.md` on the target branch.

Forbidden:

- `contracts/**` / ADR changes;
- `src/brokers/**` / `src/execution/**`;
- E6 storage/platform;
- E1-E3 production;
- E4 PROTECTION_STOP flat-observer changes;
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
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud execution, Computer Adapter, provider/private APIs, or credentials. `NOT_RUN` is not PASS.

## Acceptance

### DONE

- current Gate B TradeResult builder consumes canonical `funding-allocation-v0.1` evidence rather than relying on the E5-private helper;
- required profile/lineage/interval/completeness/status/cost/currency/identity rules fail closed;
- TradeResult emits exact funding evidence profile/id audit references;
- deterministic TradeResult identity correctly binds canonical funding evidence without depending on `calculated_at` alone;
- PR #49 closure/fee/PnL/lifecycle safety is preserved;
- no E4/E6/E7/provider/release scope is crossed;
- deterministic E5 tests are materialized;
- executable verification is approved-local evidence or explicit `NOT_RUN` with exact commands.

### BLOCKED

- accepted funding profile cannot be safely consumed without a genuine shared semantic change;
- record exact expected-vs-actual evidence and `next_owner = E7`;
- do not invent a workaround or parallel contract.

Do not declare the complete E4->E5 funding system chain, PROTECTION_STOP TradeResult path, Paper E2E, Gate B/PAPER_READY, or any PAPER/SHADOW/LIVE mode PASS.

## Completion / mailbox rule

Commit/push bounded code/tests/evidence/status to `agent/e5-gate-b-funding-consumer-20260824`.

Worker-owned terminal STATUS must be written/pushed to `coordination/E5/STATUS.md` on this target branch, not main.

Then stop. Do not self-start E4 PROTECTION_STOP flat-truth remediation, E6 persistence, E7 Paper E2E/integration, approved-local verification, Gate C, PAPER, SHADOW or LIVE.