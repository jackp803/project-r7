# PM Mature OKX Bot Failure-Prevention Baseline — 2026-08-29

## Purpose

Product Owner supplied operational incident history from a separate, more mature OKX BTC trading bot and instructed project-r7 to learn from those failures and prevent equivalent failure classes before future provider/runtime progression.

This artifact is a **sanitized failure-prevention baseline**, not a code transplant and not evidence that project-r7 has already implemented or verified every control below.

The reference bot is primarily OKX **Spot BTC/USDT** while project-r7 currently targets **BTC-USDT-SWAP perpetual** for Gate C work. Therefore Spot-specific fixes (`tdMode=cash`, Spot `reduceOnly` rejection, BTC balance dust, Spot algo-order `ccy`) must **not** be copied literally into SWAP code. E7/E4 must translate each incident into instrument/mode-specific safety invariants.

No credentials, local filesystem paths, exact balances, provider IDs, private responses, or other sensitive source-project data are recorded here.

## Product Owner incident lessons

### FP-01 — Runtime mode must never drift across restart

Observed class:
- safe default / environment handling caused a restarted bot to enter an unintended DRY_RUN/live posture until the watchdog explicitly injected the intended mode.

R7 prevention invariant:
- operational mode is authoritative, persisted/audited, and explicit at startup;
- missing/ambiguous runtime mode must fail closed rather than silently selecting a more permissive mode;
- environment variables or scheduler defaults must not override authoritative mode without validated policy;
- mode transitions must have provenance and survive restart consistently.

Primary owners: E6 + E7.

### FP-02 — Provider parameters must be instrument/account-mode specific

Observed class:
- OKX Spot rejected unsupported `reduceOnly` and required correct Spot `tdMode/ccy` semantics.

R7 prevention invariant:
- E4 maintains a provider capability/parameter matrix tied to exact instrument type, account mode, margin mode, position mode, and order role;
- unsupported parameter combinations fail locally before network dispatch;
- BTC-USDT-SWAP semantics are tested independently from Spot semantics;
- no generic order builder may silently reuse parameters across incompatible market types.

Primary owner: E4; integration acceptance: E7.

### FP-03 — Do not rebuild invalid protection after trigger is already breached

Observed class:
- stop-loss recreation failed when the trigger was already on the wrong side of current market price.

R7 prevention invariant:
- before protection create/replace, validate trigger geometry against current/fresh market truth and provider rules;
- if required protection is already breached, do not loop on the same invalid protection request;
- transition to E5-defined exit/emergency/reconciliation handling instead of retry storms;
- terminal/retry state must be explicit and auditable.

Primary owners: E5 policy + E4 capability/execution + E7 lifecycle integration.

### FP-04 — External/manual provider activity must reconcile into system truth or fail closed

Observed class:
- manual/external stop orders existed at OKX but local DB/order truth did not know them, producing persistent DESYNC/LOCKED conditions.

R7 prevention invariant:
- unknown provider orders/fills/positions are first-class reconciliation events;
- the system must define whether each external state may be safely adopted/imported, must be rejected, or requires manual review;
- do not silently treat an untracked provider order as trusted protection;
- local order/protection registries and provider truth must converge under explicit rules before new exposure.

Primary owners: E4 + E6; semantic authority: E5/E7.

### FP-05 — Residual quantity and minimum-size handling must not create fake positions or retry storms

Observed class:
- tiny Spot BTC residuals/dust and below-minimum exits left local lifecycle active, causing repeated ENSURE_SL/EXIT attempts.

R7 prevention invariant for SWAP:
- use provider instrument metadata (`lotSz`, minimum quantity/notional where applicable, contract sizing/precision) and exact position truth;
- close/reduce quantity must be clamped to actual reducible position, never stale requested/entry quantity;
- define explicit residual/rounding state instead of arbitrary floating-point equality;
- if remaining exposure cannot be acted on because of provider minimums/availability, enter a stable fail-closed waiting/reconciliation state and do not retry every loop.

Primary owners: E4 + E5; persistence/visibility: E6.

### FP-06 — Reporting must identify authoritative source and freshness

Observed class:
- Telegram/audit output displayed stale local position after provider was flat.

