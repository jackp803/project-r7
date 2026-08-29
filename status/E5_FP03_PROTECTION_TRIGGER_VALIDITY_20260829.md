# E5 FP-03 Protection Trigger Validity Handoff — 2026-08-29

- task_id: `E5-20260829-029`
- agent: `E5`
- target_branch: `agent/e5-fp03-protection-trigger-validity-20260829`
- base_main_revision: `3c94c12ff96c61e176d523790919c250c19cacd5`
- implementation_revision_before_handoff: `7737c46fd05b11d95d2080d2cfbe0b480d110fee`
- result: `PARTIAL / IMPLEMENTATION COMPLETE / LOCAL VERIFICATION NOT_RUN`
- parent_schema: `contracts-v0.1`
- protection_profile: `protection-v0.1 / unchanged`
- trigger_validity_profile: `protection-trigger-validity-v0.1`
- shared_contract_changes: `NONE`
- ADR_changes: `NONE`

## Implemented E5 boundary

```text
exact current Position authority
+ exact E5 protection-v0.1 PositionAction.PROTECT / stop authority
+ exact parent ApprovedTradePlan for protection-action validation
+ E1 canonical current MarketSnapshot
+ E1-attested FRESH | STALE | UNKNOWN classification
+ explicit post-evidence UTC evaluated_at
-> canonical ProtectionTriggerValidityEvidence
```

Implementation:

- `src/position/protection_trigger_validity.py`
  - `build_protection_trigger_validity_evidence(...)`
  - `validate_protection_trigger_validity_evidence(...)`
  - `stable_protection_trigger_validity_id(...)`
  - `protection_trigger_validity_is_actionable(...)`
  - `protection_trigger_validity_evidence_is_current(...)`
- `src/position/__init__.py` exports the bounded E5 FP-03 surface.

No provider client, provider parameter translation, provider mutation, order submission, lifecycle transition selection, persistence or new shared DTO was added.

## Contract behavior materialized

V0.1 supports only shared `trigger_reference_semantic=LAST_PRICE`, copied from the exact E1 `MarketSnapshot.last_price`.

Strict geometry:

```text
LONG  stop < last_price -> ACTIONABLE
SHORT stop > last_price -> ACTIONABLE
LONG  stop >= last_price -> FAIL_CLOSED / TRIGGER_ALREADY_BREACHED
SHORT stop <= last_price -> FAIL_CLOSED / TRIGGER_ALREADY_BREACHED
```

Equality is fail closed.

The producer consumes E1-attested freshness classification and does not introduce another numerical freshness threshold. `STALE` and `UNKNOWN`, non-healthy or unusable market truth are non-actionable.

Temporal ordering is fail closed unless `evaluated_at` is at or after the bound market receipt, Position observation and PositionAction creation boundaries.

The producer reuses existing `validate_protection_action(...)` so current `protection-v0.1` lineage, action identity, exact parent stop/target/max-hold bounds, actual exposure quantity, expiry and no-stop-widening rules remain authoritative. Trigger validity cannot make a forged/loosened protection action executable.

Current baseline `REPLACE` is non-actionable because no executable `MODIFY_PROTECTION` profile exists; this task does not create one.

## Stable reason and handoff behavior

Failure reasons are emitted only from the accepted deterministic vocabulary and fixed order:

1. `TRIGGER_REFERENCE_SEMANTIC_UNSUPPORTED`
2. `TRIGGER_REFERENCE_PRICE_UNKNOWN`
3. `MARKET_EVIDENCE_UNKNOWN`
4. `MARKET_EVIDENCE_STALE`
5. `POSITION_AUTHORITY_MISMATCH`
6. `POSITION_AUTHORITY_STALE`
7. `TEMPORAL_ORDER_INVALID`
8. `TRIGGER_SIDE_OR_GEOMETRY_INVALID`
9. `TRIGGER_ALREADY_BREACHED`

ACTIONABLE evidence uses only:

```text
reason_codes = [PROTECTION_TRIGGER_ACTIONABLE]
handoff_category = NONE
```

