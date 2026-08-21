# E7 Current Task

- task_id: `E7-20260821-006`
- issued_at: `2026-08-21T12:41:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-e2-e5-profile-review-20260821`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, Product Owner OKX decision

## Objective

Perform static integration review of the completed E2 `TradeIntent` producer and E5 `ApprovedTradePlan` / canonical quantity producer as one producer-consumer chain before E4 is authorized to implement profile translation and OKX sizing logic.

This task does not re-review E1 PR #8. E1 is separately resolving repository synchronization finding `E1-INTEGRATION-SYNC-001`.

## Review inputs

### E2

- branch: `agent/e2-strategy-engine`
- implementation/handoff revision: `f99a8d00cd1fe40e1d73964d8b1cf37bc1886bd4`
- handoff: `status/E2_TRADE_INTENT_ENTRY_PROFILE_HANDOFF.md`
- expected profile: `entry-v0.1 / MARKET`
- executable verification: `NOT_RUN`

### E5

- branch: `agent/e5-risk-position`
- implementation revision: `e5f7088301a92deadfd9f6c416ae03b466c38a47`
- reported post-task branch head: `3c8f9fa558cc90ad69fd5e58dcd4f6aa457e8de4`
- handoff: `status/E5_RISK_POSITION_HANDOFF.md`
- expected entry profile: `entry-v0.1 / MARKET`
- expected quantity profile: `base-asset-v0.1 / BASE_ASSET / BTC`
- executable verification: `NOT_RUN`

## Required actions

1. Work only on fresh branch `agent/e7-e2-e5-profile-review-20260821` from latest `main`.
2. Statically review E2 against `contracts-v0.1`, `entry-v0.1`, and ADR-0002. Confirm at minimum:
   - explicit profile opt-in is required;
   - only `MARKET` is executable;
   - legacy `entry_style` is non-executable;
   - `entry_reference_price` remains advisory;
   - provider/exchange/risk/quantity authority does not leak into TradeIntent;
   - existing Slice 1 Strategy Runtime/DSL/Signal semantics are not rewritten.
3. Statically review E5 against `contracts-v0.1`, `entry-v0.1`, `base-asset-v0.1`, ADR-0002, and ADR-0003. Confirm at minimum:
   - only explicit `entry-v0.1 / MARKET` TradeIntent is execution-eligible;
   - legacy style-only intent cannot become executable;
   - ApprovedTradePlan emits `entry_instruction.profile_version=entry-v0.1` and `order_type=MARKET`;
   - advisory reference price never becomes executable limit/stop/trigger/TIF;
   - `quantity_profile_version=base-asset-v0.1`, `quantity_unit=BASE_ASSET`, `quantity_asset=BTC` for `BTC_USDT_PERP`;
   - plan `quantity` remains the maximum E5-approved new-position BTC exposure bound;
   - no OKX/provider-native sizing fields or API concerns enter E5;
   - accepted `E5-RISK-UNKNOWN-001` fail-closed guards remain intact.
4. Review the E2 -> E5 boundary together. Verify E5 consumes the exact E2 field names/values and no translation ambiguity remains before E4.
5. Check source/test/handoff changed-file scope for contract collision, provider leakage, authority bypass, unsafe defaults, secrets, or GitHub-compute violations.
6. Review deterministic test definitions for the producer chain but do not execute tests in GitHub.
7. Persist an E7 review artifact and update `coordination/E7/STATUS.md` with separate dispositions for E2, E5, and the combined E2->E5 boundary: `PASS | FAIL | BLOCKED`.
8. If both producers and their boundary are statically accepted, explicitly state whether E4 may receive the next bounded task for:
   - mechanical `entry-v0.1` translation;
   - canonical quantity preservation;
   - deterministic OKX instrument-metadata conversion/round-down-or-reject logic;
   while still excluding private/Demo API implementation.
9. If a defect remains, issue a precise owner-specific finding. Do not modify E2/E5 production code yourself and do not create a Codex bug ticket without local reproduction.
10. Keep executable disposition `NOT_RUN`, Gate A/B/C/D unchanged, and do not use GitHub Actions/CI/hosted runner/project compute.

## Acceptance

Task is complete when Git contains:

- E2 static disposition;
- E5 static disposition;
- combined E2 -> E5 profile-boundary disposition;
- exact remaining blockers/findings, if any;
- explicit yes/no recommendation for starting bounded E4 profile/OKX sizing implementation;
- no E1-E6 domain implementation edits;
- executable evidence still `NOT_RUN`;
- release gates unchanged.

## Writable scope

- E7-owned review/status/integration artifacts
- `coordination/E7/STATUS.md`

## Forbidden scope

- E1/E2/E3/E4/E5/E6 production implementation edits;
- shared-contract changes;
- E1 PR #8 re-review in this task;
- OKX private/Demo API implementation;
- PAPER/SHADOW/LIVE enablement;
- GitHub compute/CI;
- treating static PASS as executable PASS.

## Completion / status

Persist the producer-chain review, update STATUS, then stop and wait for PM. Do not start E4 implementation automatically.
