# E4 Current Task

- task_id: `E4-20260822-002`
- issued_at: `2026-08-22T02:47:00+08:00`
- state: `HOLD`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0002/0003, `docs/execution/OKX_DEMO_ADAPTER_SCOPE.md`, Product Owner OKX/sub-account decision, E7 final review `status/e7/E4_OKX_DEMO_FINAL_REREVIEW_20260822.md`

## Objective

Hold the accepted Demo-first OKX provider-adapter source after PR #12 merge. Do not begin provider connectivity, Demo order execution, retry enablement, or another E4 provider feature until a separate PM/Product Owner task explicitly authorizes the next bounded stage.

## Accepted evidence

- final E4 implementation/tests/docs/handoff revision: `99bf09461e32117001ce7e587be44dcc3d152ab2`
- PR #12 head: `25294d72920efab3011eb5060079bf2edca5d056`
- PR #12 merged to `main`: `572b54f9d454ddf33bb5a2d92f98bba67e852e16`
- E7 final review: `E7-20260822-001 / PASS STATIC`
- all five prior E4 findings: `CLOSED / PASS STATIC`
- executable verification: `NOT_RUN`
- actual provider requests/orders: `NOT_SENT`
- provider retry: `STRUCTURALLY DISABLED / NOT AUTHORIZED`

## Required actions

1. Do not modify the merged Demo adapter source during this HOLD.
2. Preserve Demo-only mode, mandatory `x-simulated-trading: 1`, runtime-only/redacted credentials, bounded endpoint allowlist, MARKET-only isolated path, V1 account matrix, canonical/provider quantity separation, freshness hardening, submit-integrity provenance, fail-closed response normalization, and disabled retry.
3. Do not add concrete networking, real credentials, production/live fallback, automatic account/position/leverage mutation, or asset movement.
4. Do not send Demo/provider requests or orders.
5. Do not modify shared contracts or other-agent production code.
6. Keep executable verification `NOT_RUN` until a Product Owner-approved local environment is separately authorized.
7. If acknowledging HOLD, update only `coordination/E4/STATUS.md`.

## Acceptance

- merged E4 source remains frozen;
- no provider execution or release-gate advancement;
- no GitHub Actions/CI/hosted runner/project compute;
- executable evidence remains `NOT_RUN`.

## Writable scope

Only `coordination/E4/STATUS.md` for HOLD acknowledgement unless PM replaces this task.

## Completion / status

Wait for a separate PM/Product Owner decision on approved-local connectivity/read-only dry integration. Do not start it automatically.