Fail-closed routing precedence is:

```text
POSITION_RECONCILIATION_REQUIRED
> REFRESH_MARKET_EVIDENCE_REQUIRED
> E5_PROTECTION_POLICY_REEVALUATION_REQUIRED
```

The handoff category is routing evidence only; the producer does not turn it into an automatic lifecycle transition.

## Freshness/currentness and retry safety

- raw broker Position authority is bound by deterministic canonical SHA-256 reference;
- `position-lifecycle-projection-v0.1` authority is bound by exact `lifecycle_projection_id` and `lifecycle_revision`;
- market truth is bound by deterministic canonical snapshot SHA-256 reference;
- changed action ID/stop, Position authority, lifecycle projection, market snapshot, operation or trigger semantic invalidates prior evidence;
- a newer accepted market snapshot requires reevaluation;
- a newer broker Position requires fresh E5 protection authority;
- a newer lifecycle projection invalidates older evidence even with an equal broker observation anchor;
- advancing wall-clock/evaluated time alone is deliberately not treated as materially new authority by the currentness check and cannot make unchanged breached evidence retryable.

`protection_trigger_validity_id` uses the contract algorithm: complete canonical evidence payload except the ID -> sorted compact UTF-8 JSON -> SHA-256 -> `prottrigval_<hex>`.

## Test definitions added

`tests/position/test_protection_trigger_validity.py` defines deterministic credential-free coverage for:

- LONG_VALID;
- SHORT_VALID;
- LONG_EQUALITY_BREACHED;
- SHORT_EQUALITY_BREACHED;
- LONG_CROSSED;
- SHORT_CROSSED;
- STALE_MARKET;
- UNKNOWN_MARKET;
- STALE_POSITION_EVIDENCE;
- MISMATCHED_SIDE;
- UNSUPPORTED_TRIGGER_REFERENCE;
- TEMPORAL_PRECOMPUTE;
- UNCHANGED_EVIDENCE_RETRY;
- NEW_MARKET_REEVALUATION;
- NEW_POSITION_REQUIRES_NEW_AUTHORITY;
- newer lifecycle projection invalidation;
- deterministic evidence identity/replay and material identity change;
- changed stop policy -> changed E5 action identity;
- existing no-stop-widening enforcement;
- FAIL_CLOSED never represented as successful protection/lifecycle verification;
- absence of provider-trigger mapping, credential and mutation authority.

## Executable verification

```text
local_verification = NOT_RUN
```

Reason: the task authorizes Product-Owner-approved local credential-free execution, but this GitHub-connected session exposes no approved Windows/non-GitHub runner pinned to this exact candidate revision. No project code or test was executed in GitHub or another substitute environment. `NOT_RUN != PASS`.

Exact intended Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_protection_trigger_validity.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

Because executable verification is `NOT_RUN`, task classification is `PARTIAL`, not `DONE`.

## Security / runtime / release boundary

```text
provider requests                     = 0
provider/private verification         = NOT_RUN / NOT AUTHORIZED BY THIS TASK
credentials                           = NONE / NOT READ / NOT REQUESTED / NOT USED
provider/account mutation             = 0
submit/cancel/amend/close order action = 0
SHADOW runtime                        = NOT_STARTED
PAPER runtime                         = NOT_STARTED
capital movement/exposure             = NONE
GitHub Actions/CI/hosted compute      = NOT USED
```

No OKX/provider `triggerPxType` or provider-native trigger basis is selected or encoded by E5.

## Residual dependency / downstream state

```text
E5 FP-03 producer/policy = IMPLEMENTED / LOCAL VERIFICATION NOT_RUN / PM REVIEW REQUIRED
E4 FP-03 consumer/provider mapping = STILL REQUIRED / NOT STARTED BY E5
FP-03 overall = NOT YET COMPLETE
```

E4 must later consume exact actionable evidence and own provider-capability/trigger-basis mapping under a separate authorized task. E5 does not self-start that work.
