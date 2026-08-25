# Release Gates

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Current reconciliation: 2026-08-25 / `E7-20260825-066`  
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

### Accepted post-remediation qualification

```text
source task_id       = E7-20260825-064
execution_revision   = d5ddb4cec47c15e8d3ed7045dce4bed043fb6aa8
request_id           = REQ-E7-GATEB-064-01-7B3E91C4
job_id               = JOB-3EE69A58605DF9D2
job_state            = SUCCEEDED
job_exit_code        = 0
overall_matrix       = PASS
PM evidence review   = ACCEPTED
```

All ten required Gate B suites ran exactly once in the Product-Owner-approved local Windows / non-GitHub environment. Total tests reported as run: `450`; every required suite exited `0`.

Durable evidence:

`status/e7/GATE_B_POST_REMEDIATION_QUALIFICATION_20260825.md`

Formal disposition:

```text
Gate B — PAPER_READY = PASS
qualified revision = d5ddb4cec47c15e8d3ed7045dce4bed043fb6aa8
PAPER runtime = NOT STARTED
```

Gate B PASS is technical readiness evidence and does not itself activate PAPER or authorize SHADOW/LIVE execution.

## Gate C — SHADOW_READY

### Product Owner authority

At `2026-08-25T11:34+08:00`, Product Owner authorized governed work through a reviewable Gate C / SHADOW_READY result, including bounded design, implementation, local testing, and later provider/private **read-only** verification after safe operator credential setup.

This authority does not permit LIVE, order placement/submission (including simulated order submission as Shadow evidence), account/position/leverage/margin mutation, capital movement/exposure, credential disclosure, or GitHub project compute.

### E7-066 readiness baseline

Durable baseline:

`status/e7/GATE_C_READINESS_BASELINE_20260825.md`

Settled technical target:

```text
provider                     = OKX API V5
canonical instrument         = BTC_USDT_PERP
provider instrument          = BTC-USDT-SWAP
private Shadow environment   = production-provider READ-ONLY observation
operational account boundary = dedicated R7 OKX sub-account
API key permission           = read_only exactly
regional REST hostname       = local-operator confirmed for account registration
Shadow order submission      = FORBIDDEN / MUST BE STRUCTURALLY UNREACHABLE
Shadow provider mutation     = FORBIDDEN
```

The existing `OKXDemoAdapter` remains a separate Demo component and is not accepted as the Gate C Shadow provider dependency because it contains submit capability. Gate C requires a dedicated read-only E4 provider surface with an exact GET allowlist and default-deny transport boundary.

Current Gate C blockers/gaps:

```text
E1 current OKX MarketSnapshot/current finalized-candle surface = IMPLEMENTATION_GAP
E4 production read-only provider/no-submit boundary             = IMPLEMENTATION_GAP
E4 Shadow composition submit reachability                       = CONTRACT_OR_ARCHITECTURE_GAP
E5 trusted observation-to-risk derivation                       = IMPLEMENTATION_GAP / TEST_DEFINITION_GAP
E6 authoritative SHADOW OperationalMode persistence/restart      = IMPLEMENTATION_GAP / TEST_DEFINITION_GAP
E7 Shadow integration/E2E/safety definitions                    = TEST_DEFINITION_GAP
credential-free local Gate C qualification                       = LOCAL_EXECUTION_EVIDENCE_GAP
credential-dependent production read-only evidence               = CREDENTIAL_DEPENDENT_EVIDENCE_GAP
regional host + read-only key setup                              = OPERATOR_ACTION_BLOCKER for later phase
```

No shared-contract or ADR change is required by the E7-066 baseline. Existing `contracts-v0.1` already defines `MarketSnapshot`, fail-closed health/risk semantics, and `OperationalMode.SHADOW`.

### Gate C disposition

```text
Gate C — SHADOW_READY = BLOCKED / AUTHORIZED_WORK_IN_PROGRESS
SHADOW runtime = NOT STARTED
provider/private calls in E7-066 = NONE
credential use in E7-066 = NONE
```

Gate C may not PASS until the bounded implementation/test gaps are closed, credential-free approved-local evidence passes on an exact reviewed revision, the local operator satisfies the later read-only credential/account/domain prerequisites, separately authorized credential-dependent read-only evidence is accepted, and PM completes evidence review.

## Gate D — LIVE_READY

```text
Gate D = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

Gate C is not PASS and Product Owner LIVE authorization is absent.

## Compute / security / trading boundary

```text
E7-066 project executable verification = NOT_RUN / STATIC BASELINE TASK
GitHub Actions / CI                     = NOT USED
GitHub-hosted runner                    = NOT USED
GitHub-triggered compute                = NOT USED
provider/private API                    = NOT USED
external exchange traffic               = NOT USED
exchange credentials                    = NOT USED
PAPER runtime                           = NOT STARTED
SHADOW runtime                          = NOT STARTED
LIVE                                    = UNAUTHORIZED
capital exposure                        = NONE
```
