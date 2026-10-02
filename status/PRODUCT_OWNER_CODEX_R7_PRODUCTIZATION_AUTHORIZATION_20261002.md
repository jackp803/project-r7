# Product Owner Authorization — Codex R7 Productization V0.1 — 2026-10-02

## Decision

The Product Owner explicitly authorizes Codex to act as the primary
implementation agent for the bounded R7 Productization V0.1 program defined in:

`docs/product/R7_AUTONOMOUS_STRATEGY_TO_CAPITAL_V0_1.md`

This is a scoped exception to the historical policy that limited Codex to
bounded bug fixing.

## Authorized implementation scope

Codex may implement, test locally, refactor and integrate the credential-free
product/application work required by phases P1-P6 and P8, including:

- application/orchestration layer;
- cloud-drive transport abstraction and synced-folder adapter;
- Strategy Package intake;
- durable local intake ledger;
- automated research orchestration;
- deterministic robustness / walk-forward / Monte Carlo framework;
- Registry lifecycle extensions through READY_FOR_APPROVAL;
- continuous PAPER orchestration;
- Control Center local UI/API;
- Windows packaging/startup/recovery;
- sanitized result publishing;
- product acceptance harness;
- bounded production-code corrections revealed by local tests when they preserve
  accepted architecture/contracts.

Codex may also implement the credential-free code/test surface for P7 LIVE-capable
integration, but may not activate provider/private/capital behavior.

## Architecture authority

This authorization does NOT transfer:

- product/architecture authority;
- shared-contract authority;
- E1-E7 domain authority;
- risk-policy authority;
- provider/account authority;
- LIVE/capital authority.

PM/E7 remain architecture/contract/release reviewers. Existing owner semantics
must be preserved:

```text
E1 = market truth
E2 = strategy semantics
E3 = backtest/validation
E4 = execution/provider translation
E5 = risk/position authority
E6 = persistence/registry/platform truth
E7 = integration/contracts/release
```

Codex should build application-level composition around these boundaries rather
than silently absorbing them into one monolith.

## Infrastructure authority

Authorized:

- local Windows project execution;
- local deterministic tests/backtests/Monte Carlo/PAPER simulations;
- local filesystem/synced-cloud-folder fixtures;
- local SQLite;
- code generation/build/packaging;
- Git commit/push/PR evidence.

Forbidden unless separately authorized:

- GitHub Actions;
- GitHub-hosted runners;
- GitHub-triggered compute;
- paid LLM/API calls from R7;
- real provider credentials;
- private provider calls;
- provider/account mutation;
- real order/protection submission;
- SHADOW/LIVE runtime activation;
- capital movement or exposure.

## Cloud-drive direction

GitHub is not the Strategy/Data bus.

R7 shall use the provider-neutral CloudArtifactTransport defined by the product
spec. V0.1 begins with a configurable synced local cloud-drive folder adapter.
No fixed vendor or user-specific filesystem path is hard-coded.

## Stop conditions

Codex should continue through the currently assigned phase until PASS or a
genuine blocker.

Codex must stop and return evidence if:

- a shared contract/architecture semantic must change;
- a domain owner meaning must be redefined;
- provider/private facts are required;
- credentials/capital are required;
- a required local capability is unavailable;
- a deterministic test reveals a non-bounded architectural defect.

## Real-money boundary

The Product Owner wants the final product to support the complete path through
investment execution and performance feedback.

This authorization permits building that capability, but does NOT authorize
real-money activation.

A later fresh Product Owner decision is required before provider-private
verification, real order submission, or capital exposure.
