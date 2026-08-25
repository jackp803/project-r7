# E7 Current Task

- task_id: `E7-20260825-060`
- issued_at: `2026-08-25T07:59:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-failure-evidence-recovery-20260825`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate B source chain through PR #66, accepted approved-local FAIL evidence PR #67 merge `3f676ed3245d78a54e232292e817c965934ca489`, Product Owner approved-local Gate B verification authorization from `2026-08-25`
- source_execution_revision: `62bef3cedda7f7b65116defd9802e2aee37a4fb0`
- local_request_id: `REQ-E7-GATEB-059-01-8C4F2A71`
- local_job_id: `JOB-EA9AE3F80AD335AE`

## Objective

Recover and persist the **complete existing failure evidence** from the already-executed approved-local Gate B job `JOB-EA9AE3F80AD335AE`, then perform evidence-only root-cause triage.

This task is deliberately non-executable. Do **not** rerun project tests, execute project code, modify production/test definitions, or start remediation. The prior approved-local job already established:

```text
strategy    PASS
execution   PASS
brokers     FAIL
position    FAIL
storage     FAIL
platform    PASS
registry    PASS
integration FAIL
e2e         PASS
safety      FAIL
overall_matrix_result = FAIL
Gate B = BLOCKED
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

The missing prerequisite for safe remediation assignment is the full local failure detail that was truncated from the callback delivered during E7-059.

## Required evidence recovery

Using only persisted metadata/log/output from the already completed approved-local request/job, recover and record as much of the following as actually exists:

- approved local machine/environment label, sanitized as necessary;
- OS/version;
- Python executable path and version, sanitized if required;
- repository path, sanitized if required;
- clean/dirty working-tree state recorded before execution;
- `PYTHONPATH`;
- exact `execution_revision = 62bef3cedda7f7b65116defd9802e2aee37a4fb0` confirmation;
- per-suite execution timestamp;
- per-suite test count;
- every failing test identifier for `brokers`, `position`, `storage`, `integration`, and `safety`;
- assertion/error message and concise traceback location for each failure/error;
- suite exit codes and overall job exit code;
- any local-runner/AgentBridge evidence proving all ten suites belonged to the same approved request/job.

Do not invent any field that cannot be recovered.

## Evidence source boundary

Permitted:

- existing AgentBridge/local-runner job metadata;
- existing local stdout/stderr/transcript/log artifacts from `REQ-E7-GATEB-059-01-8C4F2A71` / `JOB-EA9AE3F80AD335AE`;
- non-executable metadata reads needed to identify the already completed job;
- Git read-only inspection needed to map an observed traceback to repository ownership/contracts.

Forbidden:

- rerunning any unittest command;
- executing any project Python/module/code;
- generating a new local verification job;
- changing E1-E6 production/tests or E7 test definitions;
- GitHub Actions/CI/hosted runners/GitHub-triggered compute;
- provider/private API/network/credentials;
- PAPER, SHADOW, LIVE;
- Gate C work;
- speculative root-cause assignment without exact failure evidence.

If full local logs are unavailable, do not recreate them by execution in this task.

## Triage rules

After recovering the evidence:

1. determine whether the five failing suites share one or more exact first-order failure causes;
2. distinguish:
   - settled-contract implementation defect;
   - E7 integration/test-definition defect;
   - environment/configuration defect;
   - contract/semantic gap;
   - insufficient evidence;
3. identify the responsible owner only where traceback + contract/source evidence supports it;
4. do not infer ownership from suite directory alone;
5. do not fix anything.

If one upstream defect fans out into multiple suites, record it once with downstream affected suites rather than creating five speculative blockers.

## Required artifacts

Create/update only E7 evidence/status:

```text
status/e7/GATE_B_LOCAL_FAILURE_EVIDENCE_RECOVERY_20260825.md
coordination/E7/STATUS.md
```

You may also update E7-owned:

```text
status/INTEGRATION_STATUS.md
status/RELEASE_GATES.md
```

only to reconcile the already-reviewed executable result to:

```text
Gate B = BLOCKED / EXECUTABLE_VERIFICATION_FAIL
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

No PASS promotion is permitted.

## Terminal states

### DONE

Use DONE only if persisted evidence is sufficient to identify the actual failing tests/tracebacks and produce a bounded evidence-based triage suitable for PM to assign remediation.

STATUS must include:

- exact recovered evidence artifact path;
- exact failing tests/traceback locations;
- classification(s);
- evidence-supported `next_owner` recommendation(s), if determinable;
- explicit `project_executable_verification = NO_NEW_RUN`.

### BLOCKED

If persisted local evidence cannot provide the missing failing-test/traceback detail, stop with:

```text
state = BLOCKED
blocker = LOCAL_FAILURE_EVIDENCE_UNAVAILABLE
project_executable_verification = NO_NEW_RUN
next_authority = PM / Product Owner decision whether to authorize a bounded failing-suite rerun solely for complete diagnostics
```

Do not request or start that rerun yourself.

## Writable scope

E7-owned evidence/status only:

- `status/e7/**`;
- `status/INTEGRATION_STATUS.md`;
- `status/RELEASE_GATES.md`;
- `coordination/E7/STATUS.md` on the target branch.

No production code, contracts, ADRs, or test-definition edits.

## Completion / mailbox rule

Read latest main, verify task_id exactly `E7-20260825-060`, create/use `agent/e7-gate-b-failure-evidence-recovery-20260825`, recover only existing job evidence, commit/push allowed evidence/status, write terminal `coordination/E7/STATUS.md`, and stop.

Do not self-start remediation, rerun verification, Gate C, provider/private work, PAPER, SHADOW, LIVE, or another task.