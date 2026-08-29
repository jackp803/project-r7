# E4 Current Task

- task_id: `E4-20260829-034`
- issued_at: `2026-08-29T20:46:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-fp02-action-capability-evidence-20260829`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, accepted E4 design profile `okx-swap-action-role-capability-v0.1`, `docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md`, merged FP-03/04/05/10/11 owner static candidates, merged FP-16 static candidate, `status/PM_E7_114_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Implement the smallest deterministic E4-owned **OKX SWAP action-role capability evidence/resolution boundary** for FP-02 using only caller-supplied sanitized repository/provider-capability facts.

This task converts the accepted E4 docs-only capability matrix into provider-local executable logic that can distinguish `REPO_EVIDENCED`, `UNRESOLVED_FAIL_CLOSED`, `FORBIDDEN`, and `NOT_APPLICABLE` facts before any provider dispatch. It must not create provider-native facts that are currently unresolved.

No provider/network/credential/mutation/runtime/capital authority is granted.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E4_EXECUTION.md`;
- `docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md` in full;
- accepted FP-03 protection-trigger-validity profile and merged E4 consumer;
- accepted FP-04 ownership/reconciliation profile and merged E4 producer;
- accepted FP-05 close/residual sizing design and merged E4 sizing candidate;
- accepted FP-11 protection registry profile and merged E4 producer;
- merged E7 FP-16 runtime-preflight implementation only as an authority boundary, without modifying it;
- `status/PM_E7_114_REVIEW_20260829.md`;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Implementation boundary

Implement an E4-local pure/provider-neutral resolver, preferably under:

- `src/brokers/okx_action_capability.py`, or an equivalently bounded E4-owned provider-local module;
- minimal direct tests under `tests/brokers/`.

The resolver may define typed/provider-local sanitized inputs/evidence and deterministic helper functions, but must not modify shared `contracts/` or invent a new cross-module contract.

The resolver must consume only explicit supplied facts such as:

- capability profile version;
- action role;
- canonical/provider instrument identity and `instType=SWAP`;
- account level;
- position mode;
- margin mode;
- operation class;
- exact provider field-set evidence/ref/hash/generation where already repo-evidenced;
- current reconciliation classification where applicable;
- FP-03/FP-05/FP-11 evidence refs/status only when required by the accepted role row;
- caller capability assertions, if supplied, solely so they can be rejected as authority.

It must perform no I/O and must never inspect credentials, account balances, raw provider payloads, filesystem paths, shell commands, or secrets.

## Required capability semantics

Use the accepted E4-local states exactly:

- `REPO_EVIDENCED`
- `UNRESOLVED_FAIL_CLOSED`
- `FORBIDDEN`
- `NOT_APPLICABLE`

Use stable E4-local reasons from the accepted matrix, including where applicable:

- `OKX_SWAP_CAPABILITY_PROFILE_UNSUPPORTED`
- `OKX_SWAP_ACTION_ROLE_UNSUPPORTED`
- `OKX_SWAP_INSTRUMENT_UNSUPPORTED`
- `OKX_SWAP_ACCOUNT_LEVEL_UNSUPPORTED`
- `OKX_SWAP_POSITION_MODE_UNSUPPORTED`
- `OKX_SWAP_MARGIN_MODE_UNSUPPORTED`
- `OKX_SWAP_SPOT_TRADE_MODE_FORBIDDEN`
- `OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN`
- `OKX_SWAP_CALLER_CAPABILITY_ASSERTION_REJECTED`
- `OKX_SWAP_TRIGGER_BASIS_UNPROVEN`
- `OKX_SWAP_REDUCIBLE_SIZE_UNPROVEN`
- `OKX_SWAP_PROTECTION_REGISTRY_NOT_CURRENT`
- `OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN`
- `OKX_SWAP_RECONCILIATION_REQUIRED`

Do not add provider-native facts merely to produce a green state.

### ENTRY

`ENTRY` may resolve only against the currently repository-evidenced bounded entry mapping when all required facts exactly match the accepted design, including:

- provider OKX / API V5 target identity;
- canonical `BTC_USDT_PERP` -> provider `BTC-USDT-SWAP` / `instType=SWAP`;
- `acctLv=2`;
- `tdMode=isolated`;
- accepted `net_mode` or entry-specific accepted `long_short_mode` mapping;
- exact current bounded entry provider field-set evidence rather than caller-manufactured fields.

Any caller-provided capability boolean/dictionary that attempts to create authority must be rejected.

A `REPO_EVIDENCED` ENTRY capability remains repository mapping evidence only. It is not provider verification or order authority.

### PROTECTION_STOP

`PROTECTION_STOP` must remain `UNRESOLVED_FAIL_CLOSED` for provider dispatch under current repository facts.

Even with exact current FP-03 `ACTIONABLE` shared geometry and exact current FP-11 registry facts, the resolver must not infer:

- provider protection/algo endpoint;
- trigger field names;
- provider trigger basis / `triggerPxType`;
- provider-native reduce-only semantics;
- provider protection `posSide` semantics;
- exact provider readback/cancel identity.

