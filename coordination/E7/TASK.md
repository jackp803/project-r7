# E7 Current Task

- task_id: `E7-20260822-015`
- issued_at: `2026-08-22T22:12:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-a-preflight-20260822`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, current `main`, merged E1/E2/E3/E6 research baseline

## Objective

Assemble the **Gate A static preflight** for the current merged research platform and determine whether `main` is structurally ready for a future Product Owner-approved **local-only** Gate A execution run.

This task is integration/preflight work only. It must not execute project tests, backtests, imports, migrations, provider calls, or any GitHub-triggered compute, and it must not claim Gate A PASS. The maximum positive outcome is:

```text
GATE A STATIC PREFLIGHT READY / LOCAL EXECUTION REQUIRED
```

If a source/contract/integration defect would prevent a meaningful local Gate A run, report `BLOCKED_SOURCE` with the exact owner/path instead.

## Accepted current-main baseline

- E1 market-data import-integrity correction PR #21 merge: `1158a777a2830afc37066ef62ebefe624a9ca28e`;
- E3 historical replay / canonical BacktestResult PR #22 merge: `7f70d737ffb1276e251bc552ca9e6d39bb44393d`;
- E7 E3 replay review evidence PR #23 merge: `d8ab1ac540e954d818bbdc271577e945dbc42b72`;
- E6 Registry/evidence persistence accepted/merged baseline remains on `main`;
- E7 OOS ValidationDecision review evidence PR #25 merge: `2b0b725446350b04b9950820ce79a2b919587301`;
- E3 OOS ValidationDecision PR #24 merge: `2ff34a894c4ac16bc989ac701d7e8a9b42eb8692`;
- executable verification across Gate A remains `NOT_RUN`;
- no real strategy ValidationDecision PASS or durable E3 `LOCAL_EXECUTION` evidence exists;
- Gate A/B/C/D remain `BLOCKED`.

## Gate A preflight scope

The research pipeline to assemble is:

```text
E1 canonical closed Candle / historical market data
    -> E2 parse_strategy_definition + actual StrategyRuntime
    -> E3 deterministic historical replay
    -> canonical BacktestResult
    -> E3 explicit OOS ValidationDecision policy/context
    -> canonical ValidationDecision
    -> E6 canonical evidence validation / Registry persistence authority
```

Gate A is a research/integration gate only. It does not include E4 provider execution, E5 live risk/exits, PAPER/SHADOW/LIVE, OKX private endpoints, or Slice 3 execution flow.

## Required actions

1. Read this TASK from latest `main`, fetch latest `main` again, and work only on fresh branch `agent/e7-gate-a-preflight-20260822` created by PM from post-TASK latest `main`.
2. Audit the actual current-main source and test surfaces for E1, E2, E3, and the minimal E6 Registry/evidence path. Do not rely only on historical STATUS claims.
3. Reconfirm dependency direction and contract boundaries:
   - E3 replay consumes actual E2 runtime rather than copied strategy logic;
   - E3 validation consumes canonical BacktestResult and does not depend on E6 production;
   - E6 remains authoritative for durable evidence and lifecycle mutation;
   - `contracts-v0.1` field/enum/time/decimal semantics remain compatible across the full Gate A path;
   - no BacktestResult or synthetic ValidationDecision alone can promote lifecycle.
4. Audit whether the current deterministic test-definition surface is sufficient to exercise Gate A locally. At minimum the local matrix must cover:
   - E1 market-data package/import/Candle/historical behavior;
   - E2 strategy parser/runtime/indicator behavior required by the research path;
   - E3 backtest replay/cost/metrics/real-E2 integration;
   - E3 OOS ValidationDecision behavior;
   - E6 Registry/evidence/persistence tests including promotion authority and storage guards;
   - at least one cross-role Gate A research pipeline definition proving canonical object compatibility end-to-end without provider execution.
