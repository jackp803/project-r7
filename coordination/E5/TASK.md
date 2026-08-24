# E5 Current Task

- task_id: `E5-20260824-022`
- issued_at: `2026-08-24T17:06:00+08:00`
- state: `HOLD`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`, ADR-0007, accepted Gate B chain through PR #58

## Objective

Hold after PM static/source review accepted `E5-20260824-021` and merged the E5 canonical `position-lifecycle-projection-v0.1` producer.

Accepted evidence:

```text
PR #58
head = feba4b46e6ae016db7f726b05f2e798f42d13f30
merge = f5bbeaf1daef1fdeda28ea6d12482b3b26018cc8
E5 lifecycle projection producer = MATERIALIZED / executable NOT_RUN
```

This acceptance is source/test-definition only. `NOT_RUN` remains `NOT_RUN`; no executable Gate B criterion, Restart/persistence, Paper E2E, Gate B/PAPER_READY or PAPER authority is PASS.

## Dependency state

The next bounded dependency is E6-owned durable Paper runtime persistence/restart/audit using the accepted E5 profiled Position projections and PR #57 revision/predecessor/identity rules.

E5 must not self-start E6 storage/migrations, E7 durability/E2E, approved-local verification, provider/private APIs, Gate C, PAPER, SHADOW or LIVE.

## Current release state

```text
Gate A = PASS / RESEARCH-INTEGRATION ONLY
ordinary EXIT -> TradeResult = NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
EMERGENCY_EXIT -> TradeResult = NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
verified full PROTECTION_STOP -> TradeResult = NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
funding producer -> consumer = NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
Position lifecycle durability contract/rule = RESOLVED STATIC
E5 lifecycle projection producer = MATERIALIZED / NOT_RUN
Restart/persistence preserves required state = BLOCKED / E6 IMPLEMENTATION GAP
Paper E2E closes to TradeResult and persists audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

## Required actions while HOLD

- Preserve the accepted lifecycle projection producer, TradeResult, protection and close fail-closed semantics.
- Do not run project code or request Local Runner actions for this HOLD.
- Do not treat any `NOT_RUN` as PASS.
- Wait for PM after E6 durability review.

## Writable scope

Only `coordination/E5/STATUS.md` for HOLD acknowledgement unless PM replaces this task.

## Completion

Acknowledge HOLD if needed and wait. Do not start another task.