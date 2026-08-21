# E7 Current Task

- task_id: `E7-20260821-003`
- issued_at: `2026-08-21T09:05:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-entry-contract-vnext-20260821`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts/README.md`, `contracts-v0.1`, ADR-0001, release gates

## PM disposition on prior review

The prior E7 finding `E7-E4E5-ENTRY-001` is accepted as a real `CONTRACT MISMATCH`.

The proposed minimum executable entry semantics (`MARKET`, optionally `LIMIT` with explicit executable price/TIF) are directionally accepted for further contract work.

However, the prior draft recommendation to jump directly from the current set-wide `contracts-v0.1` baseline to `contracts-v1.0` is **not yet approved**. Before versioning, E7 must resolve the repository-wide compatibility impact of the current shared `schema_version` convention and include every affected producer/consumer, especially E2 as `TradeIntent` producer and the already-frozen E1/E2/E3 Slice 1 implementations that currently bind to `contracts-v0.1`.

## Objective

Complete the formal contract-change procedure for executable entry instructions and materialize the **smallest technically safe versioned contract revision** only if repository-wide compatibility and migration semantics are coherent.

This is a contract/ADR/integration-test-definition task only. Do not modify E2/E4/E5/E6 production implementation.

## Required actions

1. Work on fresh branch `agent/e7-entry-contract-vnext-20260821` from the latest `main`. Do not reuse or merge old E7 review branches into it.
2. Treat `docs/architecture/E4_E5_ENTRY_INSTRUCTION_CONTRACT_CHANGE_PROPOSAL.md` from the completed E7 review as input, not as an already-approved versioning decision.
3. Complete the contract-change procedure from `contracts/README.md`:
   - request/problem statement;
   - full producer inventory;
   - full consumer inventory;
   - behavioral/persistence/replay/migration/release impact;
   - compatibility classification;
   - ADR because executable shared semantics materially change;
   - versioned contract revision if coherent;
   - local integration/safety test definitions;
   - executable verification remains `NOT_RUN` unless Product-Owner-approved local evidence exists.
4. Expand the impact inventory beyond E4/E5/E6. At minimum review:
   - E2 as producer of `TradeIntent.entry_style` / future TradeIntent instances;
   - E5 as producer of `ApprovedTradePlan.entry_instruction`;
   - E4 as primary execution consumer;
   - E6 as future audit/persistence consumer;
   - E1/E2/E3 frozen Slice 1 code where a set-wide schema-version bump could make otherwise unrelated Candle/StrategyDefinition/Signal/BacktestResult consumers incompatible;
   - E7 integration evidence and release gates.
5. Explicitly decide the versioning model before changing `contracts/**`:
   - whether `schema_version` is a set-wide version that forces all shared objects to migrate together;
   - or whether a narrower object/profile version can be introduced without creating ambiguous parallel contract authority;
   - whether an additive compatible revision is possible while old `style`-only plans remain valid-but-non-executable;
   - whether a breaking revision is truly required.
6. **Do not perform a set-wide major bump merely because the entry sub-profile is currently underspecified.** If a major set-wide bump is selected, document why no smaller safe compatible treatment exists and provide an explicit migration/support plan for every currently implemented `contracts-v0.1` producer/consumer, including the frozen Slice 1 E1/E2/E3 code.
7. Preserve the following semantic requirements regardless of version treatment:
   - `ApprovedTradePlan.entry_instruction` must have explicit executable semantics before E4 translation;
   - initial supported executable order types are deliberately minimal;
   - `MARKET` may not carry executable limit/stop/TIF fields;
   - if `LIMIT` is supported, `limit_price` must be explicit, positive finite decimal-string data and `time_in_force` must use an explicit supported enum;
   - `reference_price` remains audit/advisory context and must never be silently promoted to executable `limit_price`/`stop_price`;
   - STOP/trigger/post-only/trailing/exchange-specific styles remain unsupported until separately versioned;
   - unknown/unsupported order types or invalid conditional combinations fail closed;
   - E4 maps canonical fields mechanically and cannot invent price, quantity, leverage, margin mode, protection loosening, or risk approval.
8. Decide how upstream `TradeIntent.entry_style` participates. If current E2 has no executable TradeIntent producer yet, record that fact, but still define the producer contract so E5 is not forced to infer executable price semantics later.
9. If the coherent result is an approved versioned contract revision, materialize it on the E7 branch:
   - update `contracts/README.md` registry/version/support policy;
   - add or revise canonical shared-contract documentation without mutating the historical meaning of `contracts-v0.1`;
   - create/update an ADR describing the entry-instruction semantics and versioning decision;
   - add E7-owned local-only integration/safety test definitions for E2/E5/E4 boundaries as applicable;
   - record migration/compatibility rules and exact follow-up scopes for E2/E5/E4/E6.
10. If no coherent versioning treatment can be established without a broader architecture decision, do **not** modify `contracts/**`; return `BLOCKED` with the exact unresolved decision and alternatives.
11. Do not enable PAPER/SHADOW/LIVE and do not advance Gate A/B/C/D.
12. Do not use GitHub Actions/CI/hosted runner/project compute.

## Acceptance

This task is complete only when one of the following is true:

### A. Contract revision materialized

- full producer/consumer inventory exists;
- compatibility/versioning decision is explicit and justified;
- historical `contracts-v0.1` semantics are not silently rewritten;
- ADR exists for the material semantic/versioning decision;
- canonical versioned entry-instruction semantics are materialized;
- migration/support rules are explicit;
- E2/E5/E4/E6 follow-up scopes are bounded;
- integration/safety test definitions exist;
- executable verification is `NOT_RUN` unless approved local evidence exists;
- release gates remain blocked.

### B. Contract change remains blocked

- `contracts/**` remains unchanged;
- the unresolved architectural/versioning decision is precisely documented;
- alternatives and affected owners are identified;
- no domain implementation starts against an unapproved semantic profile.

## Writable scope

- `contracts/**` only as part of the formal versioned change procedure
- `docs/adr/**`
- E7-owned architecture/integration/status/review paths
- `tests/integration/**`
- `tests/safety/**` only for E7-owned cross-module contract scenarios
- `coordination/E7/STATUS.md`

## Forbidden scope

- E1/E2/E3/E4/E5/E6 production implementation edits;
- silent mutation of historical `contracts-v0.1` meaning;
- unversioned executable entry semantics;
- Pionex/private execution work;
- PAPER/SHADOW/LIVE enablement;
- GitHub Actions/CI/runner/project compute;
- treating static evidence or `NOT_RUN` as executable PASS.

## Completion / status

Persist the contract decision/revision or precise blocker, update `coordination/E7/STATUS.md`, and stop. Do not automatically start E2/E4/E5 implementation after the contract task.
