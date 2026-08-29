# E4 Current Task

- task_id: `E4-20260829-035`
- issued_at: `2026-08-29T21:00:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-fp02-action-capability-evidence-20260829`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, accepted E4 design profile `okx-swap-action-role-capability-v0.1`, `docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md`, `status/PM_E4_034_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Remediate only the PM-identified FP-02 **positive repository-evidence provenance fail-open** on the existing unmerged E4-034 branch, add deterministic regression definitions in the existing authorized test module, update E4 evidence/status, and stop.

Do not expand provider semantics, execute project code, call provider endpoints, inspect/request credentials, change provider transport/auth/signing/private API calls, launch runtime/processes, mutate provider/account state, submit/cancel/amend/close/protection orders, start SHADOW/PAPER/live runtime, expose/move capital, create Local Job Requests, prepare exact revisions, or use GitHub compute.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E4_EXECUTION.md`;
- `docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md`;
- `status/PM_E4_034_REVIEW_20260829.md`;
- current branch `src/brokers/okx_action_capability.py`;
- current branch `tests/brokers/test_okx_action_capability.py`;
- current branch `status/e4/FP02_OKX_SWAP_ACTION_CAPABILITY_IMPLEMENTATION_20260829.md`;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

Verify wake task ID exactly `E4-20260829-035`. Execute only this task and do not read/execute another Worker's TASK mailbox.

## Precise defect to fix

The E4-034 resolver currently allows a positive repository capability row when a caller supplies:

- a fieldset equal to the public expected descriptor;
- the deterministic hash of that descriptor;
- any non-null `provider_fieldset_ref`;
- any non-null `provider_fieldset_generation_id`.

Because descriptor and hash are publicly reproducible and ref/generation are not matched to an E4-owner-authoritative current repository identity, a caller can manufacture `REPO_EVIDENCED` by copying the descriptor, recomputing the hash, and inventing ref/generation values.

That violates the accepted requirement that positive capability bind the exact current E4 repository-evidenced field-set rather than caller-manufactured fields.

## Required remediation

Within the existing E4-local module/test/evidence paths only:

1. Preserve the pure/provider-local/no-I/O resolver boundary.
2. Define or consume an **E4-owner-authoritative immutable repository row identity** for each currently positive row:
   - `ENTRY / net_mode`;
   - `ENTRY / long_short_mode`;
   - `READ_ONLY_RECONCILIATION / net_mode`;
   - `READ_ONLY_RECONCILIATION / long_short_mode`.
3. That owner-authoritative identity must bind, as one exact row, at least:
   - action role;
   - position mode;
   - exact repository fieldset descriptor;
   - exact deterministic descriptor hash;
   - exact stable E4-owned fieldset reference;
   - exact stable E4-owned fieldset generation identifier.
4. A positive `REPO_EVIDENCED` result must require exact match to that owner-authoritative row identity. Merely supplying a correct public descriptor/hash with arbitrary ref/generation is insufficient.
5. Do not treat a generic caller-passed "authority" boolean/dictionary as proof. If a helper/typed owner row is introduced, its positive values must be resolver/E4-owned canonical row material, not caller-selected arbitrary identity strings.
6. Forged/arbitrary/mismatched fieldset ref, generation, descriptor, hash, role/mode cross-use, or missing owner-row material must fail closed using the existing accepted E4-local vocabulary, preferably `OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN` where applicable.
7. Preserve current caller capability assertion rejection.
8. Preserve all existing unresolved provider facts:
   - `PROTECTION_STOP = UNRESOLVED_FAIL_CLOSED`;
   - `POSITION_EXIT = UNRESOLVED_FAIL_CLOSED`;
   - `EMERGENCY_EXIT = UNRESOLVED_FAIL_CLOSED`;
   - FP-03 `LAST_PRICE` never selects provider trigger basis;
   - FP-05 sizing never proves endpoint/`posSide`/native reduce-only/close fieldset;
   - emergency urgency grants no bypass.
