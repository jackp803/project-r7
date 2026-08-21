# E5 Current Task

- task_id: `E5-20260821-004`
- issued_at: `2026-08-21T10:58:00+08:00`
- state: `ACTIVE`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0002, ADR-0003

## Objective

Implement the new provider-neutral executable entry and canonical quantity profiles at the E5 RiskDecision -> ApprovedTradePlan boundary while preserving E5 risk authority and the accepted fail-closed correction.

## Required actions

1. Work on `agent/e5-risk-position` and synchronize non-destructively with the latest `main` before implementation. Do not force-rewrite history. If safe synchronization is not possible, report `BLOCKED`.
2. Preserve the accepted `E5-RISK-UNKNOWN-001` correction and the authority chain `TradeIntent -> RiskDecision -> ApprovedTradePlan`.
3. Consume executable TradeIntent only when it declares:
   - `entry_profile_version = entry-v0.1`
   - `entry_order_type = MARKET`
   Unknown/missing/unsupported executable profiles fail closed.
4. Emit canonical ApprovedTradePlan entry instruction:
   - `entry_instruction.profile_version = entry-v0.1`
   - `entry_instruction.order_type = MARKET`
   - optional `reference_price` remains advisory only.
5. Emit the canonical quantity profile for `BTC_USDT_PERP`:
   - `quantity_profile_version = base-asset-v0.1`
   - `quantity_unit = BASE_ASSET`
   - `quantity_asset = BTC`
   - `quantity` means maximum E5-approved new-position BTC exposure bound.
6. Do not interpret legacy `entry_style` as executable and do not promote advisory/reference price into executable limit/stop price.
7. Do not implement OKX `sz`, `ctVal`, `ctMult`, `ctValCcy`, `lotSz`, `minSz`, `tickSz`, instrument metadata retrieval, account mode, provider API calls, or credentials. Those remain E4/provider-adapter responsibilities.
8. Preserve the rule that downstream provider quantization may realize less than the approved canonical quantity but may never exceed the E5-approved bound.
9. Add deterministic local-only safety/risk tests covering at minimum:
   - valid profiled MARKET intent -> profiled ApprovedTradePlan;
   - missing/unknown profile -> reject;
   - unsupported executable order type -> reject;
   - legacy style-only intent -> not execution eligible;
   - advisory reference price remains non-executable;
   - exact quantity profile/unit/asset propagation;
   - forged/unsafe approval cannot bypass the existing fail-closed state checks.
10. Update E5 handoff/status and `coordination/E5/STATUS.md` with exact branch HEAD, changed files, profile semantics, and verification state.
11. Executable verification remains local-only. If no Product Owner-approved local environment exists, record `NOT_RUN` plus exact commands.

## Acceptance

- E5 produces `entry-v0.1` MARKET-only ApprovedTradePlan instructions;
- E5 quantity is explicitly canonical BTC base-asset exposure under `base-asset-v0.1`;
- no exchange contract sizing or OKX API logic enters E5;
- existing fail-closed risk behavior remains intact;
- no shared-contract changes;
- no Pionex new development;
- no PAPER/SHADOW/LIVE authority;
- no GitHub Actions/CI/hosted runner/project compute;
- executable evidence remains `NOT_RUN` if local execution is unavailable.

## Writable scope

E5-owned paths only:

- `src/risk/**`
- `src/position/**` only if directly required for canonical quantity/profile propagation
- `tests/risk/**`
- `tests/position/**` only if directly required
- `tests/safety/**` for E5-owned scenarios
- E5-owned docs/status/handoff
- `coordination/E5/STATUS.md`

## Forbidden scope

- `contracts/**` changes;
- E1/E2/E3/E4/E6 production rewrites;
- OKX/Pionex API/auth/instrument-metadata implementation;
- provider contract sizing/quantization;
- production policy-value expansion;
- PAPER/SHADOW/LIVE enablement;
- GitHub compute/CI.

## Completion / status

Persist the bounded producer/profile implementation and handoff, update STATUS, then stop. Do not start OKX adapter, broker, or new risk-policy features automatically.
