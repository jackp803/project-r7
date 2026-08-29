# P0 Credential-Free Qualification Manifest — E7-20260829-116

## Purpose

This manifest defines the deterministic future approved-local credential-free qualification sequence for the P0 candidate containing merged FP-02/03/04/05/10/11/16 owner implementations plus E7-116 cross-module definitions.

This task executes nothing. Qualification may start only after:

1. E7-116 is merged;
2. PM identifies the exact resulting candidate revision;
3. fresh approved-local evidence establishes that exact revision `EXACT_CLEAN`;
4. a fresh E7 execution task authorizes qualification.

## Current state

```text
qualification_revision = TBD UNTIL E7-116 MERGE + FRESH EXACT-CLEAN PREPARATION
project executable verification = NOT_RUN / NOT_PASS
P0 integrated credential-free execution = NOT_RUN / NOT_PASS
FP-02 executable verification = NOT_RUN / NOT PASS
FP-16 executable verification = NOT_RUN / NOT PASS
LF-0 = BLOCKED / UNCHANGED
LF-1 = NOT_RUN / NOT PASS
LF-2 = PARTIAL / NOT PASS
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order/protection actions = 0
process launch/restart = 0
SHADOW/PAPER = NOT_AUTHORIZED
10U bounded live fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN != PASS`.

## Revision provenance

- Qualification revision is deliberately `TBD`; the current branch head is not a substitute for a future merged and approved-local exact-clean candidate.
- Historical exact-clean revision `8fbf5fcae2eaf44accdf535121d8abf29ef5c93c` is historical only and cannot qualify the E7-116 candidate.
- Historical FP-03 combined candidate `9462b2594675b2e28388f55a2af189100b7cbdfc` does not qualify the later integrated candidate.
- E7-101 preparation request `REQ-E7-PREPARE-101-01-72A4C9E1` is terminal/non-reusable.
- E7-101 job `JOB-41D0F958C484CCF7` is `REFUSED` and terminal/non-reusable.
- Historical provider-facing revision/evidence remains bound to its own revision and is not imported into credential-free qualification.
- No prior test count or PASS may be copied to the future candidate; actual counts must be measured during the authorized run.

## Approved-local environment requirements

Qualification must run from repository root on a Product-Owner-approved Windows, non-GitHub environment with:

- exact PM-bound candidate revision;
- fresh authoritative exact-revision preparation/equivalent operator fact;
- clean worktree;
- `PYTHONPATH=src`;
- actual Windows build and Python version recorded;
- no GitHub Actions, GitHub-hosted runner, GitHub-triggered runner or CI;
- provider/private API access forbidden;
- credentials not read/requested/used;
- provider/account mutation zero;
- process launch/restart zero for this qualification;
- submit/cancel/amend/close/protection provider actions zero;
- SHADOW/PAPER/live runtime not started;
- capital exposure none.

## PowerShell exact-revision preflight

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
Write-Output 'CAPITAL_EXPOSURE=NONE_EXPECTED'
Write-Output 'GITHUB_COMPUTE=FORBIDDEN'
```

The future durable result must record the actual OS/build, Python version, exact revision and exact-clean/clean-worktree evidence. It must not persist local filesystem paths or secrets.

## Phase 1 — focused P0 deterministic sequence

Run these commands in exactly this order on the same exact clean revision and environment:

```powershell
$env:PYTHONPATH = 'src'

# FP-02 owner capability boundary
python -m unittest discover -s tests/brokers -p 'test_okx_action_capability.py' -v

# FP-03 owner producer / E4 consumer
python -m unittest discover -s tests/position -p 'test_protection_trigger_validity.py' -v
python -m unittest discover -s tests/execution -p 'test_protection_trigger_consumer.py' -v

# FP-04 + FP-10 E4/E5 owner chain
python -m unittest discover -s tests/execution -p 'test_external_close_evidence.py' -v
python -m unittest discover -s tests/position -p 'test_external_close_reinterpretation.py' -v

# FP-05 owner close/residual sizing
python -m unittest discover -s tests/brokers -p 'test_okx_close_sizing.py' -v

# FP-11 E4 producer / E5 policy / E6 persistence-currentness
python -m unittest discover -s tests/execution -p 'test_protection_registry_evidence.py' -v
python -m unittest discover -s tests/position -p 'test_protection_registry_policy.py' -v
python -m unittest discover -s tests/storage -p 'test_protection_registry_currentness.py' -v

# FP-10 E6 persistence/currentness and supersession
python -m unittest discover -s tests/storage -p 'test_external_close_currentness.py' -v
python -m unittest discover -s tests/storage -p 'test_external_close_currentness_supersession.py' -v

# FP-16 owner evaluator
python -m unittest discover -s tests/integration -p 'test_runtime_preflight.py' -v

