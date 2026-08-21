# OKX Demo Adapter Construction Scope

This document records the Product Owner/PM construction boundary for the next E4 task after PR #11 static acceptance.

## Purpose

Construct a Demo-first OKX provider adapter on top of the merged broker-neutral execution, canonical entry translation, and deterministic sizing layers.

This is **source construction only**. It is not authorization to execute Demo orders from GitHub, not PAPER/SHADOW/LIVE promotion, and not real-money trading authorization.

## Allowed provider surface

The bounded adapter may implement code for:

- OKX REST authentication/signature construction;
- Demo request header enforcement (`x-simulated-trading: 1`);
- public/current instrument metadata retrieval for `BTC-USDT-SWAP`;
- private Demo account/configuration reads required to validate execution prerequisites;
- Demo order request materialization for the already-approved `entry-v0.1 / MARKET` path;
- provider `clOrdId` mapping with deterministic/idempotent traceability;
- order query, open-order/position/fill reads required for ambiguity reconciliation;
- fail-closed parsing/typing of provider responses.

## Hard safety boundary

The construction must not:

- contain or commit real credentials/secrets;
- execute project code or provider requests on GitHub infrastructure;
- call a production trading environment during verification;
- enable real-money order submission;
- expose withdrawal, funding transfer, deposit, sub-account capital movement, or asset-movement capability;
- silently mutate account mode, position mode, leverage, or margin configuration as a convenience;
- treat a successful HTTP acknowledgement as final order/fill truth;
- retry an ambiguous order submission before querying/reconciling provider state;
- increase provider exposure above the E5-approved canonical BTC bound.

## Configuration prerequisites

The adapter must validate rather than silently repair the configured trading prerequisites for the V1 target:

- provider = OKX;
- instrument = `BTC-USDT-SWAP`;
- trade mode = isolated;
- expected position mode must be explicit and consistent with request mapping;
- Demo requests must carry `x-simulated-trading: 1`;
- provider instrument metadata must be current enough for submit-time sizing.

Any required user/account configuration that cannot be proven safe is a fail-closed blocker.

## Metadata freshness hardening

Finding `E4-OKX-FRESHNESS-HARDEN-001` must be addressed before future Demo/private adapter acceptance.

The existing 300-second E4-local TTL is not a guarantee that provider instrument terms remain stable. Provider adapter construction should refresh/validate metadata at or immediately before request materialization/submission, and should account for provider scheduled instrument changes such as `upcChg` / `effTime` when exposed by current official OKX metadata.

## Official OKX authority

Implementation must recheck current OKX API V5 documentation at construction time. As of 2026-08-21, official documentation states:

- private REST requests require `OK-ACCESS-KEY`, `OK-ACCESS-SIGN`, `OK-ACCESS-TIMESTAMP`, and `OK-ACCESS-PASSPHRASE`;
- Demo Trading requests require `x-simulated-trading: 1`;
- account mode must first be set via Web/App;
- `POST /api/v5/trade/order` is the place-order endpoint;
- `POST /api/v5/account/set-position-mode` and `POST /api/v5/account/set-leverage` exist, but this construction scope does not authorize silently mutating them;
- Demo Trading does not support withdrawal/deposit and other asset-movement functions, which remain outside R7's Broker surface regardless.

## Verification policy

All executable verification remains local-only. Without a Product Owner-approved local environment, report `NOT_RUN` with exact commands. GitHub Actions, CI, hosted runners, and GitHub-triggered project compute are prohibited.
