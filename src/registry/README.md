# Strategy Registry — E6 Skeleton

Status: **design-only / no executable implementation yet**.

This directory is reserved for E6-owned Strategy Registry implementation.

Authoritative design: `docs/platform/E6_REGISTRY_PERSISTENCE_LIFECYCLE_SKELETON.md`.

## Intended responsibilities

- register exact `(strategy_id, strategy_version)` identity;
- enforce same-identity/same-hash idempotence;
- reject same-identity/different-hash conflicts;
- retain rejected and retired versions;
- bind evidence to the exact strategy version;
- expose lifecycle state/history without redefining E2/E3 semantics.

## Not implemented yet

- executable StrategyDefinition adapter;
- Strategy Inbox;
- lifecycle promotion predicates;
- database access;
- migrations;
- UI/API endpoints.

Implementation begins only after E2/E3 executable contract representations are available and E7 confirms Slice 2 integration expectations.
