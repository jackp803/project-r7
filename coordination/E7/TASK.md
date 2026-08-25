# E7 Current Task

- task_id: `E7-20260825-070`
- issued_at: `2026-08-25T17:26:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-c-storage-diagnostic-20260825`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate C baseline PR #75, accepted Phase-1/2/3 work through PR #81, accepted E7-069 failed credential-free qualification evidence PR #82 merge `0d24fa68994e1d7ee36fbe46b30e179472042c9c`, Product Owner Gate C / SHADOW-only authorization including approved local-only verification

## Objective

Recover enough sanitized executable evidence to identify the exact `tests/storage` failure that caused the first Gate C credential-free qualification `E7-20260825-069` to FAIL.

This is a **diagnostic/evidence-only** task. It is not a second Gate C qualification and must not change the authoritative result of E7-069:

```text
E7-069 credential-free Gate C qualification = FAIL
original failing suite                         = tests/storage / 87 tests / exit 1
Gate C                                         = BLOCKED
```

Do not modify production code, test definitions, contracts, ADRs, migrations, risk policy, provider semantics, or any E1-E6-owned file. Do not remediate in this task.

## Exact diagnostic source revision

Any project-code diagnostic execution must use exactly the same source revision as the failed qualification:

```text
9b3370cbf29ce47abe048cc18860cc89b5fd532d
```

Before any new execution, prove:

- repository revision exactly equals the SHA above;
- working tree is clean;
- approved local Windows / non-GitHub environment;
- Python executable/version and `PYTHONPATH=src`;
- no GitHub Actions/CI/hosted/GitHub-triggered compute.

If those preconditions cannot be established, stop `BLOCKED` with exact evidence.

## Evidence-recovery priority

First, if the approved local bridge can retrieve the complete sanitized stdout/stderr/result for the existing failed job **without executing project code again**, recover the missing failure detail from:

```text
request_id = REQ-E7-GATEC-069-01-6F8C2A41
action_id  = GATE_C_CREDENTIAL_FREE_QUALIFICATION
job_id     = JOB-B92E542317631555
```

Persist only the minimum sanitized material needed to identify:

- every failing/erroring storage test name;
- failure vs error classification;
- exception/assertion type and sanitized message/reason;
- relevant traceback frames/file/line information;
- unittest failure/error summary.

If complete existing-job failure detail is successfully recovered, **do not run project code again**.

## Bounded diagnostic execution fallback

If complete existing-job detail cannot be recovered from the prior job, Product Owner authority permits exactly one bounded approved-local diagnostic execution of the storage suite against the exact source revision above:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

Use a diagnostic-specific local action such as:

```text
GATE_C_STORAGE_FAILURE_DIAGNOSTIC
```

Capture enough sanitized stdout/stderr so that failing/erroring test identity and reason cannot be lost to a short callback excerpt. Use the existing local-job mechanism only; do not use GitHub compute.

This single-suite diagnostic is **not** a qualification rerun. Its result cannot convert E7-069 from FAIL to PASS and cannot be combined with the thirteen earlier passing suites to manufacture a Gate C PASS.

### Diagnostic interpretation

If `tests/storage` FAILs again:

- preserve every failing/erroring test identity and sanitized reason;
- classify only whether the evidence points to E6-owned storage implementation/test definition, E7 integration expectation, environment/reproducibility, or still-unknown ownership;
- recommend an owner, but do not modify or remediate that owner's files.

If `tests/storage` PASSes in the diagnostic:

- record `NON_REPRODUCED / REPRODUCIBILITY GAP`;
- preserve that the original E7-069 qualification remains FAIL;
- do not declare the issue fixed and do not mark Gate C credential-free qualification PASS;
- stop for PM review so a bounded reproducibility/remediation decision can be made.

If the diagnostic itself cannot execute or its output is again insufficient, stop `PARTIAL` or `BLOCKED` with the exact remaining evidence gap.

## Credential-free / safety boundary

This task must remain completely credential-free and provider-disconnected.

Forbidden:

- real API key/secret/passphrase/token/cookie/browser-auth material;
- provider/private authenticated requests;
- external exchange account reads;
- order submission/place/cancel/amend/close;
- leverage/account/position-mode mutation;
- transfer/deposit/withdrawal/capital movement;
- PAPER or SHADOW runtime start;
- Gate D/LIVE/capital exposure;
- GitHub Actions/CI/hosted/GitHub-triggered execution;
- any production/test/contract/migration change;
- selective test edits, assertion weakening, or remediation.

## Required evidence artifact

Create/update only E7-owned diagnostic evidence, for example:

```text
status/e7/GATE_C_STORAGE_FAILURE_DIAGNOSTIC_20260825.md
```

Include:

- task ID and authority;
- original E7-069 request/action/job IDs;
- exact diagnostic source revision;
- whether evidence was recovered from the original job or obtained by one bounded storage diagnostic run;
- approved-local environment/clean-tree evidence if execution occurred;
- exact diagnostic command if execution occurred;
- storage test count, exit code, PASS/FAIL/NON_REPRODUCED;
- every failing/erroring test identity and sanitized reason if present;
- ownership classification/recommendation only, with no remediation;
- explicit statement that E7-069 remains FAIL and Gate C remains BLOCKED;
- proof no credentials/provider/private/mutation/GitHub compute/SHADOW/LIVE activity occurred.

Do not include secrets, raw provider payloads, raw UID/account identifiers, exact balances, provider order/fill IDs, cookies/tokens, browser-auth material, or unnecessary user-specific filesystem paths.

## Writable scope

Only:

- `coordination/E7/LOCAL_JOB_REQUEST.json` if a bounded diagnostic local job is needed;
- `coordination/E7/STATUS.md`;
- `status/e7/GATE_C_STORAGE_FAILURE_DIAGNOSTIC_20260825.md`;
- optionally `status/INTEGRATION_STATUS.md` / `status/RELEASE_GATES.md` only to preserve the non-promotional Gate C BLOCKED state.

Forbidden:

- all production source changes;
- all test-definition changes;
- E1-E6 TASK/STATUS or owned code/tests;
- contracts/ADRs/migrations;
- remediation;
- credentials/secrets;
- provider/private real execution;
- PAPER/SHADOW runtime start;
- Gate D/LIVE/capital exposure;
- GitHub compute.

## Acceptance

### DONE

- exact missing storage failure identity/reason is recovered with sanitized evidence, either from the original job or from at most one bounded storage diagnostic execution; **or** the storage suite passes in that diagnostic and the result is correctly classified `NON_REPRODUCED / REPRODUCIBILITY GAP`;
- no remediation or source/test change occurs;
- E7-069 remains recorded as FAIL;
- Gate C remains BLOCKED;
- evidence and terminal E7 STATUS are committed/pushed to the target branch.

### PARTIAL / BLOCKED

- exact source/clean approved-local environment cannot be established when execution is needed;
- original job evidence cannot be recovered and bounded diagnostic execution is unavailable;
- diagnostic output is again insufficient to identify the failure;
- any authority/safety boundary cannot be satisfied.

## Completion

Read latest `main`, verify wake task ID `E7-20260825-070`, execute only this TASK, update `coordination/E7/STATUS.md`, commit/push required evidence to the target branch, and stop on `DONE`, `PARTIAL`, or `BLOCKED`. Do not self-start E6 remediation, another qualification, credential setup/provider verification, SHADOW runtime, Gate D, or LIVE work.