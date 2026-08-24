# ADR-0006 — Funding Allocation Evidence Authority Boundary

- Status: `ACCEPTED`
- Date: `2026-08-24`
- Decision task: `E7-20260824-041`
- Authority: E7 Integration / Architecture / System QA / Release Engineer
- Parent contract: `contracts-v0.1`
- Profile: `funding-allocation-v0.1`
- Canonical profile: `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`

## Context

PR #50 / E7-20260824-040 proved that ordinary and emergency close-to-authoritative-flat paths are statically materialized, while final `trade-result-v0.1` finalization remains blocked by an undefined cross-module funding evidence boundary.

The accepted E5 builder contains a private `FundingEvidence` helper, but its own documentation explicitly states that it is an E5-internal validation input rather than a shared/persisted contract. Current E4 Broker/PaperBroker surfaces have no governed funding evidence producer, and E6 has only early Slice 2 Registry persistence.

Allowing E4 or E6 to import the E5-private helper or to invent an undocumented mapping would violate the project's contract-first architecture.

## Decision

Classify the missing funding evidence boundary as:

```text
ADDITIVE_PROFILE_REQUIRED
```

under unchanged:

```text
schema_version = contracts-v0.1
```

Introduce the shared provider-neutral profile:

```text
funding-allocation-v0.1
```

The normative object, validation, interval, identity, conflict and migration rules are defined in `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`.

## 1. Funding source authority belongs to E4

Funding ledger/model truth is execution/account/Paper-source truth.

Therefore:

- E4 owns source acquisition, source completeness, normalization, position-interval allocation and canonical FundingAllocationEvidence emission;
- E5 consumes/validates the canonical evidence and owns final TradeResult/lifecycle interpretation;
- E6 persists/replays/audits immutable evidence and conflicts, but never invents financial truth;
- E7 owns contract/version/integration/release semantics.

E4 may implement the producer as a separate provider-neutral funding-evidence source port rather than forcing the existing minimal Broker interface to change incompatibly. Exact implementation surface remains E4 scope.

## 2. Paper funding requires positive model authority

Gate B Paper work must not require exchange credentials or private APIs.

A local E4-owned Paper funding model may produce canonical evidence only under an explicit immutable model version.

A zero-funding Paper model may emit:

```text
ZERO_CONFIRMED
```

only because the model contract affirmatively proves no funding applies to the entire exact interval. Empty rows, unavailable data or lack of provider access never imply zero.

A Paper model containing scheduled funding events emits `INCLUDED` and aggregates its deterministic event set.

Paper evidence remains Paper evidence; it cannot be relabeled as provider/live funding truth.

## 3. Exact interval is half-open

FundingAllocationEvidence binds exactly to:

```text
interval_start = TradeResult.opened_at
interval_end   = TradeResult.closed_at / flat_position_observed_at
```

with canonical semantics:

```text
[interval_start, interval_end)
```

This assigns a boundary event to at most one adjacent Position interval:

- event at start: included;
- event at end: excluded.

If source/provider event-time semantics cannot be normalized unambiguously to this boundary, canonical final evidence cannot be emitted.

## 4. Final shared evidence has no UNKNOWN shortcut

The shared profile intentionally permits only:

```text
ZERO_CONFIRMED
INCLUDED
```

Unknown, unavailable, incomplete, stale or partially covered source state is non-finalizable. It may exist as domain-local diagnostics, but it cannot be serialized as valid final FundingAllocationEvidence and cannot authorize TradeResult finalization.

This keeps absence distinct from zero.

## 5. Completeness is explicit

Final evidence requires a source-owned completeness watermark:

```text
source_complete_through >= interval_end
```

and a calculation/materialization time at or after the final interval boundary.

`ZERO_CONFIRMED` additionally requires zero applicable source records and exact funding cost zero. `INCLUDED` requires one or more applicable source records.

## 6. Current currency is USDT only

For `linear-base-asset-pnl-v0.1`:

```text
cost_currency = USDT
```

No currency conversion is introduced by this ADR. Unsupported currency fails closed until a separate E7-reviewed conversion profile exists.

Signed-cost meaning remains:

```text
positive = cost
negative = credit
```

## 7. Funding lineage is position/plan/source lineage, not risk authority

The evidence requires:

```text
trade_plan_id
position_id
symbol
exact interval
```