9. Preserve `READ_ONLY_RECONCILIATION` as exact GET-only/default-deny observation capability; mutation remains `FORBIDDEN / OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN`.
10. Preserve deterministic identity/currentness: wall-clock-only change does not upgrade evidence; material owner-row generation/hash/ref change invalidates prior evidence. Do not invent TTLs.
11. Do not add provider-native endpoint/field facts beyond already accepted ENTRY/read-only repository mapping.
12. Do not change shared contracts/ADRs.

## Required regression definitions

Modify the existing authorized file only:

`tests/brokers/test_okx_action_capability.py`

Cover at minimum:

- exact canonical ENTRY net_mode owner row -> `REPO_EVIDENCED`;
- exact canonical ENTRY long_short_mode owner row -> `REPO_EVIDENCED`;
- exact canonical READ_ONLY owner row -> `REPO_EVIDENCED`;
- copied correct descriptor + correct reproducible hash + forged ref -> `UNRESOLVED_FAIL_CLOSED / OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN`;
- copied correct descriptor + correct hash + forged generation -> fail closed;
- valid ref/generation paired with wrong role or wrong mode -> fail closed;
- descriptor/hash mismatch -> fail closed;
- missing ref/generation -> fail closed;
- existing caller capability assertion remains rejected;
- existing PROTECTION_STOP / POSITION_EXIT / EMERGENCY_EXIT unresolved tests remain intact;
- read-only mutation rejection remains intact;
- deterministic identity/currentness remains intact;
- no provider/network/credentials/private API/process/runtime/order mutation/capital dependency.

Do not execute tests through GitHub or in this ChatGPT environment.

## Verification boundary

All executable verification remains local-only. LF-0 approved-local exact-revision preparation remains blocked.

Unless separately authoritative approved-local exact-revision evidence already exists for the exact resulting revision, record:

```text
project executable verification = NOT_RUN / NOT_PASS
FP-02 capability resolver tests = NOT_RUN / NOT_PASS
LF-0 = BLOCKED / UNCHANGED
LF-1 = NOT_RUN / NOT_PASS
LF-2 = PARTIAL / NOT PASS
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order/protection actions = 0
process launch/restart = 0
SHADOW/PAPER = NOT_AUTHORIZED
10U bounded live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN` is not PASS.

## Required durable evidence

Update:

`status/e4/FP02_OKX_SWAP_ACTION_CAPABILITY_IMPLEMENTATION_20260829.md`

Document the PM defect, exact owner-authoritative repository-row binding used, regression definitions, unchanged unresolved provider semantics, future local commands, and zero provider/credential/mutation/runtime/capital authority.

Update `coordination/E4/STATUS.md`, commit, and push the existing target branch.

## Writable scope

Only:

- `src/brokers/okx_action_capability.py`;
- `tests/brokers/test_okx_action_capability.py`;
- `status/e4/FP02_OKX_SWAP_ACTION_CAPABILITY_IMPLEMENTATION_20260829.md`;
- `coordination/E4/STATUS.md`.

Do not add another test module. Do not modify `src/brokers/__init__.py`, provider transport/auth/signing/private API code, shared contracts/ADRs, E1/E2/E3/E5/E6/E7 production code, AgentBridge/local-action infrastructure, Product Owner authorization artifacts, risk/leverage/capital thresholds, LIVE/release policy, or GitHub Actions/CI files.

## Result classification

### DONE
Use DONE only if remediation/test definitions are complete and required executable verification actually ran on an approved local exact revision with PASS evidence.

### PARTIAL
Use PARTIAL when remediation/test definitions are complete but executable verification remains `NOT_RUN / NOT_PASS`.

### BLOCKED
Use BLOCKED only if accepted E4 design semantics make the bounded provenance remediation impossible or contradictory.

## Completion

Read latest `main`, verify `E4-20260829-035`, continue only the existing unmerged FP-02 branch, apply this exact provenance remediation, persist evidence, update STATUS, commit/push, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start provider verification, credentials, protection/exit mutation, exact-revision preparation, Local Job Requests, qualification execution, SHADOW/PAPER, bounded live-fire, Gate D, LIVE, process action, order action, or capital movement/exposure.
