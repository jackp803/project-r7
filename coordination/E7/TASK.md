# E7 Current Task

- task_id: `E7-20260825-066`
- issued_at: `2026-08-25T11:34:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-c-readiness-baseline-20260825`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, formal Gate B PASS on `main`, Product Owner explicit Gate C / SHADOW-only authorization at `2026-08-25T11:34+08:00`

## Product Owner authority boundary

Product Owner authorizes PM/E1-E7 to continue governed work through a reviewable `Gate C / SHADOW_READY` result, including Gate C design, implementation, tests, evidence, and necessary provider/private **read-only or shadow verification** after the local operator safely configures credentials.

This authority does **not** authorize:

- LIVE;
- real or simulated order placement/submission as part of SHADOW verification;
- any capital exposure;
- deposits, withdrawals, transfers, funding movement, or asset movement;
- account/position-mode/leverage/margin mutation;
- strategy promotion to LIVE;
- credentials/tokens/cookies/browser-auth material in Git, chat, logs, status artifacts, fixtures, screenshots, or callbacks;
- GitHub-hosted/GitHub-triggered project compute.

If credentials, paid access, provider account permissions, allowlisting, or another local operator action is required, identify the exact action and stop the affected credential-dependent path at `HOLD`/`BLOCKED`; never obtain, infer, fabricate, paste, log, or commit secrets.

## Objective

Establish the authoritative Gate C / SHADOW_READY technical baseline and evidence plan before PM fans work out to domain engineers.

This task is primarily architecture/contract/static-gap analysis. Do **not** start provider/private network verification or any credential-dependent action in this task.

Use the accepted Gate B state and current repository implementation as the baseline. In particular, inspect the current broker/provider implementation and documentation (including the existing OKX Demo-first surface) rather than assuming an obsolete provider path. If the current authoritative repository leaves the Gate C provider/environment target materially ambiguous or conflicts with product requirements, record that as a PM/Product Owner decision point rather than silently switching providers.

## Required analysis and design

### 1. Gate C acceptance definition

Define concrete, reviewable `SHADOW_READY` criteria covering at minimum:

- provider/environment identity and why it is the accepted Gate C target;
- authentication/signature and clock/timestamp requirements;
- credential source boundary: operator-configured local secret only, never repository material;
- exact provider/private **read-only allowlist** required for Gate C (for example account/config/position/order-status/open-order/fill reads only where genuinely necessary);
- exact mutation/submit denylist;
- provider/public market-state freshness needed by Shadow;
- local/provider truth reconciliation and unknown-state fail-closed behavior;
- Shadow runtime semantics: live/provider inputs may be observed, Strategy/Risk/Execution planning may run, but no provider order submission or account mutation is reachable;
- E5 risk veto and stale/unknown provider-state behavior;
- E6 operational mode, persistence, audit, restart, and Backtest/Paper/Shadow/Live separation requirements;
- E7 integration/E2E/safety evidence required for Gate C;
- secret-redaction and public-repository evidence rules;
- explicit proof required that LIVE and order-submit paths remain disabled/unreachable.

### 2. Current-state gap map

Review current `main` across E1-E7-owned implementation/tests/docs and classify every Gate C criterion as:

- `SATISFIED_STATICALLY`;
- `IMPLEMENTATION_GAP`;
- `TEST_DEFINITION_GAP`;
- `LOCAL_EXECUTION_EVIDENCE_GAP`;
- `CREDENTIAL_DEPENDENT_EVIDENCE_GAP`;
- `OPERATOR_ACTION_BLOCKER`;
- `CONTRACT_OR_ARCHITECTURE_GAP`.

Do not infer owner from a suite directory alone. Assign an owner recommendation only from authoritative role/source ownership.

### 3. Provider/private safety architecture

The current repository includes an OKX Demo-first adapter capable of constructing private requests and, in other modes/scopes, submit materialization. Gate C SHADOW must be stricter than that construction capability.

Define how Gate C proves that:

- credential-dependent verification uses only the minimum read-only provider calls necessary;
- no `place order`, cancel, amend, leverage/mode mutation, transfer, withdrawal, deposit, or similar provider mutation is sent;
- the Shadow path cannot reach submit even if valid credentials exist;
- provider acknowledgements/order history are not fabricated as execution truth;
- local unknown/ambiguous state fails closed;
- credentials are injected only by the local operator and redacted from all durable evidence.

