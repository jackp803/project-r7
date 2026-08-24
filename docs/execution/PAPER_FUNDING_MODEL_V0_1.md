# E4 Paper Funding Model — V0.1

## Authority and scope

This document records the exact E4-owned local Paper funding source semantics used by task `E4-20260824-011` to produce canonical `funding-allocation-v0.1` evidence.

It consumes the accepted shared profile without changing it:

- parent schema: `contracts-v0.1`
- evidence profile: `funding-allocation-v0.1`
- shared contract: `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`
- authority ADR: `docs/adr/ADR-0006-funding-allocation-evidence-boundary.md`

This is local Paper source truth only. It is not broker/provider funding truth, does not use credentials or networking, and does not authorize PAPER, SHADOW, or LIVE.

## Registered source

The only source semantics accepted by the V0.1 producer are immutable:

```text
source_kind = PAPER_MODEL
source = R7_PAPER_FUNDING_MODEL
source_version = paper-zero-funding-v0.1
interval_semantics = START_INCLUSIVE_END_EXCLUSIVE
status = ZERO_CONFIRMED
funding_cost = "0"
cost_currency = USDT
source_record_count = 0
```

Model assertions:

```text
zero_assertion = FUNDING_EQUALS_ZERO_FOR_EVERY_INSTANT_IN_EXACT_INTERVAL
completeness_assertion = MODEL_COMPLETE_THROUGH_EXACT_INTERVAL_END
```

The meaning is affirmative:

> For this exact local Paper model version, funding cost is defined as zero for every instant in the requested canonical half-open position interval.

It is **not** inferred from an empty event list, missing provider rows, network unavailability, timeout, absent credentials, or a failed query. Any model/source tuple other than the registered tuple is rejected and produces no canonical evidence.

## Required authoritative inputs

The producer accepts only:

```text
exact parent ApprovedTradePlan
+ exact authoritative final same-position Position
+ calculated_at
```

It validates at minimum:

```text
ApprovedTradePlan.schema_version = contracts-v0.1
ApprovedTradePlan.trade_plan_id is non-empty
ApprovedTradePlan.symbol is non-empty

Position.schema_version = contracts-v0.1
Position.position_id is non-empty
Position.symbol == ApprovedTradePlan.symbol
Position.actual_quantity = 0
Position.reconciliation_status = CONSISTENT
Position.opened_at is RFC3339 UTC Z
Position.broker_state_observed_at is RFC3339 UTC Z
Position.opened_at < Position.broker_state_observed_at
```

If `Position.closed_at` is present, it must equal `broker_state_observed_at`.

The producer never substitutes symbol-level net exposure or `OrderStatus.FILLED` for this exact final Position truth, and it does not emit E5 lifecycle `POSITION_CLOSED`.

## Canonical interval

For this producer:

```text
interval_start = canonical Position.opened_at
interval_end = canonical Position.broker_state_observed_at
interval_semantics = START_INCLUSIVE_END_EXCLUSIVE
source_complete_through = interval_end
```

The interval is therefore:

```text
[interval_start, interval_end)
```

`calculated_at` must be UTC and greater than or equal to `interval_end`.

## Normalized zero-model source material

`source_material_hash` is the lowercase hexadecimal SHA-256 of compact, lexicographically key-sorted UTF-8 JSON containing exactly this normalized E4 source assertion material:

```json
{
  "assertion": "FUNDING_EQUALS_ZERO_FOR_EVERY_INSTANT_IN_EXACT_INTERVAL",
  "completeness_assertion": "MODEL_COMPLETE_THROUGH_EXACT_INTERVAL_END",
  "cost_currency": "USDT",
  "funding_cost": "0",
  "interval_end": "<canonical final Position broker_state_observed_at>",
  "interval_semantics": "START_INCLUSIVE_END_EXCLUSIVE",
  "interval_start": "<canonical final Position opened_at>",
  "position_id": "<exact final Position position_id>",
  "source": "R7_PAPER_FUNDING_MODEL",
  "source_complete_through": "<same exact interval_end>",
  "source_kind": "PAPER_MODEL",
  "source_record_count": 0,
  "source_version": "paper-zero-funding-v0.1",
  "status": "ZERO_CONFIRMED",
  "symbol": "<exact canonical plan/Position symbol>",
  "trade_plan_id": "<exact parent ApprovedTradePlan trade_plan_id>"
}
```

Serialization is:

```python
json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
```

followed by UTF-8 encoding and SHA-256.

Because exact plan/position/symbol/interval lineage and the completeness assertion are inside this material, a changed allocation lineage produces a different source material hash. The hash is not an empty-result hash.

## Canonical evidence identity

`funding_evidence_id` follows shared profile section 10 exactly.

Identity-bearing fields are exactly:

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

The producer serializes only those fields as lexicographically sorted compact JSON, hashes the UTF-8 bytes using SHA-256, and prefixes the lowercase digest with:

```text
fundev_
```

`calculated_at` is intentionally excluded. Re-observing identical immutable allocation material at a later calculation time therefore yields the same `funding_evidence_id`.

The E4 producer does not persist or resolve conflicting evidence. E6 conflict-safe durable storage is later scope; no last-write-wins rule is introduced here.

## Fail-closed behavior

No canonical evidence is emitted when any required fact is invalid or unavailable, including:

- unsupported schema;
- missing/blank plan, position, or source identity;
- plan/Position symbol mismatch;
- nonzero, malformed, NaN, or infinite final Position quantity;
- reconciliation status other than `CONSISTENT`;
- malformed/non-UTC timestamps;
- empty/reversed/zero-length interval;
- `closed_at` conflict when present;
- `calculated_at < interval_end`;
- any unregistered source kind/source/version/assertion/completeness/status/cost/currency/record-count semantics.

There is no generic-source fallback to `ZERO_CONFIRMED`.

## Explicit non-scope

This source does not implement or change:

- E5 TradeResult funding consumer/adaptation;
- E6 persistence/restart/audit;
- PaperBroker close or `PROTECTION_STOP` flat-observation behavior;
- provider/broker funding ledger retrieval;
- Demo/live APIs or credentials;
- PAPER/SHADOW/LIVE authorization;
- release gates.

## Verification state

The task that introduced this producer is implementation/test-definition work under the project's local-only execution policy. If no separately approved exact-revision local runner is available, verification remains `NOT_RUN` and is not PASS evidence.