5. If a narrow E7-owned cross-role integration test definition is missing, add only the minimal deterministic definition under `tests/integration/**`. It must use the real supported E1/E2/E3/E6 interfaces and must not duplicate their production semantics. Synthetic PASS fixtures, if required, must be explicitly labeled test-only and must not be represented as executable project evidence.
6. Do not modify E1-E6 production code. If preflight reveals a production defect, record the exact failure class/owner/path and stop with `BLOCKED_SOURCE`; do not fix another Agent's implementation in this task.
7. Produce an exact **Gate A local execution matrix**. Inspect current test paths and record commands rather than guessing. The matrix must identify each required suite, its purpose, expected evidence, and ordering/dependencies. It must include the exact PowerShell `PYTHONPATH` setup and all required commands.
8. Define the evidence needed to change Gate A from BLOCKED to PASS after a future approved local run. At minimum capture:
   - exact `main` source revision;
   - environment/runtime identity;
   - exact commands;
   - per-suite PASS/FAIL results;
   - result/log references;
   - no GitHub compute;
   - any durable E3 BacktestResult/ValidationDecision evidence must carry the E6-required `PASS / LOCAL_EXECUTION` metadata and exact bindings before any CANDIDATE lifecycle authority is considered.
9. Distinguish clearly between:
   - `PASS STATIC` / source readiness;
   - executable `PASS` from a real approved local run;
   - synthetic test fixtures;
   - real E3 ValidationDecision evidence;
   - Gate A release disposition.
10. Reconfirm no Gate A scope accidentally depends on E4 provider APIs, OKX credentials, E5 live risk/execution, PAPER/SHADOW/LIVE, GitHub Actions/CI, or hosted runners.
11. Create/update E7-owned preflight documentation, preferably:
   - `status/e7/GATE_A_STATIC_PREFLIGHT_20260822.md`;
   - optionally `docs/integration/GATE_A_LOCAL_VERIFICATION_PLAN.md` if a reusable execution runbook materially helps;
   - any missing E7-owned integration test definitions under `tests/integration/**` only.
12. Update `coordination/E7/STATUS.md` with:
   - exact reviewed current-main revision;
   - merged component/revision inventory;
   - contract/dependency disposition;
   - test-definition completeness disposition;
   - exact local execution command matrix;
   - source blocker list, if any;
   - `executable_verification = NOT_RUN`;
   - Gate A disposition exactly one of `BLOCKED_SOURCE` or `STATIC_PREFLIGHT_READY_LOCAL_EXECUTION_REQUIRED`;
   - Gate B/C/D unchanged BLOCKED;
   - PAPER/SHADOW/LIVE unchanged unauthorized.
13. Do not execute tests/backtests/import probes/migrations, do not call providers, and do not use GitHub Actions/CI/hosted runners or GitHub-triggered self-hosted compute.
14. Do not create a Codex bug ticket unless a defect has already been reproduced in an approved local environment; static concerns remain E7 source findings assigned to the owning Agent.
15. Push only E7-owned preflight docs/status/integration-test definitions to the target branch and stop for PM.

## Acceptance

Task completes when Git contains an exact-revision Gate A static preflight that either:

```text
STATIC_PREFLIGHT_READY_LOCAL_EXECUTION_REQUIRED
```

with a complete local-only command/evidence matrix, or:

```text
BLOCKED_SOURCE
```

with precise source/contract/integration defects and owners.

Neither outcome is Gate A PASS. Without approved local executable evidence, Gate A remains `BLOCKED`.

## Writable scope

- `tests/integration/**` for E7-owned cross-role Gate A test definitions only
- `docs/integration/**`
- `status/e7/**`
- `coordination/E7/STATUS.md`

## Forbidden scope

- E1-E6 production implementation edits;
- `contracts/**` edits;
- provider/private API execution;
- E4/E5 Slice 3 implementation;
- Registry lifecycle promotion performed as project evidence;
- PAPER/SHADOW/LIVE advancement;
- credentials/secrets;
- GitHub Actions/CI/hosted/project compute;
- executable PASS or Gate A PASS claims without approved local execution.

## Completion / status

Persist the Gate A static preflight and exact local execution plan, update STATUS, push, and stop. Do not start Slice 3 or another task automatically.
