# E5 Current Task

- task_id: `E5-20260821-006`
- issued_at: `2026-08-21T12:50:00+08:00`
- state: `HOLD`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0002/0003

## Objective

Freeze the E7-accepted `ApprovedTradePlan` entry/quantity producer now integrated into `main` while E4 implements downstream deterministic translation/sizing.

## Accepted evidence

- reviewed E5 implementation: `e5f7088301a92deadfd9f6c416ae03b466c38a47`
- E7 producer-chain disposition: `PASS / STATIC ONLY`
- integration PR #10: merged
- merge commit: `3e657ba75e02a96d497a3175c214b5babd5e9cae`
- `E5-RISK-UNKNOWN-001`: preserved / statically resolved
- executable verification: `NOT_RUN`

## Required actions

1. Do not modify the accepted `entry-v0.1 / MARKET` and `base-asset-v0.1 / BASE_ASSET / BTC` producer semantics while E4 implements downstream sizing.
2. Preserve E5 risk veto/approval authority and fail-closed state guards.
3. Do not add OKX `sz`, provider metadata, quantization, API/account/credential logic, or provider-native units to E5.
4. Do not add production policy values, PAPER/SHADOW/LIVE authority, or broker behavior.
5. Keep executable evidence `NOT_RUN` until approved local execution.
6. If acknowledging HOLD, update only `coordination/E5/STATUS.md`.

## Acceptance

- accepted producer remains unchanged;
- canonical BTC exposure meaning remains the E5 upper bound;
- no provider-native sizing leakage;
- no shared-contract change or GitHub compute;
- no executable PASS/release-gate claim.

## Writable scope

Only `coordination/E5/STATUS.md` for HOLD acknowledgement unless PM/E7 replaces this task.

## Completion / status

Acknowledge HOLD if needed and wait.
