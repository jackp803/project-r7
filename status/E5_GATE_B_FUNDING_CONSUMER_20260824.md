# E5 Gate B Canonical Funding Consumer Handoff — 2026-08-24

## Authority / scope

- task_id: `E5-20260824-018`
- agent: `E5`
- target branch: `agent/e5-gate-b-funding-consumer-20260824`
- base main after required fast-forward: `84d48e2da290365f4c896936ee790bc21a38aa5f`
- implementation/test-definition head before this handoff: `0314ea3ba0969580a4594edae18551130af00810`
- shared schema: `contracts-v0.1`
- TradeResult profile: `trade-result-v0.1`
- funding profile: `funding-allocation-v0.1`
- PnL profile: `linear-base-asset-pnl-v0.1`

This task changes only the E5 canonical funding consumer / TradeResult finalization boundary. It does not implement E4 funding production, E4 protection-stop flat observation, E6 persistence/restart/audit, E7 Paper E2E, provider/private funding lookup, or any PAPER/SHADOW/LIVE authority.

## Contract-first disposition

```text
CONTRACT_OR_SEMANTIC_GAP = NO
```

The accepted funding profile and ADR-0006 fully define the provider-neutral serialized evidence needed by E5. Accepted PR #52 already materializes the first E4 local Paper `ZERO_CONFIRMED` producer with the same 19-field serialized shape.

E5 therefore did not modify `contracts/**`, ADRs, E4 code, broker code, or invent a parallel Funding DTO.

## Implemented boundary

```text
accepted E4-authoritative entry/exit Fill + final flat Position truth
+ exact E5 exit/protection authority
+ canonical funding-allocation-v0.1 FundingAllocationEvidence
-> fail-closed E5 funding validation
-> financial calculation
-> existing PositionEvent.POSITION_CLOSED
-> canonical trade-result-v0.1 with funding audit binding
```

`POSITION_CLOSED` remains last. Invalid funding evidence cannot cause lifecycle closure.

## Canonical funding evidence requirement

`build_trade_result()` now requires a serialized mapping with all current profile fields:

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

The old `FundingEvidence` dataclass remains only as an explicitly documented legacy E5-private migration type. It is not accepted by current Gate B `build_trade_result()` and cannot provide a missing-evidence/zero-funding fallback.

E5 production imports no `src.execution.funding` implementation class/function.

## Exact lineage / interval validation

Canonical evidence must bind exactly to:

```text
trade_plan_id = ApprovedTradePlan.trade_plan_id
position_id   = exit authority position_id = final Position.position_id
symbol        = ApprovedTradePlan.symbol = final Position.symbol
interval_start = earliest authoritative included entry Fill.filled_at
interval_end   = final flat Position.broker_state_observed_at
interval_semantics = START_INCLUSIVE_END_EXCLUSIVE
```

The existing final Position check still requires:

```text
same position_id
same symbol/direction
actual_quantity = 0
reconciliation_status = CONSISTENT
broker_state_observed_at >= latest included exit Fill.filled_at
opened_at = earliest included entry Fill.filled_at
```

`OrderStatus.FILLED` is not used as flat proof.

## Source / completeness validation

E5 fails closed unless:

```text
schema_version = contracts-v0.1
funding_evidence_profile_version = funding-allocation-v0.1
source_kind = PAPER_MODEL | BROKER_LEDGER
source/source_version = non-empty canonical strings
source_material_hash = lowercase 64-hex SHA-256 shape
source_record_count = non-negative integer
source_complete_through >= interval_end
calculated_at >= interval_end
all shared timestamps = RFC3339 UTC Z strings
interval_start < interval_end
cost_currency = USDT
```

E5 does not recompute E4 provider/Paper raw `source_material_hash`; it validates its canonical digest shape and consumes the E4-owned assertion through the shared evidence identity.

## Status / cost rules

```text
ZERO_CONFIRMED:
  source_record_count = 0
  funding_cost = "0"
  cost_currency = USDT

INCLUDED:
  source_record_count >= 1
  funding_cost = finite signed canonical decimal string
  cost_currency = USDT
```

Signed meaning is unchanged:

```text
positive = funding cost
negative = funding credit
```

Current materialized E4 Gate B runtime producer is only:

```text
PAPER_MODEL
R7_PAPER_FUNDING_MODEL
paper-zero-funding-v0.1
ZERO_CONFIRMED
```

`INCLUDED` handling in E5 is structural/profile validation only. This task does not claim an E4 runtime INCLUDED producer exists.

## Canonical funding evidence identity

E5 recomputes `funding_evidence_id` using exactly the 17 contract identity-bearing fields:

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

Algorithm:

```text
sorted compact JSON
-> UTF-8
-> SHA-256
-> fundev_<lowercase hex>
```

`calculated_at` is intentionally excluded.

Corrupt/mismatched evidence ID fails before lifecycle closure/result emission.

