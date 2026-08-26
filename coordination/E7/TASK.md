# E7 Current Task

- task_id: `E7-20260826-086`
- issued_at: `2026-08-26T15:53:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-zero-capital-shadow-readiness-20260826`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, `contracts-v0.1`, `status/PRODUCT_OWNER_ZERO_CAPITAL_SHADOW_AUTHORIZATION_20260826.md`, `status/PM_GATE_C_FINAL_REVIEW_20260826.md`, `status/RELEASE_GATES.md`, `coordination/LOCAL_ACTION_CATALOG.md`

## Objective

Prepare the minimum integration/session boundary needed for the single Product-Owner-authorized **zero-capital bounded SHADOW runtime session**. This task is a static/source/readiness audit and execution-plan task only. Do not start the SHADOW session and do not send provider requests in E7-086.

The Product Owner authorization is limited to exactly one future bounded session using the accepted Gate C implementation:

```text
qualified executable revision = ab725965e96cac7a9769fd1ab15a3e626f920b95
environment                   = OKX production read-only shadow
official REST hostname        = openapi.okx.com
approved computer             = current registered local Windows computer only
maximum session duration      = 30 minutes
maximum HTTPS GET requests    = 300
available capital             = exactly zero
capital exposure              = forbidden
order submission              = forbidden
provider/account mutation     = forbidden
PAPER runtime                 = not authorized
Gate D / LIVE                 = not authorized
GitHub compute                = forbidden
```

## Required review

Read current `main`, the Product Owner authorization artifact, Gate C final review/evidence, current source/test definitions relevant to SHADOW composition and persistence, and the local action catalog.

At minimum inspect the accepted cross-module surfaces needed for a bounded SHADOW session, including:

- E1 current market-state/finality/freshness surface;
- E2 deterministic strategy runtime consumption boundary;
- E4 `OKXShadowProviderReader` / exact GET allowlist / redaction / no-submit boundary;
- E5 provider-observation-derived RiskContext / fail-closed behavior;
- E6 `OperationalMode.SHADOW`, sanitized checkpoint/persistence/restart semantics;
- E7 ShadowComposition / integration/E2E/safety definitions;
- the current canonical AgentBridge action catalog.

Do not modify E1-E6-owned production/tests in this task.

## Required output

Create one bounded evidence/plan artifact:

`status/e7/ZERO_CAPITAL_SHADOW_SESSION_READINESS_20260826.md`

It must establish, without executing project/provider code:

1. whether the current accepted implementation can support one bounded SHADOW session without architectural or domain-code changes;
2. the exact session start prerequisites and fail-closed stop conditions;
3. how the 30-minute and 300-HTTPS-GET hard caps must be enforced and evidenced;
4. what sanitized session evidence must be durable, including at minimum:
   - exact executable revision;
   - start/end timestamps and elapsed duration;
   - total/private GET counts;
   - `MUTATION_REQUEST_COUNT=0`;
   - `SUBMIT_REQUEST_COUNT=0`;
   - zero-capital classification without exact balance;
   - provider/permission/account/position/freshness health classifications;
   - pending-order/unreconciled-fill classifications;
   - operational mode/checkpoint/restart state as applicable;
   - terminal stop reason;
   - confirmation that no credential value, exact balance, UID, signature, token/cookie, raw private response, provider order/fill ID, or browser auth is persisted;
5. the exact canonical AgentBridge capability required for the future runtime execution.

## Local action governance

The current catalog contains `GATE_C_OKX_PRODUCTION_READONLY`, which is an accepted bounded verification action. Do **not** reuse or reinterpret it as a 30-minute SHADOW runtime action unless its committed/operator-owned contract already proves that exact session behavior.

Do not invent a task-specific action ID and do not create a Local Job Request in E7-086.

If no existing canonical action exactly matches the authorized bounded SHADOW session, record:

```text
execution_dependency = LOCAL_ACTION_NOT_REGISTERED
required_operator_capability = <precise bounded capability description>
```

A proposed canonical action identity may be documented as a proposal only; do not add it to `coordination/LOCAL_ACTION_CATALOG.md` and do not assume local allowlisting exists. Operator review/allowlisting is an external dependency.

## Mandatory fail-closed runtime conditions to preserve

The future session must stop if any of the following is true:

- available USDT is not explicitly classified zero;
- any unexpected position/exposure, pending order, or unreconciled fill appears;
- provider permission is not exactly read-only;
- hostname/account classification/position mode/clock health is invalid or unknown;
- any mutation/submit capability becomes reachable or is attempted;
- exact qualified revision / clean dedicated worktree cannot be proven;
- 30-minute duration or 300-GET limit is reached;
- credentials/provider responses/evidence cannot be handled without disclosure.

No rule may be weakened to make the session executable.

## Execution / safety boundary for E7-086

```text
project code execution = NOT_RUN / NOT AUTHORIZED IN THIS READINESS TASK
provider requests = NONE
credentials = DO NOT READ / REQUEST / USE
Local Job Request = DO NOT CREATE
PAPER runtime = DO NOT START
SHADOW runtime = DO NOT START
order/provider mutation = FORBIDDEN
capital movement/exposure = FORBIDDEN
Gate D / LIVE = DO NOT START / NOT AUTHORIZED
GitHub Actions / CI / hosted runner / GitHub-triggered compute = FORBIDDEN
```

`NOT_RUN` in this task is not PASS evidence for the future SHADOW session.

## Writable scope

Only E7-owned integration/readiness evidence and status:

- `status/e7/ZERO_CAPITAL_SHADOW_SESSION_READINESS_20260826.md`;
- `coordination/E7/STATUS.md`;
- optionally `status/INTEGRATION_STATUS.md` only if needed to record a newly identified bounded execution dependency without changing Gate C PASS.

Do not modify production source, tests, contracts, ADRs, migrations, runtime configuration, local action catalog, credentials, E1-E6 TASK/STATUS, or other-agent-owned files.

## Completion

### DONE

Use `DONE` when the bounded session architecture/readiness plan is complete and ownership/dependencies are precise enough for PM to issue the next minimum task or persist an external blocker.

### BLOCKED

Use `BLOCKED` only if authoritative requirements conflict or the readiness determination itself cannot be made safely from repository evidence.

Commit/push the required evidence and `coordination/E7/STATUS.md` to the target branch and stop. Do not self-start implementation, local execution, provider access, another task, SHADOW runtime, Gate D, or LIVE.