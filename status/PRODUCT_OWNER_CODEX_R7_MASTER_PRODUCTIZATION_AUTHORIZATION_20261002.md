# Product Owner Authorization — Codex R7 Master Productization — 2026-10-02

## Authorization state

```text
authorization_id = PO-CODEX-R7-MASTER-PRODUCTIZATION-20261002
state = ACTIVE
scope = PRODUCT IMPLEMENTATION / CREDENTIAL-FREE THROUGH LIVE-CAPABLE CODE
continuous_milestone_execution = AUTHORIZED
real_provider_private_access = NOT_AUTHORIZED
real_order_submission = NOT_AUTHORIZED
capital_exposure = NOT_AUTHORIZED
```

This authorization supersedes the narrower
`PRODUCT_OWNER_CODEX_R7_PRODUCTIZATION_AUTHORIZATION_20261002.md` only with
respect to implementation sequencing.

The Product Owner explicitly wants Codex to complete the entire R7 product
implementation without requiring a new chat instruction between normal
milestones.

## Governing architecture

Codex must follow:

1. `docs/product/R7_AUTONOMOUS_STRATEGY_TO_CAPITAL_V0_1.md`
2. `docs/product/R7_MASTER_PRODUCT_ARCHITECTURE_V0_1.md`
3. `docs/product/R7_CODEX_MASTER_EXECUTION_PLAN_V0_1.md`
4. `docs/product/R7_PRODUCT_ACCEPTANCE_MATRIX_V0_1.md`
5. existing shared contracts and ADRs

When documents differ, the more specific later master product architecture and
execution plan govern productization, but they do not silently override shared
domain semantics.

## Continuous authority

Codex is authorized to implement and self-advance through:

```text
M1 Cloud Intake
M2 Automated Research
M3 Robustness
M4 Lifecycle Materialization
M5 Continuous PAPER
M6 Control API
M7 Control Center
M8 Windows Packaging
M9 LIVE-Capable Credential-Free Integration
M10 Cloud Result Feedback
M11 Full Product Acceptance
```

Codex does NOT need a new PM/PO wake message between milestones if the previous
milestone gate is PASS.

Codex may maintain one bounded long-lived productization branch and build later
milestones on earlier accepted local milestone checkpoints in that branch.

## Authorized writes

Within the productization branch Codex may modify/create:

- `src/application/**`;
- application-owned migrations/storage adapters;
- `ui/**`;
- `packaging/**`;
- `tests/application/**`;
- `tests/product/**`;
- `tests/acceptance/**`;
- product docs/evidence;
- existing E1-E6 implementation/tests when a deterministic defect or required
  bounded extension is necessary to realize the already-accepted architecture;
- E6 lifecycle implementation necessary to materialize lifecycle states/edges
  already defined in `contracts-v0.1`;
- dependency/build configuration necessary for free/open-source product
  dependencies.

Shared contract meaning remains outside Codex authority.

## Local execution authority

Authorized on Product-Owner-approved local Windows infrastructure:

- unit/regression tests;
- backtests;
- dataset fixture processing;
- parameter robustness;
- walk-forward;
- Monte Carlo;
- PAPER simulation;
- fake-provider LIVE simulation;
- frontend build;
- backend startup;
- browser/UI local smoke;
- Windows packaging/build;
- product acceptance harness;
- local filesystem/cloud-synced-folder fixture testing.

This authorization does not make GitHub a compute platform.

## Cost constraint

R7 product runtime must not require a paid AI/LLM API.

Codex may use open-source/free dependencies.

Do not introduce a required paid SaaS/backend simply to complete productization.

## Provider/capital boundary

Codex is authorized to COMPLETE the code for provider/LIVE integration and to
exercise it against fake/synthetic/local deterministic providers.

Codex is not authorized to:

- request real API keys/passphrases;
- read existing real credentials;
- make real private provider requests;
- submit/cancel/amend/close real provider orders;
- change real provider account configuration;
- start a real SHADOW/LIVE capital-bearing runtime;
- move funds;
- expose capital.

If M9 implementation is complete and only real provider verification remains,
continue to M10/M11 credential-free work. Do not stop the overall product build
merely because real provider activation is not authorized.

## Architecture authority

Codex does not become the architecture owner.

Stop only if implementation requires a semantic decision not already resolved
by the governing architecture/contracts.

Do not stop for ordinary engineering decisions such as filenames, internal
class decomposition, UI component layout, dependency wiring, build tooling or
bounded implementation refactoring.

## Defect authority

Codex may directly fix deterministic defects found during this program when the
fix:

- preserves accepted contracts;
- preserves owner boundaries;
- does not weaken fail-closed behavior;
- is covered by regression;
- is locally verified.

This includes defects in existing code exposed by product composition.

## Dependency authority

Codex may add free/open-source dependencies needed for:

- FastAPI/local HTTP API;
- frontend/build;
- charting;
- Parquet/data serialization;
- Windows packaging;
- test automation.

Prefer minimal dependencies and pin/reproduce them appropriately.

A dependency requiring user billing, cloud subscription, secret account setup or
commercial license is not authorized.

## Final authority boundary

A completed implementation may be classified:

```text
PRODUCT_IMPLEMENTATION_COMPLETE
LIVE_CAPABLE_CREDENTIAL_FREE
```

It may not be classified:

```text
REAL_PROVIDER_VERIFIED
REAL_MONEY_ACTIVATED
PROFIT_GUARANTEED
```

without separate later evidence/authority.

## Stop / callback

Return to PM before final branch merge, or earlier only for a genuine master-plan
stop condition.

If blocked, report:

```text
MASTER_RESULT = BLOCKED
milestone
exact revision
blocker class
why architecture/local capability/external authority is genuinely required
completed milestones
remaining milestones
```
