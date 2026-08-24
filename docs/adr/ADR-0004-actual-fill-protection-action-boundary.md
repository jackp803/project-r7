# ADR-0004 — Actual-Fill Protection Action and Execution Boundary

- Status: `ACCEPTED`
- Date: `2026-08-24`
- Decision task: `E7-20260824-028`
- Authority: E7 Integration / Architecture / System QA / Release Engineer
- Parent contract: `contracts-v0.1`
- Profile: `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md` / `protection-v0.1`

## Context

Gate B static preflight identified the missing Slice 3 chain:

```text
actual fill/open exposure
-> E5 protection authorization
-> E4 executable protection request
-> broker truth
-> E5 lifecycle verification/failure handling
```

E5 task `E5-20260824-008` then stopped correctly on a shared semantic blocker: the parent `PositionAction` contract requires protective quantity to follow actual filled/open quantity but does not serialize that quantity, its canonical unit/profile, the exact ApprovedTradePlan/RiskDecision lineage, or executable protection bounds. The parent `OrderRequest` simultaneously requires `trade_plan_id` while permitting authorization by an E5 PositionAction without defining the immediate authorization reference.

Allowing E5 or E4 to invent private cross-module fields would violate the contract-first architecture and could permit quantity/unit ambiguity or protection-bound loosening.

## Decision

Introduce additive executable object profile:

```text
protection-v0.1
```

under the unchanged parent:

```text
schema_version = contracts-v0.1
```

The canonical field-level definition is `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`.

## 1. Authority remains separated

- E4 remains authoritative for broker order/fill/open-exposure truth.
- E5 remains authoritative for risk decisions, protective requirements, and lifecycle interpretation.
- E5 issues executable protection authority only through a profiled `PositionAction.PROTECT`.
- E4 validates and mechanically translates that action; it does not choose protection quantity, stop/target bounds, or policy.

## 2. Actual quantity is exact known exposure

For ordinary initial protection, E5 must use a `CONSISTENT` normalized Position observation with positive known `actual_quantity`.

The protection quantity is exactly the current canonical open quantity observed by E4, including a partial fill. It is not the entry requested quantity and is not automatically the full approved plan quantity.

The canonical quantity uses the existing `base-asset-v0.1` profile. Provider-native contract counts remain E4 adapter facts.

If actual open exposure is unknown, unreconciled, non-positive, incompatible, or exceeds the parent ApprovedTradePlan maximum approved quantity, ordinary `PROTECT` fails closed. Over-approved exposure is an exceptional reconciliation/emergency condition; the parent plan is not silently expanded.

## 3. Protection bounds remain parent-plan authority

A `protection-v0.1` PositionAction binds to exact:

- `trade_plan_id`;
- `risk_decision_id`;
- `risk_policy_version`;
- canonical position observation;
- actual protection quantity;
- parent `protection_instruction` stop/optional target/max-hold values.

For `PROTECT`, the action protection instruction must equal the parent ApprovedTradePlan values. The action cannot loosen or invent them.

## 4. Initial profile is stop-protection only

`protection-v0.1` makes only `PositionAction.action=PROTECT` executable.

The existing shared `MODIFY_PROTECTION` action remains in the baseline vocabulary but is not executable under this profile. A later profile must define side-aware monotonic tightening semantics before ordinary modification can execute. A modification that would loosen a bound requires a new explicitly authorized E5 decision/profile.

The V0.1 E4 mapping creates one canonical reduce-only protective stop request:

```text
LONG position  -> SELL
SHORT position -> BUY
order_role     = PROTECTION_STOP
order_type     = STOP_MARKET
quantity       = exact E5-authorized actual canonical open quantity
stop_price     = exact approved stop_level
reduce_only    = true
```

`target_level` and `max_hold_seconds` remain bound E5 lifecycle facts; this ADR does not authorize E4 to invent a take-profit order, OCO linkage, or exit timer.

## 5. OrderRequest authorization lineage is explicit

For a position-action request, the parent `trade_plan_id` remains required as immutable plan lineage. The profile adds the immediate authorization identity and related audit binding:

