# E2 Current Task

- task_id: `E2-20260821-002`
- issued_at: `2026-08-21T10:58:00+08:00`
- state: `ACTIVE`
- authority: `agents/E2_STRATEGY_ENGINE.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0002

## Objective

Implement the provider-neutral executable TradeIntent entry profile required by the new canonical `entry-v0.1` contract refinement, without changing strategy logic, broker behavior, or the existing Slice 1 Strategy Runtime semantics.

## Required actions

1. Work on `agent/e2-strategy-engine` and synchronize non-destructively with the latest `main` before implementation. Do not force-rewrite history. If safe synchronization is not possible, report `BLOCKED`.
2. Preserve the existing corrected StrategyDefinition/DSL/runtime behavior and Issue #5 compatibility fix.
3. At the TradeIntent serialization/production boundary, support canonical executable intent fields:
   - `entry_profile_version = entry-v0.1`
   - `entry_order_type = MARKET`
4. Treat legacy `entry_style` and `entry_reference_price` as non-executable/advisory only. Do not infer executable order type or price from them.
5. Reject/fail closed for executable promotion when:
   - profile version is unknown/unsupported;
   - `entry-v0.1` is missing `entry_order_type`;
   - order type is anything other than `MARKET`;
   - provider/exchange-specific order semantics are requested.
6. Do not add quantity, leverage, margin, broker credentials, OKX instrument IDs, provider contract units, or risk approval into TradeIntent.
7. Add deterministic local-only tests covering:
   - canonical `entry-v0.1/MARKET` serialization;
   - unsupported entry order type rejection;
   - unknown profile rejection;
   - legacy `entry_style` does not become executable automatically;
   - advisory reference price remains advisory;
   - existing Strategy Runtime deterministic behavior is unchanged.
8. Update E2 handoff/status and `coordination/E2/STATUS.md` with exact branch HEAD, changed files, profile behavior, and verification state.
9. Executable verification is local-only. If no Product Owner-approved local environment exists, record `NOT_RUN` plus exact commands.

## Acceptance

- E2 emits contract-compatible `entry-v0.1` TradeIntent objects for MARKET-only executable intent;
- no strategy-logic rewrite;
- no broker/OKX/private API code;
- no quantity/risk authority leakage into E2;
- no shared-contract edits;
- no GitHub Actions/CI/hosted runner/project compute;
- executable evidence remains `NOT_RUN` if local execution is unavailable.

## Writable scope

E2-owned paths only:

- `src/strategy/**`
- `src/indicators/**` only if directly required by existing imports, not for new indicator features
- E2 schema/serialization files
- `tests/strategy/**`
- E2-owned docs/status/handoff
- `coordination/E2/STATUS.md`

## Forbidden scope

- `contracts/**` changes;
- E1/E3/E4/E5/E6 production rewrites;
- OKX/Pionex provider logic;
- risk sizing/approval;
- PAPER/SHADOW/LIVE enablement;
- GitHub compute/CI.

## Completion / status

Persist the bounded profile implementation and handoff, update STATUS, then stop. Do not start additional primitives, indicators, broker work, or provider-specific features automatically.
