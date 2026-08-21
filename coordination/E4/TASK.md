# E4 Current Task

- task_id: `E4-20260821-011`
- issued_at: `2026-08-21T16:02:00+08:00`
- state: `HOLD`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0002/0003, `docs/execution/OKX_DEMO_ADAPTER_SCOPE.md`, Product Owner OKX/sub-account decision, E7 review `status/e7/E4_OKX_DEMO_STATIC_SECURITY_REVIEW_20260821.md`

## Objective

Freeze the corrected PR #12 Demo-first OKX provider-adapter source while E7 performs targeted static/security re-review of the five prior blocking findings.

## Frozen evidence

- completed correction task: `E4-20260821-010`
- branch: `agent/e4-okx-demo-adapter-20260821`
- corrected implementation/tests/docs/handoff revision: `651541ba0da646f0c2ab69117219e2c8ca21247c`
- current PR #12 branch head after status completion: `c151fa7c37adafbf9f93157d80cf4b763dd775e2`
- PR: `#12 execution: add Demo-first OKX provider adapter`
- executable verification: `NOT_RUN`
- actual provider requests/orders: `NOT_SENT`
- provider retry: `STRUCTURALLY DISABLED`

## Correction claims pending E7 re-review

- `E4-OKX-MATERIALIZATION-INTEGRITY-001`: provider sizing recomputed from exact `OrderRequest` + submit-validated metadata; supplied audit is evidence-only and must match recomputed facts.
- `E4-OKX-ACCOUNT-MATRIX-001`: V1 narrowed to `acctLv=2` with `net_mode | long_short_mode` and `tdMode=isolated`; other account levels rejected pending authority.
- `E4-OKX-RETRY-PROVENANCE-001`: retry is structurally disabled; reconciliation evidence cannot authorize a second submit.
- `E4-OKX-ORDER-ABSENCE-001`: caller-controlled order-absence codes removed; non-success/empty lookup never proves absence for retry.
- `E4-OKX-ORDER-STATE-CONSISTENCY-001`: provider order state is cross-checked against `accFillSz/sz`; contradictions fail closed.

## Required actions

1. Do not modify PR #12 production/test source while E7 re-reviews the corrected revision.
2. Preserve all prior accepted boundaries: Demo-only environment/header, runtime-only credential handling, canonical/provider quantity separation, MARKET + isolated scope, freshness hardening, endpoint allowlist, and Broker/PaperBroker safety behavior.
3. Keep provider retry structurally disabled. Do not add retry tokens, absence-code configuration, or another retry path during HOLD.
4. Do not add concrete networking, real credentials, actual Demo/provider requests, production/live mode, account/position/leverage mutation, or asset-movement capability.
5. Do not modify shared contracts or other-agent production code.
6. Keep executable verification `NOT_RUN` until a Product Owner-approved local environment is explicitly authorized.
7. If acknowledging HOLD, update only `coordination/E4/STATUS.md`.

## Acceptance

- corrected PR #12 source remains frozen for exact-revision E7 review;
- no provider execution or release-gate advancement;
- no GitHub Actions/CI/hosted runner/project compute;
- executable evidence remains `NOT_RUN`.

## Writable scope

Only `coordination/E4/STATUS.md` for HOLD acknowledgement unless PM/E7 replaces this task.

## Completion / status

Wait for E7 disposition. Do not merge PR #12, begin local Demo connectivity, enable retry, or start another provider feature automatically.
