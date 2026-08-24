# E5 Current Task

- task_id: `E5-20260824-008`
- issued_at: `2026-08-24T10:24:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e5-gate-b-fill-protection-20260824`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate A PASS, merged Gate B static preflight PR #34, merged E5 risk-limit evidence PR #35

## Objective

Implement only the E5-owned half of the next dependency-ordered Gate B gap identified by E7:

```text
actual execution fill/open quantity
-> exact provider-neutral protection quantity/action
```

The required protection must be derived from **actual filled/open exposure**, never requested/approved entry quantity alone.

This task stops at the E5 protection decision/action boundary. Do not implement E4 broker/order submission, protection-failure orchestration, E6 persistence/restart, TradeResult closure, E7 Paper E2E, provider/private API behavior, or PAPER/SHADOW/LIVE authority.

## Accepted prerequisite evidence

Gate B static preflight:

```text
PR #34
merge = 2d0ba0f103c7e395ad4c2b6cf67beca83915cc65
artifact = status/e7/GATE_B_STATIC_PREFLIGHT_20260824.md
finding = IMPLEMENTATION_GAP / required protection follows actual filled quantity
owner order = E5 then E4
```

E5 risk-limit test materialization:

```text
PR #35
merge = 133e62b2ad8aa5c31d3f0aef1679c0449aa2a10c
implementation = eb57637e7c91262f2bbffa140b39db2d24c8c6fc
executable verification = NOT_RUN
```

PR #35 closes only the requested test-definition materialization task. Its `NOT_RUN` remains `NOT_RUN` and does not make the Gate B risk-limit criterion PASS.

## Required inspection before editing

Read latest `main` and at minimum:

- `agents/E5_RISK_POSITION.md`;
- `agents/README.md`;
- `contracts-v0.1` shared contracts and execution-object profiles;
- `status/e7/GATE_B_STATIC_PREFLIGHT_20260824.md`;
- `status/RELEASE_GATES.md`;
- `src/risk/**`;
- `src/position/**`;
- E4 public execution/fill models only as read-only dependency evidence;
- existing E5 risk/position/safety tests.

Do not infer a shared `PositionAction`/protection payload shape if the authoritative contract does not define enough semantics.

## Contract-first blocker rule

If current E7-owned contracts do **not** provide a sufficient shared/provider-neutral representation for the E5 protection action required here, stop and report:

```text
state = BLOCKED
blocker = CONTRACT_OR_SEMANTIC_GAP
next_owner = E7
```

Include the exact missing field/semantic and producer/consumer impact. Do not invent a parallel shared model and do not modify `contracts/**` in this task.

## Required behavior

Subject to the existing shared contract shape, materialize deterministic E5 behavior that proves all of the following:

1. **Actual-fill quantity is authoritative**
   - a partial entry fill must produce required protection for the actual open/filled quantity, not the original requested or E5-approved maximum quantity;
   - protection quantity must never exceed known actual open exposure;
   - provider-native units/quantization remain outside E5.

2. **Approved risk bounds are preserved**
   - stop/target/protection bounds come only from the already approved E5 plan/policy semantics;
   - an execution fill must not loosen the approved stop/risk boundary;
   - E5 must not manufacture broker-specific order type, exchange symbol metadata, OKX `sz`, contract count, tick/lot quantization, credentials, or provider fields.

3. **Fail closed on unknown/inconsistent execution truth**
   - unknown/unreconciled fill or position quantity cannot produce a falsely safe protection claim;
   - zero/negative/inconsistent quantity fails closed according to current contract/lifecycle semantics;
   - if observed actual exposure exceeds the approved E5 maximum, do not silently expand protection/risk authority; surface the existing unsafe/reconciliation path or block with exact evidence if the current contracts cannot represent it.

4. **Lifecycle semantics remain explicit**
   - observing an entry fill establishes `OPEN_UNPROTECTED`/equivalent unsafe exposure first;
   - producing/requesting a protection action does **not** itself mark the position `OPEN_PROTECTED`;
   - only verified protection may produce the existing `PROTECTION_VERIFIED` transition;
   - preserve `PROTECTION_FAILED` / `PROTECTION_LOST` semantics for the later bounded E4/E5 task; do not implement that orchestration now.

5. **No exposure/risk escalation**
   - no averaging down, second-position approval, martingale, stop widening, leverage increase, or risk-limit weakening;
   - no new TradeIntent may reset existing unsafe/unprotected position state.

## Required tests

Add deterministic E5-owned test definitions sufficient to demonstrate the implemented boundary. At minimum cover:

- approved/requested entry quantity greater than actual partial fill -> protection quantity equals actual exposure;
- full fill -> protection quantity equals actual exposure and remains within approved maximum;
- unknown/reconciliation-required execution truth -> no safe protection claim / fail closed;
- actual exposure greater than approved maximum -> fail closed, never expand E5 authority;
- protection action/request does not skip `OPEN_UNPROTECTED` directly to safe/protected state;
- existing approved stop/risk bounds are preserved and not loosened by fill handling.

Prefer existing fixtures/contracts. Do not create test-only semantics that production code does not implement.

## Writable scope

E5-owned paths only:

- `src/risk/**` only if needed for E5 protection/risk-bound logic;
- `src/position/**`;
- `tests/risk/**`;
- `tests/position/**`;
- `tests/safety/**` for E5-owned fail-closed scenarios;
- E5-specific `status/**` handoff/evidence;
- `coordination/E5/STATUS.md`.

Forbidden:

- `src/execution/**`;
- `src/brokers/**`;
- E6 storage/registry/persistence;
- E2/E3 code;
- `contracts/**` or ADR changes;
- provider/private API/credential code;
- lifecycle promotion to PAPER/SHADOW/LIVE;
- GitHub Actions/CI/workflows.

## Executable verification

All project-code execution remains local-only.

If an explicitly approved AgentBridge Local Runner action exists for the exact branch/revision, E5 may use only that registered action and must record exact revision/environment/command/result.

Otherwise report:

```text
local_verification = NOT_RUN
```

with exact future Windows PowerShell commands, at minimum:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud execution, Computer Adapter, provider APIs, or live credentials.

`NOT_RUN` is acceptable task evidence when no approved exact-revision action exists, but it is not PASS and does not satisfy Gate B executable criteria.

## Acceptance

Task completion requires one of two bounded outcomes:

### DONE

- E5 provider-neutral actual-fill protection action boundary is materialized under existing contracts;
- protection quantity derives only from known actual open/fill exposure and never exceeds it;
- approved E5 risk/protection bounds are not loosened;
- unsafe/unknown/over-approved exposure fails closed;
- lifecycle cannot claim protected state before verification;
- deterministic tests are materialized;
- no E4/E6/provider/lifecycle authority scope was crossed;
- executable verification is genuine approved-local evidence or explicitly `NOT_RUN` with commands.

### BLOCKED

- current shared contracts are insufficient or a cross-role semantic dependency prevents safe implementation;
- exact missing semantic/evidence is recorded;
- no speculative parallel model is introduced;
- next owner is identified as E7/PM as appropriate.

Do not declare the Gate B protection criterion PASS and do not declare Gate B/PAPER_READY PASS.

## Completion

Update `coordination/E5/STATUS.md`, commit/push bounded code/tests/evidence to `agent/e5-gate-b-fill-protection-20260824`, then stop. Do not self-start E4 protection execution, protection-failure emergency orchestration, E6 persistence, TradeResult closure, Paper E2E, Gate C, provider/private work, PAPER, SHADOW, or LIVE.