Shared FP-03 `LAST_PRICE` geometry is never provider trigger-basis proof.

### POSITION_EXIT / EMERGENCY_EXIT

Both roles must remain `UNRESOLVED_FAIL_CLOSED` for provider dispatch under current repository facts.

Exact FP-05 sizing evidence may prove canonical/provider-local quantity constraints for sizing, but it must not prove unresolved provider-native:

- endpoint/field set;
- `posSide` close behavior;
- native reduce-only behavior;
- role-specific provider close semantics.

Original entry quantity/requested quantity must never substitute for fresh actual reducible exposure.

Emergency urgency does not waive provider proof.

### READ_ONLY_RECONCILIATION

The role may resolve only as the currently repository-evidenced observation-only capability when the supplied facts bind the accepted GET-only/default-deny Shadow observation surface.

It must never resolve a mutation operation. Any attempted POST/create/cancel/amend/close/protection mutation through this role must fail closed with `OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN` or the exact equivalent accepted E4-local reason.

## Currentness / identity

If the implementation persists/returns a provider-local evidence object:

- use deterministic canonical serialization and identity;
- bind exact profile/action role/instrument/account/mode/margin/operation and supplied evidence generation/hash facts;
- material capability changes must produce a different identity/currentness result;
- wall-clock/evaluated-at change alone must not upgrade unresolved facts or manufacture supersession;
- do not invent numeric TTLs.

A helper may recompute whether evidence remains current against fresh supplied facts, but it must remain pure and provider-neutral.

## Required deterministic tests to define

Cover at minimum:

1. exact supported ENTRY `net_mode` row -> repository-evidenced capability only;
2. exact supported ENTRY `long_short_mode` row -> repository-evidenced capability only for ENTRY;
3. wrong canonical/provider instrument or non-SWAP -> fail closed;
4. wrong/unknown account level -> fail closed;
5. wrong/unknown position mode -> fail closed;
6. non-isolated/Spot `tdMode=cash` -> forbidden/fail closed;
7. caller capability assertion cannot create capability;
8. caller-mutated/unknown provider field set -> `OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN`;
9. FP-03 ACTIONABLE protection evidence still cannot select provider trigger basis or provider protection field set;
10. PROTECTION_STOP remains unresolved with no provider mutation materialization;
11. POSITION_EXIT remains unresolved even when supplied FP-05 sizing evidence is otherwise coherent;
12. EMERGENCY_EXIT remains unresolved and receives no emergency bypass;
13. stale/unknown/reconciliation-required facts remain non-authorizing;
14. READ_ONLY_RECONCILIATION accepts only the exact observation role and rejects any mutation request;
15. deterministic same-input output/identity and material-currentness invalidation if evidence identity is implemented;
16. no provider/network/credentials/private API/process/runtime/order mutation/capital dependency.

Do not execute tests through GitHub.

## Verification boundary

All project-code execution remains local-only. LF-0 approved-local exact-revision preparation remains blocked.

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

`NOT_RUN` is not PASS. Do not create a Local Job Request or exact-revision preparation request in this task.

## Required durable evidence

Create:

`status/e4/FP02_OKX_SWAP_ACTION_CAPABILITY_IMPLEMENTATION_20260829.md`

Document task ID, exact files changed, accepted design consumed, implemented provider-local states/reasons, exact ENTRY/read-only repo-evidenced boundaries, unresolved protection/exit/emergency behavior, currentness/identity behavior if applicable, future local commands, limitations, and zero provider/credential/mutation/runtime/capital authority.

Update `coordination/E4/STATUS.md`, commit, and push the target branch.

## Writable scope

Only E4-owned paths needed directly for this task:

- `src/brokers/okx_action_capability.py` or one equivalently named new E4-local capability module;
- minimal `src/brokers/__init__.py` export only if needed;
- `tests/brokers/test_okx_action_capability.py` or one direct E4-owned test module;
- `status/e4/FP02_OKX_SWAP_ACTION_CAPABILITY_IMPLEMENTATION_20260829.md`;
- `coordination/E4/STATUS.md`.

Do not modify existing provider transport/auth/signing/private API calls, shared contracts/ADRs, E1/E2/E3/E5/E6/E7 production code, AgentBridge/local-action infrastructure, Product Owner authorization artifacts, risk/leverage/capital thresholds, LIVE/release policy, or GitHub Actions/CI files.

## Result classification

### DONE
Use DONE only if implementation/test definitions are complete and required executable verification actually ran on an approved local exact revision with PASS evidence.

### PARTIAL
Use PARTIAL when implementation/test definitions are complete but executable verification remains `NOT_RUN / NOT_PASS`, or a precise provider fact remains intentionally unresolved/fail-closed.

### BLOCKED
Use BLOCKED only for a contradictory authoritative requirement that prevents this bounded E4-local implementation.

## Completion

Read latest `main`, verify wake task ID `E4-20260829-034`, execute only this task, persist evidence, update STATUS, commit/push the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start provider verification, credential use, protection/exit mutation, exact-revision preparation, Local Job Requests, qualification execution, SHADOW/PAPER, bounded live-fire, Gate D, LIVE, process action, order action or capital movement/exposure.
