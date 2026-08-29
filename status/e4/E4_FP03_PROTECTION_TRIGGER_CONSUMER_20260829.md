# E4 FP-03 Protection Trigger Consumer Handoff — E4-20260829-024

## Handoff

**From:** E4 / Trading Execution / Broker Integration Engineer  
**To:** PM / E7  
**Branch:** `agent/e4-fp03-protection-trigger-consumer-20260829`  
**Source/tests revision before this handoff:** `0549096671806526f8e3fc85c78736201202ea09`  
**Baseline main:** `9bd9c52e255ac583ae607d8d72cd8107e95166f4`  
**Date:** `2026-08-29`

## 1. Objective

Implement only the E4 execution-consumer/binding side of FP-03 `protection-trigger-validity-v0.1`, without provider calls, credentials, provider mutation, E5 policy changes, FP-02 expansion, FP-15/REPLACE execution, runtime start, Gate D, or LIVE.

## 2. Implementation

Added `src/execution/protection_trigger.py` with these E4-owned boundaries:

- `validate_protection_trigger_create_evidence(...)`
- `prepare_trigger_validated_protection_order(...)`
- `require_provider_trigger_basis_compatibility(...)`
- `ProtectionTriggerConsumerError`

The consumer uses the accepted E5 public trigger-validity surface directly:

- `validate_protection_trigger_validity_evidence(...)`
- `protection_trigger_validity_evidence_is_current(...)`

It does not duplicate/fork the shared evidence schema or reason vocabulary.

## 3. Shared profiles consumed

- `contracts-v0.1`
- `protection-v0.1`
- `protection-trigger-validity-v0.1`
- current Position lifecycle projection/execution-evidence freshness semantics as authority context

Contracts changed: `NONE`.

## 4. Binding / currentness / fail-closed behavior

Before provider-neutral protection translation, E4 requires:

- exact `protection-trigger-validity-v0.1` profile;
- structurally valid deterministic evidence identity through the accepted E5 validator;
- `validity_status=ACTIONABLE`;
- exact `reason_codes=[PROTECTION_TRIGGER_ACTIONABLE]`;
- exact current `position_action_id`;
- exact current `position_id` and Position observation anchor;
- exact Position/action side and canonical symbol;
- `order_role=PROTECTION_STOP`;
- `protection_operation=CREATE`;
- exact action stop level;
- exact broker-Position or lifecycle-projection authority binding;
- exact current E1 market evidence through the accepted E5 currentness comparison.

Missing, unsupported, malformed, `FAIL_CLOSED`, binding-mismatched, newer-Position, newer-market, or otherwise non-current evidence fails closed.

Unchanged breached/failed evidence remains non-actionable even when wall-clock time advances. E4 does not choose an E5 lifecycle response from the evidence handoff category.

After FP-03 evidence passes, existing `validate_protection_authority(...)` remains mandatory, preserving existing protection-v0.1 quantity, reconciliation, expiry, protection-bound, and idempotency semantics.

`REPLACE` remains non-executable under this baseline. FP-15 is unchanged/separate.

## 5. Provider trigger-basis non-inference

Shared:

```text
trigger_reference_semantic = LAST_PRICE
```

is treated only as shared pre-mutation geometry evidence. It is not converted into or treated as proof of OKX/provider-native `triggerPxType` or an equivalent provider parameter.

`prepare_trigger_validated_protection_order(...)` returns only the existing canonical provider-neutral `OrderRequest`; this is not provider-mutation authority.

`require_provider_trigger_basis_compatibility(...)` intentionally has no positive proof path in FP-03 because the current repository has no accepted applicable provider trigger-basis capability proof object. Arbitrary caller booleans, mappings, strings, callbacks, or shared LAST_PRICE evidence cannot manufacture that authority. The guard remains fail closed with `PROVIDER_TRIGGER_BASIS_NOT_PROVEN`; unsupported shared trigger semantics fail `PROVIDER_TRIGGER_BASIS_INCOMPATIBLE`.

A future separately scoped E4 provider capability boundary must supply its own accepted proof semantics. This task does not implement the broader FP-02 capability matrix.

## 6. Test definitions added

`tests/execution/test_protection_trigger_consumer.py` defines credential-free deterministic coverage for:

- matching ACTIONABLE CREATE evidence accepted by the E4 consumer;
- missing/unsupported evidence fail closed;
- breached FAIL_CLOSED evidence cannot authorize create or time-only retry;
- `E4_BINDING_MISMATCH` for different action ID, Position ID, side, symbol, stop, role, operation, and Position authority reference;
- newer market/Position truth invalidates prior evidence;
- REPLACE remains non-executable;
- existing protection quantity, expiry and deterministic idempotency remain enforced;
- provider-neutral request contains no provider-native trigger-basis field;
- shared LAST_PRICE plus arbitrary caller assertions cannot authorize provider trigger basis;
- unsupported provider/native basis semantics fail closed;
- no provider client, request, credentials or mutation are required/invoked by these definitions.

The default test PositionAction is constructed through E5's accepted `build_protect_position_action(...)` public surface so its deterministic action identity is canonical rather than manually asserted.

## 7. Local verification

Result: `NOT_RUN`.

Reason: this E4 conversation has no Product-Owner-approved local/non-GitHub runner action. `NOT_RUN != PASS`.

Intended approved-local Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.execution.test_protection_trigger_consumer -v
python -m unittest tests.execution.test_protection -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

No GitHub Actions/CI/hosted/GitHub-triggered compute was used.

## 8. Execution / security evidence

```text
provider requests = 0
provider/private access = NOT_USED
credentials = NONE / NOT_READ / NOT_REQUESTED
provider/account mutation = 0
submit/place/cancel/amend/close order actions = 0
SHADOW runtime = NOT_STARTED
PAPER runtime = NOT_STARTED
capital exposure = NONE
Gate D / LIVE = NOT_AUTHORIZED / NOT_STARTED
```

No secrets or provider payloads were added.

## 9. Remaining dependencies

- E5 FP-03 producer/policy remains merged as an unverified executable candidate; its prior local verification is `NOT_RUN`.
- E4 FP-03 consumer/binding implementation is source-complete but locally `NOT_RUN` in this conversation.
- FP-03 overall executable qualification is not established.
- A fresh combined E7 approved-local credential-free requalification is required after PM review.
- FP-02 provider/action-role capability-matrix work remains separate.
- FP-15 protection REPLACE/MODIFY_PROTECTION remains separate and non-executable.
- Provider/private verification remains separately governed and is not authorized by this task.

## 10. Result classification

`PARTIAL` — bounded implementation/test definitions are complete, but required approved-local executable verification is unavailable in this conversation and therefore remains `NOT_RUN`.
