# E7 Current Task

- task_id: `E7-20260824-024`
- issued_at: `2026-08-24T09:12:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-a-local-rerun4-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, Product Owner-approved Windows local execution policy, AgentBridge runtime fix `ed57928b228720f0876f0060224ed532b17fd799`, AgentBridge PR #6 head `af6ae97f96e172572496de987cfb96f261f58e0c`

## Objective

Execute a fresh complete Gate A local-only matrix at exact project revision `4da559bbbb569ea4f32246a40ef35f4bd8477a71` through the approved AgentBridge Local Runner.

This task supersedes `E7-20260824-023 / HOLD` because the AgentBridge execution-result delivery/cancellation state-machine blocker has now been locally diagnosed, fixed, and validated against the real `project-r7` registration.

No previous Gate A execution evidence is reusable. Start from suite 1 and generate fresh evidence only.

## Accepted AgentBridge infrastructure repair evidence

Root cause of the E7-022 incident is now classified as infrastructure/result-delivery state-machine behavior, not target-branch observation failure and not project-r7 source failure.

Accepted supporting infrastructure evidence:

```text
AgentBridge runtime code actually running:
ed57928b228720f0876f0060224ed532b17fd799

fix commits:
407fc78bde7ce8d5ed7443633b21552f4f020376
ed57928b228720f0876f0060224ed532b17fd799

AgentBridge PR #6 head:
af6ae97f96e172572496de987cfb96f261f58e0c

real project target-branch smoke request:
REQ-AB-REAL-20260824-001-9C0A7E21

job:
JOB-732712DC6A83201E

result:
SUCCEEDED / exit 0 / exactly one execution
notification:
DELIVERED

cancel-before-execution regression:
PASS / zero process executions

finished-job late-cancel regression:
PASS / FINISHED preserved / no rerun

AgentBridge local tests:
58 / 58 PASS

compile check:
PASS

