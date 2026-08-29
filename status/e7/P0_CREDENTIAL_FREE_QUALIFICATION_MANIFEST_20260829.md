# P0 Credential-Free Qualification Manifest — E7-20260829-111

## Purpose

This manifest defines the exact future approved-local qualification sequence for the integrated P0 static candidate after:

1. E7-111 test definitions are merged;
2. PM identifies the exact merged integration candidate revision;
3. approved-local infrastructure establishes that exact revision as `EXACT_CLEAN`;
4. a fresh E7 qualification task authorizes execution.

E7-111 itself executes nothing.

## Current qualification state

```text
qualification_revision = TBD AFTER MERGE + EXACT-CLEAN PREPARATION
project executable verification = NOT_RUN / NOT_PASS
integrated P0 safety/E2E matrix = NOT_RUN / NOT_PASS
LF-0 = BLOCKED / UNCHANGED
LF-1 = NOT_RUN / NOT_PASS
LF-2 = PARTIAL / NOT PASS
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order/protection actions = 0
SHADOW/PAPER = NOT_AUTHORIZED
bounded 10U live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN != PASS`.

## Revision provenance rules

- The future qualification revision is **not yet known** because the E7-111 branch is not the merged integration candidate while this manifest is authored.
- Historical exact-clean revision `8fbf5fcae2eaf44accdf535121d8abf29ef5c93c` does **not** qualify this candidate.
- FP-03 combined candidate `9462b2594675b2e28388f55a2af189100b7cbdfc` is not `EXACT_CLEAN` under current accepted evidence and does not qualify the E7-111 integrated candidate.
- E7-101 preparation request `REQ-E7-PREPARE-101-01-72A4C9E1` is terminal/non-reusable.
- E7-101 local job `JOB-41D0F958C484CCF7` is `REFUSED` and is terminal/non-reusable evidence.
- A fresh exact-clean preparation/equivalent operator fact and a fresh qualification task/request identity are required after merge.
- No historical test PASS or provider-facing evidence may be rebound to the future merged candidate.

## Required approved-local environment assertions

The qualification host must be:

- Product-Owner-approved Windows/non-GitHub local execution environment;
- repository root working directory;
- exact PM-bound merged candidate revision;
- clean worktree with no untracked/modified project files affecting execution;
- Python 3.10-compatible project runtime; prior accepted Windows evidence used Python `3.10.6`, but the future task must record the actual interpreter version;
- `PYTHONPATH=src`;
- no GitHub Actions/CI/hosted runner/GitHub-triggered runner;
- no provider/private API access for this qualification;
- no credentials read/requested/used;
- no provider/account mutation;
- no order/protection submit/cancel/amend/close;
- no SHADOW/PAPER/live runtime;
- no capital exposure.

## PowerShell preflight — exact future command block

Run from repository root on the approved Windows host only. PM must replace the placeholder with the exact merged revision after integration and exact-clean preparation is accepted.

```powershell
$ErrorActionPreference = 'Stop'
$ExpectedRevision = '<PM_BIND_EXACT_MERGED_P0_INTEGRATION_REVISION_AFTER_PREPARATION>'

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
Write-Output 'MUTATION_REQUESTS=0_EXPECTED'
Write-Output 'GITHUB_COMPUTE=FORBIDDEN'
```

The future durable result must record the actual OS build, Python version, exact revision, and clean-worktree result. Do not persist local filesystem paths or secrets.

## Phase 1 — focused P0 owner + integrated matrix

Run these exact commands after the preflight succeeds:

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

python -m unittest discover -s tests/integration -p 'test_p0_integrated_failure_prevention.py' -v
python -m unittest discover -s tests/safety -p 'test_p0_integrated_fail_closed.py' -v
python -m unittest discover -s tests/e2e -p 'test_p0_reconciliation_restart_e2e.py' -v
```

Every command must exit `0`. Actual tests run, failures, errors and skips must be recorded per module. A skipped critical P0 test is not automatically accepted; PM/E7 must review the skip reason.

## Phase 2 — current full credential-free matrix

After focused P0 suites pass, run the full current project matrix on the same exact revision/worktree/environment:

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
focused P0 modules PASS
same exact revision for every command
same clean approved-local worktree
zero provider/private requests
zero credentials
zero provider/account mutation
zero submit/cancel/amend/close/protection action
zero GitHub compute
```

