# E4 Status

- task: `PRODUCT_OWNER_DIRECT_FP02_REASON_AGGREGATION_REMEDIATION_20260830`
- formal_mailbox_task_id: `NONE — direct Product Owner bounded defect remediation after approved-local qualification`
- agent: `E4`
- state: `PARTIAL`
- branch: `agent/e4-fp02-reason-aggregation-20260830`
- authoritative_main_at_task_start: `2fe9912429cad3eebebac1fa46f933b78f024b78`
- reproduced_qualification_revision: `bacb5205ac9b895bb968459f88f148323bcc5da6`
- source_fix_commit: `632ec79d7a3fdeb9491750ef44f6861afc869b34`
- regression_definition_commit: `84a9cdb76d217dc4f1ddfee71cfe6f3442ae7c09`
- handoff_commit: `d7f92f5c109b0c76fd117ce6ab6a7116ad29be62`
- head_before_terminal_status_commit: `d7f92f5c109b0c76fd117ce6ab6a7116ad29be62`
- handoff_path: `status/e4/FP02_REASON_AGGREGATION_REMEDIATION_20260830.md`
- summary: `Fixed only the deterministic FP-02 reason-code aggregation defect. Common validation no longer first-returns after the first rejection; independently valid common and role-specific diagnostics are collected, deduplicated, and ordered by the existing accepted FP-02 reason ordering while pre-existing capability-state precedence is preserved. E4-035 exact owner-row provenance hardening and all unresolved mutation-role semantics remain unchanged.`
- local_regression: `NOT_RUN / NOT_PASS — this ChatGPT session has no approved-local Windows checkout/execution surface`
- next_owner: `PM integrated requalification after approved-local execution of the corrected exact revision`

## Exact root cause

`src/brokers/okx_action_capability.py::_common_failures()` returned immediately on the first matching common rejection. `_derive_capability()` then returned immediately whenever that common state was non-null. Therefore independently valid role-specific diagnostics were unreachable.

The accepted matrix independently defines:

```text
OKX_SWAP_CALLER_CAPABILITY_ASSERTION_REJECTED
OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN
```

and the E7 integration definition `tests/integration/test_p0_fp02_fp16_composition.py::test_runtime_preflight_eligible_and_allowlist_facts_cannot_upgrade_fp02_provider_capability` requires both when a caller capability assertion is invalid while the PROTECTION_STOP provider-native fieldset remains unresolved.

## Exact fix boundary

- `_common_failures()` records all independently true accepted common reasons instead of returning after the first.
- The first common state-bearing rejection still preserves the resolver's previous deterministic state precedence.
- Role-specific evaluation always computes applicable diagnostics.
- Role state applies only when common validation found no state-bearing rejection.
- Common + role reasons are merged once.
- `_sorted_reasons()` now deduplicates explicitly without relying on set iteration order, then orders by existing `_REASON_ORDER` / `_REASON_INDEX`.
- Evidence construction, evidence identity, currentness semantics, vocabulary, and capability state labels are unchanged.

## Preserved E4-035 provenance hardening

Positive `REPO_EVIDENCED` rows remain only:

```text
ENTRY / net_mode
ENTRY / long_short_mode
READ_ONLY_RECONCILIATION / net_mode
READ_ONLY_RECONCILIATION / long_short_mode
```

They still require exact resolver-owned role/mode/descriptor/hash/ref/generation binding. Forged ref, forged generation, descriptor/hash mismatch, row cross-use, missing provenance, and caller-manufactured provenance remain fail closed.

## Mutation-role safety remains unchanged

```text
PROTECTION_STOP = UNRESOLVED_FAIL_CLOSED
POSITION_EXIT = UNRESOLVED_FAIL_CLOSED
EMERGENCY_EXIT = UNRESOLVED_FAIL_CLOSED
```

FP-03 ACTIONABLE does not prove trigger capability. FP-11 convergence does not prove provider protection mutation capability. FP-05 coherent sizing does not prove provider close capability. READ_ONLY_RECONCILIATION remains GET_ONLY/default-deny; mutation remains FORBIDDEN.

## Regression definitions

Updated only:

```text
tests/brokers/test_okx_action_capability.py
```

Coverage includes:

- existing single-rejection reason/state behavior;
- caller assertion rejected + provider fieldset unresolved -> both reasons;
- deterministic accepted reason order;
- duplicate reason deduplication;
- PROTECTION_STOP + FP-03 ACTIONABLE + FP-11 converged remains unresolved and keeps fieldset/trigger diagnostics;
- POSITION_EXIT + coherent FP-05 remains unresolved;
- EMERGENCY_EXIT no bypass;
- READ_ONLY mutation remains FORBIDDEN;
- exact ENTRY owner row remains REPO_EVIDENCED;
- forged owner provenance remains fail closed;
- aggregated evidence identity/currentness remains deterministic;
- same repeated input returns exact same ordered reason_codes;
- no provider/network/runtime/credential/capital dependency.

No E7-owned integration/safety test was modified.

## Verification

Approved-local reproduction supplied by Product Owner for exact revision `bacb5205ac9b895bb968459f88f148323bcc5da6`:

```text
Phase 1: 11/16 commands PASS; 212 passed; 21 failed; 8 errors; 0 skipped
Phase 2: 10/14 suites PASS; 828 passed; 21 failed; 8 errors; 0 skipped
```

Post-fix executable verification cannot be run from this chat because no approved-local Windows checkout/execution surface is exposed. GitHub Actions/CI/hosted/GitHub-triggered compute was not used.

```text
post_fix_project_executable_verification = NOT_RUN / NOT_PASS
```

Exact future approved-local Windows PowerShell commands:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests/brokers -p 'test_okx_action_capability.py' -v
python -m unittest discover -s tests/integration -p 'test_p0_fp02_fp16_composition.py' -v
python -m unittest discover -s tests/safety -p 'test_p0_integrated_fail_closed.py' -v
```

`NOT_RUN` is not PASS.

## Scope / safety

```text
files changed = src/brokers/okx_action_capability.py; tests/brokers/test_okx_action_capability.py; status/e4/FP02_REASON_AGGREGATION_REMEDIATION_20260830.md; coordination/E4/STATUS.md
contracts changed = NONE
E5/E6/E7 production changed = NONE
E7 tests changed = NONE
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order/protection actions = 0
runtime/process launch = 0
SHADOW = NOT_STARTED
PAPER = NOT_STARTED
LIVE = NOT_STARTED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

E4 stops on `PARTIAL`. Do not self-start integrated requalification or another task.
