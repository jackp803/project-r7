# E4 Current Task

- task_id: `E4-20260822-001`
- issued_at: `2026-08-22T02:34:00+08:00`
- state: `HOLD`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0002/0003, `docs/execution/OKX_DEMO_ADAPTER_SCOPE.md`, Product Owner OKX/sub-account decision, E7 targeted re-review `status/e7/E4_OKX_DEMO_TARGETED_REREVIEW_20260821.md`

## Objective

Freeze the final corrected PR #12 Demo-first OKX provider-adapter source while E7 performs exact-revision static/security re-review of `E4-OKX-MATERIALIZATION-INTEGRITY-001` at the provider submit boundary.

## Frozen evidence

- completed correction task: `E4-20260821-012`
- branch: `agent/e4-okx-demo-adapter-20260821`
- source/tests/docs/handoff revision: `99bf09461e32117001ce7e587be44dcc3d152ab2`
- current PR #12 head after completion status: `25294d72920efab3011eb5060079bf2edca5d056`
- PR: `#12 execution: add Demo-first OKX provider adapter`
- branch synchronization: non-destructive merge completed; branch observed `behind_by=0` before this HOLD issuance
- executable verification: `NOT_RUN`
- actual provider requests/orders: `NOT_SENT`
- provider retry: `STRUCTURALLY DISABLED`

## Claimed final correction pending E7 review

E4 reports that `submit_entry()` now:

- requires the exact adapter-issued `OKXOrderMaterialization` object instance;
- validates public materialization semantics against adapter-owned immutable preparation facts before idempotency-cache access or transport;
- re-derives the signed provider request body from trusted issued facts rather than using caller body as execution authority;
- rejects direct caller construction, cross-adapter substitution, semantic mutation, and post-prepare body tampering;
- preserves the canonical BTC exposure upper bound and existing Demo/account/freshness constraints.

A new deterministic test file `tests/brokers/test_okx_submit_integrity.py` defines post-prepare tamper, direct-construction, cross-adapter, same-client-material-change, valid-submit, idempotency, and quantity-bound scenarios. These tests remain `NOT_RUN`.

## Required actions

1. Do not modify PR #12 production/test/docs source while E7 reviews the exact corrected revision.
2. Preserve the four already closed findings without redesign:
   - `E4-OKX-ACCOUNT-MATRIX-001`;
   - `E4-OKX-RETRY-PROVENANCE-001`;
   - `E4-OKX-ORDER-ABSENCE-001`;
   - `E4-OKX-ORDER-STATE-CONSISTENCY-001`.
3. Preserve Demo-only mode/header, runtime-only credentials, endpoint allowlist, `acctLv=2`, `net_mode | long_short_mode`, `tdMode=isolated`, MARKET-only path, freshness policy, canonical/provider quantity separation, disabled retry, and no asset/account-mutation surface.
4. Do not add concrete networking, real credentials, actual Demo/provider requests, production/live mode, provider retry, account/position/leverage mutation, or asset movement.
5. Do not modify shared contracts or other-agent production code.
6. Keep executable verification `NOT_RUN` until a Product Owner-approved local environment is separately authorized.
7. If acknowledging HOLD, update only `coordination/E4/STATUS.md`.

## Acceptance

PR #12 remains frozen and unmerged while E7 performs final static re-review. No provider execution or release-gate advancement is authorized.

## Writable scope

Only `coordination/E4/STATUS.md` for HOLD acknowledgement unless PM/E7 replaces this task.

## Completion / status

Wait for E7 disposition. Do not merge PR #12, begin local Demo connectivity, enable retry, or start another provider feature automatically.
