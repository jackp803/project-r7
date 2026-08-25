# E7 Current Task

- task_id: `E7-20260825-061`
- issued_at: `2026-08-25T08:32:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-bounded-diagnostic-rerun-20260825`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate B source chain through PR #66, approved-local FAIL evidence PR #67 merge `3f676ed3245d78a54e232292e817c965934ca489`, accepted failure-evidence recovery blocker PR #68 merge `e6d210000e607c1dbcda5b43e4ef26b26bbd3814`, Product Owner explicit approval in PM control channel on `2026-08-25T08:32:00+08:00` for this bounded diagnostic rerun only
- source_execution_revision: `62bef3cedda7f7b65116defd9802e2aee37a4fb0`

## Objective

Execute only a bounded approved-local diagnostic rerun of the five Gate B suites that failed in E7-059:

```text
brokers
position
storage
integration
safety
```

The sole purpose is to capture complete diagnostic evidence sufficient for PM/E7 to identify actual root cause(s) and assign bounded remediation to the correct owner(s).

This task does **not** authorize remediation, production/test changes, a new ten-suite Gate B qualification run, Gate C, provider/private APIs, PAPER, SHADOW, LIVE, strategy promotion, exchange traffic, credentials, GitHub Actions/CI, hosted runners, or GitHub-triggered compute.

## Exact source revision rule

All five diagnostic suites must execute against exactly:

```text
62bef3cedda7f7b65116defd9802e2aee37a4fb0
```

This is the exact source revision that produced the authoritative E7-059 Gate B FAIL.

Before execution:

1. verify latest `main` TASK task_id is exactly `E7-20260825-061` and ACTIVE;
2. read `README.md`, `agents/README.md`, `agents/E7_INTEGRATION.md`, E7-059/E7-060 evidence, `status/RELEASE_GATES.md`, and `status/INTEGRATION_STATUS.md`;
3. use the Product Owner-approved local Windows/non-GitHub environment;
4. check out/use exact source revision `62bef3cedda7f7b65116defd9802e2aee37a4fb0` for project execution;
5. verify project source/test content at execution time is exactly that revision and clean before the first unittest command;
6. do not substitute current `main`, the diagnostic branch, or any newer production/test revision for execution;
7. create/use the target Git evidence branch separately for evidence/status commits after execution, without changing the diagnosed source/test content.

If exact revision or approved environment cannot be satisfied, stop `BLOCKED / REVISION_OR_ENVIRONMENT_MISMATCH` with `project_executable_verification = NOT_RUN`.

## Approved environment metadata

Before the first test command, capture and later persist sanitized evidence for:

- approved local machine/environment label;
- OS/version;
- Python executable path and Python version;
- repository path;
- exact checked-out revision;
- clean/dirty working-tree state;
- `PYTHONPATH`;
- diagnostic start timestamp.

Do not expose secrets, tokens, private keys, account identifiers, provider data, or sensitive user paths beyond what is needed to prove local execution.

## Exact diagnostic commands

From repository root in approved local Windows PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

Run all five even if an earlier suite fails, provided the approved environment remains valid.

Do not execute strategy, execution, platform, registry, e2e, backtests, network/provider calls, Paper daemons, exchange adapters, or any other project workload in this task.

## Diagnostic evidence requirements

For each of the five suites, persist all actual evidence needed to avoid another truncated-callback blocker:

- exact command;
- suite start/end timestamp;
- exit code;
- tests run count;
- complete failing test identifiers;
- whether each item is FAILURE or ERROR;
- assertion/error type and message;
- concise but sufficient traceback frames including repository file path, line number, and function/test name;
- first-order causal exception where chained exceptions exist;
- any repeated identical failure signature grouped without losing the list of affected tests.

Also persist:

- exact source revision;
- approved local environment metadata listed above;
- all five suite result summary;
- job/request identity if AgentBridge/local runner is used;
- explicit proof that all five results belong to this one approved bounded diagnostic request.

