# E7 Current Task

- task_id: `E7-20260825-068`
- issued_at: `2026-08-25T13:55:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-c-shadow-composition-20260825`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, Gate C baseline PR #75 merge `c158c8ca4fd01fa9314dd2e7a1a9c0c0d2935624`, accepted E1 PR #76 merge `61ea28f8b6d3ea6cd54e0abb84299303d490a63d`, accepted E6 PR #77 merge `64eb6f6689cb6f3e2d067af029df36ac58f4a321`, accepted E4 PR #78 merge `562c4c324129557e5d565b1a37deb49d2c007429`, accepted E4 balance handoff PR #79 merge `9de9a7f457f4c3d577229b9a667e8d14cc2226ee`, accepted E5 PR #80 merge `fda1d8805c8807ea66196b11fcccc24c55ced239`, Product Owner Gate C / SHADOW-only authorization

## Objective

Execute only Gate C Phase 3 from `status/e7/GATE_C_READINESS_BASELINE_20260825.md`: materialize the cross-module **Shadow composition boundary plus integration/E2E/safety test definitions** now that E1/E4/E5/E6 dependencies are accepted.

This task is credential-free and must not start a real SHADOW provider session. It must prove by architecture/test definition that the Shadow runtime can observe and reason about production-read-only provider state while provider mutation/order submission remains structurally unreachable.

## Composition requirements

Build the smallest E7-owned cross-cutting composition/glue necessary to define and test this path using accepted owner surfaces without reimplementing domain semantics:

```text
E1 current OKX public MarketSnapshot + finalized Candle
-> unchanged E2 Strategy Runtime
-> E5 Gate C RiskContext derivation / existing risk evaluation
-> hypothetical/no-submit Shadow planning boundary only
-> E6 OperationalMode.SHADOW sanitized checkpoint/audit/restart
```

Requirements:

1. Reuse E1 current-market/finalized-candle implementation unchanged.
2. Reuse E2 StrategyDefinition/runtime semantics unchanged; no private Shadow strategy fork.
3. Reuse E5 `derive_gate_c_risk_context(...)` and existing risk-policy evaluation unchanged.
4. Consume E4 `OKXShadowProviderReader`/`OKXShadowReadResult` only through its accepted read-only capability surface. A submit-capable Demo/live broker object must not be injected into or reachable from the Shadow composition graph.
5. Reuse E6 authoritative `OperationalMode`/SHADOW checkpoint store. SHADOW mode/checkpoint evidence must remain distinct from PAPER and must never become LIVE authority.
6. Synthetic credential objects may be used only as fake-test inputs to prove capability shape/redaction. Credential presence must not activate a submit branch.
7. No E7 code may parse provider payloads, implement auth/signing, define risk caps, redefine MarketSnapshot/RiskContext/OperationalMode, or duplicate domain logic.
8. If a shared contract is genuinely insufficient, stop `BLOCKED` with exact evidence before inventing a parallel shared type.

## Mandatory integration/safety proofs

Add E7-owned definitions proving at minimum:

- authoritative persisted mode must be `SHADOW` before Shadow planning/evaluation can be considered ready;
- restart of SHADOW requires the E6 fresh-reconciliation rule before planning can become safe again;
- healthy E1 + healthy E4 + safe E5 state can flow through unchanged E2/E5 semantics and produce a hypothetical/auditable Shadow decision without any provider mutation;
- stale/future/non-healthy E1 market truth fails closed;
- E4 auth/permission/clock/domain/account/position/order/fill degradation fails closed through E5 and cannot become new-exposure permission;
- E4 same-batch runtime balance may be consumed in memory but never enters E6 durable/public Shadow checkpoint material;
- Paper evidence cannot satisfy Shadow provider truth/checkpoint requirements;
- Shadow evidence cannot authorize LIVE or instantiate a LIVE execution path;
- no submit/place/cancel/amend/close/leverage/mode/transfer/deposit/withdraw/generic authenticated request capability is reachable from the Shadow composition object graph;
- attempts to miswire a submit-capable E4 adapter/broker into Shadow are rejected structurally or at composition validation before any transport call;
- fake transport audit for a healthy Shadow observation contains only the accepted public time read plus exact private GET allowlist and zero mutation methods/requests;
- synthetic valid credentials do not alter the reachable capability graph;
- exceptions/loggable integration evidence redact credential material, exact runtime balance, raw UID/main UID/API label/bound IP, provider order/fill IDs and full raw responses;
- missing/corrupt/contradictory E6 state/checkpoint fails closed;
- SHADOW -> LIVE is never automatic or inferred.

## Test locations

Use only E7-owned cross-module test paths as appropriate:

- `tests/integration/**`
- `tests/e2e/**`
- cross-module `tests/safety/**`

You may add narrowly scoped E7-owned composition code under an already accepted cross-cutting location (for example `src/domain/**` or a clearly integration-owned module) only if needed. Do not modify E1-E6 production behavior to make integration tests pass; return any domain defect to its owner instead.

## Executable verification

Product Owner authorizes approved-local, non-GitHub, **credential-free fake/sanitized** verification for this task. If the approved local runner is available, run only relevant E7 integration/E2E/safety suites, for example:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/e2e -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

No real provider/private network request, real credential, SHADOW runtime start, order submission, provider mutation, LIVE, or capital exposure is authorized. If approved-local execution is unavailable, record `NOT_RUN` with exact commands. `NOT_RUN != PASS`.

This task is **not** the final Gate C executable qualification. A separate exact-revision full credential-free Gate C matrix will be issued after PM reviews and merges these definitions.

## Writable scope

Only E7-owned integration/architecture/test/status paths needed for this task:

- `tests/integration/**`;
- `tests/e2e/**`;
- E7-owned cross-module `tests/safety/**`;
- narrowly required E7-owned composition/glue under shared/integration locations allowed by the E7 role contract;
- `docs/architecture/**` if needed;
- `status/e7/**`;
- `status/INTEGRATION_STATUS.md` and `status/RELEASE_GATES.md` only for non-promotional work-in-progress reconciliation;
- `coordination/E7/STATUS.md`.

Forbidden:

- E1-E6 production/test modifications;
- strategy logic changes;
- risk-policy/cap changes;
- provider auth/signing/payload parsing implementation;
- storage/migration changes owned by E6;
- shared contract/ADR changes unless the task stops for explicit architecture escalation;
- real credentials/secrets/tokens/cookies/browser-auth material;
- real provider/private requests;
- provider mutation/order submission/cancel/amend;
- PAPER/SHADOW runtime start;
- Gate D/LIVE/capital exposure;
- GitHub Actions/CI/hosted/GitHub-triggered compute;
- unrelated cleanup.

## Acceptance

### DONE

- cross-module Shadow composition/test definitions cover the mandatory no-submit, fail-closed, mode/restart, redaction and separation proofs;
- accepted E1/E2/E4/E5/E6 semantics are reused rather than reimplemented;
- no submit-capable dependency is reachable in the valid Shadow graph;
- no domain production behavior or shared contract/ADR was changed;
- local evidence is PASS or explicitly `NOT_RUN` without misclassification;
- required status/evidence is committed and pushed to the target branch;
- Gate C/SHADOW_READY is **not** claimed PASS by worker completion alone.

### BLOCKED

Stop with exact evidence if integration proves a domain defect or shared-contract gap. Do not silently repair another owner or broaden scope.

## Completion

Execute only this TASK, update `coordination/E7/STATUS.md`, commit/push required work to the target branch, and stop. Do not self-start the full Gate C qualification, credential-dependent provider verification, SHADOW runtime, Gate D or LIVE work.