R7 prevention invariant:
- dashboards/reports distinguish provider observation, canonical lifecycle projection, persisted historical state, and their timestamps;
- never display stale ledger/projection state as current provider truth;
- degraded/stale/unknown must not render as healthy/flat/open without provenance;
- provider observation freshness and lifecycle revision are visible/auditable.

Primary owner: E6; source contracts: E4/E5/E7.

### FP-07 — DESYNC lock and true risk kill switch are different state machines

Observed class:
- stale desync lock survived restart and was interpreted as a real kill switch.

R7 prevention invariant:
- operational/reconciliation lock, financial risk kill switch, release/runtime authorization, and provider health are separately typed states;
- one state must not be reconstructed from another boolean/string;
- restart recovery must preserve reason/provenance and only clear states according to their own rules;
- UI must not conflate them.

Primary owners: E5 + E6 + E7.

### FP-08 — Provider clock skew must be a startup/runtime safety precondition

Observed class:
- Windows time drift caused OKX `50102 Timestamp request expired` failures after outage/restart.

R7 prevention invariant:
- private-provider activity requires provider/local clock-health preflight;
- skew thresholds are explicit and fail closed;
- time-sync failures do not trigger blind retries or order duplication;
- authentication timestamp, provider observation time, and E7 risk-decision temporal ordering remain distinct and tested.

Primary owners: E4 + E7.

### FP-09 — Watchdog recovery must be state-aware, not merely process-aware

Observed class:
- reboot/outage stopped runtime; later watchdog recovery had to distinguish safe flat restart from stale/hung process and protected-position cases.

R7 prevention invariant:
- watchdog/launcher proves single active instance, revision identity, mode, heartbeat freshness, and required local state before restart;
- automatic restart is allowed only for explicitly safe classes (for example exact flat/known state if policy says so);
- unknown/protected/open-position recovery must not be guessed or force-restarted without defined evidence;
- restart must re-run reconciliation before any new exposure.

Primary owners: E7 operational integration + E6 operational state; E4/E5 recovery semantics.

### FP-10 — Position lifecycle closes only after actual execution truth

Observed class:
- exit lifecycle previously risked closing on first exit execution instead of aggregate fills; manual flatten also required a distinct reconciliation path.

R7 prevention invariant:
- requested, acknowledged, partially filled, fully filled, position-flat, and lifecycle-closed are distinct facts;
- `CLOSED` depends on canonical execution/provider truth and lifecycle policy, not the existence of an exit request/one execution row;
- manual/provider-side flatten maps through explicit reconciliation (`RECONCILED_FLAT` or approved equivalent);
- partial fills must update protection/remaining quantity using actual fills.

Primary owners: E4 + E5 + E7; persistence: E6.

### FP-11 — Protection registry must be authoritative and uniquely linked

Observed class:
- stop-loss existence was too dependent on repeated exchange probing; later a protection registry linked active SL to the trade.

R7 prevention invariant:
- every open position requiring protection has an explicit protection role/identity linked to the canonical position/trade/lifecycle revision;
- at most the policy-allowed number of active protection orders exists for a position;
- provider order identity, local registry identity, execution evidence and lifecycle projection remain cross-referenceable;
- unknown/multiple/missing protection fails closed.

Primary owners: E4 execution evidence + E5 semantic protection + E6 persistence + E7 contract.

### FP-12 — Pending/ambiguous execution must not mutate position truth as if filled

Observed class:
- pending execution data inflated local position ledger, creating quantity mismatch and desync.

R7 prevention invariant:
- only actual fill/position evidence changes filled position quantity;
- request/ack/pending states do not mutate fill-derived exposure;
- timeout/ambiguous acknowledgement triggers idempotent query/reconciliation before retry;
- requested quantity and filled quantity remain separate everywhere.

Primary owner: E4; lifecycle consumer: E5/E6/E7.

### FP-13 — Reconciliation must not continue with a stale pre-recovery snapshot

Observed class:
- after DESYNC resolution, subsequent management logic consumed stale sync state and rebuilt duplicate protection.

R7 prevention invariant:
- a reconciliation transition invalidates stale pre-reconcile snapshots;
- subsequent risk/protection decisions must consume a newly attested/monotonically newer snapshot or stop;
- snapshot observation time and lifecycle revision are independently ordered;
- no same-cycle reuse of state known to be superseded.

Primary owners: E7 integration + E4/E5; E6 persistence ordering.

