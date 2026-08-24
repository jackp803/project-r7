# E5 Current Task

- task_id: `E5-20260824-010`
- issued_at: `2026-08-24T11:04:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e5-gate-b-protection-producer-20260824`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, ADR-0004, accepted Gate A PASS, Gate B static preflight PR #34, accepted protection contract PR #37

## Objective

Implement only the E5 producer side of the accepted `protection-v0.1` actual-fill protection boundary:

```text
known CONSISTENT normalized Position observation
+ exact parent ApprovedTradePlan
-> E5 protection-v0.1 PositionAction.PROTECT
```

This task resumes the previously blocked E5 actual-fill work only because E7 has now resolved the shared contract semantics. Stop at the E5 PositionAction boundary. Do not implement E4 OrderRequest translation/submission, broker/provider behavior, protection verification orchestration, E6 persistence, TradeResult closure, Paper E2E, provider/private API behavior, or PAPER/SHADOW/LIVE authority.

## Accepted prerequisite

E7 contract decision:

```text
PR #37
merge = e6769b5b78f1b5f699ae4000204b803b2f8b69d5
profile = protection-v0.1
parent schema_version = contracts-v0.1
contract blocker = RESOLVED BY CONTRACT
E5 downstream sufficiency = PASS STATIC
```

Authoritative contract artifacts:

- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`
- `docs/adr/ADR-0004-actual-fill-protection-action-boundary.md`

Do not reinterpret or extend the contract locally. If implementation reveals a genuine ambiguity or contradiction in the accepted contract, stop `BLOCKED` with exact evidence and return ownership to E7.

## Required behavior

Implement deterministic E5-owned production behavior and tests for all of the following.

### 1. Authoritative actual quantity

For ordinary initial `PROTECT`:

```text
PositionAction.quantity = exact known Position.actual_quantity
```

Requirements:

- source Position must be `reconciliation_status=CONSISTENT`;
- actual quantity must be known, finite, and strictly positive;
- source symbol/side/profile/unit/asset must be compatible with the exact parent ApprovedTradePlan;
- initial lifecycle state must be `OPEN_UNPROTECTED`;
- partial fill protects only the actual open quantity;
- full fill protects only the actual open quantity;
- never substitute entry requested quantity or blindly copy full ApprovedTradePlan quantity;
- actual quantity greater than the parent ApprovedTradePlan maximum must fail closed and must not expand ordinary E5 authority.

Provider-native quantities such as OKX `sz` or contract counts remain forbidden in E5.

### 2. Canonical action shape

Produce an executable `PositionAction` only when all required `protection-v0.1` fields are valid, including:

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
quantity_profile_version
quantity_unit
quantity_asset
protection_instruction
risk_policy_version
created_at
expires_at
reason_codes
position_action_id
```

Use the exact field/semantic definitions from the accepted profile. Do not invent alternate shared names.

### 3. Approved bounds and lineage

For `PROTECT`, copy/bind the exact already-approved parent values:

- `trade_plan_id`;
- `risk_decision_id`;
- `risk_policy_version`;
- symbol/direction-compatible position side;
- stop level;
- optional target level;
- max hold seconds;
- canonical quantity profile/unit/asset.

E5 must not loosen or invent stop/target/max-hold bounds after a fill.

`position_action_id` must be deterministic/stable for one logical authorization material and change when authority-bearing material changes as required by the profile.

### 4. Freshness / expiry

Materialize action-specific `created_at` / `expires_at` handling consistent with `protection-v0.1`.

Do not reinterpret the original entry-plan TTL as the lifetime of post-fill protection authority.

Expired or invalidly-timed action material must fail closed.

### 5. Fail closed

Do not produce ordinary executable PROTECT when any required truth is:

- unknown;
- unreconciled;
- mismatched;
- zero or negative;
- non-finite;
- stale/unverifiable under the accepted profile inputs;
- over the parent approved maximum quantity;
- legacy/no protection profile where executable protection is required.

`MODIFY_PROTECTION` remains non-executable under `protection-v0.1`; do not implement executable modification semantics.

