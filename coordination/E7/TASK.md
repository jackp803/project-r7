# E7 Current Task

- task_id: `E7-20260824-022`
- issued_at: `2026-08-24T01:56:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-a-local-rerun3-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, Product Owner-approved Windows local execution policy, merged PR #28, E7 review evidence PR #29, AgentBridge production-validation branch observation semantics, preparation evidence `JOB-F53BD229F125 / SUCCEEDED`

## Objective

Execute a fresh complete Gate A local-only matrix at exact project revision `4da559bbbb569ea4f32246a40ef35f4bd8477a71` through AgentBridge. This task corrects the coordination error in `E7-20260824-021`: AgentBridge reads Worker-owned STATUS and Local Job Request from the TASK `target_branch`, not from `main`.

The previous `E7-20260824-021` result remains historical `BLOCKED / NOT_RUN`; do not reinterpret it as project test failure or executable PASS.

## Root-cause correction

AgentBridge production validation explicitly defines split Git authority:

```text
PM-owned TASK              -> registered governance branch (`main`)
Worker-owned STATUS        -> validated TASK `target_branch`
Worker Local Job Request   -> validated TASK `target_branch`
```

Therefore every `coordination/E7/LOCAL_JOB_REQUEST.json` request for this task MUST be committed/pushed to:

```text
agent/e7-gate-a-local-rerun3-20260824
```

Do NOT write Local Job requests to `main`.

The TASK itself remains authoritative on `main`. E7 evidence/status and mailbox requests are Worker-owned and belong on the target branch until reviewed/merged.

## Approved execution pin

Approved environment:

```text
current Windows local development computer
```

Exact project source revision:

```text
4da559bbbb569ea4f32246a40ef35f4bd8477a71
```

Prepared Local Runner state:

```text
detached HEAD
HEAD = 4da559bbbb569ea4f32246a40ef35f4bd8477a71
working tree = CLEAN
```

Preparation evidence:

```text
JOB-F53BD229F125 / SUCCEEDED
```

AgentBridge infrastructure repair evidence remains supporting infrastructure evidence only:

```text
commit 9a3db44325ff1aa07553fd32e7a37ad90f8b6f1d
REQ-INFRA-MONITOR-20260824
JOB-7C7A436EE5816A6E / SUCCEEDED / exit 0 / exactly once
```

None of those infrastructure smoke results count as Gate A suite evidence.

## Fresh evidence only

Do not reuse:

- old revision `6ed214276038b1ad517e8875c10946b8fcccf4a3` PASS evidence;
- E7-020 or E7-021 `NOT_RUN` outcomes;
- `JOB-9089696FF6BB9C98` historical/suppressed evidence;
- infrastructure smoke results.

All eight suites must run freshly for E7-20260824-022.

## Required ordered matrix

Execute only the already registered allowlisted actions, exactly in this order:

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

For each action:

1. On target branch `agent/e7-gate-a-local-rerun3-20260824`, write/update `coordination/E7/LOCAL_JOB_REQUEST.json` with a unique request_id, current task_id `E7-20260824-022`, the action_id, and `state: REQUESTED`.
2. Commit and push that target branch.
3. Wait for AgentBridge durable execution/result notification/evidence before requesting the next suite.
4. Do not create a competing second request while the previous request is unresolved.
5. If cancellation is required, update the SAME target-branch mailbox request to `state: CANCELLED`, commit/push, and retain it as durable protocol evidence. Do not delete it as cancellation.

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

`PYTHONPATH=src` must remain configured by the registered actions.

## Stop-on-first-failure

On the first `FAILED`, `ERROR`, `TIMED_OUT`, or unexpected `REFUSED`:

- stop immediately;
- preserve durable AgentBridge evidence;
- do not run later suites;
- do not edit production/tests/contracts to force PASS;
- report:

```text
LOCAL_EXECUTION_MATRIX = FAIL
GATE_A_REVIEW_CANDIDATE = NO
```

Later suites remain `NOT_RUN`.

## Environment mismatch

If AgentBridge acknowledges the correctly located target-branch request but reports source/worktree mismatch, or if the target branch/mailbox cannot be observed safely, report:

```text
LOCAL_EXECUTION_MATRIX = NOT_RUN
GATE_A_REVIEW_CANDIDATE = NO
```

with exact evidence. Do not substitute GitHub compute or arbitrary local shell.

## Success interpretation

Only if all eight suites freshly execute at exact revision `4da559bbbb569ea4f32246a40ef35f4bd8477a71` with zero failures/errors:

```text
LOCAL_EXECUTION_MATRIX = PASS
GATE_A_REVIEW_CANDIDATE = YES
```

Do not declare Gate A PASS. PM/E7 must perform a separate evidence review.

## Evidence requirements

Record at minimum:

- exact source revision and clean/detached confirmation;
- Windows environment identity;
- Python executable/version;
- PYTHONPATH;
- target branch used for each mailbox request;
- request ID and AgentBridge job ID;
- action ID / actual registered command / cwd;
- exit code / terminal state / test count;
- bounded stdout/stderr summary;
- durable DB/audit/result reference;
- execution timestamps/duration;
- GitHub compute = NO;
- provider/private requests = NOT_SENT;
- PAPER/SHADOW/LIVE = NOT_USED;
- Registry real promotion = NONE.

## Safety / forbidden scope

Do not use GitHub Actions/CI/hosted runners/GitHub-triggered self-hosted compute, arbitrary shell, Computer Adapter, provider/private API, exchange credentials, E4/E5 live execution, PAPER/SHADOW/LIVE, real Registry promotion, or production/test/contract edits.

## Writable scope

On target branch only:

- `coordination/E7/LOCAL_JOB_REQUEST.json`;
- `coordination/E7/STATUS.md`;
- `status/e7/**` evidence for this task.

`coordination/E7/TASK.md` remains PM-owned on main and must not be rewritten by E7.

## Completion

After terminal matrix outcome, commit/push E7 evidence/status on the target branch and stop. Do not start Gate A release review, implementation, provider, PAPER/SHADOW/LIVE, or Slice 3 work automatically.