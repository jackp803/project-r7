# PM 10U Bounded Live-Fire Readiness Plan — 2026-08-29

## Purpose

Define the mandatory readiness path before any future 10 USDT bounded real-money end-to-end integration test. This document is planning/governance only. It grants no provider mutation, credential use, SHADOW/PAPER runtime, capital exposure, Gate D, or LIVE authority.

## Current authoritative baseline

```text
FP-03 shared contract = ACCEPTED
FP-03 E5 producer/policy = MERGED CANDIDATE / LOCAL VERIFICATION NOT_RUN
FP-03 E4 consumer/binding = MERGED CANDIDATE / LOCAL VERIFICATION NOT_RUN
FP-03 combined candidate revision = 9462b2594675b2e28388f55a2af189100b7cbdfc
FP-03 combined credential-free qualification = NOT_RUN / NOT_PASS
blocking dependency = approved-local PREPARE_EXACT_REVISION refused / exact-clean candidate not established
provider-facing verification on 9462b259... = NOT_RUN / NOT_INFERRED
SHADOW/PAPER = NOT AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
```

`NOT_RUN != PASS` throughout this plan.

## Readiness gates

### Gate LF-0 — Exact-revision local infrastructure

Required before any executable qualification:

- exact revision `9462b2594675b2e28388f55a2af189100b7cbdfc` established `EXACT_CLEAN` on Product-Owner-approved Windows/non-GitHub environment;
- canonical `PREPARE_EXACT_REVISION` restored/allowlisted or equivalent authoritative operator evidence accepted by PM;
- no reuse of terminal E7-101 request IDs.

Current state: `BLOCKED / EXTERNAL APPROVED-LOCAL INFRASTRUCTURE`.

### Gate LF-1 — Full credential-free executable qualification

Run a fresh exact-revision full matrix, not only FP-03 tests:

- market_data
- indicators
- strategy
- backtest
- validation
- execution
- brokers
- risk
- position
- storage
- platform
- integration
- e2e
- safety

Required result: all current suites PASS on the same exact clean revision, with actual test counts recorded. FP-03 E5 and E4 tests must be materially included.

Current state: `NOT_RUN / NOT_PASS`.

### Gate LF-2 — P0 pre-provider-runtime failure-prevention closure

The mature-bot incident audit remains the source of required failure-prevention work. Before any provider-capable runtime, all P0 items must be either implemented + freshly locally verified, or explicitly reclassified by E7/PM with evidence:

- FP-02 — SWAP action-role capability matrix;
- FP-03 — protection trigger geometry / already-breached trigger handling;
- FP-04 — external/manual provider activity ownership/reconciliation;
- FP-05 — provider-native close/residual quantity handling;
- FP-10 — authoritative external/manual close lifecycle convergence;
- FP-11 — unique active-protection registry / multiplicity reconciliation;
- FP-16 — exact runtime process/revision/mode/heartbeat preflight.

No Spot-only parameter assumption may be transplanted to OKX SWAP.

### Gate LF-3 — Failure-injection and restart/recovery qualification

Credential-free local failure-injection must cover at minimum:

- timeout / ambiguous provider-style outcome modeling without network access;
- partial fill lifecycle;
- pending/ACK does not mutate exposure truth;
- duplicate/orphan protection detection;
- missing protection / protection lost;
- stale market / stale Position / stale execution evidence;
- already-breached stop and equality boundary;
- restart while flat;
- restart while open and protected;
- restart while open and unprotected;
- restart in reconciliation-required state;
- unchanged failure evidence cannot create an unbounded retry loop;
- clock/temporal ordering fail-closed behavior;
- external/manual order/fill/position observations are never silently adopted.

Required result: locally verified fail-closed behavior with durable evidence.

### Gate LF-4 — Production provider read-only verification

Only after LF-0 through LF-3 are accepted may PM propose a separate provider read-only verification task. It requires separate Product Owner authority and secure local credentials.

