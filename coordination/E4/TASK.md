# E4 Current Task

- task_id: `E4-20260829-036`
- issued_at: `2026-08-29T21:00:00+08:00`
- state: `HOLD`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, merged E4-20260829-035 FP-02 static candidate, `status/PM_E4_035_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Hold after PM accepted and merged the remediated FP-02 OKX SWAP action-role capability resolver as a static implementation/test-definition candidate only.

Authoritative state:

```text
FP-02 project implementation = MERGED / IMPLEMENTED_UNQUALIFIED
FP-02 executable verification = NOT_RUN / NOT PASS
positive repository-row provenance fail-open = STATICALLY REMEDIATED
PROTECTION_STOP provider-native capability = UNRESOLVED_FAIL_CLOSED
POSITION_EXIT provider-native capability = UNRESOLVED_FAIL_CLOSED
EMERGENCY_EXIT provider-native capability = UNRESOLVED_FAIL_CLOSED
READ_ONLY_RECONCILIATION = REPOSITORY-EVIDENCED GET-ONLY BOUNDARY ONLY
LF-0 exact-revision infrastructure = BLOCKED / UNCHANGED
LF-1 = NOT_RUN / NOT PASS
LF-2 = PARTIAL / NOT PASS
provider read-only = FUTURE PRODUCT OWNER AUTHORITY REQUIRED
SHADOW/PAPER = NOT_AUTHORIZED
10U bounded live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
```

## Required actions while HOLD

- Preserve merged FP-02 canonical owner-row provenance and fail-closed unresolved-role semantics.
- Do not treat `REPO_EVIDENCED`, merge status, `PARTIAL`, or `NOT_RUN` as provider verification, dispatch authority, or executable PASS.
- Do not infer provider-native protection/exit endpoint, `posSide`, reduce-only, trigger basis, or readback/cancel semantics.
- Do not call providers, inspect/request credentials, modify transport/auth/private API code, or mutate provider/account/order state.
- Do not create Local Job Requests, prepare exact revisions, or bypass LF-0.
- Do not start SHADOW/PAPER, bounded live fire, Gate D, or LIVE.
- Do not move/expose capital.

## Unblock condition

PM may issue a fresh bounded E4 task only after E7 static integration exposes a concrete E4-owned defect/dependency, approved-local exact-revision qualification becomes available, or later separately authorized provider-capability work is explicitly opened.

## Writable scope

Only `coordination/E4/STATUS.md` for HOLD acknowledgement if needed.

## Completion

Acknowledge HOLD if needed and stop. Do not self-start provider verification, credentials, protection/exit mutation, exact-revision preparation, Local Job Requests, qualification execution, SHADOW/PAPER, bounded live fire, Gate D, LIVE, process action, order action, or capital movement/exposure.