### Anti-truncation requirement

Do not rely on the terminal chat/AgentBridge callback as the only carrier of failure detail.

Before terminal STATUS, materialize a durable sanitized diagnostic artifact in Git under:

```text
status/e7/GATE_B_BOUNDED_DIAGNOSTIC_RERUN_20260825.md
```

That artifact must contain the failing test identifiers, error/assertion text, traceback locations, counts, timestamps, environment metadata, and exact revision needed for root-cause triage. Raw logs need not be committed if they contain excessive/noisy output, but every failure/error must be represented faithfully enough to reproduce ownership/contract triage without rerunning tests.

If the local runner cannot provide enough output to populate that artifact, stop `BLOCKED / DIAGNOSTIC_OUTPUT_INSUFFICIENT`; do not infer root cause and do not launch another job.

## Evidence-only triage

After the five suites finish, E7 may perform static Git read-only inspection against contracts/source to classify each distinct first-order failure cause as one of:

- `SETTLED_CONTRACT_IMPLEMENTATION_DEFECT`;
- `E7_TEST_OR_INTEGRATION_DEFINITION_DEFECT`;
- `ENVIRONMENT_OR_CONFIGURATION_DEFECT`;
- `CONTRACT_OR_SEMANTIC_GAP`;
- `INSUFFICIENT_EVIDENCE`.

For each distinct cause, record:

- affected failing tests/suites;
- exact evidence;
- responsible owner recommendation only where supported by traceback + contract/source ownership;
- whether one upstream cause fans out into multiple suites.

Do not assign owner from suite directory alone. Do not fix anything in this task.

## Release interpretation

The authoritative release state remains:

```text
Gate B = BLOCKED / EXECUTABLE_VERIFICATION_FAIL
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

This diagnostic rerun cannot promote Gate B even if one or more rerun suites unexpectedly pass. A later full Gate B qualification rerun, if justified after remediation, will require a separate PM/PO decision and exact-revision task.

## Writable scope

E7 evidence/status only:

- `status/e7/GATE_B_BOUNDED_DIAGNOSTIC_RERUN_20260825.md`;
- `coordination/E7/STATUS.md` on target branch;
- `status/INTEGRATION_STATUS.md` / `status/RELEASE_GATES.md` only if needed to record factual diagnostic disposition while keeping Gate B BLOCKED.

Forbidden:

- production code changes;
- any E1-E6 test changes;
- E7 test-definition changes;
- contracts/ADR changes;
- `.github/workflows/**` or any GitHub compute;
- provider/private API/network/credentials;
- PAPER/SHADOW/LIVE;
- strategy promotion;
- remediation implementation;
- another task.

## Terminal states

### DONE

Use DONE only when all five approved diagnostic suites actually ran at exact source revision and the durable diagnostic artifact contains sufficient evidence for bounded root-cause/owner triage.

STATUS must include:

- task_id `E7-20260825-061`;
- exact source revision;
- all five suite exit codes/counts;
- diagnostic artifact path;
- distinct failure classifications;
- evidence-supported next_owner recommendation(s), if determinable;
- `project_executable_verification = RAN / DIAGNOSTIC_ONLY`;
- Gate B still BLOCKED;
- no remediation started.

### PARTIAL

Use PARTIAL if execution starts but not all five suites complete. Persist all obtained diagnostics and exact cause.

### BLOCKED

Use BLOCKED if approved environment/exact revision cannot be satisfied or diagnostic output is still insufficient for evidence-based triage. Do not start remediation.

## Completion / mailbox rule

Commit/push only allowed E7 evidence/status changes to `agent/e7-gate-b-bounded-diagnostic-rerun-20260825`, write terminal `coordination/E7/STATUS.md`, and stop.

Do not self-start remediation, another verification run, Gate C, provider/private work, PAPER, SHADOW, LIVE, or another task. PM will review terminal evidence and assign any bounded remediation through the correct owner TASK mailbox.