It does not require `risk_decision_id`, `risk_policy_version`, strategy ID or strategy version because the funding source does not own those semantics. E5 validates the parent plan and retains risk/strategy lineage in the final TradeResult.

This avoids forcing E4 to manufacture E5 authority fields merely for persistence convenience.

## 8. Evidence identity is content-derived and immutable

`funding_evidence_id` is a deterministic SHA-256 identity over canonical allocation material, including source/version/material hash, completeness, position/plan/symbol, exact interval, status/cost/currency.

`calculated_at` is observation metadata rather than financial allocation identity.

Rules:

- same immutable allocation material -> same identity;
- changed financial/source/lineage material -> different identity;
- same identity with changed identity material -> corrupt/conflicting evidence;
- different identities for the same exact lineage interval -> reconciliation conflict, never last-write-wins.

Once a durable TradeResult references a funding evidence ID, later conflicting evidence cannot silently rewrite financial history.

## 9. TradeResult audit binding becomes explicit

For current Gate B finalization after domain follow-up implementation, `trade-result-v0.1` consumes exactly one valid `funding-allocation-v0.1` object and records additive audit references:

```text
funding_evidence_profile_version
funding_evidence_id
```

Existing `funding_evidence_status` and `funding_cost` semantics remain unchanged.

No PnL formula changes:

```text
net_pnl = gross_pnl - total_fees - funding_cost_effective
```

Historical/static TradeResult objects are not rewritten. Objects lacking the new audit binding are not current Gate B finalization evidence once the producer/consumer path is adopted.

## 10. E6 persistence is storage authority, not source authority

E6 later stores the evidence exactly as produced, preserves source/material/interval identity, detects duplicates/conflicts, restores it unchanged on restart and binds final TradeResult to the exact evidence ID.

E6 must not:

- infer zero from missing rows;
- call a provider to fill missing evidence;
- recompute a new evidence identity on restart;
- choose conflicting financial truth using last-write-wins.

## 11. Next bounded implementation owner

The shared semantic blocker is resolved by this ADR/profile.

Next implementation owner:

```text
E4
```

Bounded next producer behavior:

```text
exact closed Position lineage + exact interval
-> explicit versioned Paper funding model
-> complete canonical funding-allocation-v0.1 evidence
```

The first Gate B producer should be local Paper-only and require no provider credentials/private API.

After E4 canonical producer materializes, a bounded E5 follow-up adapts `build_trade_result()` to consume the shared object and emit its evidence references. E6 persistence follows after consumer semantics are integrated.

## 12. Separate blocker remains separate

This ADR does not change PaperBroker close observation behavior.

Known independent blocker:

```text
PROTECTION_STOP -> same-position residual/flat Position truth
= BLOCKED / E4 IMPLEMENTATION_GAP
```

It must not be conflated with funding evidence production.

## Compatibility decision

No set-wide schema bump is required. The missing object was previously undefined, and the new audit references are additive. Existing object meanings are unchanged, while consumers requiring current Gate B finalization fail closed when canonical funding evidence is absent.

## Rejected alternatives

### Reuse E5 private FundingEvidence as the contract

Rejected: a private domain validation helper is not a governed cross-module serialization boundary.

### Make E6 the funding producer because it owns persistence

Rejected: persistence does not own broker/Paper financial source truth.

### Treat empty provider/Paper rows as ZERO_CONFIRMED

Rejected: absence without complete source authority is not zero evidence.

### Let E5 manufacture ZERO_CONFIRMED during TradeResult construction

Rejected: E5 owns risk/lifecycle interpretation, not funding source truth.

### Use closed intervals on both ends

Rejected: adjacent positions could both allocate an event on the shared boundary.

### Add automatic non-USDT conversion

Rejected: conversion semantics are not defined by the current PnL profile and would require a separately versioned contract.

## Verification

This is static contract/architecture work only:

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION
```

No Local Runner, project-code execution, GitHub Actions/CI/hosted runner, provider/private API, credential, PAPER, SHADOW or LIVE activity is used as evidence.

## Release impact

```text
funding shared semantic gap = RESOLVED BY CONTRACT
funding canonical producer = IMPLEMENTATION_GAP / next_owner=E4
E5 canonical consumer adaptation = IMPLEMENTATION_GAP / later E5 task
Restart/persistence = BLOCKED / E6 IMPLEMENTATION GAP
PROTECTION_STOP same-position flat truth = BLOCKED / E4 IMPLEMENTATION GAP
Paper E2E / durable TradeResult audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```
