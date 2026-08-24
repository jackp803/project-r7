# E4 Current Task

- task_id: `E4-20260824-003`
- issued_at: `2026-08-24T11:13:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-gate-b-protection-consumer-20260824`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, ADR-0004, accepted Gate A PASS, accepted protection contract PR #37, accepted E5 protection producer PR #38

## Objective

Implement only the E4 provider-neutral consumer/translation side of the accepted `protection-v0.1` boundary:

```text
E5 protection-v0.1 PositionAction.PROTECT
+ exact parent ApprovedTradePlan
+ exact current normalized Position truth
-> deterministic provider-neutral protection OrderRequest
```

This task stops at E4 shared execution request construction/validation and the additive request/fill lineage needed by the accepted contract. Do **not** submit any broker order, call OKX/Pionex/private APIs, enable Demo/live provider execution, implement protection verification/failure orchestration, change E5 risk semantics, add E6 persistence, build Paper E2E, or authorize PAPER/SHADOW/LIVE.

## Accepted prerequisites

### E7 shared contract

```text
PR #37
merge = e6769b5b78f1b5f699ae4000204b803b2f8b69d5
profile = protection-v0.1
parent schema_version = contracts-v0.1
```

Authoritative artifacts:

- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`
- `docs/adr/ADR-0004-actual-fill-protection-action-boundary.md`

### E5 producer

```text
PR #38
merge = 268ac8708f84d0c856ac2d1d7436dcb100347a46
head = b98188691f7b9468204bf4f8f3164c07367741db
producer = src/position/protection.py
local executable verification = NOT_RUN
```

E5 `NOT_RUN` remains `NOT_RUN`; this task must not treat the producer as executable PASS evidence.

## Required inspection before editing

Read latest `main` and at minimum:

- `agents/E4_EXECUTION.md` and `agents/README.md`;
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md` and ADR-0004;
- `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`;
- accepted E5 producer implementation and tests as read-only dependency evidence;
- `src/execution/models.py`;
- `src/execution/gateway.py`;
- existing E4 execution tests and idempotency/reconciliation behavior.

Do not reinterpret the contract. If implementation reveals a genuine shared semantic contradiction, stop `BLOCKED / CONTRACT_OR_SEMANTIC_GAP` and return ownership to E7 rather than inventing a private shape.

## Required behavior

### 1. Validate the immediate E5 authority

For executable protection, E4 must accept only a valid shared mapping/object whose contract material is mutually consistent:

```text
schema_version = contracts-v0.1
protection_profile_version = protection-v0.1
action = PROTECT
position_reconciliation_status = CONSISTENT
quantity_profile_version = base-asset-v0.1
quantity_unit = BASE_ASSET
```

For current BTC V1, `symbol=BTC_USDT_PERP` and `quantity_asset=BTC` remain the supported canonical path.

Reject missing/legacy/unsupported protection profile, `MODIFY_PROTECTION`, malformed/expired action authority, unknown/mismatched/reconciliation-required current position truth, or any inconsistent lineage.

E4 may validate E5 output independently at its consumer boundary. Do not mutate E5 code or use a private E4 payload that diverges from the shared profile.

### 2. Validate all three authoritative inputs

Before constructing a protection request, validate:

```text
PositionAction
+ exact parent ApprovedTradePlan
+ exact current normalized Position observation
```

At minimum prove exact consistency for:

- `trade_plan_id`;
- `risk_decision_id`;
- `risk_policy_version`;
- `position_action_id`;
- `position_id`;
- canonical symbol and side;
- exact source/current position observation binding required by the profile;
- `reconciliation_status=CONSISTENT`;
- exact canonical quantity/profile/unit/asset;
- exact parent stop/optional target/max-hold protection instruction;
- action-specific `created_at` / `expires_at` freshness.

E4 must reject stale, mismatched, expired, unknown, or unreconciled evidence. It must never substitute a new quantity, stop, target, side, or policy.

### 3. Do not reuse entry-plan TTL as protection TTL

The parent ApprovedTradePlan entry expiry is **not** the lifetime of post-fill protection authority.

Do not call/reuse the existing entry-plan validation path in a way that rejects an otherwise valid post-fill protection action solely because the parent entry TTL has elapsed after a legitimate fill. Validate the immutable parent plan lineage/profile/protection bounds required by `protection-v0.1`, while using the PositionAction's own `expires_at` for protection-action freshness.

### 4. Mechanical protection OrderRequest mapping

For a valid `protection-v0.1` PROTECT action, materialize exactly:

```text
authorization_type = POSITION_ACTION
position_action_id = exact E5 action identity
position_id = exact position lineage
risk_decision_id = exact parent risk lineage
order_role = PROTECTION_STOP
trade_plan_id = exact parent plan lineage

LONG position  -> side = SELL
SHORT position -> side = BUY
order_type = STOP_MARKET
quantity = exact PositionAction.quantity
quantity_profile_version = exact action profile
quantity_unit = exact action unit
quantity_asset = exact action asset
stop_price = exact approved stop_level
reduce_only = true
limit_price = null
time_in_force = null
```

No target order, OCO behavior, timer, max-hold execution, trailing behavior, or `MODIFY_PROTECTION` execution is authorized by this task.

Provider-specific trigger fields, OKX `sz`, contract counts, lot/tick quantization, provider instrument IDs, or credentials must not appear in the shared OrderRequest.

### 5. Idempotency and authority fingerprint

The protective `client_order_id` must be stable for the logical tuple:

```text
(position_action_id, PROTECTION_STOP)
```

