# E5 Gate B Protection Producer Handoff — 2026-08-24

- task_id: `E5-20260824-010`
- agent: `E5`
- state: `DONE / EXECUTABLE_NOT_RUN`
- branch: `agent/e5-gate-b-protection-producer-20260824`
- base_main_sha: `9a1b639cd9f94913f899edc84b27d8b0dafc829f`
- implementation_head_before_evidence: `816ae09e87024ae107fdca67bcb92afdc62bfbdd`
- parent_contract: `contracts-v0.1`
- protection_profile: `protection-v0.1`
- quantity_profile: `base-asset-v0.1`
- next_owner: `PM/E7`

## Objective completed

Materialized only the E5 producer side of the accepted actual-fill protection boundary:

```text
known CONSISTENT normalized Position observation
+ exact parent ApprovedTradePlan
-> E5 protection-v0.1 PositionAction.PROTECT
```

The implementation stops at the E5 PositionAction boundary. It does not create or submit an E4 OrderRequest and does not contact any broker/provider.

## Production implementation

New E5-owned module:

```text
src/position/protection.py
```

Public E5 API exported by `src/position/__init__.py`:

- `ProtectionActionError`
- `build_protect_position_action(...)`
- `validate_protection_action(...)`

### Actual quantity authority

For ordinary initial `PROTECT`:

```text
PositionAction.quantity = exact Position.actual_quantity
```

The producer requires:

- `Position.reconciliation_status = CONSISTENT`;
- `Position.lifecycle_state = OPEN_UNPROTECTED`;
- positive finite actual quantity;
- valid normalized Position identity/timestamps;
- position symbol/side/profile/unit/asset compatible with the parent ApprovedTradePlan;
- actual quantity `<= ApprovedTradePlan.quantity`.

A partial fill therefore protects only the partial actual open quantity. A full fill protects only the full actual open quantity. The producer never substitutes requested entry quantity and never expands authority when actual exposure is greater than the parent maximum.

### Canonical protection-v0.1 action

Successful output carries the accepted profile fields:

```text
schema_version = contracts-v0.1
protection_profile_version = protection-v0.1
action = PROTECT
trade_plan_id
risk_decision_id
position_id
symbol
position_side
position_observed_at
position_reconciliation_status = CONSISTENT
quantity
quantity_profile_version = base-asset-v0.1
quantity_unit = BASE_ASSET
quantity_asset
protection_instruction
risk_policy_version
created_at
expires_at
reason_codes
position_action_id
```

For `BTC_USDT_PERP`, the canonical quantity asset remains `BTC`.

No OKX `sz`, provider contract count, lot/tick metadata, provider instrument ID, credential, or provider field is produced.

### Parent risk/protection bounds preserved

The action copies/binds exact parent:

- `trade_plan_id`;
- `risk_decision_id`;
- `risk_policy_version`;
- symbol / direction-compatible position side;
- `protection_instruction.stop_level`;
- optional `target_level`;
- `max_hold_seconds`;
- quantity profile/unit/asset.

Producer-side validation rejects a changed/loosened protection instruction rather than accepting a post-fill rewrite.

### Identity and freshness

`position_action_id` is a deterministic SHA-256-derived identity over authority-bearing material, including parent lineage, source position observation, quantity/profile/unit/asset, protection instruction, policy, action type, and action-specific creation/expiry timestamps.

Identical authorization material yields the same ID. Materially changed authority yields a different ID.

The profile does not define a fixed protection-action TTL, so E5 does not invent one. The caller supplies explicit UTC `created_at` and `expires_at`; E5 requires:

```text
created_at >= Position.broker_state_observed_at
expires_at > created_at
```

`validate_protection_action(..., now=...)` rejects an expired action.

The original entry-plan TTL is not reused as the lifetime of post-fill protection authority.

### Fail-closed behavior

Ordinary executable PROTECT is rejected for:

- unknown / `MISMATCH` / `RECONCILIATION_REQUIRED` position truth;
- position lifecycle other than `OPEN_UNPROTECTED` for initial protection;
- missing/blank position identity;
- zero, negative, NaN, Infinity, or otherwise invalid quantity;
- symbol/side/quantity-profile/unit/asset mismatch;
- actual exposure greater than parent approved maximum;
- changed/tampered action quantity not equal to source `Position.actual_quantity`;
- changed/tampered parent lineage or protection bounds;
- missing/legacy/unsupported protection profile;
- `MODIFY_PROTECTION` under `protection-v0.1`;
- invalid/future observation ordering;
- invalid or expired action timing;
- invalid deterministic action identity.

## Lifecycle boundary preserved

Creating a PositionAction does not mutate the Position or generate `PROTECTION_VERIFIED`.

Existing lifecycle remains unchanged:

```text
ENTRY_FILL_OBSERVED -> OPEN_UNPROTECTED
OPEN_UNPROTECTED + PROTECTION_VERIFIED -> OPEN_PROTECTED
OPEN_UNPROTECTED + PROTECTION_FAILED -> EMERGENCY
```

This task does not implement broker verification or protection-failure orchestration.

## Deterministic test definitions

Added:

```text
tests/position/test_protection_action.py
```

Static definitions cover:

- partial actual fill -> exact partial protection quantity;
- full fill -> exact actual protection quantity;
- action quantity cannot exceed/replace source actual exposure;
- actual exposure above approved maximum fails closed;
- unknown/mismatch/reconciliation-required source truth fails closed;
- zero/negative/non-finite quantity fails closed;
- symbol/side/position identity/profile/unit/asset mismatch fails closed;
- exact parent stop/target/max-hold copy;
- tampered/loosened protection bounds fail closed;
- deterministic stable action identity and identity change on authority-material change;
- invalid action timing and expired action fail closed;
- missing/unsupported protection profile fails closed;
- `MODIFY_PROTECTION` is non-executable under `protection-v0.1`;
- creating PROTECT does not mark `OPEN_UNPROTECTED` as safe/protected;
- provider-native fields are absent.

No test-only semantics were added without corresponding producer/validator behavior.

## Files changed

- `src/position/protection.py`
- `src/position/__init__.py`
- `tests/position/test_protection_action.py`
- `status/E5_GATE_B_PROTECTION_PRODUCER_20260824.md`
- `coordination/E5/STATUS.md` is updated separately on this same target branch as the terminal mailbox state.

No changes to:

- `contracts/**`;
- ADRs;
- `src/execution/**`;
- `src/brokers/**`;
- E2/E3/E6 code;
- provider/private API code;
- GitHub workflows/CI;
- PAPER/SHADOW/LIVE authority.

## Executable verification

```text
local_verification = NOT_RUN
```

No explicitly approved AgentBridge Local Runner action pinned to this exact new branch revision is exposed in this session. Per project policy, static inspection is not executable PASS evidence.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

No GitHub Actions, GitHub CI, hosted runner, GitHub-triggered self-hosted compute, arbitrary cloud execution, Computer Adapter, provider API, or credentials were used.

## Release impact

```text
E5 protection-v0.1 producer = MATERIALIZED STATICALLY
local executable evidence = NOT_RUN
Required protection follows actual filled quantity = NOT DECLARED PASS
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

E7/PM must review this E5 producer and coordinate the separately bounded E4 consumer plus later approved-local integration evidence.

E5 stops after terminal STATUS for `E5-20260824-010` and does not self-start E4 consumer work or any later Gate B phase.
