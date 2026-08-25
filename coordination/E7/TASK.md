# E7 Current Task

- task_id: `E7-20260825-067`
- issued_at: `2026-08-25T12:10:00+08:00`
- state: `HOLD`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted E7-20260825-066 baseline PR #75 merge `c158c8ca4fd01fa9314dd2e7a1a9c0c0d2935624`, Product Owner Gate C / SHADOW-only authorization

## Objective

Hold after PM accepted the authoritative Gate C / SHADOW_READY readiness baseline and issued Phase-1 domain tasks.

Current governed Phase 1:

```text
E1-20260825-003 = ACTIVE / current OKX public MarketSnapshot + finalized-candle surface
E4-20260825-017 = ACTIVE / dedicated production read-only Shadow provider boundary
E6-20260825-022 = ACTIVE / authoritative durable OperationalMode.SHADOW + checkpoint/restart
E2 = no Gate-C-specific implementation gap identified
E3 = no Gate-C-specific implementation gap identified
E5 = dependency-wait; do not start until E1/E4 normalized observations are PM-reviewed
```

Gate state remains:

```text
Gate A — RESEARCH_READY = PASS
Gate B — PAPER_READY = PASS
Gate C — SHADOW_READY = BLOCKED / AUTHORIZED_WORK_IN_PROGRESS
Gate D — LIVE_READY = BLOCKED / NOT AUTHORIZED
SHADOW runtime = NOT STARTED
LIVE = UNAUTHORIZED
```

## Required actions while HOLD

- Preserve the accepted Gate C baseline and settled contracts/architecture.
- Do not execute project code or provider/private verification under this HOLD.
- Do not create E7 Shadow integration/E2E/safety definitions until PM has reviewed the necessary E1/E4/E6 Phase-1 outputs and then the E5 derivation dependency.
- Do not change shared contracts/ADR unless a worker returns exact evidence that the baseline is insufficient.
- Do not request, use, expose, log, or commit credentials/tokens/cookies/browser-auth material.
- Do not start SHADOW runtime, provider/private read verification, order submission, account mutation, Gate D, or LIVE.
- GitHub Actions/CI/hosted/GitHub-triggered project compute remain forbidden.

## Dependency order after Phase 1

If E1/E4/E6 are accepted:

1. PM issues bounded E5 normalized Shadow observation -> RiskContext derivation/fail-closed task.
2. After E5 acceptance, PM issues E7 Shadow composition + integration/E2E/safety/no-submit definitions.
3. After implementation/test definitions are accepted, PM may issue an exact-revision credential-free approved-local Gate C qualification.
4. Credential-dependent production read-only verification remains a later operator-gated task; if regional domain/read-only key/sub-account prerequisites are missing, stop and request only that exact operator action.

No worker DONE automatically promotes Gate C.

## Writable scope

Only `coordination/E7/STATUS.md` for HOLD acknowledgement if needed.

## Completion

Acknowledge HOLD if needed and stop. Do not self-start another task.