### 6. Lifecycle authority boundary

Preserve the existing lifecycle sequence:

```text
ENTRY_FILL_OBSERVED -> OPEN_UNPROTECTED
OPEN_UNPROTECTED + PROTECTION_VERIFIED -> OPEN_PROTECTED
OPEN_UNPROTECTED + PROTECTION_FAILED -> EMERGENCY
```

Creating a PositionAction does not mark the position protected. This task must not generate `PROTECTION_VERIFIED` from action creation/request intent alone.

## Required tests

Add deterministic E5-owned tests covering at minimum:

- partial actual fill < approved maximum -> action quantity equals actual quantity;
- full actual fill -> action quantity equals actual quantity;
- action quantity never exceeds actual open exposure;
- actual exposure > parent approved maximum -> fail closed;
- unknown / `MISMATCH` / `RECONCILIATION_REQUIRED` source truth -> no executable PROTECT;
- zero/negative/non-finite actual quantity -> fail closed;
- source symbol/side/position identity or quantity profile mismatch -> fail closed;
- exact stop/target/max-hold values copied from parent plan without loosening;
- deterministic/stable `position_action_id` for identical authority material and changed identity when authority-bearing material changes;
- invalid/expired action timing fails closed where applicable;
- legacy/unsupported protection profile fails closed;
- `MODIFY_PROTECTION` is not executable under `protection-v0.1`;
- producing PROTECT does not bypass `OPEN_UNPROTECTED` to protected state.

Use existing E5 risk/position fixtures where possible. Do not create test-only semantics that production code does not implement.

## Writable scope

E5-owned paths only:

- `src/risk/**` only for E5 protection authorization/risk-bound logic;
- `src/position/**`;
- `tests/risk/**`;
- `tests/position/**`;
- `tests/safety/**` for E5-owned fail-closed coverage;
- E5-specific `status/**` evidence/handoff;
- `coordination/E5/STATUS.md` on the target branch.

Forbidden:

- `contracts/**` or ADR edits;
- `src/execution/**`;
- `src/brokers/**`;
- E6 persistence/registry;
- E2/E3 code;
- provider/private API or credentials;
- Paper/Shadow/Live mode authority;
- GitHub Actions/CI/workflows.

## Executable verification

All project-code execution is local-only.

If an explicitly approved AgentBridge Local Runner action exists for the exact clean/pinned target revision, use only that registered action and record exact revision/environment/command/result.

Otherwise report:

```text
local_verification = NOT_RUN
```

with exact future Windows PowerShell commands at minimum:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud execution, Computer Adapter, provider APIs, or credentials. `NOT_RUN` is not PASS.

## Acceptance

Allowed terminal outcomes:

### DONE

- `protection-v0.1 PositionAction.PROTECT` producer is materialized inside E5 scope;
- actual known open quantity is the exact protection quantity;
- parent protection/risk bounds and lineage are preserved exactly;
- unknown/inconsistent/over-approved truth fails closed;
- action identity/freshness semantics are deterministic;
- lifecycle remains unprotected until later verified broker evidence;
- deterministic tests are materialized;
- no E4/E6/provider/release scope is crossed;
- executable verification is genuine approved-local evidence or explicitly `NOT_RUN` with commands.

### BLOCKED

- accepted contract cannot be implemented safely without a genuine unresolved semantic/cross-role dependency;
- record exact expected-vs-actual evidence and next owner;
- do not invent a workaround.

Do not declare the actual-fill protection Gate B criterion PASS and do not declare Gate B/PAPER_READY PASS.

## Completion / mailbox rule

Commit/push bounded code/tests/evidence to `agent/e5-gate-b-protection-producer-20260824`.

**Worker-owned terminal STATUS must be written and pushed to `coordination/E5/STATUS.md` on this target branch, not main**, so AgentBridge can observe the terminal state and callback PM.

Then stop. Do not self-start E4 consumer work, protection-failure orchestration, persistence, TradeResult, Paper E2E, Gate C, provider/private work, PAPER, SHADOW, or LIVE.
