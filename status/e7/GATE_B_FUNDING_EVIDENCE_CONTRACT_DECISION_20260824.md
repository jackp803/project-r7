# Gate B Funding Allocation Evidence Contract Decision — E7-20260824-041

## Authority / scope

- task_id: `E7-20260824-041`
- target branch: `agent/e7-gate-b-funding-evidence-contract-20260824`
- reviewed main: `2754f3f9c0f34e92fdfae26e75d853ec96a24a26`
- authoritative TASK blob: `be4ad2ef28adcc5b3920121ef22ba05cf0785977`
- parent contract: `contracts-v0.1 / BASELINE`
- close profile: `close-v0.1`
- TradeResult profile: `trade-result-v0.1`
- PnL profile: `linear-base-asset-pnl-v0.1`
- accepted blocker source: PR #50 / `status/e7/GATE_B_TRADE_RESULT_INTEGRATION_REVIEW_20260824.md`
- project executable verification: `NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION`

This task is static contract/architecture work only. No project code/tests, Local Runner, GitHub Actions/CI, hosted runner, Computer Adapter, provider/private API, credentials, PAPER, SHADOW or LIVE activity was executed.

## Terminal decision

```text
funding boundary versioning = ADDITIVE_PROFILE_REQUIRED
parent schema_version = contracts-v0.1
new profile = funding-allocation-v0.1
shared funding semantic gap = RESOLVED BY CONTRACT
next canonical producer owner = E4
E4 Paper funding producer = IMPLEMENTATION_GAP
E5 shared-evidence consumer adaptation = IMPLEMENTATION_GAP
E6 funding persistence/restart/audit = BLOCKED / later implementation
PROTECTION_STOP same-position flat truth = BLOCKED / E4 IMPLEMENTATION_GAP / unchanged
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

No executable status is promoted to PASS.

## Inspected authority surfaces

### Shared contracts

The baseline already establishes:

- Decimal-string financial interchange;
- E4 authority over order/fill/exposure truth;
- E5 authority over lifecycle/risk interpretation and final TradeResult production;
- E6 persistence/display authority without source-semantic ownership;
- explicit `funding_evidence_status = ZERO_CONFIRMED | INCLUDED` and signed funding-cost PnL semantics in `trade-result-v0.1`.

No shared serialized funding allocation evidence object existed.

### E5 current consumer

`src/position/trade_result.py` defines `FundingEvidence` but explicitly labels it:

```text
E5-internal validation input
not a shared/persisted funding contract
```

It validates source version, exact position, exact interval, status and signed cost, but it cannot lawfully become the E4/E6 interchange object by convention.

### E4 current source surface

`src/brokers/base.py` exposes submit/query-order/query-position/query-fills/reconcile/retry only. There is no current funding allocation/evidence port.

Funding ledger/model truth is nevertheless an E4 boundary because E4 owns broker/account/Paper execution-source truth and provider normalization. A separate E4-owned funding evidence source port can be added later without forcing an incompatible change to the existing minimal Broker interface.

### E6 current persistence

`src/storage/README.md` and `src/storage/platform.py` remain early Slice 2 Registry/CANDIDATE persistence only. There is no Paper funding/runtime persistence source or write API. E6 therefore cannot be the funding truth producer merely because it will eventually store the evidence.

## Versioning decision

Classification:

```text
ADDITIVE_PROFILE_REQUIRED
```

No set-wide major bump is required because the serialized funding evidence family was previously undefined. Existing fee/PnL/funding meanings remain unchanged. New current-Gate-B finalization requires explicit support for `funding-allocation-v0.1`; legacy/static objects remain historical but are not rewritten or upgraded in place.

## Canonical object

New profile:

`contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`

Canonical object:

```text
FundingAllocationEvidence
```

Required evidence binds:

```text
schema/profile
stable funding_evidence_id
source_kind / source / source_version
source_material_hash / record count / completeness watermark
trade_plan_id
position_id
symbol
exact interval_start / interval_end
START_INCLUSIVE_END_EXCLUSIVE
ZERO_CONFIRMED | INCLUDED
signed funding_cost
USDT cost currency
calculated_at
```

## Exact interval semantics

Canonical interval:

```text
[opened_at, closed_at)
```

with:

```text
interval_start = TradeResult.opened_at
interval_end = TradeResult.closed_at = flat_position_observed_at
```

Start is inclusive and end is exclusive. This prevents an event exactly on a shared adjacent-position boundary from being allocated to both positions.

If a source cannot normalize event-time ownership to this boundary without ambiguity, it cannot emit final evidence.

## ZERO_CONFIRMED semantics

`ZERO_CONFIRMED` is a positive authoritative assertion, not row absence.

Required:

```text
source_record_count = 0
funding_cost = "0"
cost_currency = USDT
source_complete_through >= interval_end
```

A failed query, missing page, incomplete cache, unavailable provider, unversioned model or accidental empty result cannot become ZERO_CONFIRMED.

For Paper mode, E4 may later implement a versioned local zero-funding model. Such a model may emit ZERO_CONFIRMED only because its immutable model semantics explicitly state that no funding is applied over the complete requested interval. No credentials/private API are needed.

## INCLUDED semantics

`INCLUDED` requires one or more normalized applicable funding records:

```text
source_record_count >= 1
funding_cost = finite signed Decimal string
cost_currency = USDT
```

Positive cost means cost; negative means credit. An INCLUDED event set may net to exactly zero and still remains INCLUDED.

## Completeness / unknown behavior

The shared final profile intentionally has no UNKNOWN/PARTIAL/INCOMPLETE state.

If source data are unavailable, partial, stale, ambiguous or unsupported, the producer emits no valid final FundingAllocationEvidence object and E5 cannot finalize TradeResult.

Final evidence additionally requires:

```text
source_complete_through >= interval_end
calculated_at >= interval_end
```

## Identity / conflict semantics

Canonical `funding_evidence_id` is SHA-256-derived from stable allocation material. Identity-bearing material includes source/version/material hash, completeness, plan/position/symbol, exact interval, status/cost/currency. `calculated_at` is audit observation metadata and is excluded from the financial allocation identity.

Rules:

```text
same immutable allocation material -> same ID
changed material -> different ID
same ID + changed identity material -> corrupt/conflict
different IDs for same exact lineage interval -> reconciliation conflict
```

No last-write-wins financial correction is allowed. A durable TradeResult referencing one funding evidence ID cannot be silently rewritten by later conflicting evidence.

## Lineage decision

Required:

```text
trade_plan_id
position_id
symbol
exact interval
```

Not required on the funding evidence object:

```text
risk_decision_id
risk_policy_version
strategy_id
strategy_version
```

Those are E5/TradeResult authority lineage, not funding-source truth. Requiring E4 to manufacture them would invert ownership. E5 validates the exact parent ApprovedTradePlan separately.

## TradeResult compatibility

After later producer/consumer implementation, current Gate B `trade-result-v0.1` finalization consumes one exact canonical funding evidence object and emits additive audit references:

```text
funding_evidence_profile_version = funding-allocation-v0.1
funding_evidence_id = exact consumed evidence ID
```

Existing status/cost semantics remain unchanged:

```text
TradeResult.funding_evidence_status == evidence.status
INCLUDED -> TradeResult.funding_cost == evidence.funding_cost
ZERO_CONFIRMED -> effective funding cost = 0
```

PnL formula remains:

```text
net_pnl = gross_pnl - total_fees - funding_cost_effective
```

A later bounded E5 task must adapt `build_trade_result()` to consume the shared shape and emit the audit references. This E7 task does not modify E5 code.

## Producer / consumer / persistence ownership

### E4 — next implementation owner

E4 owns source acquisition/completeness/allocation and canonical evidence emission.

First bounded Gate B behavior should be a local Paper-only funding source/model:

```text
exact closed position lineage + exact interval
-> explicit versioned Paper funding model
-> complete funding-allocation-v0.1 evidence
```

No provider credential/private API is required or authorized.

### E5

Validates/consumes the canonical object and finalizes TradeResult. E5 cannot manufacture source truth or ZERO_CONFIRMED.

### E6

Persists/replays/audits the immutable evidence and conflicts. E6 does not infer zero, query providers, change source facts or recompute identity on restart.

### E7

Owns profile/version/integration/release semantics.

## Persistence / restart expectations

Later E6 storage must durably preserve:

- canonical evidence bytes/fields;
- stable funding_evidence_id;
- exact lineage key;
- source/version/material hash;
- exact interval/completeness/status/cost/currency;
- idempotent replay;
- explicit conflicting-evidence state;
- final TradeResult -> exact funding evidence relationship.

Restart must restore the accepted immutable object rather than recalculate it.

## Static example coverage

The canonical contract contains non-executable serialized/static examples for:

- valid ZERO_CONFIRMED exact interval;
- valid INCLUDED positive cost;
- valid INCLUDED negative credit;
- same material -> same identity relation;
- material change -> different identity/conflict relation;
- unknown source, interval mismatch, position/plan/symbol mismatch, unsupported currency, malformed cost and contradictory duplicate evidence failing closed.

Symbolic `<derived-id>` values are used intentionally because no code is executed in this static task.

## Separate blocker unchanged

PR #50 independently found:

```text
PROTECTION_STOP -> same-position residual/flat Position truth
= BLOCKED / E4 IMPLEMENTATION_GAP
```

E7-041 does not modify `src/brokers/**` and does not absorb this work.

## Release reconciliation

Preserved:

```text
Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path = NOT_RUN
Drawdown/daily/position/kill-switch = NOT_RUN
ordinary EXIT close-to-flat = NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
EMERGENCY_EXIT close-to-flat = NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
Restart/persistence = BLOCKED
Paper E2E / durable TradeResult audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

Changed only:

```text
funding evidence shared boundary
CONTRACT_OR_SEMANTIC_GAP
-> RESOLVED BY CONTRACT

funding canonical producer
-> IMPLEMENTATION_GAP / next_owner=E4
```

## Verification / security

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION
Local Runner = NOT_REQUESTED
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered project compute = NOT_USED
Computer Adapter = NOT_USED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
PAPER / SHADOW / LIVE = UNAUTHORIZED
E1-E6 production changes by E7 = NONE
Codex ticket = NONE
```

## Completion

E7 completes only the shared funding evidence contract/architecture task. It does not self-start E4 funding producer implementation, E5 adapter work, E4 PROTECTION_STOP flat-truth remediation, E6 persistence, approved-local verification, Gate C, PAPER, SHADOW or LIVE.
