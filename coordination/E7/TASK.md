# E7 Current Task

- task_id: `E7-20260823-017`
- issued_at: `2026-08-23T20:58:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-a-local-execution-20260823`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, merged Gate A static preflight, explicit Product Owner approval in chat

## Product Owner execution approval

The Product Owner explicitly approved use of the **current Windows local development computer** for Gate A local-only executable verification.

Approved executable source revision:

```text
6ed214276038b1ad517e8875c10946b8fcccf4a3
```

This approval is bounded to the Gate A local verification matrix only.

Forbidden substitutes / extensions:

- GitHub Actions / CI;
- hosted runners;
- GitHub-triggered self-hosted compute;
- remote project compute;
- provider/private API calls;
- credentials/secrets use;
- E4 broker execution;
- E5 live risk/execution;
- PAPER / SHADOW / LIVE;
- Slice 3 implementation;
- Registry promotion as project evidence beyond the test-only in-memory definitions already present.

## Objective

Execute the exact Gate A local verification matrix from `docs/integration/GATE_A_LOCAL_VERIFICATION_PLAN.md` on the approved current Windows local development computer at exact source revision `6ed214276038b1ad517e8875c10946b8fcccf4a3`, preserve the complete local evidence, and report the result without reinterpretation.

This task is executable verification only. Do not modify E1-E6 production or contracts to make tests pass. If a suite fails, stop the acceptance path, preserve exact evidence, classify the failure, and report it. Do not fix another Agent's code in this task.

## Required local execution procedure

1. Read this TASK from latest `main`.
2. Work on target branch `agent/e7-gate-a-local-execution-20260823` for evidence/status commits only.
3. Perform the executable run from a local checkout/worktree whose project source is exactly:

```text
6ed214276038b1ad517e8875c10946b8fcccf4a3
```

4. Before executing suites, capture and retain:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
New-Item -ItemType Directory -Force -Path ".gate-a-evidence" | Out-Null
Start-Transcript -Path ".gate-a-evidence\gate-a-local-verification.log" -Force

git rev-parse HEAD
git status --short
python --version
python -c "import platform,sys; print(sys.executable); print(platform.platform()); print(sys.version)"
```

5. `git rev-parse HEAD` must equal the approved source revision above. If it does not, do not run the matrix; report `ENVIRONMENT_MISMATCH / NOT_RUN`.
6. Record working-tree state. If source/test files relevant to Gate A are locally modified, do not treat results as candidate Gate A evidence; report the exact drift and stop.
7. Run the required suites **in this exact order**:

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

8. Do not skip a failing suite and later claim overall PASS. Preserve each suite result as `PASS | FAIL | ERROR | NOT_RUN`.
9. End transcript after the run:

```powershell
Stop-Transcript
```

10. Preserve the local transcript/result references. Do **not** commit secrets, machine-sensitive credentials, API keys, tokens, or unrelated personal data. Sanitized environment identity is sufficient: OS family/version, Python executable/version, source revision, commands, timestamps, and result references.

## Evidence/report requirements

Persist E7-owned evidence/status on the target branch, preferably:

- `status/e7/GATE_A_LOCAL_EXECUTION_20260823.md`;
- `coordination/E7/STATUS.md`.

Record at minimum:

- Product Owner approval scope: current Windows local development computer;
- approved source revision `6ed214276038b1ad517e8875c10946b8fcccf4a3`;
- actual executed source revision;
- working-tree state;
- local OS/runtime identity;
- Python executable/version;
- `PYTHONPATH`;
- exact command list;
- per-suite PASS/FAIL/ERROR/NOT_RUN;
- test counts where available;
- transcript/log/result references;
- execution timestamp/timezone;
- `GitHub compute used = NO`;
- provider/private requests = `NOT_SENT`;
- PAPER/SHADOW/LIVE = `NOT_USED`;
- real Registry promotion = `NONE`;
- any failure classification and exact owner/path if inferable from executable evidence.

## Gate interpretation

If and only if all eight required suites execute locally at the exact approved source revision with zero failures/errors, report:

```text
LOCAL_EXECUTION_MATRIX = PASS
GATE_A_REVIEW_CANDIDATE = YES
```

Do **not** self-declare Gate A PASS. E7/PM must perform a separate evidence review after this execution task.

If any required suite fails/errors, report:

```text
LOCAL_EXECUTION_MATRIX = FAIL
GATE_A_REVIEW_CANDIDATE = NO
```

and preserve the first failing command plus all available failure evidence. Do not open a Codex bug ticket automatically; PM will classify whether a locally reproduced defect warrants a bounded ticket or owner correction.

If environment/source preconditions prevent execution, report:

```text
LOCAL_EXECUTION_MATRIX = NOT_RUN
GATE_A_REVIEW_CANDIDATE = NO
```

with exact blocker.

## Scope constraints

Writable:

- `status/e7/**` for this local execution evidence;
- `coordination/E7/STATUS.md`.

Forbidden:

- E1-E6 production changes;
- `contracts/**` changes;
- test semantic modifications to make a failure disappear;
- provider/private APIs;
- credentials/secrets;
- GitHub Actions/CI/hosted runners/GitHub-triggered compute;
- E4/E5/Slice 3 work;
- lifecycle promotion as real project evidence;
- PAPER/SHADOW/LIVE advancement.

## Completion

Commit/push only the E7 local-execution evidence/status to the target branch, then stop. Do not start a Gate A PASS review, another implementation task, Slice 3, or any provider work automatically.