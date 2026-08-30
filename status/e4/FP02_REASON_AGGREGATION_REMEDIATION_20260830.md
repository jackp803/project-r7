# E4 FP-02 Reason Aggregation Remediation — 2026-08-30

## Authority / scope

```text
owner = E4 — Execution / Broker Integration Engineer
source_qualification_revision = bacb5205ac9b895bb968459f88f148323bcc5da6
target_branch = agent/e4-fp02-reason-aggregation-20260830
branch_base_main = 2fe9912429cad3eebebac1fa46f933b78f024b78
result = PARTIAL / SOURCE + REGRESSION DEFINITIONS COMPLETE / LOCAL EXECUTION NOT_RUN
```

This remediation handles only the deterministic FP-02 OKX SWAP action-role capability resolver reason-code aggregation defect. It does not redo E4-20260829-035 provenance hardening and does not modify FP-11 timestamp normalization, canonical import architecture, provider transport/auth, strategy, backtest, risk, runtime, LIVE, or capital policy.

## Qualification evidence supplied by Product Owner

Exact approved-local credential-free qualification revision:

```text
bacb5205ac9b895bb968459f88f148323bcc5da6
```

Observed qualification totals:

```text
Phase 1: 11/16 commands PASS; 212 passed; 21 failed; 8 errors; 0 skipped
Phase 2: 10/14 suites PASS; 828 passed; 21 failed; 8 errors; 0 skipped
```

The bounded E4 root cause is the FP-02 resolver's first-rejection short-circuit.

## Repository reproduction / accepted semantics

The accepted matrix `docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md` independently defines both of these fail-closed reasons:

```text
OKX_SWAP_CALLER_CAPABILITY_ASSERTION_REJECTED
OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN
```

The E7-owned integration definition `tests/integration/test_p0_fp02_fp16_composition.py::test_runtime_preflight_eligible_and_allowlist_facts_cannot_upgrade_fp02_provider_capability` supplies a PROTECTION_STOP evaluation where a caller-provided runtime-preflight evidence object is an invalid capability assertion while the provider-native protection fieldset remains unresolved. The integration definition requires both reasons to remain visible.

Before this fix:

```text
_common_failures()
  caller_capability_assertion is not None
  -> return UNRESOLVED_FAIL_CLOSED + caller-assertion reason

_derive_capability()
  sees common state
  -> immediate return

PROTECTION_STOP role diagnostics
  -> unreachable
```

Therefore the resolver retained only the first valid rejection reason and discarded independently valid role-specific fail-closed evidence.

The E7 safety definition `tests/safety/test_p0_integrated_fail_closed.py` was also reviewed. It contains no contrary reason-ordering rule and continues to require unresolved provider/native close/protection capability to remain non-authorizing.

## Fix

`src/brokers/okx_action_capability.py` now separates state precedence from diagnostic reason aggregation:

1. common validation records all independently true accepted common reasons;
2. the first common state-bearing rejection retains the resolver's pre-existing state precedence;
3. role-specific evaluation always computes its applicable state/reasons;
4. role state is used only if no common state-bearing rejection exists;
5. common and role reasons are merged;
6. reasons are deduplicated without relying on set iteration order;
7. final reasons are ordered by the existing accepted `_REASON_ORDER` / `_REASON_INDEX` vocabulary;
8. evidence is constructed once and keeps the existing deterministic identity/currentness semantics.

No capability-state label, provider field, provider endpoint, or positive role row was added.

## Preserved E4-035 provenance hardening

The only positive repository rows remain exactly:

```text
ENTRY / net_mode
ENTRY / long_short_mode
READ_ONLY_RECONCILIATION / net_mode
READ_ONLY_RECONCILIATION / long_short_mode
```

`REPO_EVIDENCED` still requires exact resolver-owned binding of:

```text
role
position mode
provider fieldset descriptor
provider fieldset hash
E4-owned provider_fieldset_ref
E4-owned provider_fieldset_generation_id
```

Forged ref, forged generation, descriptor/hash mismatch, row cross-use, missing provenance, and caller-manufactured provenance remain fail closed.

## Mutation-role safety preserved

```text
PROTECTION_STOP = UNRESOLVED_FAIL_CLOSED
POSITION_EXIT = UNRESOLVED_FAIL_CLOSED
EMERGENCY_EXIT = UNRESOLVED_FAIL_CLOSED
```

FP-03 ACTIONABLE does not prove provider trigger basis. FP-11 converged registry does not prove provider protection mutation capability. FP-05 coherent sizing does not prove provider exit capability. Emergency urgency does not bypass provider proof.

READ_ONLY_RECONCILIATION remains GET_ONLY/default-deny; mutation remains FORBIDDEN with `OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN`.

## Regression definitions

Updated only E4-owned `tests/brokers/test_okx_action_capability.py`.

Definitions now cover:

- existing single-rejection cases remain single and state-compatible;
- caller capability assertion + unproven provider fieldset returns both accepted reasons;
- PROTECTION_STOP + caller assertion + FP-03 ACTIONABLE + FP-11 converged remains UNRESOLVED_FAIL_CLOSED and exposes provider fieldset + caller assertion + trigger basis reasons;
- duplicate trigger-basis diagnostics deduplicate to one reason;
- reason ordering is the existing accepted `_REASON_ORDER` order;
- repeated identical inputs produce identical ordered reason codes;
- aggregated evidence identity is deterministic and evaluation-time-only change remains current;
- FORBIDDEN state precedence remains intact while other diagnostics are retained;
- exact ENTRY owner row remains REPO_EVIDENCED;
- forged owner provenance remains fail closed;
- POSITION_EXIT + coherent FP-05 remains unresolved;
- EMERGENCY_EXIT has no bypass;
- READ_ONLY mutation remains FORBIDDEN;
- no provider/network/runtime/credential/capital dependency is introduced.

No E7-owned integration or safety test was modified.

## Verification

This ChatGPT session does not expose an approved-local Windows checkout/execution surface. GitHub Actions/CI/hosted/GitHub-triggered compute was not used.

```text
local_regression = NOT_RUN / NOT_PASS
```

Required future approved-local Windows PowerShell commands:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests/brokers -p 'test_okx_action_capability.py' -v
python -m unittest discover -s tests/integration -p 'test_p0_fp02_fp16_composition.py' -v
python -m unittest discover -s tests/safety -p 'test_p0_integrated_fail_closed.py' -v
```

`NOT_RUN` is not PASS. Historical qualification counts are reproduction evidence for `bacb520...`; they are not rebound as post-fix PASS evidence.

## Files changed

```text
src/brokers/okx_action_capability.py
tests/brokers/test_okx_action_capability.py
status/e4/FP02_REASON_AGGREGATION_REMEDIATION_20260830.md
coordination/E4/STATUS.md
```

## Safety / authority state

```text
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

## Handoff

Source and regression-definition remediation are complete. Post-fix approved-local execution remains unavailable in this session, so terminal classification is PARTIAL rather than DONE.

```text
NEXT = Return to PM. Do not start integrated requalification.
```
