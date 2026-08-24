# E5 Gate B Actual-Fill Protection Boundary — Blocker Evidence

- task_id: `E5-20260824-008`
- agent: `E5`
- state: `BLOCKED`
- blocker: `CONTRACT_OR_SEMANTIC_GAP`
- target_branch: `agent/e5-gate-b-fill-protection-20260824`
- reviewed_main: `cd0313fd268edb2e1a532c635713f4f77249ab54`
- contract_set: `contracts-v0.1`
- execution_profile: `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`
- next_owner: `E7`

## Objective reviewed

The assigned boundary is:

```text
actual execution fill/open quantity
-> exact provider-neutral E5 protection quantity/action
```

The action must preserve the already-approved E5 stop/target/risk bounds, use actual filled/open exposure rather than requested/approved entry quantity, and remain provider-neutral.

## Static inspection result

Implementation must stop before production changes because the current E7-owned shared contract does not define a sufficient executable/provider-neutral `PositionAction` payload for this boundary.

The existing contract states the correct invariant:

```text
protective quantity is based on actual filled/open quantity
```

but the serialized `PositionAction` contract currently defines only:

```text
schema_version
position_action_id
position_id
action
reason_codes
risk_policy_version
created_at
```

with actions including `PROTECT` and `MODIFY_PROTECTION`.

That is insufficient to serialize the exact action this task requires.

## Exact missing semantics

### 1. No protective quantity field or equivalent binding

There is no canonical `PositionAction` field that carries the actual protection quantity, nor a normative rule that allows E4 to derive that quantity by dereferencing a specific `Position.actual_quantity` observation.

Producer/consumer impact:

- E5 cannot serialize `PROTECT` with the exact actual filled/open quantity.
- E4 cannot mechanically execute the exact E5-authorized quantity without inventing a private mapping.
- A partial fill versus full fill cannot be distinguished in the action payload itself.

### 2. No canonical quantity-profile semantics on PositionAction

`base-asset-v0.1` defines canonical BTC quantity semantics for ApprovedTradePlan / OrderRequest / OrderResult / Fill / Position / TradeResult, but it does not define a profiled quantity field on `PositionAction`.

Producer/consumer impact:

- E5 cannot state, in the shared action object, that protection quantity is canonical `BASE_ASSET / BTC` rather than provider-native contracts.
- E4 would have to guess units or rely on out-of-band assumptions, which violates contract-first integration.

### 3. No protection-bound payload or approved-plan binding

Current `PositionAction` has no shared field for the already-approved protection bounds, such as the approved stop/target/max-hold semantics already present in `ApprovedTradePlan.protection_instruction`, and it has no required `trade_plan_id` / `risk_decision_id` reference that normatively binds the action back to those approved bounds.

Producer/consumer impact:

- E5 cannot prove that a post-fill `PROTECT` action preserves the approved stop/target bounds.
- E4 cannot mechanically distinguish an E5-authorized original protection bound from a loosened or invented bound based only on the current PositionAction envelope.

### 4. E4 public execution model has no PositionAction translation path

Current E4 public execution code exposes entry-plan translation only:

```text
ApprovedTradePlan -> ExecutionGateway.prepare_entry_order() -> OrderRequest
```

`src/execution/models.py` has no public `PositionAction` model and no protection-action request model. `OrderRequest` requires `trade_plan_id`; the shared rule says requests may also be traceable to an E5-authorized position action, but no `position_action_id` reference/conditional shape is currently defined in the executable model.

Producer/consumer impact:

- even if E5 invented a local protection-action dictionary, current E4 has no authoritative shared consumer shape for it;
- implementing a private E5 payload now would create undocumented cross-role coupling and force the later E4 task to reverse-engineer E5 assumptions.

## Existing semantics that are sufficient and remain unchanged

The current lifecycle state machine already safely represents:

```text
PENDING_ENTRY + ENTRY_FILL_OBSERVED -> OPEN_UNPROTECTED
OPEN_UNPROTECTED + PROTECTION_VERIFIED -> OPEN_PROTECTED
OPEN_UNPROTECTED + PROTECTION_FAILED -> EMERGENCY
OPEN_PROTECTED/PROFIT_PROTECTED + PROTECTION_LOST -> EMERGENCY
unknown state -> RECONCILIATION_REQUIRED
```

Therefore the lifecycle invariant is not the blocker. The missing piece is the shared action payload/traceability semantics required between E5 and E4.

The current execution/fill models also correctly distinguish requested quantity from actual filled quantity. That fact is sufficient as E5 input evidence, but not sufficient to serialize the resulting protection authorization.

## Why E5 did not implement a private workaround

A local E5 dataclass/dict such as a speculative object containing `quantity`, `stop_level`, `target_level`, or provider-neutral execution fields would become a new cross-module contract because E4 must consume it.

That is prohibited by:

- `agents/README.md` contract-first rule;
- E5 role contract, which assigns shared contract authority to E7;
- this TASK's explicit contract-first blocker rule.

No production/test semantics were added merely to make the task appear complete.

## Required E7 follow-up

E7 needs to define an accepted shared/provider-neutral representation sufficient for E5 -> E4 protection authorization. At minimum, the contract must unambiguously define the semantics for:

1. exact protective quantity derived from known actual open/fill exposure;
2. canonical quantity unit/profile/asset or an equivalent unambiguous binding;
3. binding to the approved risk/protection bounds without allowing stop/risk loosening;
4. traceability from the protection action into the E4 executable request;
5. fail-closed handling when actual exposure is unknown, unreconciled, non-positive, or greater than the E5-approved maximum.

This evidence intentionally does not prescribe final E7 field names or a schema design.

## Scope confirmation

Changed for this task:

- `status/E5_GATE_B_FILL_PROTECTION_BLOCKER_20260824.md`
- `coordination/E5/STATUS.md` is updated separately.

Not changed:

- `src/risk/**`
- `src/position/**`
- `tests/**`
- `src/execution/**`
- `src/brokers/**`
- `contracts/**`
- ADRs
- E6 persistence
- provider/private APIs
- PAPER/SHADOW/LIVE authority

## Executable verification

```text
local_verification = NOT_RUN
```

Reason: the task stopped on a static contract/semantic blocker before implementing executable project-code changes. No approved exact-revision AgentBridge action was used, and GitHub/cloud execution is forbidden.

Exact future Windows PowerShell commands after E7 resolves the contract and a bounded implementation task materializes code/tests:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

No PASS is claimed from static inspection.

## Release impact

```text
Required protection follows actual filled quantity = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER = UNAUTHORIZED
```

No Gate B criterion is promoted by this blocker report.

## Completion

E5 stops on `BLOCKED` for `E5-20260824-008` and does not begin E4 protection execution, protection-failure orchestration, persistence, TradeResult, Paper E2E, provider/private work, or any later Gate B phase.
