# E7 Current Task

- task_id: `E7-20260824-020`
- issued_at: `2026-08-24T01:14:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-a-local-rerun-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, merged PR #28, merged E7 review evidence PR #29, Product Owner-approved Windows local execution policy, AgentBridge preparation evidence `JOB-F53BD229F125 / SUCCEEDED`

## Objective

Execute a fresh, complete Gate A local-only verification matrix through the approved AgentBridge Local Runner against the exact merged candidate revision below. Preserve durable evidence and report the matrix without reinterpretation.

This task is executable verification only. Do not modify E1-E6 production, tests, contracts, or semantics to make a suite pass. If any suite fails, errors, or times out, stop immediately, preserve exact evidence, classify the failure, and report it.

## Product Owner-approved execution environment

Approved environment:

```text
current Windows local development computer
```

Approved exact source revision:

```text
4da559bbbb569ea4f32246a40ef35f4bd8477a71
```

AgentBridge preparation evidence:

```text
JOB-F53BD229F125 / SUCCEEDED
```

Prepared Local Runner worktree requirements already confirmed by PM/Product Owner:

```text
detached HEAD
HEAD = 4da559bbbb569ea4f32246a40ef35f4bd8477a71
working tree = CLEAN
```

Before the first suite, independently confirm the active Local Runner worktree still satisfies those exact conditions. If HEAD differs, relevant files are dirty, or the prepared worktree is unavailable, do not run the matrix; report `ENVIRONMENT_MISMATCH / NOT_RUN`.

## Old evidence is not reusable

The previous partial Gate A execution at revision:

```text
6ed214276038b1ad517e8875c10946b8fcccf4a3
```

must not be reused as PASS evidence for this task.

Even though Market Data / Indicators / Strategy / Backtest passed at that older revision, this new candidate requires a fresh ordered execution of all eight required suites from the beginning.

## Required AgentBridge Local Runner matrix

Use only the already registered, allowlisted Gate A actions. Do not use arbitrary shell execution or Computer Adapter.

Execute in this exact order:

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

These actions correspond to the approved local commands:

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

`PYTHONPATH=src` must remain part of the registered action environment.

For each suite, request execution through the AgentBridge Local Job mailbox / registered Local Runner mechanism and wait for the durable result before proceeding to the next suite.

## Mandatory stop-on-first-failure rule

For any suite result of:

```text
FAILED
ERROR
TIMED_OUT
REFUSED where execution was expected
```

stop immediately. Do not execute any later suite. Do not modify code/tests. Do not skip the failure. Preserve the durable AgentBridge job evidence and report:

```text
LOCAL_EXECUTION_MATRIX = FAIL
GATE_A_REVIEW_CANDIDATE = NO
```

Any suites after the first failure remain `NOT_RUN`.

## Evidence requirements

For the environment and every executed suite, record at minimum:

- exact source revision;
- detached-HEAD / working-tree-clean confirmation;
- Product Owner-approved Windows environment;
- preparation job `JOB-F53BD229F125` reference;
- Python executable and version;
- OS identity sufficient for reproducibility without secrets;
- `PYTHONPATH`;
- AgentBridge job ID;
- action ID;
- actual command;
- cwd;
- start/end timestamp or duration;
- exit code;
- AgentBridge terminal job state;
- test count where available;
- bounded stdout/stderr summary;
- durable local evidence reference (AgentBridge DB/job/audit reference);
- `GitHub compute used = NO`;
- provider/private requests = `NOT_SENT`;
- PAPER/SHADOW/LIVE = `NOT_USED`;
- Registry real promotion = `NONE`.

Do not commit local secrets, tokens, browser auth material, credentials, full personal filesystem dumps, or unrelated machine data.

## Allowed interpretation

If and only if all eight suites execute against exact revision `4da559bbbb569ea4f32246a40ef35f4bd8477a71` and all eight return successful zero-error results, report exactly:

```text
LOCAL_EXECUTION_MATRIX = PASS
GATE_A_REVIEW_CANDIDATE = YES
```

Do not declare `Gate A PASS`. A separate PM/E7 evidence review is required after this task.

If environment/source preconditions prevent execution, report:

```text
LOCAL_EXECUTION_MATRIX = NOT_RUN
GATE_A_REVIEW_CANDIDATE = NO
```

with the exact blocker.

## Safety / compute constraints

Forbidden for this task:

- GitHub Actions / CI / hosted runners;
- GitHub-triggered self-hosted compute;
- arbitrary shell beyond the pre-registered Local Runner actions;
- Computer Adapter;
- provider/private API calls;
- OKX credentials or any exchange credentials;
- E4 broker execution;
- E5 live risk/execution;
- PAPER / SHADOW / LIVE;
- lifecycle promotion as real project evidence;
- production/test/contract edits to make a failing suite pass.

## Writable scope

Evidence/status only:

- `status/e7/**` for this Gate A local rerun evidence;
- `coordination/E7/STATUS.md`;
- `coordination/E7/LOCAL_JOB_REQUEST.json` only as required by the registered AgentBridge Local Job protocol.

Do not modify E1-E6 production/tests/contracts or unrelated project files.

## Completion

After terminal matrix outcome, persist E7-owned evidence and update `coordination/E7/STATUS.md`, commit/push to the target branch, then stop.

Do not start a Gate A PASS review, another implementation task, provider work, PAPER/SHADOW/LIVE, or Slice 3 automatically.