- `authorization_type=POSITION_ACTION`;
- `position_action_id`;
- `position_id`;
- `risk_decision_id`;
- `order_role=PROTECTION_STOP`.

Thus `trade_plan_id` is no longer ambiguous: it identifies the parent plan while `position_action_id` identifies the immediate E5 executable authority.

Entry-path requests remain unchanged.

## 6. E4 validates rather than decides

Before translation E4 must validate, directly or through an authoritative equivalent lookup:

```text
protection-v0.1 PositionAction
+ exact ApprovedTradePlan
+ exact current E4-normalized Position truth
```

Mismatched/stale/expired/unreconciled inputs are rejected. E4 may not substitute a different quantity, side, stop, target, or risk policy.

Provider translation remains downstream and provider-specific. OKX `sz`, trigger fields, and contract counts do not become E5/shared quantities.

## 7. Lifecycle verification is distinct from submission

Creating a PositionAction, preparing an OrderRequest, or calling submit does not imply protection is verified.

The position remains `OPEN_UNPROTECTED` until broker truth establishes the exact protective request is active/effective with no reconciliation ambiguity and E5 consumes that evidence.

Only then:

```text
OPEN_UNPROTECTED + PROTECTION_VERIFIED -> OPEN_PROTECTED
```

Definitive protection failure preserves:

```text
OPEN_UNPROTECTED + PROTECTION_FAILED -> EMERGENCY
```

Previously verified protection loss preserves:

```text
OPEN_PROTECTED/PROFIT_PROTECTED + PROTECTION_LOST -> EMERGENCY
```

Unknown broker/order/position truth never counts as `PROTECTION_VERIFIED`.

## Compatibility decision

No set-wide version bump is required.

The parent contract already permits PositionAction-authorized E4 requests and already states that protective quantity follows actual exposure. The missing executable shape was underspecified, not conflicting. New fields are profile-gated and additive.

Legacy objects:

- keep their original historical/research/audit meaning;
- are not rewritten in place;
- do not become executable-protection eligible by inference;
- fail closed when `protection-v0.1` is required.

Existing `entry-v0.1` and `base-asset-v0.1` meanings are unchanged.

## Producer / consumer impact

### E5

Next bounded producer task may implement:

```text
known CONSISTENT Position observation + exact ApprovedTradePlan
-> protection-v0.1 PositionAction.PROTECT
```

No provider metadata or provider contract sizing belongs in E5.

### E4

After E5 materializes the producer shape, next bounded consumer task may implement:

```text
PositionAction + parent ApprovedTradePlan + current Position truth
-> deterministic protection OrderRequest
```

No risk selection or bound loosening belongs in E4.

### E7

After both exist, E7 integration/safety definitions must prove partial-fill quantity, exact lineage, no bound loosening, submit-vs-verified lifecycle distinction, failure/emergency behavior, reconciliation, and idempotency.

## Rejected alternatives

### Private E5 protection DTO

Rejected because E4 must consume it, making it a de facto undocumented shared contract.

### Let E4 derive quantity from entry requested quantity

Rejected because partial fills make requested quantity different from actual exposure.

### Let E4 fetch Position and choose protection quantity independently

Rejected because E4 may verify broker truth but must not become the risk/protection authority.

### Reuse only `trade_plan_id` as OrderRequest authorization identity

Rejected because it cannot identify the exact post-fill PositionAction authorization.

### Make MODIFY_PROTECTION executable immediately

Rejected because side-aware monotonic tightening semantics are not yet defined and guessing could widen loss risk.

### Set-wide contract major bump

Rejected as disproportionate. Existing meanings are preserved and the new execution capability fails closed when the profile is absent.

## Verification

This is a static architecture/contract decision.

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION
```

No GitHub Actions/CI/hosted runner, Local Runner execution, provider request, Paper runtime, SHADOW, or LIVE activity was used.

## Release impact

This ADR resolves the shared semantic blocker only.

```text
actual-fill protection contract blocker = RESOLVED BY CONTRACT
Required protection follows actual filled quantity = BLOCKED pending E5/E4 implementation + local evidence
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
provider/private API = NOT AUTHORIZED
```
