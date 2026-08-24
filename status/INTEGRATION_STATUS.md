# Integration Status

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Current review: `E7-20260824-041` / 2026-08-24  
> Reviewed main: `2754f3f9c0f34e92fdfae26e75d853ec96a24a26`  
> Contract baseline: `contracts-v0.1 / BASELINE`  
> Profiles: `close-v0.1 / trade-result-v0.1 / linear-base-asset-pnl-v0.1 / funding-allocation-v0.1`

## Current integration target

**Gate B / Slice 3 Paper readiness — governed funding allocation evidence boundary**

This task is static contract/architecture work only. No project code/tests, Local Runner, Paper runtime verification, provider/private API, GitHub CI, SHADOW, or LIVE activity was executed.

## Release-gate state

```text
Gate A — RESEARCH_READY = PASS / RESEARCH-INTEGRATION ONLY
Gate B — PAPER_READY    = BLOCKED / NOT YET PASS
Gate C — SHADOW_READY   = BLOCKED / UNCHANGED
Gate D — LIVE_READY     = BLOCKED / UNCHANGED

PAPER / SHADOW / LIVE   = UNAUTHORIZED
project executable verification = NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION
```

## Funding evidence contract decision

PR #50 / E7-040 identified:

```text
funding evidence producer/source
= CONTRACT_OR_SEMANTIC_GAP / next_owner=E7
```

E7-041 resolves that shared semantic gap by materializing:

- `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`;
- profile `funding-allocation-v0.1`;
- `docs/adr/ADR-0006-funding-allocation-evidence-boundary.md`.

Versioning classification:

```text
ADDITIVE_PROFILE_REQUIRED
schema_version = contracts-v0.1
```

No existing execution/PnL semantics are reinterpreted.

## Canonical funding boundary

Provider-neutral path:

```text
E4 Paper/provider funding source truth
-> exact interval completeness + deterministic allocation
-> FundingAllocationEvidence / funding-allocation-v0.1
-> E5 validation + TradeResult finalization
-> E6 immutable persistence / replay / audit
```

Canonical required binding includes:

```text
trade_plan_id
position_id
symbol
interval_start
interval_end
source/source_version
source completeness
status/cost/currency
stable evidence identity
```

Risk-decision/policy and strategy lineage remain TradeResult/E5 authority rather than funding-source fields.

## Exact interval semantics

Funding evidence covers exactly:

```text
[TradeResult.opened_at, TradeResult.closed_at)
```

Serialized:

```text
START_INCLUSIVE_END_EXCLUSIVE
```

An event exactly at opened_at belongs to the position. An event exactly at closed_at does not. Adjacent positions therefore cannot both allocate one boundary funding event.

Provider/model event timing that cannot be normalized unambiguously blocks final evidence.

## Completeness / ZERO_CONFIRMED

Final shared evidence supports only:

```text
ZERO_CONFIRMED
INCLUDED
```

Unknown, unavailable, partial, stale or ambiguous source truth is non-finalizable and cannot be serialized as valid final evidence.

`ZERO_CONFIRMED` requires:

```text
source_record_count = 0
funding_cost = "0"
cost_currency = USDT
source_complete_through >= interval_end
```

No-row results without explicit complete-source authority are not zero evidence.

For Paper mode, an E4-owned versioned local zero-funding model may legitimately emit ZERO_CONFIRMED only because its model semantics affirmatively define funding as zero for the complete exact interval. No provider credentials/private API are required.

## INCLUDED / signed cost

`INCLUDED` requires one or more applicable normalized funding records.

```text
positive funding_cost = cost
negative funding_cost = credit
```

An INCLUDED record set may net to zero while remaining INCLUDED.

Current `linear-base-asset-pnl-v0.1` accepts only:

```text
cost_currency = USDT
```

No conversion profile is introduced.

## Identity / conflict semantics

Canonical evidence identity is SHA-256-derived from immutable allocation material.

```text
same allocation material -> same funding_evidence_id
changed source/financial/lineage material -> different ID
same ID + changed identity material -> invalid/corrupt
different IDs for same exact lineage interval -> reconciliation conflict
```