If the existing adapter/API surface cannot satisfy a read-only Shadow boundary without architecture changes, identify the exact bounded E4/E6/E7 work needed. Do not weaken the boundary.

### 4. Verification plan

Split Gate C evidence into two classes:

**Credential-free approved-local verification**
- unit/integration/e2e/safety tests using fakes/sanitized fixtures;
- must prove no-submit/no-mutation Shadow behavior, reconciliation, redaction, mode separation, and fail-closed handling.

**Credential-dependent approved-local verification**
- only after operator setup;
- exact provider read-only calls/capabilities required;
- exact environment/account permission prerequisites;
- sanitized evidence fields to persist;
- explicit abort conditions;
- no secrets in commands, Git, callback, stdout/stderr evidence, or status docs.

Do not execute either class in this baseline task unless a tiny non-project static inspection command is intrinsically required; project executable verification for implementation/qualification belongs to later bounded tasks.

## Required deliverable

Create:

`status/e7/GATE_C_READINESS_BASELINE_20260825.md`

It must include:

1. authoritative Gate C acceptance criteria;
2. provider/environment decision or exact unresolved decision point;
3. read-only allowlist and mutation/submit denylist;
4. Shadow no-submit invariant;
5. current gap matrix;
6. exact recommended E1-E7 task fan-out in dependency order, only for owners with real gaps;
7. credential-free local verification matrix;
8. credential-dependent verification plan and exact operator blocker conditions;
9. security/redaction requirements;
10. Gate C disposition after this task (must remain non-PASS until executable evidence is reviewed).

Also update as appropriate:

- `status/INTEGRATION_STATUS.md`;
- `status/RELEASE_GATES.md`;
- `coordination/E7/STATUS.md`.

Contracts/ADR changes are permitted only if static review proves they are necessary to define Gate C safely. If changed, clearly identify all affected producers/consumers and migration/compatibility impact. Do not change domain production code in this task.

## Writable scope

Allowed:

- `status/e7/GATE_C_READINESS_BASELINE_20260825.md`;
- `status/INTEGRATION_STATUS.md`;
- `status/RELEASE_GATES.md`;
- `coordination/E7/STATUS.md`;
- `contracts/**`, `docs/adr/**`, `docs/architecture/**`, `docs/integration/**`, and E7-owned Gate C test definitions only when required to settle the baseline safely.

Forbidden:

- E1-E6 production implementation changes;
- E1-E6 owned test changes;
- provider/private network calls;
- credential use;
- GitHub Actions/CI/hosted runners/GitHub-triggered compute;
- PAPER runtime start;
- SHADOW runtime start;
- LIVE;
- provider order submission or mutation;
- capital movement/exposure;
- strategy promotion;
- unrelated cleanup.

## Release semantics

During and after this baseline task:

```text
Gate A — RESEARCH_READY = PASS
Gate B — PAPER_READY = PASS
Gate C — SHADOW_READY = BLOCKED / AUTHORIZED_WORK_IN_PROGRESS
Gate D — LIVE_READY = BLOCKED / NOT AUTHORIZED
SHADOW runtime = NOT STARTED
LIVE = UNAUTHORIZED
```

Worker `DONE` is evidence for PM review, not automatic Gate C acceptance.

## Acceptance

### DONE

Use `DONE` only when the Gate C acceptance baseline, gap matrix, provider/read-only boundary, Shadow no-submit invariant, verification plan, and bounded owner fan-out are complete and committed/pushed to the target branch.

### BLOCKED / NEEDS PM DECISION

If a material provider/environment choice or shared architecture question cannot be settled from authoritative repository/product constraints, stop with the exact decision required. Do not guess.

### HOLD

If the only remaining issue discovered is a credential/account/operator prerequisite for a later credential-dependent verification step, document it precisely but this baseline task may still be `DONE`; later affected tasks must HOLD before credential-dependent execution until the operator performs that action.

## Completion

Execute only this TASK, update `coordination/E7/STATUS.md`, commit/push required evidence to the target branch, and stop. Do not self-start domain remediation, provider verification, Shadow runtime, Gate C qualification, or another task.