# E4 Current Task

- task_id: `E4-20260821-005`
- issued_at: `2026-08-21T10:58:00+08:00`
- state: `HOLD`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0002/0003, Product Owner OKX decision

## Objective

Freeze the statically accepted broker-neutral Broker/PaperBroker skeleton while E2 and E5 implement the newly approved producer-side execution profiles.

The prior entry-contract design blocker is resolved by canonical profiles:

```text
entry-v0.1      = MARKET only
base-asset-v0.1 = canonical base-asset exposure
```

E4 implementation follow-up must wait until E2/E5 producer revisions are available for review/integration.

## Frozen evidence

- branch: `agent/e4-execution-v2`
- reviewed implementation revision: `53487a93f6f10d89723403b1a2e2426ba1c7e82a`
- E7 static disposition: `PASS (STATIC ONLY)`
- executable verification: `NOT_RUN`

## Required actions

1. Do not modify E4 production/test source during this HOLD.
2. Preserve current Broker/PaperBroker authority, idempotency, partial-fill, overfill, ambiguity, and reconciliation fail-closed behavior.
3. Do not implement the new entry translator until PM/E7 accepts the E2/E5 producer revisions.
4. Do not yet implement OKX Demo/private API, authentication, signatures, real/demo order submission, account calls, leverage-setting calls, or credentials.
5. Do not build PionexBroker or new Pionex logic.
6. Do not expose withdrawal, funding transfer, or sub-account capital-movement capability.
7. Preserve the canonical/provider quantity separation: E5-approved base-asset quantity is not OKX `sz`.
8. Keep executable evidence `NOT_RUN` until approved local execution.
9. If acknowledging HOLD, update only `coordination/E4/STATUS.md`.

## Acceptance

- reviewed E4 skeleton remains unchanged;
- no premature translator/provider implementation;
- no shared-contract fork;
- no GitHub Actions/CI/hosted runner/project compute;
- no PAPER/SHADOW/LIVE authorization.

## Writable scope

Only `coordination/E4/STATUS.md` for HOLD acknowledgement unless PM/E7 replaces this task.

## Completion / status

Acknowledge HOLD if needed and wait for accepted E2/E5 producer revisions. The next E4 ACTIVE task will be bounded to mechanical `entry-v0.1` translation plus deterministic OKX metadata/quantization logic; Demo/private execution will remain a separate future authorization.
