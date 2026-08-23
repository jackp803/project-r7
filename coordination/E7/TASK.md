# E7 Current Task

- task_id: `E7-20260824-021`
- issued_at: `2026-08-24T01:27:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-a-local-rerun2-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, merged PR #28, merged E7 review evidence PR #29, Product Owner-approved Windows local execution policy, AgentBridge preparation evidence `JOB-F53BD229F125 / SUCCEEDED`, AgentBridge infrastructure repair commit `9a3db44325ff1aa07553fd32e7a37ad90f8b6f1d`

## Objective

Execute a fresh, complete Gate A local-only verification matrix through the approved AgentBridge Local Runner against the exact candidate revision below. This supersedes the blocked execution attempt `E7-20260824-020`; its eight `NOT_RUN` results remain historical and must not be reinterpreted or reused as executable evidence.

This task is executable verification only. Do not modify E1-E6 production, tests, contracts, or semantics to make a suite pass.

## Approved execution pin

Approved environment:

```text
current Windows local development computer
```

Approved exact source revision:

```text
4da559bbbb569ea4f32246a40ef35f4bd8477a71
```

Prepared Local Runner requirements:

```text
detached HEAD
HEAD = 4da559bbbb569ea4f32246a40ef35f4bd8477a71
working tree = CLEAN
```

Preparation evidence:

```text
JOB-F53BD229F125 / SUCCEEDED
```

AgentBridge infrastructure repair evidence supplied by Product Owner/Codex:

```text
commit = 9a3db44325ff1aa07553fd32e7a37ad90f8b6f1d
isolated monitor request = REQ-INFRA-MONITOR-20260824
isolated monitor job = JOB-7C7A436EE5816A6E / SUCCEEDED / exit 0 / exactly once
classification = PRODUCTION_READY_WITH_KNOWN_LIMITATIONS
```

Historical E7 job `JOB-9089696FF6BB9C98` is audit-only / `SUPPRESSED` and is forbidden as Gate A evidence.

Before suite 1, confirm the active Local Runner still reports the exact approved HEAD/worktree/environment. If not, stop with `ENVIRONMENT_MISMATCH / NOT_RUN`.

## Evidence non-reuse

Do not reuse:

- partial PASS evidence from revision `6ed214276038b1ad517e8875c10946b8fcccf4a3`;
- any `NOT_RUN` result from `E7-20260824-020`;
- historical/suppressed AgentBridge jobs;
- the infrastructure smoke job as project Gate A evidence.

All eight Gate A suites must execute freshly for this task.

## Required ordered Local Runner matrix

Use only these already registered allowlisted actions, in exactly this order:

```text
1. GATE_A_MARKET_DATA
2. GATE_A_INDICATORS
3. GATE_A_STRATEGY
4. GATE_A_BACKTEST
5. GATE_A_VALIDATION
6. GATE_A_REGISTRY
7. GATE_A_STORAGE
8. GATE_A_INTEGRATION
```

Registered commands correspond to:

```powershell
python -m unittest discover -s tests/market_data -p "test_*.py" -v
python -m unittest discover -s tests/indicators -p "test_*.py" -v
python -m unittest discover -s tests/strategy -p "test_*.py" -v
python -m unittest discover -s tests/backtest -p "test_*.py" -v
python -m unittest discover -s tests/validation -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
```

`PYTHONPATH=src` must remain active in the registered action environment.

For each action, use the registered AgentBridge Local Job mailbox and wait for durable terminal job evidence before requesting the next action.

## Mailbox cancellation protocol

The repaired AgentBridge protocol supports `CANCELLED`. If an outstanding request must be cancelled, commit the same mailbox request with:

```text
state = CANCELLED
```

Do not delete an unacknowledged/pending request as a cancellation mechanism. Do not create a second competing request while the first is unresolved.

## Stop-on-first-failure

If any suite returns `FAILED`, `ERROR`, `TIMED_OUT`, or an execution refusal where execution was expected:

1. stop immediately;
2. do not run later suites;
3. do not edit project production/tests/contracts;
4. preserve the exact AgentBridge evidence;
5. report:

```text
LOCAL_EXECUTION_MATRIX = FAIL
GATE_A_REVIEW_CANDIDATE = NO
```

Later suites remain `NOT_RUN`.

## Evidence requirements

Record for the environment and every executed suite:

- exact source revision;
- detached HEAD and clean working-tree confirmation;
- approved Windows environment;
- preparation evidence `JOB-F53BD229F125`;
- Python executable/version;
- OS identity sufficient for reproducibility without secrets;
- `PYTHONPATH`;
- AgentBridge request/job ID;
- action ID;
- actual command;
- cwd;
- timestamps/duration;
- exit code;
- terminal state;
- test count where available;
- bounded stdout/stderr summary;
- durable DB/audit reference;
- `GitHub compute used = NO`;
- provider/private requests = `NOT_SENT`;
- PAPER/SHADOW/LIVE = `NOT_USED`;
- Registry real promotion = `NONE`.

Do not commit credentials, tokens, browser auth material, secrets, or unrelated machine data.

## Allowed terminal interpretation

Only if all eight suites freshly execute against exact revision `4da559bbbb569ea4f32246a40ef35f4bd8477a71` and all succeed:

```text
LOCAL_EXECUTION_MATRIX = PASS
GATE_A_REVIEW_CANDIDATE = YES
```

Do **not** declare `Gate A PASS`; separate evidence review is required.

If the approved environment/source/runner cannot be established:

```text
LOCAL_EXECUTION_MATRIX = NOT_RUN
GATE_A_REVIEW_CANDIDATE = NO
```

with the exact blocker.

## Safety / compute constraints

Forbidden:

- GitHub Actions / CI / hosted runners;
- GitHub-triggered self-hosted compute;
- arbitrary shell beyond registered Local Runner actions;
- Computer Adapter;
- provider/private API or exchange credentials;
- E4/E5 broker/live execution;
- PAPER / SHADOW / LIVE;
- real lifecycle/Registry promotion;
- project production/test/contract edits to force a PASS.

## Writable scope

Evidence/status/mailbox only:

- `status/e7/**` for this rerun;
- `coordination/E7/STATUS.md`;
- `coordination/E7/LOCAL_JOB_REQUEST.json` according to the registered request/CANCELLED protocol.

## Completion

Persist terminal evidence and update `coordination/E7/STATUS.md`, commit/push to the target branch, then stop. Do not start another Gate review, implementation task, provider work, PAPER/SHADOW/LIVE, or Slice 3 automatically.