# P0 Credential-Free Qualification Manifest — E7-111 / E7-112 / E7-113 / E7-114 update

## Purpose

This manifest defines the future approved-local qualification sequence for the integrated P0 executable candidate after the FP-16 source candidate and E7-114 governance/test-layout remediation are merged.

Prerequisites remain:

1. PM identifies the exact merged executable candidate revision;
2. approved-local infrastructure establishes that exact revision as `EXACT_CLEAN`;
3. a fresh E7 qualification task authorizes execution.

E7-114 itself executes nothing.

## Current qualification state

```text
qualification_revision = TBD AFTER MERGE + FRESH EXACT-CLEAN PREPARATION
project executable verification = NOT_RUN / NOT_PASS
FP-16 runtime-preflight tests = NOT_RUN / NOT_PASS
integrated P0 safety/E2E matrix = NOT_RUN / NOT_PASS
LF-0 = BLOCKED / UNCHANGED
LF-1 = NOT_RUN / NOT_PASS
LF-2 = PARTIAL / NOT PASS
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
process launch/restart = 0
order/protection actions = 0
SHADOW/PAPER = NOT_AUTHORIZED
bounded 10U live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN != PASS`.

## Revision provenance rules

- The future qualification revision is not yet known while this branch remains unmerged.
- E7-111 merge commit `ae2fcc5daacaf7045f1efab5e0778b921f12efed` predates the FP-16 executable candidate and cannot qualify it.
- Historical exact-clean revision `8fbf5fcae2eaf44accdf535121d8abf29ef5c93c` does not qualify this candidate.
- FP-03 combined candidate `9462b2594675b2e28388f55a2af189100b7cbdfc` is not established `EXACT_CLEAN` under current accepted evidence and does not qualify this candidate.
- E7-101 preparation request `REQ-E7-PREPARE-101-01-72A4C9E1` and job `JOB-41D0F958C484CCF7` are terminal/non-reusable.
- A fresh exact-clean preparation/equivalent approved-local operator fact plus a fresh qualification task/request identity are required after merge.
- No historical test PASS, suite count, or provider-facing evidence may be rebound to the future merged candidate.

## Required approved-local environment assertions

The future qualification host must be Product-Owner-approved Windows/non-GitHub execution, repository root, exact PM-bound merged revision, clean worktree, Python 3.10-compatible, and `PYTHONPATH=src`.

The qualification must use:

```text
provider/private API access = FORBIDDEN
credentials = NONE
provider/account mutation = 0
process launch/restart = 0
order/protection submit/cancel/amend/close = 0
SHADOW/PAPER/live runtime = NOT_STARTED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

## Exact future PowerShell preflight

```powershell
$ErrorActionPreference = 'Stop'
$ExpectedRevision = '<PM_BIND_EXACT_MERGED_P0_EXECUTABLE_REVISION_AFTER_PREPARATION>'

if ($ExpectedRevision -like '<*') {
    throw 'P0 qualification revision is still TBD; do not execute qualification.'
}

$ActualRevision = (git rev-parse HEAD).Trim()
if ($ActualRevision -ne $ExpectedRevision) {
    throw "Revision mismatch: expected $ExpectedRevision, got $ActualRevision"
}

$Worktree = @(git status --porcelain)
if ($Worktree.Count -ne 0) {
    throw 'Worktree is not clean; qualification is forbidden.'
}

$env:PYTHONPATH = 'src'
python --version
Write-Output "EXECUTION_REVISION=$ActualRevision"
Write-Output 'WORKING_TREE=CLEAN'
Write-Output 'PROVIDER_ACCESS=FORBIDDEN'
Write-Output 'CREDENTIALS=NONE'
Write-Output 'PROCESS_LAUNCH_RESTART=0_EXPECTED'
Write-Output 'MUTATION_REQUESTS=0_EXPECTED'
Write-Output 'GITHUB_COMPUTE=FORBIDDEN'
```

The durable result must record actual OS/build, Python version, exact revision, and clean/exact-clean fact. Do not persist local filesystem paths or secrets.

## Phase 1 — focused P0 owner + E7 matrix

Run, on the same approved exact-clean revision:

```powershell
$env:PYTHONPATH = 'src'

python -m unittest discover -s tests/position -p 'test_protection_trigger_validity.py' -v
python -m unittest discover -s tests/execution -p 'test_protection_trigger_consumer.py' -v

python -m unittest discover -s tests/execution -p 'test_external_close_evidence.py' -v
python -m unittest discover -s tests/position -p 'test_external_close_reinterpretation.py' -v

python -m unittest discover -s tests/brokers -p 'test_okx_close_sizing.py' -v

python -m unittest discover -s tests/execution -p 'test_protection_registry_evidence.py' -v
python -m unittest discover -s tests/position -p 'test_protection_registry_policy.py' -v
python -m unittest discover -s tests/storage -p 'test_protection_registry_currentness.py' -v
python -m unittest discover -s tests/storage -p 'test_external_close_currentness.py' -v
python -m unittest discover -s tests/storage -p 'test_external_close_currentness_supersession.py' -v

