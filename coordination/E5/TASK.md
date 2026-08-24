# E5 Current Task

- task_id: `E5-20260824-007`
- issued_at: `2026-08-24T09:57:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e5-gate-b-risk-evidence-20260824`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate A PASS, merged Gate B static preflight PR #34

## Objective

Close only the first dependency-ordered Gate B gap identified by E7 static preflight: **explicit criterion-level E5 risk-limit test materialization** for the Gate B requirement:

```text
Drawdown / daily / position / kill-switch rules enforced
```

E7 found the production policy/engine already contains these controls, but current repository test definitions do not establish equally explicit criterion-level coverage for the complete set. This task is therefore expected to be test-definition/evidence materialization, not a policy redesign.

Do not start the later E5/E4 actual-fill protection path, protection-failure orchestration, E6 persistence, TradeResult closure, or E7 Paper E2E work in this task.

## Accepted prerequisite evidence

Gate B static preflight:

```text
PR #34
merge = 2d0ba0f103c7e395ad4c2b6cf67beca83915cc65
artifact = status/e7/GATE_B_STATIC_PREFLIGHT_20260824.md
Gate B = BLOCKED / NOT YET PASS
```

Relevant E7 finding:

```text
E5 policy/engine implements daily-trade cap, open-position cap,
drawdown lock and kill-switch behavior.

Gap = complete explicit criterion-level targeted test/evidence coverage.
```

## Required work

Read latest main, `agents/E5_RISK_POSITION.md`, `agents/README.md`, contracts-v0.1, `status/RELEASE_GATES.md`, `status/e7/GATE_B_STATIC_PREFLIGHT_20260824.md`, current E5 risk implementation, and existing E5 tests before editing.

Materialize deterministic test definitions that explicitly prove, at minimum:

1. **Daily trade cap**
   - below-limit context may continue through the normal risk evaluation path;
   - at/above configured daily limit rejects new exposure with the existing canonical reason behavior;
   - test must use configured policy values rather than introducing a hard-coded new product policy.

2. **Open-position / simultaneous-position cap**
   - existing position/open-position-limit condition rejects new exposure;
   - no risk-layer bypass or second-position approval is introduced;
   - preserve existing same-symbol/unknown-position fail-closed behavior.

3. **Drawdown lock**
   - drawdown below threshold does not itself trigger the drawdown rejection;
   - threshold/exceeded state rejects new exposure using existing versioned policy semantics;
   - do not redefine how drawdown is calculated unless current code already exposes the required canonical input/state.

4. **Kill switch**
   - preserve existing kill-switch rejection coverage;
   - if existing coverage is already explicit and sufficient, do not duplicate it merely to increase test count;
   - ensure the combined Gate B criterion can point to a concrete test for kill-switch enforcement.

5. **Fail-closed / no policy weakening**
   - tests must not introduce a path that resets/bypasses locks merely because a new TradeIntent arrives;
   - no martingale, risk escalation, stop widening, or second-position behavior may be enabled.

## Expected writable scope

Prefer test-only changes:

- `tests/risk/**`
- `tests/safety/**` only for E5-owned safety scenarios
- E5 handoff/status artifact if useful
- `coordination/E5/STATUS.md`

Do **not** modify production risk semantics merely to make the new tests pass. E7 preflight classified production controls as already present. If static inspection shows a genuine production implementation defect or a contract mismatch, stop and report `BLOCKED` with exact expected-vs-actual evidence rather than broadening this task.

Do not modify:

- `src/execution/**` or `src/brokers/**`;
- E6 persistence/registry;
- Strategy/validation code;
- shared contracts/ADRs;
- provider/private API code;
- lifecycle/PAPER/SHADOW/LIVE authority;
- GitHub workflow/CI files.

## Executable verification

This task does **not** authorize ad-hoc cloud/GitHub execution. If the currently approved AgentBridge Local Runner does not yet have a safe exact-revision action for this new branch/revision, keep executable verification:

```text
NOT_RUN
```

and record these exact future local commands:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners or arbitrary remote compute. Do not claim PASS from static inspection.

If an already-approved local execution path is explicitly available to this task and exact branch revision can be proven clean/pinned, execution may be performed only under that existing approved local-only policy; otherwise `NOT_RUN` is the correct result.

## Acceptance

The task is complete when:

- explicit daily-trade-limit test definition exists;
- explicit open/simultaneous-position-limit test definition exists;
- explicit drawdown-threshold/lock test definition exists;
- existing kill-switch coverage is identified or minimally completed without duplication;
- no production-policy weakening or cross-role change occurred;
- tests are deterministic and use versioned/configured policy semantics;
- executable result is either genuine approved-local evidence or `NOT_RUN` with exact commands;
- no GitHub compute/CI was used;
- `coordination/E5/STATUS.md` records files changed, semantic impact, verification state, blocker if any, and next owner PM/E7.

Do not declare the Gate B criterion PASS and do not declare Gate B/PAPER_READY PASS. E7/PM must later review and execute the required local evidence.

## Completion

Commit/push the bounded work to `agent/e5-gate-b-risk-evidence-20260824`, update E5 STATUS, then stop. Do not self-start the actual-fill protection task or any subsequent Gate B phase.