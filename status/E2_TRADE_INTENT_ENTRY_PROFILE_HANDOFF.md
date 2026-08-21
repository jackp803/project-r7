# Handoff

**From:** E2 / Strategy Engine Engineer  
**To:** E7 / Integration Engineer; E5 / Risk & Position Engineer  
**Branch:** `agent/e2-strategy-engine`  
**Commit(s):** non-destructive main sync `efa8703dd47ce4221a0c56fccb8b330d81e46ee1`; implementation commit = branch HEAD containing this handoff  
**Date:** 2026-08-21

### 1. Objective

Implement task `E2-20260821-002`: the provider-neutral executable TradeIntent entry profile required by canonical `entry-v0.1`, without changing existing Slice 1 Strategy Runtime/DSL/Signal semantics, broker behavior, risk authority, or shared contracts.

### 2. What changed

- added `src/strategy/trade_intent.py` as an E2 TradeIntent production/serialization boundary;
- added exact executable profile constants:
  - `entry_profile_version = entry-v0.1`
  - `entry_order_type = MARKET`;
- added deterministic `intent_id` derivation over canonical serialized intent material;
- required explicit profile opt-in: legacy `entry_style` never creates `entry_order_type`;
- kept `entry_reference_price` and strategy stop/target levels advisory strategy context only;
- fail closed for unknown profile, missing order type, non-MARKET order type, executable LIMIT/trigger/TIF fields, provider/exchange-specific fields, and risk/sizing/broker authority fields;
- preserved parent shared schema `contracts-v0.1`;
- added local-only unit/regression test definitions for profile serialization/failure cases and existing Strategy Runtime determinism;
- added E2 entry-profile documentation.

`src/strategy/runtime.py` is unchanged by this task. No StrategyDefinition, Signal, Candle, SMA, DSL, or runtime-version semantic change was made.

### 3. Files changed

Task implementation paths:

- `src/strategy/trade_intent.py` — new
- `src/strategy/__init__.py` — exports TradeIntent profile API
- `tests/strategy/test_trade_intent.py` — new local-only test definitions
- `docs/strategy/TRADE_INTENT_ENTRY_PROFILE.md` — new behavior/authority documentation
- `status/E2_TRADE_INTENT_ENTRY_PROFILE_HANDOFF.md` — this handoff
- `coordination/E2/STATUS.md` — updated separately after implementation commit

Pre-implementation synchronization:

- merge commit `efa8703dd47ce4221a0c56fccb8b330d81e46ee1` non-destructively synchronized latest `main` into `agent/e2-strategy-engine` with both histories preserved.

### 4. Contracts consumed

- parent shared contract set: `contracts-v0.1`
- `contracts/SHARED_CONTRACTS_V1.md` — Signal and TradeIntent baseline
- `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md` — `entry-v0.1`
- ADR-0002 — versioned executable entry profile decision
- E2 Strategy Runtime `0.1.0` / DSL `0.1` Signal producer boundary

Relevant canonical semantics consumed:

```text
TradeIntent.schema_version = contracts-v0.1
entry_profile_version      = entry-v0.1
entry_order_type           = MARKET
```

Legacy `entry_style` and `entry_reference_price` remain advisory/non-executable.

### 5. Contracts produced or changed

Shared contract changes: `NONE`.

E2 now produces new TradeIntent instances compatible with existing `contracts-v0.1` plus additive `entry-v0.1` fields when executable-profile eligibility is explicitly requested.

No `contracts/**` path was modified by E2.

### 6. Local verification

Result: `NOT_RUN`

Reason: this GPT repository session has no Product Owner-approved local project execution environment. GitHub infrastructure is not an approved execution environment.

Required full local command from repository root, Windows PowerShell:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests -p "test_*.py" -v
```

Focused E2 strategy command:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/strategy -p "test_*.py" -v
```

New test definitions cover:

- deterministic canonical `entry-v0.1/MARKET` serialization;
- unsupported `LIMIT` rejection;
- unknown profile rejection;
- `entry-v0.1` missing `entry_order_type` rejection;
- legacy `entry_style` does not become executable automatically;
- advisory reference price remains advisory and does not produce executable price fields;
- provider-specific entry semantics rejection;
- quantity/risk authority rejection;
- existing Strategy Runtime same-input deterministic Signal behavior remains unchanged.

No executable PASS is claimed.

### 7. Known limitations

- `entry-v0.1` supports MARKET only;
- no LIMIT, stop/trigger entry, post-only, IOC/FOK, trailing entry, executable price, or TIF semantics;
- legacy baseline TradeIntent without a declared profile remains valid for historical/research/advisory use but is not execution-profile eligible;
- TradeIntent production consumes an actionable `LONG` or `SHORT` Signal only; `NO_TRADE` fails closed;
- this E2 revision does not validate E5 quantity profiles or E4 provider conversion semantics.

### 8. Dependencies / blockers

- executable verification remains `NOT_RUN` pending approved local execution;
- E5 must consume the explicit E2 `entry_profile_version` / `entry_order_type` fields and must not infer executable semantics from legacy fields;
- E4 provider translation remains downstream of an E5-approved plan and is outside E2 scope;
- E7 must integrate/review the producer-consumer profile boundary before any release-gate movement.

### 9. Required next action

**E7:** static-review this E2 revision against `contracts-v0.1`, `entry-v0.1`, and ADR-0002; require local test evidence before accepting executable behavior.

**E5:** consume only explicit supported E2 profile fields for executable promotion. Do not infer order type from `entry_style` and do not turn `entry_reference_price` into an executable price.

No next E2 feature is started automatically.

### 10. Security / secrets

Confirmed:

- no real API key, API secret, token, credential, password, private key, or live `.env` value was committed;
- fixtures use only synthetic BTC market values;
- TradeIntent explicitly rejects broker/provider credential and provider-specific authority fields;
- real secrets remain local-only and outside this producer boundary.

### 11. GitHub compute policy

Confirmed:

- no GitHub Actions workflow was created or used;
- no GitHub-hosted or GitHub-triggered runner was used;
- no unit/integration/E2E/backtest/project workload was executed on GitHub infrastructure;
- verification remains `NOT_RUN` with exact local commands above.

### 12. Live-trading impact

This change does not enable PAPER, SHADOW, Demo, or LIVE trading and does not authorize exposure.

It makes E2 candidate TradeIntent entry semantics explicit for downstream risk/execution construction. E5 retains risk veto/sizing authority, E4 retains broker translation/order authority, and E7/Product Owner release gates remain unchanged.

### 13. Codex bug ticket, if applicable

`NONE` — this is a bounded E2 feature task under an accepted shared object profile, not a reproduced implementation defect.
