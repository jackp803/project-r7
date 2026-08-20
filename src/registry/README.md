# Strategy Registry — E6 Early Slice 2

Status: **bounded executable skeleton / local verification NOT_RUN**.

This directory now contains the minimal E6-owned Registry and Strategy Inbox service boundary needed to prepare Slice 2 without claiming that Slice 1 has passed locally.

Authoritative shared semantics remain `contracts/SHARED_CONTRACTS_V1.md` (`contracts-v0.1`). E6 does not reimplement E2 Strategy DSL/runtime semantics or E3 statistical validation semantics.

## Implemented boundary

- exact `(strategy_id, strategy_version)` registry identity;
- same identity + same immutable content is idempotent;
- same identity + conflicting content fails closed;
- StrategyDefinition shared-envelope intake at `contracts-v0.1`;
- secret-like key rejection before StrategyDefinition persistence;
- pluggable E2 `StrategyCompatibilityBoundary`;
- default compatibility boundary returns `NOT_RUN`, never synthetic PASS;
- BacktestResult evidence storage bound to exact strategy/content hash;
- ValidationDecision evidence storage bound to the exact stored BacktestResult;
- lifecycle audit + current-state projection;
- early lifecycle service only for:
  - `DRAFT -> BACKTESTING`;
  - `BACKTESTING -> REJECTED`;
  - `BACKTESTING -> CANDIDATE`.

## Evidence gates

`DRAFT -> BACKTESTING` requires explicit E2 compatibility evidence with:

- `status = PASS`;
- `verification_kind = LOCAL_EXECUTION`;
- source revision;
- local environment;
- command;
- result reference.

`BACKTESTING -> CANDIDATE` requires both the stored E3 BacktestResult and E3 ValidationDecision to have explicit local PASS evidence metadata. A contract-shaped payload, a `decision = PASS` field, or a GitHub branch/commit by itself is insufficient.

## Deliberately unavailable

This slice exposes no service path for:

- `CANDIDATE -> PAPER`;
- `READY_FOR_APPROVAL`;
- `APPROVED`;
- `LIVE`;
- operational-mode LIVE activation;
- Product Owner approval capture;
- UI promotion controls.

Those remain later-slice work after the required local/E7 evidence exists.

## Files

- `models.py` — internal E6 records/errors; not shared contract replacements.
- `ports.py` — RegistryStore and E2 compatibility adapter boundaries.
- `service.py` — guarded Strategy Inbox/evidence/early lifecycle orchestration.

All tests are local-only. GitHub Actions/CI/hosted runners are forbidden.
