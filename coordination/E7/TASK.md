# E7 Current Task

- task_id: `E7-20260825-059`
- issued_at: `2026-08-25T07:03:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-approved-local-verification-20260825`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate B source chain through PR #65, accepted E7 durable Paper static re-review PR #66 merge `426130b305122da64a362472e74aa1d72dcd302f`, Product Owner explicit approval in PM control channel on `2026-08-25` for approved-local Gate B verification
- pre_authorization_main_revision: `399b817093dc555e18204027e46ff62c6fbb948e`

## Objective

Execute only the complete **Gate B approved-local verification matrix** that E7-057 declared ready for execution, using the Product Owner-approved local Windows/non-GitHub project execution environment.

This task authorizes project test execution only. It does **not** authorize PAPER runtime operation, SHADOW, LIVE, provider/private APIs, credentials, exchange traffic, strategy promotion, capital exposure, GitHub Actions/CI, hosted runners, or GitHub-triggered compute.

Do not modify production code or test definitions in order to make verification pass. This is an evidence task, not an implementation task.

## Exact-revision rule

Before executing project code:

1. read latest `main`, `README.md`, `agents/README.md`, `agents/E7_INTEGRATION.md`, this exact TASK, `status/RELEASE_GATES.md`, and `status/INTEGRATION_STATUS.md`;
2. verify this TASK task_id exactly matches `E7-20260825-059`;
3. record the exact latest `main` commit containing this TASK as `execution_revision`;
4. create/use the target branch from that exact revision without any production/test-content modification before verification;
5. require a clean project working tree before the first test command, except for verification-output files that are created only after test execution;
6. if `main` moves after `execution_revision` is recorded, continue only on the recorded exact revision and explicitly state that later main commits were not tested;
7. all PASS/FAIL evidence must be attributed only to that exact `execution_revision`.

The pre-authorization main revision `399b817093dc555e18204027e46ff62c6fbb948e` differs from the execution revision only by PM coordination needed to issue this approved task unless later Git evidence proves otherwise. If any project source/test/contract/release content changed between them unexpectedly, stop `BLOCKED / REVISION_SCOPE_CHANGED` and return evidence to PM rather than silently broadening approval.

## Approved environment boundary

Execution is authorized only in the Product Owner-approved local Windows/non-GitHub environment for `project-r7`.

Before running tests, record at minimum:

- machine/environment label sufficient to identify the approved local runner without exposing secrets;
- OS/version;
- Python executable path and version;
- repository path;
- `execution_revision`;
- clean/dirty working-tree state;
- `PYTHONPATH` used.

If the worker cannot access that approved local environment, or is running only in ChatGPT/container/GitHub/hosted/cloud compute, stop:

```text
state = BLOCKED
environment = ENVIRONMENT_MISMATCH
project_executable_verification = NOT_RUN
```

Do not substitute another environment.

## Required Gate B matrix

From repository root in the approved local Windows PowerShell environment:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/strategy -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/e2e -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

Run the matrix exactly against the recorded revision. Do not skip a suite because an earlier suite fails. Continue through all ten suites when the environment remains valid so PM receives a complete failure/pass matrix.

Do not run backtests, network calls, provider/private requests, Paper daemons, long-running services, exchange adapters against real endpoints, or any command outside the bounded verification matrix unless required only to collect non-executable environment/revision metadata.

## Evidence requirements

Create E7-owned evidence under:

```text
status/e7/GATE_B_APPROVED_LOCAL_VERIFICATION_20260825.md
```

and update:

```text
coordination/E7/STATUS.md
```

Record for each suite:

- exact command;
- exit code;
- tests run count if emitted;
- PASS or FAIL based only on actual local output;
- concise failure identifiers/traceback location when failed;
- execution timestamp;
- exact `execution_revision`.

Also record an overall matrix result:

```text
ALL_PASS
FAIL
PARTIAL
BLOCKED
```

Rules:

- `ALL_PASS` only if all ten commands actually ran and returned success in the approved environment;
- any executed suite failure -> overall `FAIL` even if other suites pass;
- inability to complete all suites after some execution -> `PARTIAL` with exact cause;
- no executable run because environment/revision approval boundary cannot be satisfied -> `BLOCKED / NOT_RUN`;
- never convert static acceptance or prior `NOT_RUN` into PASS.

Do not commit credentials, machine secrets, private paths containing secrets, raw tokens, account identifiers, or provider data. Sanitize environment evidence as needed while retaining enough information to prove local execution.

## Release interpretation boundary

This task does not itself authorize PAPER and must not start Paper trading.

E7 may record criterion-level executable evidence and an evidence-based candidate disposition, but must keep the formal release state conservative pending PM review of this terminal evidence:

```text
Gate B = BLOCKED / PENDING_PM_EVIDENCE_REVIEW
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

Do not start Gate C or provider/private work even if every test passes.

If failures reveal a settled-contract implementation defect, identify the responsible owner and exact failing evidence; do not fix E1-E6 production code in this task. If failures reveal a new shared semantic/architecture gap, classify `CONTRACT_OR_SEMANTIC_GAP` for PM/E7 follow-up.

## Writable scope

E7 evidence only:

- `status/e7/GATE_B_APPROVED_LOCAL_VERIFICATION_20260825.md`;
- `coordination/E7/STATUS.md`;
- `status/INTEGRATION_STATUS.md` and `status/RELEASE_GATES.md` only to record actual local evidence while preserving `Gate B = BLOCKED / PENDING_PM_EVIDENCE_REVIEW`;
- no production code;
- no E1-E6 tests;
- no E7 test-definition edits during this evidence run;
- no contracts/ADR changes unless only recording a blocker is impossible without them; default is no contract/ADR write.

Forbidden:

- `.github/workflows/**` / GitHub CI / hosted runners / GitHub-triggered self-hosted compute;
- provider/private API/network/credentials;
- PAPER, SHADOW, LIVE runtime operation;
- strategy promotion;
- production/test fixes;
- another task.

## Terminal status

### DONE

Use DONE when all ten suites ran in the approved environment. STATUS must contain `overall_matrix_result = ALL_PASS | FAIL` and exact evidence. Do not equate DONE with Gate B PASS.

### PARTIAL

Use PARTIAL when approved-local execution began but the complete ten-suite matrix could not finish. Preserve all completed-suite evidence and exact blocker.

### BLOCKED

Use BLOCKED when the approved environment/revision boundary cannot be satisfied before execution. Keep `project_executable_verification = NOT_RUN`.

## Completion / mailbox rule

Commit/push only allowed E7 evidence/status changes to `agent/e7-gate-b-approved-local-verification-20260825`.

Write/push terminal `coordination/E7/STATUS.md` with task_id `E7-20260825-059` and stop.

Do not self-start remediation, Gate C, provider/private APIs, PAPER, SHADOW, LIVE, or another task.