Conflicts are never last-write-wins. Later evidence cannot silently mutate a durable TradeResult.

## Ownership decision

### E4 — next implementation owner

E4 owns funding source acquisition, completeness, normalization, interval allocation and canonical evidence emission because those facts are broker/account/Paper-source truth.

First bounded implementation should be local Paper-only:

```text
exact position/plan/symbol + exact closed interval
-> explicit versioned Paper funding model
-> funding-allocation-v0.1 evidence
```

No provider/private behavior is required or authorized.

### E5

E5 consumes/validates shared evidence and later adapts `build_trade_result()` to emit:

```text
funding_evidence_profile_version
funding_evidence_id
```

It must not manufacture source truth or ZERO_CONFIRMED.

### E6

E6 later persists/restores evidence unchanged, detects duplicate/conflicting lineage and binds final TradeResult to the exact evidence ID. It does not calculate funding.

### E7

E7 owns contract/version/integration/release semantics.

## TradeResult compatibility

Accepted financial meaning remains unchanged:

```text
net_pnl = gross_pnl - total_fees - funding_cost_effective
```

Current Gate B TradeResult finalization after domain follow-up requires one valid exact canonical funding evidence object.

Additive audit binding:

```text
funding_evidence_profile_version = funding-allocation-v0.1
funding_evidence_id = exact canonical evidence ID
```

Legacy/static TradeResults are not rewritten and do not become current Gate B finalization evidence merely because the new profile exists.

## Existing close-path state

Unchanged from PR #50:

```text
ordinary EXIT close-to-flat
= IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN

EMERGENCY_EXIT close-to-flat
= IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN
```

Their final TradeResult system chain remains blocked until E4 funding producer + E5 canonical consumer adaptation + E6 persistence are materialized.

## Independent PROTECTION_STOP blocker

Unchanged:

```text
PROTECTION_STOP -> same-position residual/flat Position truth
= BLOCKED / E4 IMPLEMENTATION_GAP
```

E7-041 does not modify `src/brokers/**` and does not absorb this dependency.

## Gate B evidence reconciliation

```text
Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path          = NOT_RUN
Drawdown/daily/position/kill-switch                 = NOT_RUN
ordinary/emergency close-to-flat                    = NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
funding shared semantic boundary                    = RESOLVED BY CONTRACT
funding canonical Paper producer                    = IMPLEMENTATION_GAP / E4
E5 canonical funding consumer                       = IMPLEMENTATION_GAP / E5
Restart/persistence                                 = BLOCKED / E6 IMPLEMENTATION_GAP
Paper E2E -> TradeResult + durable audit            = BLOCKED
Gate B                                               = BLOCKED / NOT YET PASS
PAPER                                                = UNAUTHORIZED
```

No executable criterion changes to PASS.

## Safe next dependency order

E7 does not start/assign follow-up work automatically.

Recommended PM sequence:

```text
1. E4 — provider-neutral local Paper funding-allocation-v0.1 producer
2. E5 — adapt build_trade_result() to shared evidence + audit refs
3. E4 — PROTECTION_STOP same-position residual/flat truth
4. E6 — durable Paper Position/Action/Order/Fill/Funding/TradeResult persistence + restart/audit
5. E7 — complete Paper E2E/safety definitions
6. PM-authorized approved-local Gate B verification
```

## Verification / scope

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered compute = NOT_USED
Local Runner = NOT_REQUESTED
Computer Adapter = NOT_USED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
PAPER / SHADOW / LIVE = UNAUTHORIZED
E1-E6 production changes by E7 = NONE
Codex ticket = NONE
```

## Detailed evidence

`status/e7/GATE_B_FUNDING_EVIDENCE_CONTRACT_DECISION_20260824.md`

## Completion

E7-041 resolves only the shared funding evidence contract/architecture gap. E7 does not self-start E4 producer implementation, E5 adapter work, E4 protection-flat remediation, E6 persistence, approved-local verification, Gate C, PAPER, SHADOW or LIVE.
