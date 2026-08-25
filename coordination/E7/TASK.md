# E7 Current Task

- task_id: `E7-20260825-064`
- issued_at: `2026-08-25T10:55:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-post-remediation-qualification-20260825`
- qualification_source_revision: `d5ddb4cec47c15e8d3ed7045dce4bed043fb6aa8`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, Product Owner explicit approval at `2026-08-25T10:55+08:00`, accepted diagnostic evidence PR #69 merge `a044ff6e382b4fd93308f73169f0952705f922f4`, accepted E4 remediation PR #70 merge `8e7c64972ba323ba02f6250b9d72b22f348c068a`, accepted E7 remediation PR #71 merge `a55cfad82d6cff4059848382cf90896abcb3fd17`, accepted E5 remediation PR #72 merge `25714678ce578d96eabb28f221e62e19720c7427`, accepted E6 remediation PR #73 merge `a642ab88dfc6b9fd983fcb69ae27917baf58c915`

## Objective

Execute exactly one complete post-remediation Gate B qualification in the Product-Owner-approved local Windows / non-GitHub environment against the exact source revision:

```text
d5ddb4cec47c15e8d3ed7045dce4bed043fb6aa8
```

This revision was the exact latest `main` immediately before this ACTIVE task issuance and contains all accepted PRs #70-#73 plus the PM coordination state that followed those merges. The ACTIVE task issuance itself changes only `coordination/E7/TASK.md` and is not part of the executable source revision under qualification.

The purpose of this task is only to obtain complete post-remediation executable evidence for PM review. It does not authorize a production/test fix, contract change, release promotion, or any trading/provider action.

## Mandatory pre-execution revision / environment checks

Before requesting or running any project executable work, record and verify all of the following:

1. approved execution environment is the Product-Owner-approved local Windows / non-GitHub environment;
2. repository checkout is exactly `d5ddb4cec47c15e8d3ed7045dce4bed043fb6aa8`;
3. working tree is clean before execution;
4. no source/test/contract/ADR changes are applied to that checkout;
5. record sanitized machine/environment label, OS/version, Python executable/path/version, repository path, `PYTHONPATH`, start timestamp, and source revision;
6. if the exact revision or clean-worktree condition cannot be established, do not execute and report `BLOCKED`.

## Authorized executable scope — exactly one ten-suite matrix

Set:

```powershell
$env:PYTHONPATH="src"
```

Run exactly once, on the same approved local checkout and same qualification job/request, the required Gate B suites:

```powershell
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

Required suite order is:

1. `strategy`
2. `execution`
3. `brokers`
4. `position`
5. `storage`
6. `platform`
7. `registry`
8. `integration`
9. `e2e`
10. `safety`

Run all ten even if an earlier suite fails, so one qualification attempt yields a complete matrix. Do not run additional suites, selective reruns, or a second qualification attempt under this authorization.

## Required durable evidence

Persist complete sanitized evidence sufficient for independent PM review, including:

- Product Owner approval reference and qualification source revision;
- approved local request/job identifiers;
- source revision confirmation and clean-worktree evidence;
- sanitized environment metadata listed above;
- exact command for every suite;
- per-suite start/end timestamps;
- per-suite test counts (`run`, `failures`, `errors`, `skipped` when reported);
- per-suite exit code/result;
- overall matrix result and job exit code;
- for every non-passing test: exact test identifier, assertion/error text, and concise traceback location;
- proof all ten suites belonged to the same approved qualification request/job;
- explicit confirmation GitHub Actions/CI/hosted/GitHub-triggered compute was not used;
- explicit confirmation provider/private APIs, network/exchange traffic, credentials, PAPER, SHADOW, and LIVE were not used/authorized.

Required artifact:

```text
status/e7/GATE_B_POST_REMEDIATION_QUALIFICATION_20260825.md
```

Also update:

```text
coordination/E7/STATUS.md
```

E7 may update its owned:

```text
status/INTEGRATION_STATUS.md
status/RELEASE_GATES.md
```

only to reflect the observed qualification outcome without promoting Gate B to PASS before PM review.

## Result semantics

If all ten suites pass:

```text
overall_matrix_result = PASS
Gate B = BLOCKED / PENDING_PM_EVIDENCE_REVIEW
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

`PASS` here means the executable matrix passed; it does not itself authorize PAPER or any later gate, and PM still must review the evidence before any formal Gate B acceptance.

If any suite fails/errors:

```text
overall_matrix_result = FAIL
Gate B = BLOCKED / EXECUTABLE_VERIFICATION_FAIL
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

Persist full failure evidence and stop. Do not remediate or rerun in this task.

## Writable scope

Only:

- `coordination/E7/STATUS.md`;
- `coordination/E7/LOCAL_JOB_REQUEST.json` if required by the approved local execution bridge;
- `status/e7/GATE_B_POST_REMEDIATION_QUALIFICATION_20260825.md`;
- `status/INTEGRATION_STATUS.md` and `status/RELEASE_GATES.md` only for non-promotional qualification-state reconciliation.

No production or test source files may be modified.

## Explicitly forbidden

This approval does **not** authorize:

- production code changes;
- test-definition changes;
- contract or ADR changes;
- a second qualification run or selective rerun;
- GitHub Actions / CI / GitHub-hosted runners / GitHub-triggered self-hosted compute;
- provider/private API calls;
- external network or exchange traffic;
- credentials;
- PAPER;
- SHADOW;
- LIVE;
- Gate C;
- strategy promotion;
- any capital exposure.

If execution reveals a defect, collect evidence and stop. PM will assign any remediation only after reviewing the terminal evidence.

## Completion

### DONE

Use `DONE` only after the one authorized complete ten-suite qualification attempt has finished and complete evidence has been persisted and pushed to the target branch, regardless of whether the overall matrix result is PASS or FAIL.

### BLOCKED

Use `BLOCKED` if the exact approved revision, clean approved-local environment, or authorized execution path cannot be established before the run, or if evidence cannot be durably persisted. Do not substitute GitHub or another environment.

Execute only this TASK, update `coordination/E7/STATUS.md`, commit/push required evidence to the target branch, and stop. Do not self-start another task.