# E7 P0 composition, including newly merged FP-02 -> FP-03/05/11/16 seams
python -m unittest discover -s tests/integration -p 'test_p0_fp02_fp16_composition.py' -v
python -m unittest discover -s tests/integration -p 'test_p0_integrated_failure_prevention.py' -v
python -m unittest discover -s tests/safety -p 'test_p0_integrated_fail_closed.py' -v
python -m unittest discover -s tests/e2e -p 'test_p0_reconciliation_restart_e2e.py' -v
```

Every command must exit `0`. Record actual tests run, passed, failed, errored and skipped for each command. A critical skipped scenario is not automatically accepted.

## Required scenario coverage by focused modules

### FP-02

`tests/brokers/test_okx_action_capability.py` plus `tests/integration/test_p0_fp02_fp16_composition.py` must materially prove:

- only exact canonical ENTRY/READ_ONLY owner rows can be `REPO_EVIDENCED`;
- copied/forged provenance and cross-role/mode use fail closed;
- PROTECTION_STOP remains unresolved despite FP-03/FP-11 positive project evidence;
- POSITION_EXIT and EMERGENCY_EXIT remain unresolved despite coherent FP-05 sizing;
- emergency does not bypass provider proof;
- READ_ONLY is GET-only/default-deny and cannot mutate;
- repository capability evidence is not provider verification, local mutation allowlisting, runtime authorization, Product Owner authority or capital authority;
- material owner-row change invalidates prior positive evidence.

### FP-03 / FP-04 / FP-05 / FP-10 / FP-11

Focused owner and E7 modules must preserve:

- breached/equality/stale trigger fail closed and no time-only retry authority;
- external/manual/prior/unknown/conflicting ownership no silent adoption;
- current actual reducible exposure/residual semantics and no original-entry-quantity fallback;
- order status/arithmetic zero not flatness authority;
- flat Position with unresolved execution/protection not lifecycle-close eligible;
- exactly-one intended/current-owned/current-lineage protection is the sole healthy registry case;
- no non-green registry state creates cleanup/create mutation authority;
- E6 restart/currentness uses exact current material and supersession, not row arrival.

### FP-16 composition

`tests/integration/test_runtime_preflight.py` plus `tests/integration/test_p0_fp02_fp16_composition.py` must materially prove:

- `ELIGIBLE` is admission evidence only;
- local action capability/allowlist evidence cannot substitute for E4 provider-native capability proof;
- E4 `REPO_EVIDENCED` cannot substitute for runtime/Product Owner authorization;
- current external-consumer authority with missing matching evidence fails closed;
- runtime role authority is non-transferable;
- bounded-live-fire mode policy remains undefined/fail closed under V0.1;
- historical exact-clean evidence/revision cannot satisfy the current candidate.

## Phase 2 — full current 14-suite credential-free matrix

Only after every Phase 1 command passes, run the complete current project matrix on the same exact revision/worktree/environment:

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

Future qualification requires:

```text
14 / 14 suite directories PASS
all focused P0 commands PASS
same exact candidate revision for every command
same approved-local clean worktree
actual counts measured, not guessed
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order/protection actions = 0
process launch/restart = 0
SHADOW/PAPER/live runtime = NOT_STARTED
capital exposure = NONE
GitHub compute = NOT_USED
```

A failure stops qualification. Do not continue to provider read-only, SHADOW/PAPER, bounded live fire, Gate D or LIVE from a failing or partial credential-free result.

## Future evidence fields

For every focused/full command, persist sanitized durable evidence containing at minimum:

- task/request/action/job identity when applicable;
- exact execution revision;
- clean/exact-clean fact;
- OS product/build;
- Python version;
- `PYTHONPATH=src`;
- command/module identity;
- actual test count;
- passed/failed/error/skipped counts;
- exit code and duration/time boundary;
- provider requests = 0;
- private API = NONE;
- credentials read/requested/used = NONE;
- provider/account mutation = 0;
- order/protection actions = 0;
- process launch/restart = 0;
- SHADOW/PAPER/live = NOT_STARTED;
- capital exposure = NONE;
- GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED.

Do not persist secrets, local filesystem paths, provider signatures/tokens/cookies, raw private provider payloads, unrelated shell history or exact private balances.

## Interpretation

A future credential-free PASS can prove only the exact candidate's deterministic project/integration behavior. It does not establish:

- production OKX provider compatibility for unresolved protection/exit fieldsets;
- provider/private verification;
- secure credential/runtime readiness;
- AgentBridge/operator launcher enforcement;
- provider mutation capability;
- SHADOW/PAPER authorization;
- bounded 10U live-fire authorization;
- Gate D or recurring LIVE.

Those remain later gates. Provider read-only and later runtime/capital stages require fresh authority under the accepted readiness profile.

## LF-0 blocker preservation

LF-0 remains blocked by approved-local exact-revision preparation infrastructure until fresh current-candidate evidence establishes the future merged revision as `EXACT_CLEAN`. E7-116 creates no Local Job Request and does not retry/reuse the terminal E7-101 request/job identities.
