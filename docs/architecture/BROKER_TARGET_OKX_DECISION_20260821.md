# Product / Architecture Decision — OKX as V1 Broker Target

> Decision date: 2026-08-21
> Decision authority: Product Owner
> Repository: `jackp803/project-r7`
> Status: `ACTIVE PRODUCT BASELINE`
> Scope: V1 exchange/broker target and migration constraints

## 1. Decision

Project R7 will no longer target Pionex for new V1 market-data or private execution development.

The V1 broker/exchange target is:

```text
Exchange: OKX
Operational account boundary: dedicated OKX sub-account for R7
Canonical research instrument: BTC_USDT_PERP
OKX instrument adapter target: BTC-USDT-SWAP
Margin intent: isolated
```

The system must remain broker-neutral above the adapter boundary. This is a target migration, not permission to hard-code OKX semantics into Strategy, Backtest, Risk, Registry, or shared objects that do not require broker-specific facts.

## 2. Immediate effect

Effective immediately:

- no new Pionex-specific implementation is authorized;
- no Pionex private API, credentials, signatures, account calls, or real-order path may be added;
- existing reviewed Pionex public-market code is historical/migration evidence only until the OKX replacement is statically reviewed and later locally verified;
- do not delete old reviewed code merely to make the repository look migrated;
- PaperBroker remains the exchange-independent execution baseline;
- OKX Demo Trading is the intended exchange-simulation stage after the relevant contracts/adapters are statically coherent and local verification becomes available;
- real OKX private execution remains NOT AUTHORIZED in the current construction state.

## 3. Account isolation and API security baseline

Future real execution, if separately approved after release gates, must use a dedicated OKX sub-account for R7 rather than the Product Owner's general-purpose trading account.

Future API-key policy:

- minimum permissions required for the approved runtime;
- Read permitted when required;
- Trade permitted only for the bounded execution adapter when the appropriate release gate is met;
- Withdraw permission forbidden;
- trusted-IP restriction required where operationally feasible;
- API key, secret, passphrase, credentials, and live `.env` values never enter Git;
- R7 will not expose funding transfer, withdrawal, or sub-account capital-movement operations as an executable broker capability even if the exchange API technically offers them.

OKX account mode is a manually configured external prerequisite and must be verified/fail-closed by future runtime code; R7 must not assume that credentials imply the account is correctly configured.

## 4. Canonical symbol and data boundary

Shared/canonical research identity remains broker-neutral:

```text
BTC_USDT_PERP
```

The OKX adapter maps that canonical identity to:

```text
BTC-USDT-SWAP
```

E1 should preserve `contracts-v0.1` Candle semantics unless E7 identifies a real contract mismatch. Provider-specific details belong in the E1 adapter.

Target public historical timeframes remain:

```text
1m
15m
1h
4h
```

The OKX adapter must normalize provider bar labels/timestamps/finality into the existing canonical UTC, half-open, closed-candle semantics and must surface malformed/missing/out-of-order data rather than manufacture candles.

## 5. Derivatives sizing boundary

OKX derivative order size is exchange-instrument-specific. Future E4/E5 integration must not assume that canonical risk quantity is numerically identical to an OKX `sz` value.

Before any OKX private or Demo order translation is considered integration-ready, E7/E4/E5 must define and test the boundary for provider instrument metadata including, as applicable:

- contract value (`ctVal`);
- contract type (`ctType`);
- lot size (`lotSz`);
- minimum size (`minSz`);
- price tick (`tickSz`);
- instrument state/tradability.

Safety rule:

> Exchange quantization may round down or reject. It must never round up into exposure greater than the E5-approved bound.

Unknown/stale/incompatible instrument metadata fails closed for new exposure.

## 6. Execution path target

Intended staged path:

```text
Backtest
  -> internal PaperBroker
  -> OKX Demo Trading adapter
  -> dedicated OKX sub-account (real execution only after explicit release approval)
```

No stage may be inferred as approved merely because source code exists or an API credential is available.

## 7. Agent impact

### E1 — Market Data

Replace the V1 provider target with OKX public market data while preserving canonical Candle semantics. Do not add private account/execution logic.

### E2 — Strategy

No broker-specific rewrite. StrategyDefinition/Signal/TradeIntent semantics remain exchange-neutral.

### E3 — Backtest / Validation

No strategy-logic rewrite. Dataset/source reproducibility metadata may identify OKX-derived datasets after migration. Existing replay semantics remain unchanged unless a concrete provider-independent defect is found.

### E4 — Execution

Keep Broker/PaperBroker broker-neutral. Do not build PionexBroker. Future exchange adapter target is OkxBroker/OKX Demo first, but private implementation is not authorized until E7 resolves shared entry semantics and OKX sizing/account-mode boundaries.

### E5 — Risk / Position

Preserve risk authority. Future approved plan-to-exchange sizing must remain inside approved exposure bounds; E5 does not become an exchange API client.

### E6 — Platform / Registry

Persist broker/source/audit identity when that execution slice exists, without reinterpreting exchange semantics or inferring approval.

### E7 — Integration / Contracts

Keep shared contracts exchange-neutral where possible. Review OKX-specific adapter boundaries, entry-instruction semantics, sizing/quantization semantics, operational account assumptions, and local integration evidence before any Paper/Demo/Live gate advancement.

## 8. Release-gate effect

This decision does not advance a release gate.

```text
Gate A RESEARCH_READY   BLOCKED
Gate B PAPER_READY      BLOCKED
Gate C SHADOW_READY     BLOCKED
Gate D LIVE_READY       BLOCKED
```

Existing executable evidence remains `NOT_RUN` where not run locally.

## 9. GitHub compute policy

No GitHub Actions, GitHub CI, hosted runner, GitHub-triggered runner, or scheduled GitHub project execution may be used for migration verification. Source/test definitions may be committed; executable evidence must come from an approved local/non-GitHub environment or remain `NOT_RUN` with exact commands.

## 10. External references used for this decision

Official OKX references current at decision time:

- Subaccounts / account mode / API FAQ: https://www.okx.com/zh-hant/help/subaccounts-account-mode-and-api-connections-faq
- OKX API V5 documentation: https://www.okx.com/docs-v5/en/

Provider behavior must be reverified from official OKX documentation before private/Demo implementation because exchange APIs and product availability can change.