or an equivalently collision-resistant deterministic identity explicitly tied to the immediate PositionAction authority.

Do not derive protective idempotency only from the parent `trade_plan_id`, because different post-fill PositionActions under one parent plan must not collide.

Any OrderRequest safety/idempotency fingerprint must include the new authority-bearing protection fields so a materially changed immediate authorization cannot masquerade as the same logical request.

Repeated translation of the identical accepted action must yield the same logical request identity.

### 6. Additive OrderRequest / Fill lineage

Materialize the accepted additive shared fields needed by `protection-v0.1` without breaking the existing entry path.

For protection OrderRequest, the required immediate-authority fields are:

- `authorization_type`;
- `position_action_id`;
- `position_id`;
- `risk_decision_id`;
- `order_role`.

For independently serialized Fill generated from a protection-authorized request, the accepted additive lineage is:

- `position_action_id`;
- `position_id`;
- `order_role = PROTECTION_STOP`;

Keep legacy/entry objects backward compatible for their existing meaning. Do not rewrite historical objects or infer protection authority when the profile/lineage is absent.

This task need not implement provider Fill retrieval; it must only make the provider-neutral E4 model/normalization boundary capable of preserving the accepted lineage when such a protection Fill is later produced.

### 7. Lifecycle boundary remains external to request creation

Preparing a protection OrderRequest does not mean protection is verified and must not generate or imply:

```text
PROTECTION_VERIFIED
OPEN_PROTECTED
```

The position remains `OPEN_UNPROTECTED` until later broker truth and E5 lifecycle consumption satisfy the accepted verification semantics.

This task does not implement `PROTECTION_FAILED` / `PROTECTION_LOST` orchestration.

## Required deterministic tests

Add E4-owned test definitions covering at minimum:

- partial-fill E5 action -> OrderRequest quantity equals exact action/actual quantity, not parent approved/requested maximum;
- full-fill action -> exact action quantity;
- LONG -> SELL and SHORT -> BUY;
- exact `STOP_MARKET`, approved `stop_price`, `reduce_only=true`, no limit/TIF;
- exact parent/action/position/risk lineage fields;
- different immediate PositionActions do not collide in client-order identity;
- identical action translation is deterministic/idempotent;
- OrderRequest safety fingerprint changes when authority-bearing protection material changes;
- mismatched quantity, position observation, side, symbol, profile/unit/asset, risk/plan lineage, or protection bounds fails closed;
- current position `UNKNOWN`, `MISMATCH`, or `RECONCILIATION_REQUIRED` fails closed;
- expired action fails closed;
- legacy/missing/unsupported protection profile fails closed;
- `MODIFY_PROTECTION` fails closed under `protection-v0.1`;
- parent entry-plan expiry alone does not invalidate a still-valid post-fill PositionAction;
- entry-v0.1 `prepare_entry_order()` behavior remains unchanged;
- protection request contains no provider-native fields;
- additive protection Fill lineage can be represented without changing legacy entry Fill meaning;
- request creation does not claim `PROTECTION_VERIFIED` or protected lifecycle state.

Use sanitized/fake fixtures only. Do not create test-only semantics absent from production code.

## Writable scope

E4-owned paths only:

- `src/execution/**`;
- `tests/execution/**`;
- `tests/brokers/**` only if needed for provider-neutral model compatibility, without provider calls;
- E4-specific `status/**` evidence/handoff;
- `coordination/E4/STATUS.md` on the target branch.

Do not modify:

- `contracts/**` or ADRs;
- `src/risk/**` or `src/position/**`;
- E2/E3/E6 code;
- concrete provider/private networking or credential behavior;
- OKX/Pionex Demo/live submission enablement;
- lifecycle/PAPER/SHADOW/LIVE authority;
- GitHub Actions/CI/workflows.

## Executable verification

All project-code execution remains local-only.

If an explicitly approved AgentBridge Local Runner action exists for the exact clean/pinned target revision, use only that registered action and record exact revision/environment/command/result.

Otherwise report:

```text
local_verification = NOT_RUN
```

with exact future Windows PowerShell commands from repository root, at minimum:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud execution, Computer Adapter, provider APIs, or credentials. `NOT_RUN` is not PASS.

## Acceptance

Allowed terminal outcomes:

### DONE

- E4 materializes the provider-neutral `protection-v0.1` consumer/translator under the accepted contract;
- exact E5 action quantity and parent protection bounds are mechanically preserved;
- request authority/plan/position/risk lineage is explicit;
- protective idempotency is tied to immediate PositionAction authority;
- legacy entry behavior remains compatible;
- no provider/private execution or lifecycle verification is introduced;
- deterministic tests are materialized;
- executable verification is genuine approved-local evidence or explicitly `NOT_RUN` with exact commands.

### BLOCKED

- accepted contract cannot be implemented without a genuine unresolved shared semantic/cross-role dependency;
- record exact expected-vs-actual evidence and next owner E7/PM;
- do not invent a workaround.

Do not declare the actual-fill protection criterion PASS and do not declare Gate B/PAPER_READY PASS.

## Completion / mailbox rule

Commit/push bounded code/tests/evidence to `agent/e4-gate-b-protection-consumer-20260824`.

**Worker-owned terminal STATUS must be written and pushed to `coordination/E4/STATUS.md` on this target branch, not main**, so AgentBridge can observe the terminal state and callback PM.

Then stop. Do not self-start protection verification/failure orchestration, persistence, TradeResult closure, Paper E2E, provider/private work, Gate C, PAPER, SHADOW, or LIVE.