GitHub compute:
NO
```

Historical E7-022 job `JOB-F8A2FB2A2BC78F92` exists for audit only. It is explicitly forbidden as Gate A evidence.

## Approved execution pin

Approved environment:

```text
current Windows local development computer
```

Exact project source revision:

```text
4da559bbbb569ea4f32246a40ef35f4bd8477a71
```

Required active Local Runner worktree:

```text
detached HEAD
HEAD = 4da559bbbb569ea4f32246a40ef35f4bd8477a71
working tree = CLEAN
```

Preparation evidence remains:

```text
JOB-F53BD229F125 / SUCCEEDED
```

Before suite 1, use AgentBridge's registered execution path/evidence to confirm the active worktree is still the exact approved revision and clean. If the runner reports a mismatch, stop with `LOCAL_EXECUTION_MATRIX = NOT_RUN` and preserve exact evidence.

## Critical asynchronous Worker protocol

This task MUST be executed as an event-driven sequence across separate ChatGPT turns.

The previous infrastructure defect showed that keeping the E7 ChatGPT response open while waiting for a Local Runner result prevents AgentBridge from delivering the result notification to that same conversation.

Therefore, for EVERY suite:

1. On target branch `agent/e7-gate-a-local-rerun4-20260824`, write/update `coordination/E7/LOCAL_JOB_REQUEST.json` with exactly one `REQUESTED` action for the current task.
2. Commit and push the request to the target branch.
3. **Immediately end the current ChatGPT response. Do not poll GitHub, do not wait synchronously, do not sleep, and do not keep the response open waiting for the result.**
4. AgentBridge will consume the request and later wake this E7 conversation with the durable execution-result notification.
5. On the next wake, re-read latest `main` TASK, target-branch STATUS/mailbox, and the AgentBridge result supplied to the conversation. Verify task_id/request_id/action/job/result identity before proceeding.
6. If the suite succeeded, persist/update E7 evidence as needed, issue the NEXT suite request on the same target branch, push it, and again immediately end the response.
7. Repeat until either the first failure occurs or all eight suites have terminal results.

Do not remain in one ChatGPT turn waiting for multiple suites.

## Cancellation semantics

`CANCELLED` is for a genuine operator/task cancellation, not a timeout substitute while waiting for a result notification.

Do not cancel a request merely because the E7 chat has not yet seen a notification while the same response is still active. The required behavior is to end the response and allow AgentBridge to wake the conversation asynchronously.

If a genuine cancellation is required before execution, update the SAME target-branch request to:

```text
state = CANCELLED
```

and commit/push it. Do not delete the mailbox request. Do not create a competing request.

If a request already finished, a late CANCELLED state must not be interpreted as undoing or rerunning the completed job. Preserve durable FINISHED evidence.

## Fresh evidence only

Do not reuse as Gate A PASS evidence:

- any PASS from old source revision `6ed214276038b1ad517e8875c10946b8fcccf4a3`;
- E7-020 / E7-021 / E7-022 `NOT_RUN` outcomes;
- historical `JOB-F8A2FB2A2BC78F92`;
- historical `JOB-9089696FF6BB9C98`;
- AgentBridge infrastructure smoke jobs;
- preparation job as a test-suite result.

All eight suites below must execute freshly for `E7-20260824-024`.

## Required ordered matrix

Execute only the registered allowlisted Gate A actions, exactly in this order:

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

`PYTHONPATH=src` must remain configured by the registered actions.

## Stop-on-first-failure

On the first suite result of:

```text
FAILED
ERROR
TIMED_OUT
unexpected REFUSED
```

stop immediately. Do not request any later suite. Do not edit project code/tests/contracts.

Persist exact AgentBridge evidence and report:

```text
LOCAL_EXECUTION_MATRIX = FAIL
GATE_A_REVIEW_CANDIDATE = NO
```

Every later suite remains `NOT_RUN`.

## Successful terminal interpretation

Only if all eight suites freshly execute against exact revision `4da559bbbb569ea4f32246a40ef35f4bd8477a71` and every suite succeeds with zero failure/error:

```text
LOCAL_EXECUTION_MATRIX = PASS
GATE_A_REVIEW_CANDIDATE = YES
```

Do not declare `Gate A PASS`. A separate PM/E7 evidence review is required.

## Evidence requirements

For each executed suite retain/report at minimum:

- exact project source revision;
- detached HEAD / clean worktree confirmation;
- approved Windows environment;
- Python executable/version and OS identity sufficient for reproducibility;
- `PYTHONPATH`;
- target branch;
- request ID;
- AgentBridge job ID;
- action ID / actual registered command / cwd;
- timestamps/duration;
- exit code;
- terminal job state;
- test count where available;
- bounded stdout/stderr summary;
- durable SQLite/audit/result reference;
- notification state;
- execution count / no-rerun identity where available;
- `GitHub compute used = NO`;
- provider/private requests = `NOT_SENT`;
- PAPER/SHADOW/LIVE = `NOT_USED`;
- Registry real promotion = `NONE`.

Do not commit credentials, tokens, browser auth material, secrets, or unrelated personal/machine data.

## Safety / forbidden scope

Forbidden:

- GitHub Actions / CI / hosted runners;
- GitHub-triggered self-hosted compute;
- arbitrary shell beyond registered Local Runner actions;
- Computer Adapter;
- provider/private API or exchange credentials;
- E4/E5 broker/live execution;
- PAPER / SHADOW / LIVE;
- real Registry/lifecycle promotion;
- production/test/contract edits to force PASS.

## Writable scope

On target branch only:

- `coordination/E7/LOCAL_JOB_REQUEST.json`;
- `coordination/E7/STATUS.md`;
- `status/e7/**` evidence for this task.

`coordination/E7/TASK.md` remains PM-owned on `main`.

## Completion

After the terminal matrix outcome, persist E7 evidence/status to the target branch and stop.

Do not start Gate A release review, another implementation task, provider work, PAPER/SHADOW/LIVE, or Slice 3 automatically.