python -m unittest discover -s tests/integration -p 'test_runtime_preflight.py' -v
python -m unittest discover -s tests/integration -p 'test_p0_integrated_failure_prevention.py' -v
python -m unittest discover -s tests/safety -p 'test_p0_integrated_fail_closed.py' -v
python -m unittest discover -s tests/e2e -p 'test_p0_reconciliation_restart_e2e.py' -v
```

Every command must exit `0`. Actual test counts, failures, errors, and skips must be recorded. A skipped critical P0 test is not automatically accepted.

The consolidated `test_runtime_preflight.py` module must materially cover the E7-113/E7-114 external-consumer regressions:

- credential-free conditional participation from non-null current external-consumer authority;
- provider-read-only conditional participation from non-null current external-consumer authority;
- true no-external eligible case only when both input evidence and current authority show no external consumer;
- exact current external evidence + authority admissibility;
- evidence-without-authority and authority-without-evidence fail closed;
- stale/mismatched/incompatible external consumer fail closed;
- SHADOW unconditional external-consumer requirement;
- no provider/network/credential/process/order/runtime/capital authority side effects.

There is no separate external-consumer regression module or command after E7-114.

## Phase 2 — full current credential-free matrix

After focused P0 suites pass, run the full current matrix on the same exact revision/worktree/environment:

```powershell
$env:PYTHONPATH = 'src'

python -m unittest discover -s tests/market_data -p 'test_*.py' -v
python -m unittest discover -s tests/indicators -p 'test_*.py' -v
python -m unittest discover -s tests/strategy -p 'test_*.py' -v
python -m unittest discover -s tests/backtest -p 'test_*.py' -v
python -m unittest discover -s tests/validation -p 'test_*.py' -v
python -m unittest discover -s tests/execution -p 'test_*.py' -v
python -m unittest discover -s tests/brokers -p 'test_*.py' -v
python -m unittest discover -s tests/risk -p 'test_*.py' -v
python -m unittest discover -s tests/position -p 'test_*.py' -v
python -m unittest discover -s tests/storage -p 'test_*.py' -v
python -m unittest discover -s tests/platform -p 'test_*.py' -v
python -m unittest discover -s tests/integration -p 'test_*.py' -v
python -m unittest discover -s tests/e2e -p 'test_*.py' -v
python -m unittest discover -s tests/safety -p 'test_*.py' -v
```

Required future qualification result:

```text
14 / 14 suite directories PASS
focused P0 modules PASS including consolidated FP-16 tests
same exact revision for every command
same clean approved-local worktree
zero provider/private requests
zero credentials
zero provider/account mutation
zero process launch/restart
zero submit/cancel/amend/close/protection action
zero GitHub compute
```

Actual counts must be measured at execution time.

## Dependency / execution order

1. exact revision/worktree/environment preflight;
2. FP-03 owner producer/consumer tests;
3. FP-04/FP-10 owner evidence + E5 reinterpretation tests;
4. FP-05 owner close/residual tests;
5. FP-11 E4 evidence + E5 policy + E6 currentness tests;
6. consolidated FP-16 E7 runtime-preflight tests;
7. E7 P0 integration test;
8. E7 safety test;
9. E7 restart E2E test;
10. full 14-suite current project matrix;
11. E7/PM evidence reconciliation.

A failure stops qualification. Do not continue to provider-readonly, SHADOW, PAPER, bounded live-fire, Gate D, or LIVE from a failing/partial credential-free result.

## Evidence fields required

Future focused/full-suite evidence must record at minimum task/request/action/job identity where applicable, exact execution revision, clean/exact-clean fact, OS/build, Python version, `PYTHONPATH=src`, command identity, actual test counts/results/exit code/duration, and zero provider/private/credential/mutation/process/order/runtime/capital/GitHub-compute classifications.

Do not persist local filesystem paths, secrets, provider signatures/tokens/cookies, raw private provider payloads, unrelated shell history, or private exact balances unless a future separately authorized provider task explicitly defines a sanitized field.

## Scenario-to-suite coverage

| Failure-prevention class | Required focused evidence |
|---|---|
| FP-03 | E5 trigger-validity owner test + E4 consumer owner test + E7 integrated test |
| FP-04 | E4 external ownership evidence tests + FP-10/FP-11 consumers + E7 integrated test |
| FP-05 | E4 close/residual tests + E7 integrated/safety tests |
| FP-10 | E4 convergence evidence + E5 reinterpretation + E6 currentness + E7 integrated/safety/E2E |
| FP-11 | E4 registry evidence + E5 policy + E6 restart/currentness + E7 integrated/safety/E2E |
| FP-16 | `src/integration/runtime_preflight.py` + consolidated `tests/integration/test_runtime_preflight.py` + migrated E7 safety coverage; remains `IMPLEMENTED_UNQUALIFIED / NOT_RUN / NOT_PASS` until approved-local execution succeeds |
| FP-02 provider-native protection/close facts | remain `UNRESOLVED_PROVIDER_FACT`; credential-free tests prove fail-closed non-authorizing behavior, not provider compatibility |

## Qualification interpretation / blocker preservation

Passing this future credential-free manifest can establish only the exact revision's credential-free project/integration safety result. It does not itself establish production OKX compatibility, provider read-only verification, external operator/AgentBridge launcher enforcement, provider mutation capability, SHADOW/PAPER authorization, bounded 10U live-fire authorization, Gate D, or LIVE.

LF-0 remains blocked by approved-local exact-revision preparation infrastructure. E7-114 creates no Local Job Request and does not retry/reuse E7-101 evidence. The future flow must first establish the newly merged exact candidate as `EXACT_CLEAN` with fresh authoritative evidence before any command in this manifest may execute.
