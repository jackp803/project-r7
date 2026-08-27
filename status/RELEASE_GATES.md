# Release Gates

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Current reconciliation: 2026-08-27 / `E7-20260827-096`  
> Policy: no gate may PASS without accepted evidence from an allowed environment.

## Evidence vocabulary

- `PASS` — required evidence exists and satisfies the criterion.
- `FAIL` — approved evidence shows the criterion is not satisfied.
- `BLOCKED` — prerequisite, review, contract, implementation, authorization, or evidence prevents advancement.
- `NOT_RUN` — executable verification required but not executed.

`BLOCKED != PASS`, `NOT_RUN != PASS`, and task completion does not imply release-gate PASS.

## Gate A — RESEARCH_READY

```text
Gate A = PASS / RESEARCH-INTEGRATION ONLY
```

Accepted Gate A evidence remains unchanged.

## Gate B — PAPER_READY

```text
Gate B — PAPER_READY = PASS
qualified revision = d5ddb4cec47c15e8d3ed7045dce4bed043fb6aa8
PAPER runtime = NOT STARTED / NOT AUTHORIZED
```

Accepted Gate B local evidence remains `status/e7/GATE_B_POST_REMEDIATION_QUALIFICATION_20260825.md` with 450 tests passing on the approved local Windows/non-GitHub environment.

## Gate C — SHADOW_READY

### Historical accepted provider-qualified PASS

The formal provider-qualified Gate C PASS remains bound to the exact revision and evidence actually accepted in the original final review:

```text
historical provider-qualified revision = ab725965e96cac7a9769fd1ab15a3e626f920b95
Gate C — SHADOW_READY = PASS / HISTORICAL PROVIDER-QUALIFIED BASELINE PRESERVED
SHADOW runtime = NOT STARTED
```

Evidence chain:

- `status/e7/GATE_C_POST_TEST_COMPAT_CREDENTIAL_FREE_REQUALIFICATION_20260826.md` — `ab725965...`, 14/14 suites PASS, 587 tests;
- `status/e7/GATE_C_COMPLETE_SANITIZED_READONLY_EVIDENCE_20260826.md` — `ab725965...`, production OKX read-only evidence, zero mutation/submit;
- `status/PM_GATE_C_FINAL_REVIEW_20260826.md` — accepted Gate C PASS for `ab725965...`.

This historical provider evidence remains valid for its exact revision only.

### Accepted ADR-0010 temporal-remediation credential-free baseline

PM accepted E7-095 approved-local credential-free requalification of:

```text
revision = 8fbf5fcae2eaf44accdf535121d8abf29ef5c93c
result = CREDENTIAL_FREE_REQUALIFIED / PM ACCEPTED
required suites = 14 / 14 PASS
total tests = 589
provider requests = 0
credentials = NONE
mutation requests = 0
submit requests = 0
```

Evidence:

- `status/e7/SHADOW_TEMPORAL_ORDERING_CREDENTIAL_FREE_REQUALIFICATION_20260827.md`;
- `status/PM_E7_095_REVIEW_20260827.md`.

This revision contains the accepted ADR-0010 temporal-ordering remediation and is the current credential-free requalified project candidate/baseline.

### Provider-facing status of the remediated revision

```text
provider verification on 8fbf5fcae2eaf44accdf535121d8abf29ef5c93c
  = NOT_RUN / NOT_INFERRED
```

Historical provider evidence from `ab725965...` is not automatically transferred, copied, rebound, or inferred as provider evidence for `8fbf5fca...`.

No new provider-facing Gate C PASS is created by E7-095 or E7-096.

### Gate C reconciliation disposition

```text
Gate C historical provider-qualified PASS = PRESERVED / ab725965...
current ADR-0010 credential-free baseline = 8fbf5fca... / PM ACCEPTED / 14 OF 14 / 589 TESTS
provider-facing verification on 8fbf5fca... = NOT_RUN / NOT_INFERRED
```

Before any future provider SHADOW session, governance still requires:

1. AgentBridge SHADOW consumer migration/review against ADR-0010 and binding to `8fbf5fca...`;
2. any separately required and authorized provider-facing verification for `8fbf5fca...`, with its own evidence;
3. new explicit Product Owner authority for a third/replacement bounded SHADOW session.

Both previous bounded SHADOW authorizations remain consumed and cannot be reused.

## Gate D — LIVE_READY

```text
Gate D = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

No Gate C evidence grants Gate D readiness or Product Owner LIVE authorization.

## Current runtime / compute / security boundary

```text
PAPER runtime = NOT STARTED / NOT AUTHORIZED
SHADOW runtime = NOT STARTED / NO NEW AUTHORITY
third/replacement SHADOW authority = NOT GRANTED / PRODUCT OWNER REQUIRED
LIVE = UNAUTHORIZED
Gate D = BLOCKED / NOT AUTHORIZED
E7-096 project executable verification = NOT_RUN / NOT REQUIRED FOR DOCS-ONLY RECONCILIATION
E7-096 provider/private API = NOT USED
E7-096 exchange credentials = NOT READ / NOT REQUESTED / NOT USED
mutation requests = 0
submit requests = 0
GitHub Actions / CI / hosted / GitHub-triggered compute = NOT_USED
capital exposure = NONE
```

E7-095 remains the executable credential-free qualification evidence. `NOT_RUN` for E7-096 is not executable PASS.

## Reconciliation artifact

`status/e7/SHADOW_TEMPORAL_ORDERING_RELEASE_RECONCILIATION_20260827.md`