### FP-14 — Retry must become an explicit stable state when the action cannot currently succeed

Observed class:
- unavailable/frozen base balance caused repeated exit attempts and external/local alert loops until `WAITING_AVAILABLE_BASE` semantics were added.

R7 prevention invariant:
- retries are bounded and reason-aware;
- deterministic provider rejections/minimum-size/insufficient-reducible-quantity conditions do not hammer the same request every loop;
- stable waiting/reconciliation states suppress duplicate side effects while remaining visible and recoverable;
- retry eligibility requires a materially changed authoritative condition.

Primary owners: E4 + E5; visibility: E6.

### FP-15 — Profit protection must mature through staged evidence

Observed class:
- breakeven/trailing protection was developed as offline state machine -> dry-run adapter -> monitor/failure injection -> guarded live pilot with strict replacement limits and exchange/DB match requirements.

R7 prevention invariant:
- break-even/trailing/protection replacement starts as deterministic offline semantics and failure-injection tests;
- then Paper/Shadow evidence as separately authorized by release policy;
- no unlimited live cancel/replace loop;
- replacement is monotonic in risk reduction, idempotent, provider/local matched, bounded in frequency, and fail closed if replacement leaves position unprotected;
- activation is feature/policy-versioned and separately approved.

Primary owners: E5 + E4 + E7; E6 configuration/audit.

### FP-16 — Startup/runtime environment must be validated as part of execution identity

Observed class:
- PowerShell environment syntax and scheduler launcher behavior changed effective runtime behavior; hidden launcher/watchdog details mattered operationally.

R7 prevention invariant:
- runtime identity includes exact project revision, operational mode, approved local environment, process identity/heartbeat, and configured action capability;
- scheduler/launcher is infrastructure, not an implicit source of trading policy;
- startup preflight must reject missing/invalid critical configuration rather than silently defaulting to a more dangerous state;
- local-path/platform-specific details stay out of public evidence while sanitized classifications are persisted.

Primary owners: E7 + AgentBridge/operator; E6 mode persistence.

## Existing R7 controls already aligned in principle

The current role contracts already require several relevant protections:

- E4: stable client/order identity, no blind retry after timeout, exchange truth reconciliation, partial fills based on actual filled quantity, restart recovery, explicit Paper/Shadow/Live boundaries, and provider time handling.
- E5: explicit position lifecycle, unknown-state fail closed, protection based on actual execution, persistent kill switches, break-even/profit-protection ownership, and reconciliation-required state.
- E6: persistent operational mode, audit trail, current position/protection/reconciliation display, restart persistence, and false-green prevention.
- E7/current architecture: explicit lifecycle projection ordering, execution-evidence binding, fail-closed integration, local-only verification, and release-gate provenance.

These are **design alignment only**. They do not prove the concrete OKX-SWAP implementation/test matrix covers every failure-prevention item above.

## Required next step

E7 must perform a repository-grounded cross-module gap audit against FP-01..FP-16 and classify every item as exactly one of:

- `IMPLEMENTED_AND_LOCALLY_VERIFIED`
- `IMPLEMENTED_NOT_LOCALLY_VERIFIED`
- `PARTIAL`
- `MISSING`
- `NOT_APPLICABLE_TO_SWAP` (with reason and substitute invariant if applicable)

For every non-complete item, E7 must identify:

- exact owner (E4/E5/E6/E7/operator);
- exact source/test/contract evidence currently present;
- the smallest safe follow-up task;
- whether implementation changes executable source and therefore requires new local requalification;
- whether provider access, credentials, capital, Product Owner authority, or external AgentBridge/operator work is required.

The audit itself grants **no** provider/private API, credential, SHADOW/PAPER/LIVE, mutation, order, or capital authority.

## Runtime authority remains unchanged

- both prior bounded SHADOW authorizations remain consumed;
- current temporal-remediation baseline `8fbf5fcae2eaf44accdf535121d8abf29ef5c93c` is credential-free requalified only;
- provider-facing evidence for that revision remains `NOT_RUN / NOT_INFERRED`;
- AgentBridge ADR-0010 consumer migration/review remains an external prerequisite;
- any third/replacement SHADOW runtime still requires new explicit Product Owner authorization;
- PAPER, Gate D and LIVE remain unauthorized unless separately approved.
