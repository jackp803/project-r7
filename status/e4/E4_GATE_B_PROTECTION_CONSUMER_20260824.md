# E4 -> E7 Handoff — protection-v0.1 Consumer / Translator

## Handoff

**From:** E4 / Trading Execution & Broker Integration Engineer  
**To:** E7 / Integration Engineer / Project Manager  
**Task:** `E4-20260824-003`  
**Branch:** `agent/e4-gate-b-protection-consumer-20260824`  
**Baseline main:** `c1a0ad241f045b5366c460656adc83dab8e548e8`  
**Code/test implementation HEAD before this handoff:** `ce8052e3bf04cd9ec006a5ba9a55f67a6c17794d`  
**Date:** 2026-08-24

### 1. Objective

Implement only E4's provider-neutral consumer side of the accepted `protection-v0.1` boundary:

```text
E5 PositionAction.PROTECT
+ exact parent ApprovedTradePlan
+ exact current normalized Position truth
-> canonical protection OrderRequest
```

No broker/provider submission, protection verification/failure orchestration, lifecycle transition, Paper E2E, provider API, Gate B PASS, PAPER, SHADOW, or LIVE authority is included.

### 2. What changed

Added a provider-neutral protection consumer in `src/execution/protection.py`.

The consumer independently validates:

- `schema_version=contracts-v0.1`;
- `protection_profile_version=protection-v0.1`;
- `action=PROTECT`;
- exact parent `trade_plan_id`, `risk_decision_id`, `risk_policy_version`, symbol and supported canonical quantity profile;
- exact current `position_id`, side, observation timestamp, reconciliation status, quantity/profile/unit/asset;
- current Position `reconciliation_status=CONSISTENT` and initial lifecycle `OPEN_UNPROTECTED`;
- exact PositionAction quantity equals current Position actual quantity and does not exceed parent approved maximum;
- exact parent stop/optional target/max-hold protection bounds;
- PositionAction creation/expiry freshness.

The parent entry-plan TTL is intentionally **not** used as post-fill protection freshness. Parent `created_at/expires_at` are only checked for structural consistency; the action's own `expires_at` controls protection authorization freshness.

Mechanical request mapping:

```text
authorization_type = POSITION_ACTION
position_action_id = exact action identity
position_id = exact position identity
risk_decision_id = exact parent/action risk lineage
order_role = PROTECTION_STOP
trade_plan_id = exact parent lineage

LONG  -> SELL
SHORT -> BUY
order_type = STOP_MARKET
quantity = exact action/current Position actual quantity
stop_price = exact approved stop_level
reduce_only = true
limit_price = null
time_in_force = null
```

No target order, OCO, timer, trailing behavior, `MODIFY_PROTECTION`, or provider-native field is constructed.

Protective `client_order_id` is deterministic from immediate authority:

```text
POSITION_ACTION + position_action_id + PROTECTION_STOP
```

`OrderRequest.safety_fingerprint()` now includes the additive authority fields so immediate authorization lineage participates in existing E4 idempotency/conflict semantics.

`OrderRequest` additive optional fields:

- `authorization_type`
- `position_action_id`
- `position_id`
- `risk_decision_id`
- `order_role`

`Fill` additive optional lineage fields:

- `position_action_id`
- `position_id`
- `order_role`

All additive fields default to `None`, preserving existing entry/legacy constructor meaning.

### 3. Files changed

- `src/execution/models.py`
- `src/execution/protection.py`
- `tests/execution/test_protection.py`
- `status/e4/E4_GATE_B_PROTECTION_CONSUMER_20260824.md`
- `coordination/E4/STATUS.md` will be updated as the terminal mailbox commit.

No broker/provider implementation was modified.

### 4. Contracts consumed

- `contracts-v0.1`
- `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md` / `protection-v0.1`
- `docs/adr/ADR-0004-actual-fill-protection-action-boundary.md`
- accepted E5 producer `src/position/protection.py` from PR #38 as read-only dependency evidence

### 5. Contracts produced or changed

`NONE`.

No `contracts/**` or ADR file was modified.

### 6. Local verification

Result: `NOT_RUN`

Reason: this session has no Product Owner-approved AgentBridge Local Runner action/capability available for the exact target revision. Project code/tests were not executed in ChatGPT, GitHub, CI, hosted runners, provider infrastructure, or arbitrary cloud compute.

Required future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

`NOT_RUN` is not PASS.

### 7. Deterministic test definitions added

`tests/execution/test_protection.py` covers:

- partial-fill action quantity equals exact current actual quantity, not parent maximum;
- full-fill exact quantity;
- LONG -> SELL / SHORT -> BUY;
- exact STOP_MARKET / stop price / reduce-only / no limit/TIF;
- exact action/position/plan/risk lineage;
- distinct immediate PositionActions do not collide;
- identical action translation is deterministic/idempotent;
- safety fingerprint changes with authority-bearing protection lineage;
- quantity, position observation, side, symbol, profile/unit/asset, risk/plan lineage, and protection-bound mismatch fail closed;
- current Position UNKNOWN/MISMATCH/RECONCILIATION_REQUIRED fail closed;
- expired action fail closed;
- missing/unsupported protection profile fail closed;
- `MODIFY_PROTECTION` fail closed;
- expired parent entry authority alone does not invalidate a still-live post-fill PositionAction;
- existing entry-v0.1 `prepare_entry_order()` behavior remains entry-shaped with additive authority fields unset;
- canonical protection request contains no provider-native fields;
- additive protection Fill lineage can be represented while legacy entry Fill keeps `None` lineage;
- request creation does not claim protection verification or protected lifecycle state.

### 8. Known limitations

- No broker order is submitted.
- No protective order activation/effectiveness is verified.
- No `PROTECTION_VERIFIED`, `PROTECTION_FAILED`, or `PROTECTION_LOST` orchestration is implemented.
- No PaperBroker protection Fill propagation is implemented; this task only makes the provider-neutral Fill model capable of preserving accepted lineage when a later broker normalization path supplies it.
- No provider quantization/trigger mapping is implemented for protection.
- E5 producer executable verification remains `NOT_RUN`; this handoff does not upgrade it to PASS.

### 9. Dependencies / blockers

No shared semantic blocker was found for this bounded static/source implementation.

Executable evidence remains outstanding and must be produced only by an approved local runner. E7 still owns integration/release-gate disposition.

### 10. Required next action

E7/PM should statically review this consumer against PR #37 / ADR-0004 and later arrange approved-local execution evidence. Do not infer actual-fill protection PASS, Gate B PASS, or PAPER_READY from this handoff alone.

### 11. Security / secrets

Confirmed:

- no real API key, API secret, token, credential, password, private key, signature, or live `.env` value was added;
- fixtures are fake/sanitized;
- no provider/private API surface was added.

### 12. GitHub compute policy

Confirmed:

- no GitHub Actions workflow was created or used;
- no GitHub-hosted or GitHub-triggered runner was used;
- no unit/integration/E2E/project code was executed on GitHub infrastructure;
- executable verification remains `NOT_RUN`.

### 13. Live-trading impact

This change only constructs/validates a provider-neutral protective-stop `OrderRequest`. It does not place an order or verify protection. PAPER/SHADOW/LIVE and Gate B remain unauthorized/unadvanced.

### 14. Codex bug ticket

`NONE` — no executable verification was performed and no reproducible implementation defect is claimed.
