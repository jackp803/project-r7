# E4 Current Task

- task_id: `E4-20260824-004`
- issued_at: `2026-08-24T11:28:00+08:00`
- state: `HOLD`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, ADR-0004, accepted Gate A PASS, accepted protection contract PR #37, accepted E5 producer PR #38, accepted E4 consumer PR #39

## Objective

Hold after PM review and static acceptance/merge of `E4-20260824-003`.

Accepted consumer evidence:

```text
PR #39
merge = 44ec171817f6c13fa632f2e7658dccc6b518f777
head = 5dd502f53b3eeb564ee917a8c5fa2090074908bc
consumer = protection-v0.1 PositionAction -> canonical protection OrderRequest
local executable verification = NOT_RUN
```

The E4 consumer implementation is accepted as materialized code/test definitions only. `NOT_RUN` remains `NOT_RUN`; neither the actual-fill protection criterion nor Gate B is PASS.

## Dependency state

E5 producer and E4 provider-neutral consumer are now both materialized. E7 may perform the bounded cross-module static integration/safety test-definition review required by the accepted `protection-v0.1` dependency order.

E4 must not self-start broker submission, protection activation/verification, protection-failure orchestration, provider/private API work, Paper E2E, persistence, TradeResult closure, Gate C, PAPER, SHADOW, or LIVE.

## Current release state

```text
Gate A = PASS / RESEARCH-INTEGRATION ONLY
E5 protection producer = MATERIALIZED / EXECUTABLE NOT_RUN
E4 protection consumer = MATERIALIZED / EXECUTABLE NOT_RUN
actual-fill protection criterion = NOT PASS / executable and integration evidence outstanding
protection failure emergency criterion = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

## Required actions while HOLD

- Preserve exact `protection-v0.1` consumer semantics and additive legacy compatibility.
- Do not weaken immediate PositionAction authority lineage, idempotency, exact actual-quantity mapping, stop-bound preservation, or fail-closed reconciliation behavior.
- Do not run project code or Local Runner actions for this HOLD.
- Do not treat prior `NOT_RUN` as PASS.
- Wait for a later PM task after E7 integration/safety disposition.

## Writable scope

Only `coordination/E4/STATUS.md` for HOLD acknowledgement unless PM replaces this task.

## Completion

Acknowledge HOLD if needed and wait. Do not start another task.