Read-only observations must verify current production OKX facts relevant to the candidate revision, including:

- account mode / position mode / margin mode;
- BTC-USDT-SWAP instrument metadata needed by current capability/sizing rules;
- balances and available capital;
- positions;
- pending orders;
- fills/reconciliation state;
- provider/local clock health;
- configured GET allowlist and zero mutation capability.

Historical provider evidence from another revision must not be rebound.

### Gate LF-5 — SHADOW and PAPER readiness

Before real-money mutation:

- AgentBridge ADR-0010 consumer migration/review must be accepted;
- external watchdog/restart behavior must obey durable OperationalMode and current reconciliation state;
- current-state reporting must distinguish source, observation time, freshness, and last-known-good;
- financial kill switch and operational desync lock must remain distinct;
- SHADOW must exercise real provider observations without mutation;
- PAPER/simulated execution must exercise full lifecycle including entry fill, protection, exit, restart, reconciliation, and failure recovery.

Any SHADOW/PAPER runtime requires its own explicit authorization. Historical consumed SHADOW authorizations are not reusable.

### Gate LF-6 — 10 USDT bounded live-fire authorization

Only after LF-0 through LF-5 are accepted may PM request explicit Product Owner authorization for one bounded real-money integration session.

The session must not be treated as strategy deployment. It is a controlled end-to-end execution/recovery test.

Minimum hard limits to be fixed before authorization:

```text
capital deposited for test = 10 USDT maximum
single session = YES
single instrument = BTC-USDT-SWAP only
single concurrent position = 1 maximum
averaging down = forbidden
martingale = forbidden
revenge/increasing size after loss = forbidden
automatic continuous retry = forbidden
unknown provider/order/position/protection state = immediate fail-closed / no new exposure
provider mutation budget = finite and explicitly enumerated before session
session duration = finite and explicitly bounded before session
max acceptable realized loss = explicitly bounded below total deposited capital before session
withdrawal/transfer capability = forbidden
Gate D / general LIVE = not implied by this session
```

The exact order size/leverage/SL distance must be derived from OKX current instrument minimums, provider metadata, and E5 risk policy after read-only verification. They are not pre-authorized here.

## Required live-fire lifecycle observations

A future authorized 10U session must produce durable evidence for the complete path:

1. preflight exact process/revision/mode/config/heartbeat;
2. fresh provider/account/market reconciliation;
3. E5 approval and exact E4 authority binding;
4. bounded entry submit;
5. ACK recorded as ACK only;
6. fill observation creates/updates authoritative exposure truth;
7. E5 protection authority + FP-03 trigger-validity evaluation;
8. E4 provider-capability validation and bounded protection mutation;
9. provider readback proves intended active protection exists exactly once;
10. local registry/lifecycle/execution evidence reconcile to provider truth;
11. controlled exit or protection-triggered exit;
12. fills + authoritative flat Position truth establish CLOSED/RECONCILED_FLAT;
13. orphan protection/order cleanup verified;
14. restart and recovery confirms flat authoritative state without duplicate action.

If any step becomes unknown or inconsistent, the session terminates fail closed and no new exposure is opened.

## Post-session scope

A successful bounded 10U session does not authorize recurring LIVE trading. It only establishes evidence for the exact tested revision/configuration/session boundary. Any broader LIVE enablement remains a separate Product Owner decision and release gate.

## Immediate next work while LF-0 is blocked

Allowed preparation that does not require credentials/provider/capital:

1. E7 defines a versioned live-fire readiness/release profile from this PM plan, preserving the existing failure-prevention audit and governance boundaries.
2. E7 identifies the exact deterministic tests/evidence required for each LF gate and maps owner handoffs without implementing other workers' code.
3. No E4/E5 executable expansion is started until the sequencing is explicit and current FP-03 exact-revision qualification blocker is preserved.

This plan does not weaken or supersede any current blocker, HOLD, local-only execution rule, or Product Owner authority requirement.