## TradeResult funding audit binding

Every current Gate B result now emits:

```text
funding_evidence_profile_version = funding-allocation-v0.1
funding_evidence_id = exact consumed canonical funding evidence ID
funding_evidence_status = exact canonical status
```

For `INCLUDED`, `funding_cost` is emitted with the exact accepted signed Decimal meaning. For `ZERO_CONFIRMED`, TradeResult continues to omit optional `funding_cost`; the profile/id/status audit references make zero authority explicit and replayable.

Financial formula is unchanged:

```text
net_pnl = gross_pnl - total_fees - funding_cost_effective
```

No `slippage_cost` is double-subtracted.

## TradeResult identity / idempotency

`trade_result_id` now binds the canonical funding allocation identity material and the required funding audit fields, while excluding `calculated_at`.

Therefore:

```text
same exact closure + same funding allocation identity + later calculated_at only
-> same funding_evidence_id
-> same trade_result_id

changed identity-bearing funding material
-> changed funding_evidence_id
-> changed TradeResult candidate identity
```

This task validates one supplied evidence object only. Durable duplicate/conflict discovery for different evidence IDs sharing one lineage interval remains later E6/E7 scope; no last-write-wins store was invented in E5.

## Existing closure safety preserved

The adapted builder still fails closed on:

- non-flat/unknown/mismatched/reconciliation-required final Position;
- stale flat observation;
- partial/under/over close;
- duplicate or cross-set Fill IDs;
- mixed/cross-plan, cross-position, wrong-side, wrong-role/action evidence;
- entry Fill not bound to exact declared entry OrderRequest;
- quantity conservation failure;
- missing Fill fee;
- unsupported fee currency;
- unsupported/missing canonical funding evidence;
- inconsistent source/interval/status/cost/currency/evidence identity.

`POSITION_CLOSED` remains after all evidence/financial validation.

## Deterministic tests materialized

Updated `tests/position/test_trade_result.py` defines sanitized tests for:

- ordinary EXIT + canonical ZERO_CONFIRMED finalization;
- EMERGENCY_EXIT + canonical ZERO_CONFIRMED finalization;
- structural protection-stop closure compatibility with canonical funding evidence;
- exact PR #52 19-field shape acceptance without E4 funding import in E5 production;
- exact funding evidence ID recomputation/corruption rejection;
- plan/position/symbol/interval mismatch rejection;
- schema/profile/source-kind/source/version rejection;
- completeness/premature calculation rejection;
- malformed source hash rejection;
- ZERO_CONFIRMED count/cost contradictions;
- INCLUDED signed cost/credit PnL semantics using canonical fixtures;
- unsupported funding currency rejection;
- missing evidence rejection;
- legacy private FundingEvidence bypass rejection;
- calculated_at-only replay identity stability;
- changed funding allocation identity changing TradeResult identity;
- authoritative flatness, quantity conservation, duplicate Fill, role, exact entry-request binding, fee and short-PnL behavior preservation;
- no provider-native/credential/persistence/release fields in TradeResult.

These are test definitions only; project code/tests were not executed in this ChatGPT environment.

## Files changed

```text
src/position/trade_result.py
tests/position/test_trade_result.py
status/E5_GATE_B_FUNDING_CONSUMER_20260824.md
coordination/E5/STATUS.md   # terminal branch mailbox update follows
```

No E4/E6/contracts/ADR/release-gate production file is changed.

## Executable verification

```text
local_verification = NOT_RUN
```

Reason: no explicitly PM/Product-Owner-approved Local Runner action pinned to this exact target revision is exposed in this session. Static inspection is not executable PASS evidence.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

`NOT_RUN` is not PASS.

## GitHub compute / security

```text
GitHub Actions / CI = NOT_USED
GitHub-hosted runner = NOT_USED
GitHub-triggered self-hosted compute = NOT_USED
arbitrary cloud project execution = NOT_USED
Computer Adapter = NOT_USED
provider/private API = NOT_USED
credentials = NOT_USED
```

No secrets/provider-native fields were added.

## Separate known blocker / release impact

This task intentionally does not absorb:

```text
PROTECTION_STOP -> same-position residual/flat Position truth
= BLOCKED / E4 IMPLEMENTATION_GAP
```

Nor does it implement E6 persistence/restart/audit or E7 full Paper E2E.

Current impact:

```text
E4 canonical Paper ZERO_CONFIRMED producer = MATERIALIZED / executable NOT_RUN
E5 canonical funding consumer adaptation = MATERIALIZED STATICALLY / this task
PROTECTION_STOP real same-position flat truth = BLOCKED / separate E4 gap
E6 durable Paper runtime/audit = BLOCKED
E7 full Paper E2E = BLOCKED
approved-local Gate B verification = NOT_RUN
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

E5 stops after terminal STATUS for `E5-20260824-018` and does not self-start any next dependency.