Actual test counts must be measured at execution time. Do not reuse historical counts.

## Dependency / execution order

1. exact revision/worktree/environment preflight;
2. FP-03 owner producer/consumer tests;
3. FP-04/FP-10 owner evidence + E5 reinterpretation tests;
4. FP-05 owner close/residual tests;
5. FP-11 E4 evidence + E5 policy + E6 currentness tests;
6. E7 integration test;
7. E7 safety test;
8. E7 restart E2E test;
9. full 14-suite current project matrix;
10. E7/PM evidence reconciliation.

A failure stops the qualification. Do not continue to provider-readonly, SHADOW, PAPER, bounded live-fire, Gate D or LIVE from a failing/partial credential-free result.

## Evidence fields required per focused/full suite

Persist sanitized durable evidence containing at minimum:

- `task_id`
- future `request_id` / `action_id` / `job_id` when AgentBridge is used under a fresh task
- `execution_revision`
- `working_tree = CLEAN / EXACT_CLEAN` as authorized evidence permits
- OS product/build
- Python version
- `PYTHONPATH=src`
- suite/module command identity
- test count actually run
- pass/failure/error/skip counts
- process exit code
- start/end or duration
- `provider_requests = 0`
- `private_api_access = NONE`
- `credentials_read_requested_used = NONE`
- `mutation_requests = 0`
- `submit_cancel_amend_close_protection = 0`
- `shadow_runtime = NOT_STARTED`
- `paper_runtime = NOT_STARTED`
- `capital_exposure = NONE`
- `github_actions_ci_hosted_runner = NOT_USED`
- `github_triggered_compute = NOT_USED`

Do not persist:

- local filesystem paths;
- API keys/secrets/passphrases;
- provider signatures/tokens/cookies;
- raw private provider payloads;
- exact private account balance unless a future authorized provider task explicitly defines a sanitized field;
- shell history unrelated to the approved action.

## Scenario-to-suite coverage

| Failure-prevention class | Required focused evidence |
|---|---|
| FP-03 | E5 trigger-validity owner test + E4 consumer owner test + E7 integrated test |
| FP-04 | E4 external ownership evidence tests + FP-10/FP-11 consumers + E7 integrated test |
| FP-05 | E4 close/residual tests + E7 integrated/safety tests |
| FP-10 | E4 convergence evidence + E5 reinterpretation + E6 currentness + E7 integrated/safety/E2E |
| FP-11 | E4 registry evidence + E5 policy + E6 restart/currentness + E7 integrated/safety/E2E |
| FP-16 | E7 safety static contract assertion only until an executable runtime-preflight implementation exists; remains `CONTRACT_ONLY` and cannot PASS as executable runtime preflight |
| FP-02 provider-native protection/close facts | remain `UNRESOLVED_PROVIDER_FACT`; credential-free tests must prove fail-closed non-authorizing behavior, not simulate provider compatibility |

## Qualification interpretation

Passing this future credential-free manifest can establish only the exact revision's credential-free static/integration safety result. It does not by itself establish:

- production OKX provider compatibility;
- provider read-only verification;
- provider mutation capability;
- SHADOW or PAPER runtime authorization;
- bounded 10U live-fire authorization;
- Gate D;
- LIVE.

FP-16 executable runtime-preflight and unresolved FP-02 provider-native facts remain separate dependencies even if every currently implemented credential-free suite passes.

## Current blocker preservation

LF-0 remains blocked by approved-local exact-revision preparation infrastructure. E7-111 creates no Local Job Request and does not retry/reuse E7-101 evidence. The future PM/E7 flow must first establish the newly merged exact candidate as `EXACT_CLEAN` with fresh authoritative evidence before any command in this manifest may be executed.
