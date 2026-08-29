# Mature OKX Failure-Prevention Gap Audit — E7-20260829-098

## Scope and authority

- task_id: `E7-20260829-098`
- task type: `DOCS / STATUS ONLY STATIC CROSS-MODULE GAP AUDIT`
- baseline: `status/PM_MATURE_OKX_BOT_FAILURE_PREVENTION_BASELINE_20260829.md`
- audited failure classes: `FP-01` through `FP-16`
- executable baseline materially supporting current implementation: `8fbf5fcae2eaf44accdf535121d8abf29ef5c93c`
- accepted credential-free evidence: `status/e7/SHADOW_TEMPORAL_ORDERING_CREDENTIAL_FREE_REQUALIFICATION_20260827.md`
- accepted Gate B evidence: `status/e7/GATE_B_POST_REMEDIATION_QUALIFICATION_20260825.md`
- historical provider-facing evidence: `status/e7/GATE_C_COMPLETE_SANITIZED_READONLY_EVIDENCE_20260826.md`, bound only to `ab725965e96cac7a9769fd1ab15a3e626f920b95`

This audit is intentionally conservative. Role contracts, design intent, test-file presence, and historical aggregate PASS counts are not by themselves classified as implementation. `IMPLEMENTED_AND_LOCALLY_VERIFIED` is used only where concrete current implementation exists and accepted local executable evidence materially exercises the exact invariant. `NOT_RUN != PASS`.

A repository comparison from `8fbf5fcae2eaf44accdf535121d8abf29ef5c93c` to the `main` audited by E7-098 found only coordination/status-document changes; no executable source/test/contract/ADR drift was present after the E7-095 qualified executable baseline. Therefore the E7-095 local matrix remains applicable to the unchanged executable implementation inspected here. This statement does not rebind historical provider evidence from `ab725965...` to `8fbf5fca...`.

## Verification boundary

```text
E7-098 executable verification = NOT_RUN / NOT REQUIRED FOR DOCS-ONLY STATIC GAP AUDIT
project code execution          = NOT_RUN
provider requests               = 0
credentials                     = NOT READ / NOT REQUESTED / NOT USED
mutation requests               = 0
submit requests                 = 0
SHADOW runtime                  = NOT STARTED
PAPER runtime                   = NOT STARTED
capital exposure                = NONE
GitHub compute                  = NOT USED
```

Accepted prior local evidence used by this static audit:

- E7-095: exact clean Windows/non-GitHub revision `8fbf5fca...`, `14/14` suites PASS, `589` tests (`execution=52`, `brokers=135`, `risk=24`, `position=97`, `storage=88`, `platform=3`, `integration=28`, `e2e=5`, `safety=58`, plus research suites).
- E7-064: Gate B approved-local Windows/non-GitHub matrix, `10/10` suites PASS, `450` tests on `d5ddb4ce...`.
- E7-083: historical OKX production read-only one-shot on `ab725965...`, healthy provider clock (`723 ms` skew), read-only account facts, no exposure/pending/unreconciled fill, `7` GETs, zero mutation/submit. This evidence is historical/provider-facing only and is never treated as provider verification of `8fbf5fca...`.

## Executive summary

| Classification | Count |
|---|---:|
| IMPLEMENTED_AND_LOCALLY_VERIFIED | 4 |
| IMPLEMENTED_NOT_LOCALLY_VERIFIED | 0 |
| PARTIAL | 10 |
| MISSING | 2 |
| NOT_APPLICABLE_TO_SWAP | 0 |
| **Total** | **16** |

The strongest existing controls are operational-mode persistence/restart reconciliation (`FP-01`), clock-skew fail-closed handling (`FP-08`), ACK-vs-fill truth separation (`FP-12`), and stale execution/Position evidence invalidation (`FP-13`).

The two core controls not presently implemented are protection-trigger geometry/breached-trigger handling (`FP-03`) and staged breakeven/trailing/profit-protection action maturity (`FP-15`).

The most important partial gaps before any future provider runtime are the complete SWAP action-role capability matrix (`FP-02`), external/manual provider reconciliation policy (`FP-04`), provider-native close/residual sizing (`FP-05`), unique active-protection registry (`FP-11`), and exact runtime process/heartbeat identity preflight (`FP-16`).

No FP row is wholly `NOT_APPLICABLE_TO_SWAP`: literal Spot mechanisms are rejected where appropriate, but each incident lesson has a corresponding SWAP invariant that still requires an explicit classification.

## Full FP matrix

| FP | Failure class | Spot lesson -> SWAP invariant | Classification | Primary owner(s) | Priority | Residual gap in one line |
|---|---|---|---|---|---|---|
| FP-01 | Runtime mode drift / restart | Do not restart into an assumed mode -> restore authoritative `OperationalMode`, then require fresh reconciliation | IMPLEMENTED_AND_LOCALLY_VERIFIED | E6 / E7 | COVERED | External launchers still must obey the persisted mode; that process-control edge is tracked by FP-09/FP-16 |
| FP-02 | Instrument/account/margin/position-mode parameter mismatch | Do not transplant Spot `cash`; enforce a per-action SWAP capability matrix | PARTIAL | E4 / E7 | P0_PRE_PROVIDER_RUNTIME | Entry and read-only paths are constrained, but protection/close provider translation is not covered by one complete capability matrix |
| FP-03 | Protection trigger already breached before create/replace | Validate trigger geometry against fresh market truth immediately before protection mutation | MISSING | E5 / E4 / E7 | P0_PRE_PROVIDER_RUNTIME | Current protection authority validates positive stop values and Position truth, but does not consume fresh market price or reject an already-breached trigger |
| FP-04 | Manual/external provider activity | Reconcile provider truth before automation; adopt/reject/manual-review rather than assume ownership | PARTIAL | E4 / E5 / E6 / E7 | P0_PRE_PROVIDER_RUNTIME | Read-only Shadow detects exposure/orders/fills and ambiguous submit is reconciled, but there is no complete external/manual ownership policy/registry convergence path |
| FP-05 | Lot/minimum/reducible residual quantity | Use live SWAP metadata and actual reducible exposure; never loop on an unrepresentable residual | PARTIAL | E4 / E5 | P0_PRE_PROVIDER_RUNTIME | Entry sizing is strong and close uses exact canonical Position quantity, but provider-native close/residual quantization/minimum handling is not implemented |
| FP-06 | Misleading current-state reporting | Every current-state claim needs provenance, source time, freshness, and last-known-good distinction | PARTIAL | E6 / E7 | P1_PRE_PAPER_OR_SHADOW | Durable objects are hashed/timestamped and recovery is explicit, but there is no mature current-state/dashboard projection with uniform source/freshness/last-known-good semantics |
| FP-07 | Desync lock conflated with financial kill switch | Operational reconciliation lock and financial risk kill switch must be separate state planes with distinct provenance | PARTIAL | E5 / E6 / E7 | P1_PRE_PAPER_OR_SHADOW | `LOCKED/PAUSED` OperationalMode and `kill_switch_active` risk input are distinct, but the financial kill switch is not yet a durable independently governed state object |
| FP-08 | Provider/local clock skew | Clock skew must be preflighted and unsafe skew must fail closed | IMPLEMENTED_AND_LOCALLY_VERIFIED | E4 / E5 / E7 | COVERED | No current control gap; provider-facing re-verification on the remediated revision remains a separate governance question, not an implementation gap |
| FP-09 | State-unaware watchdog / restart | Restart policy must depend on durable mode and current reconciled position/protection state | PARTIAL | E6 / E7 / external operator | P1_PRE_PAPER_OR_SHADOW | Project recovery is state-aware and fail-closed, but the external watchdog/process restart policy is not proven to branch on that full state before relaunch |
| FP-10 | Fill/aggregate-close/manual-flat lifecycle errors | ACK/order status is not closure; require fill sets plus authoritative flat Position truth and reconciliation events | PARTIAL | E4 / E5 / E6 | P0_PRE_PROVIDER_RUNTIME | Paper/durable lifecycle and `RECONCILED_FLAT` semantics are strong, but external/manual provider-close adoption into the same authoritative lifecycle is not end-to-end implemented |
| FP-11 | Duplicate/orphan protection orders | Exactly one intended active protection lineage per Position; reconcile extras explicitly | PARTIAL | E4 / E5 / E6 / E7 | P0_PRE_PROVIDER_RUNTIME | Deterministic PositionAction/OrderRequest lineage and durable execution bindings exist, but no provider-facing unique active-protection registry/multiplicity reconciliation exists |
| FP-12 | Pending/ACK incorrectly mutates position truth | Pending ACK remains pending; only fills/authoritative Position observations change exposure truth | IMPLEMENTED_AND_LOCALLY_VERIFIED | E4 / E5 / E6 | COVERED | No material current gap identified in the audited V0.1 boundary |
| FP-13 | Stale pre-reconcile snapshot reused after truth changes | Any newer Position/order/fill truth invalidates older authority/evidence until reinterpreted | IMPLEMENTED_AND_LOCALLY_VERIFIED | E5 / E6 / E7 | COVERED | No material current interface/restart freshness gap identified; future provider orchestration must continue passing exact current observations |
| FP-14 | Tight retry loop on stable non-actionable state | Represent stable waiting/reconciliation states and retry only on new evidence or bounded backoff | PARTIAL | E4 / E5 / E6 | P2_PRE_LIVE | Ambiguous entry is stable `RECONCILIATION_REQUIRED` with retry disabled, but unrepresentable/reducible residual and protection replacement waiting states are not fully modeled |
| FP-15 | Premature/fragile profit protection | Breakeven/trailing must be explicit policy actions with verification, bounded replacement, and audit trail | MISSING | E5 / E4 / E6 / E7 | P2_PRE_LIVE | Lifecycle vocabulary includes `PROFIT_PROTECTED`, but no implemented breakeven/trailing/modify-protection authority and provider replacement state machine was found |
| FP-16 | Wrong process/revision/mode considered healthy | Runtime preflight must bind process identity, exact revision, mode, config, and heartbeat before provider work | PARTIAL | E7 / external operator / E6 | P0_PRE_PROVIDER_RUNTIME | Exact revision/clean-worktree and OperationalMode controls exist, but no complete accepted process-identity + heartbeat/scheduler preflight contract is present |

## Detailed FP evidence and follow-up boundaries

### FP-01 — Runtime mode drift / restart

- **Failure class:** stale/default runtime mode after restart.
- **SWAP invariant:** provider-capable runtime must restore authoritative `OperationalMode`; restart cannot infer SHADOW/PAPER/LIVE and must perform fresh reconciliation before planning.
- **Implementation:** `src/storage/operational_mode.py` (`OperationalModeStore`, `OperationalModeRecovery`, append-only mode transitions, integrity/hash validation, `fresh_reconciliation_required`, `shadow_planning_safe`).
- **Contracts/architecture:** E6 OperationalMode authority under `agents/E6_PLATFORM.md`; Gate C composition in `src/integration/shadow_composition.py` requires authoritative SHADOW.
- **Tests:** `tests/storage/test_operational_mode_shadow.py`; `tests/integration/test_gate_c_shadow_composition.py`; `tests/safety/test_gate_c_shadow_composition_safety.py`.
- **Accepted local evidence:** E7-095 storage/integration/safety suites in the 589-test exact-revision PASS; historical Gate C restart definitions and E7-083 provider facts do not alter the revision binding.
- **Classification:** `IMPLEMENTED_AND_LOCALLY_VERIFIED`.
- **Residual gap:** project state restoration is covered; external process/watchdog launch compliance belongs to FP-09/FP-16.
- **Owner:** E6 / E7; external launcher compliance by operator.
- **Smallest safe follow-up:** no reimplementation; reuse current OperationalMode recovery as mandatory input to any future runtime supervisor preflight.
- **Executable-source change:** `NO` for FP-01 itself.
- **New credential-free requalification:** `NO` unless future code changes this boundary.
- **Provider/private access:** `NO`.
- **Credentials:** `NO`.
- **Product Owner authority:** `NO` for static/preflight reuse; provider runtime remains separately authorized.
- **Capital exposure:** `NO`.

### FP-02 — SWAP action-role capability matrix

- **Failure class:** invalid provider parameters caused by account/instrument/margin/position-mode assumptions.
- **Spot lesson vs SWAP invariant:** Spot `tdMode=cash` is not reusable. SWAP must explicitly define allowed fields and combinations by action role: entry, protection, close/emergency close, read-only reconciliation.
- **Implementation:** `src/brokers/okx_demo.py` (`OKXDemoAdapterConfig`, acctLv=2 Futures-mode matrix, net/long-short mapping, `tdMode=isolated`, fixed BTC-USDT-SWAP); `src/brokers/okx_shadow.py` (`OKXShadowReaderConfig`, fixed read-only GET set); `src/brokers/okx_sizing.py` (linear SWAP metadata validation).
- **Tests:** `tests/brokers/test_okx_demo_adapter.py`, `test_okx_sizing.py`, `test_okx_shadow.py`, `test_okx_submit_integrity.py`.
- **Accepted local evidence:** E7-095 `brokers=135`, `execution=52`; E7-083 confirms historical real account level 2 / net mode / isolated leverage on the historical provider-evidence revision.
- **Classification:** `PARTIAL`.
- **Residual gap:** no single provider capability matrix proves how `PROTECTION_STOP`, `POSITION_EXIT`, and `EMERGENCY_EXIT` translate under each supported position mode; generic `reduce_only` shared requests are not equivalent to proven OKX provider parameters.
- **Owner:** E4 primary; E7 for cross-module/provider capability contract review.
- **Smallest safe follow-up:** define a versioned E4 OKX SWAP action-role capability table and fixture tests for entry/protection/close across `net_mode` and any retained `long_short_mode`, rejecting every unsupported field/combination.
- **Executable-source change:** `YES` if provider translation is added/hardened; documentation/test plan alone is insufficient for completion.
- **New credential-free requalification:** `YES` after executable E4 changes.
- **Provider/private access:** `NO` for deterministic implementation/tests; `YES` only for a later separately authorized provider-facing verification.
- **Credentials:** `NO` for implementation/tests; later provider verification would require approved secure credentials.
- **Product Owner authority:** `NO` for code/tests; `YES` for any provider/private validation session.
- **Capital exposure:** `NO`.

### FP-03 — Protection trigger geometry / already-breached stop

- **Failure class:** submitting/replacing protection after price has already crossed the intended trigger.
- **SWAP invariant:** immediately before protection mutation, compare intended trigger geometry against a fresh canonical market observation and fail closed when already breached/contradictory; re-enter reconciliation/policy rather than repeatedly resubmit the same invalid trigger.
- **Implementation inspected:** `src/position/protection.py` validates plan/Position lineage and positive stop values; `src/execution/protection.py` translates the stop into `STOP_MARKET`, `reduce_only=true`.
- **Tests:** protection action/consumer/result/failure tests exist, but no audited test supplies fresh market price to validate long/short stop trigger geometry before create/replace.
- **Accepted local evidence:** E7-095 verifies the existing protection code, not the missing market-geometry control.
- **Classification:** `MISSING`.
- **Residual gap:** neither E5 protection authority nor E4 protection translation accepts a current market snapshot/trigger-reference required to reject an already-breached stop; no stable `TRIGGER_ALREADY_BREACHED`-type policy is defined.
- **Owner:** E5 owns policy/authority; E4 owns provider translation; E7 owns any shared temporal/market-proof contract.
- **Smallest safe follow-up:** define a bounded protection-trigger validity contract using fresh `MarketSnapshot` + Position side + stop level, implement fail-closed E5/E4 consumer checks, and add long/short breached-boundary tests without provider calls.
- **Executable-source change:** `YES`.
- **New credential-free requalification:** `YES`.
- **Provider/private access:** `NO` for implementation and deterministic verification.
- **Credentials:** `NO`.
- **Product Owner authority:** `NO` for code/tests; future provider mutation remains separately authorized.
- **Capital exposure:** `NO`.

### FP-04 — External/manual provider order/fill/position reconciliation

- **Failure class:** automation assumes every provider object was created by itself.
- **SWAP invariant:** current provider truth wins; unknown/manual/external exposure, pending orders, or fills must be reconciled to explicit adopt/reject/manual-review/lock policy before new exposure or protection mutation.
- **Implementation:** `src/brokers/okx_shadow.py` observes positions/pending/fills and fails health on unexpected activity; `src/brokers/okx_demo.py` blocks new exposure on existing position/pending orders and reconciles ambiguous submit before retry; E5 Gate C context fails closed on unknown/unexpected activity; E6 SHADOW checkpoint requires zero pending/unreconciled activity.
- **Tests:** `tests/brokers/test_okx_shadow.py`, `test_okx_demo_adapter.py`, `tests/risk/test_gate_c_context_derivation.py`, Gate C integration/safety tests.
- **Accepted local evidence:** E7-095 local matrix; E7-083 historical real provider observation established zero pending and zero unreconciled fill activity.
- **Classification:** `PARTIAL`.
- **Residual gap:** detection/blocking exists, but no complete durable policy identifies externally created order/protection ownership, adoption/rejection outcome, or convergence after manual intervention.
- **Owner:** E4 provider truth/identity; E5 lifecycle/risk interpretation; E6 durable reconciliation/audit; E7 contract/integration.
- **Smallest safe follow-up:** define a sanitized `provider-origin/ownership reconciliation` profile for unknown orders/fills/positions and a deterministic locked/manual-review result; implement first in credential-free fixtures before any provider test.
- **Executable-source change:** `YES`.
- **New credential-free requalification:** `YES`.
- **Provider/private access:** `NO` for implementation/tests; `YES` for later real-provider evidence.
- **Credentials:** `NO` initially; later provider verification requires secure credentials.
- **Product Owner authority:** `NO` for code/tests; `YES` for provider/private verification.
- **Capital exposure:** `NO`.

### FP-05 — Lot/minimum/reducible residual quantity

- **Failure class:** rounding/minimum-size/provider quantity rules create rejected orders or an infinite retry on an uncloseable residual.
- **SWAP invariant:** entry and reduction use current SWAP instrument metadata and authoritative reducible Position truth; rounding may never increase exposure; unrepresentable residuals become a stable reconciled/waiting state, not an immediate loop.
- **Implementation:** `src/brokers/okx_sizing.py` handles `ctVal`, `ctMult`, `lotSz`, `minSz`, `maxMktSz`, state/freshness and floors entry exposure; `src/position/close.py` + `src/execution/close.py` require exact current canonical Position quantity and reduce-only close authority.
- **Tests:** `tests/brokers/test_okx_sizing.py`; `tests/execution/test_close.py`; close/position safety tests.
- **Accepted local evidence:** E7-095 brokers/execution/position/safety PASS; Gate B E7-064 also covered close/position paths.
- **Classification:** `PARTIAL`.
- **Residual gap:** current provider sizing implementation is entry-specific. No provider-native close/protection sizing function proves representability of actual residual exposure or defines a stable state when the reducible residual is below provider minimum/lot constraints.
- **Owner:** E4 primary; E5 for residual lifecycle policy.
- **Smallest safe follow-up:** add provider-neutral-to-OKX reduction sizing using current Position actual quantity + fresh metadata, with `<= actual exposure`, no round-up, residual classification, and no retry without changed evidence.
- **Executable-source change:** `YES`.
- **New credential-free requalification:** `YES`.
- **Provider/private access:** `NO` for fixture/local implementation; public metadata verification may be separately bounded later.
- **Credentials:** `NO` for initial work.
- **Product Owner authority:** `NO` for code/tests.
- **Capital exposure:** `NO`.

### FP-06 — Current-state reporting provenance/freshness

- **Failure class:** dashboard/status says “current” using stale or mixed-origin data.
- **SWAP invariant:** each current-state projection identifies source object, source observation time, persistence/recovery status, and freshness/unknown classification; last-known-good must not be presented as current truth.
- **Implementation:** canonical storage objects include payload hashes; `PaperRuntimeRecovery` exposes exact current projection/history/evidence; `OperationalModeRecovery` exposes mode/checkpoint/reconciliation status; lifecycle projections bind source Position observation; E7 release evidence distinguishes historical provider revision from current credential-free revision.
- **Tests:** storage durability/conflict/time-ordering/freshness tests; `tests/platform/test_paper_runtime_storage_surface.py`.
- **Accepted local evidence:** E7-095 `storage=88`, `platform=3`, `integration=28`, `safety=58`; E7-064 earlier Gate B persistence matrix.
- **Classification:** `PARTIAL`.
- **Residual gap:** the repository does not yet have a mature dashboard/current-state read model uniformly carrying `source`, `observed_at`, `freshness`, `last_known_good`, and `current/unknown` across provider, operational, position, order, risk and protection planes.
- **Owner:** E6 primary; E7 for cross-module currentness contract.
- **Smallest safe follow-up:** define one read-only operational status DTO/view model derived mechanically from canonical stored facts, explicitly separating `CURRENT`, `STALE`, `UNKNOWN`, and `LAST_KNOWN_GOOD`.
- **Executable-source change:** `YES` if implemented as runtime/platform read model.
- **New credential-free requalification:** `YES` if executable storage/platform source changes.
- **Provider/private access:** `NO`.
- **Credentials:** `NO`.
- **Product Owner authority:** `NO` for code/tests.
- **Capital exposure:** `NO`.

### FP-07 — Reconciliation lock vs financial kill switch

- **Failure class:** operational desync lock and financial risk kill switch collapse into one opaque flag/state.
- **SWAP invariant:** `LOCKED/PAUSED/RECONCILIATION_REQUIRED` operational states and financial risk-veto/kill-switch state are separate, durable where required, and independently explainable.
- **Implementation:** E6 `OperationalMode` includes `PAUSED` and `LOCKED`; E5 `RiskContext` separately accepts `kill_switch_active`; risk evaluation rejects when kill switch is not false; operational recovery reasons are persisted independently.
- **Tests:** OperationalMode tests; E5 fail-closed/risk tests; Gate C integration safety tests.
- **Accepted local evidence:** E7-095 storage/risk/safety PASS.
- **Classification:** `PARTIAL`.
- **Residual gap:** financial kill switch is presently an input boolean rather than a separately durable, versioned, audited state object with activation source/reason/revision and recovery rules; UI/reporting separation is also not mature.
- **Owner:** E5 financial state; E6 persistence/reporting; E7 cross-module contract.
- **Smallest safe follow-up:** specify and persist a financial-safety lock record distinct from OperationalMode, then require E5 risk context to consume its exact current revision/provenance.
- **Executable-source change:** `YES`.
- **New credential-free requalification:** `YES`.
- **Provider/private access:** `NO`.
- **Credentials:** `NO`.
- **Product Owner authority:** `NO` for implementation/tests; changing actual capital-risk policy values remains Product Owner authority.
- **Capital exposure:** `NO`.

### FP-08 — Provider/local clock skew

- **Failure class:** signatures/temporal safety fail because local clock materially differs from provider time.
- **SWAP invariant:** provider time and local UTC clock are compared before accepting private read state; skew beyond a bounded threshold fails closed; risk decision time remains after provider observation.
- **Implementation:** `src/brokers/okx_shadow.py` (`CLOCK_SKEW_LIMIT_MS=5000`, public time observation, `CLOCK_SKEW_EXCEEDED`); `src/risk/context_derivation.py`; `src/integration/shadow_composition.py` + ADR-0010 separated strategy/risk clocks.
- **Tests:** `tests/brokers/test_okx_shadow.py`, `tests/risk/test_gate_c_context_derivation.py`, `tests/integration/test_gate_c_shadow_composition.py`, safety/E2E Gate C tests.
- **Accepted local evidence:** E7-095 exact candidate local broker/risk/integration/safety PASS; E7-083 historical provider read-only evidence measured healthy `clock_skew_ms=723` on `ab725965...`.
- **Classification:** `IMPLEMENTED_AND_LOCALLY_VERIFIED`.
- **Residual gap:** none in current credential-free implementation. Historical provider evidence is not automatically transferred to `8fbf5fca...`; any new provider-facing verification is a release-governance prerequisite, not evidence that the control is absent.
- **Owner:** E4 / E5 / E7.
- **Smallest safe follow-up:** do not reimplement; retain clock-skew and ADR-0010 tests in every future affected requalification.
- **Executable-source change:** `NO`.
- **New credential-free requalification:** `NO` unless code changes.
- **Provider/private access:** `NO` for the existing implementation claim; future provider re-verification separately governed.
- **Credentials:** `NO` for code/local tests.
- **Product Owner authority:** `NO` for preserving control; `YES` for a future provider/private run.
- **Capital exposure:** `NO`.

### FP-09 — State-aware watchdog / restart recovery

- **Failure class:** watchdog restarts a bot blindly despite unsafe persisted state.
- **SWAP invariant:** process restart policy must inspect exact revision, OperationalMode, current Position/protection/order reconciliation status, and refuse automatic restart into unsafe/unknown states.
- **Implementation:** E6 OperationalMode restart requires fresh SHADOW reconciliation; Paper recovery only reports `restart_authoritative` when exact lifecycle/execution/Position evidence is current; AgentBridge has demonstrated governed exact-revision worktree preparation.
- **Tests/evidence:** `tests/storage/test_operational_mode_shadow.py`, `tests/safety/test_gate_b_durable_lifecycle_freshness.py`; E7-095 local storage/safety PASS; `status/AGENTBRIDGE_EXACT_REVISION_PREPARATION_20260827.md` proves exact-clean preparation capability, not a state-aware watchdog policy.
- **Classification:** `PARTIAL`.
- **Residual gap:** no accepted external supervisor/watchdog contract proves restart decisions consume full project recovery state and distinguish flat/protected/unprotected/reconciliation-required/locked cases before relaunch.
- **Owner:** external operator/AgentBridge for process policy; E6 supplies recovery truth; E7 specifies integration preflight.
- **Smallest safe follow-up:** define an operator-side restart decision matrix consuming only sanitized E6 recovery/OperationalMode classifications, default-deny on unknown, and test it without provider access.
- **Executable-source change:** `YES` externally; project source only if a new integration preflight adapter is required.
- **New credential-free requalification:** `NO` for operator-only change; `YES` if project executable integration changes.
- **Provider/private access:** `NO` for watchdog validation.
- **Credentials:** `NO`.
- **Product Owner authority:** `NO` for fail-closed operator hardening; any actual provider runtime remains separately authorized.
- **Capital exposure:** `NO`.

### FP-10 — Actual-fill / aggregate-close / manual-flat lifecycle correctness

- **Failure class:** order ACK/status or one fill is mistaken for authoritative open/closed Position truth; manual close creates state divergence.
- **SWAP invariant:** exposure changes derive from canonical fills and authoritative Position observations; final closure requires aggregate quantity conservation plus later `actual_quantity=0 / CONSISTENT`; manual/external flat truth enters reconciliation, never heuristic closure.
- **Implementation:** `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`; `src/position/state_machine.py` includes `RECONCILED_FLAT`; `src/position/close.py`, `trade_result.py`; `src/execution/close.py`; lifecycle execution binding includes reduction-order Fill evidence; E6 recovery compares durable Position/execution facts.
- **Tests:** close action/result/trade-result tests, PaperBroker close-truth tests, Gate B close/trade-result integration/safety/E2E, lifecycle freshness tests.
- **Accepted local evidence:** E7-064 Gate B 450-test PASS; E7-095 position/storage/integration/e2e/safety PASS on unchanged executable source.
- **Classification:** `PARTIAL`.
- **Residual gap:** Paper/durable semantics are strong, but a production provider adapter/reconciliation flow that recognizes a manual/external flat Position and generates the exact E5 `RECONCILED_FLAT` path has not been implemented/verified end to end.
- **Owner:** E4 provider normalized Position truth; E5 reconciliation event/lifecycle; E6 persistence; E7 integration.
- **Smallest safe follow-up:** build credential-free fixtures for external/manual close -> normalized flat Position -> E5 `RECONCILED_FLAT` -> durable re-attestation, before any provider exercise.
- **Executable-source change:** `YES` for provider reconciliation integration.
- **New credential-free requalification:** `YES`.
- **Provider/private access:** `NO` for deterministic implementation; later real-provider validation `YES`.
- **Credentials:** `NO` initially; provider validation requires secure credentials.
- **Product Owner authority:** `NO` for code/tests; `YES` for provider/private validation.
- **Capital exposure:** `NO`.

### FP-11 — Unique protection registry / linkage

- **Failure class:** duplicate, orphaned, stale or conflicting protection orders exist for one Position.
- **SWAP invariant:** every intended protection order has exact PositionAction/Position lineage, and current provider reconciliation can prove the intended active protection set/multiplicity before mutation or new exposure.
- **Implementation:** deterministic protection `position_action_id`, `client_order_id`, `order_request_id`; Position-linked `PROTECTION_STOP` execution evidence is durably bound to lifecycle projections; duplicate/conflicting durable identities fail closed.
- **Tests:** protection lineage/result/terminal tests; lifecycle execution binding and durability/freshness tests; Gate B protection integration/safety tests.
- **Accepted local evidence:** E7-064 and E7-095 local suites materially cover canonical lineage and duplicate/conflict behavior.
- **Classification:** `PARTIAL`.
- **Residual gap:** no provider-facing protection registry states “expected active protection for Position X” and reconciles 0/1/>1 matching provider orders, external orders, replacement lineage, and orphan cleanup/manual review.
- **Owner:** E4 provider order registry; E5 intended protection authority; E6 durable registry/audit; E7 contract.
- **Smallest safe follow-up:** define an immutable intended-protection record plus reconciled provider-set snapshot and fail closed when multiplicity/identity differs from exactly one intended active protection.
- **Executable-source change:** `YES`.
- **New credential-free requalification:** `YES`.
- **Provider/private access:** `NO` for fixtures; later provider read verification `YES`.
- **Credentials:** `NO` initially; later provider verification requires approved secure credentials.
- **Product Owner authority:** `NO` for code/tests; `YES` for provider/private run.
- **Capital exposure:** `NO`.

### FP-12 — Pending/ACK must not mutate fill-derived Position truth

- **Failure class:** order ACK or pending status changes local exposure as though filled.
- **SWAP invariant:** submit acknowledgement is execution-state evidence only; Position quantity/lifecycle opening requires Fill and/or authoritative Position truth.
- **Implementation:** `src/brokers/okx_demo.py` maps success ACK to `OrderStatus.PENDING` with zero filled quantity; lifecycle state machine has no direct ACK->open transition; entry/protection/close result bridges require normalized execution/Position evidence.
- **Tests:** `tests/brokers/test_okx_demo_adapter.py::test_success_ack_is_pending_not_fill_truth`; PaperBroker fill/lineage tests; position lifecycle/trade-result and safety suites.
- **Accepted local evidence:** E7-095 exact candidate `brokers=135`, `position=97`, `integration=28`, `safety=58` PASS; E7-064 prior Gate B evidence.
- **Classification:** `IMPLEMENTED_AND_LOCALLY_VERIFIED`.
- **Residual gap:** no material V0.1 gap identified; future provider submit adapters must preserve this invariant.
- **Owner:** E4 / E5 / E6.
- **Smallest safe follow-up:** do not reimplement; require ACK-without-fill regression in every future submit-capable adapter qualification.
- **Executable-source change:** `NO`.
- **New credential-free requalification:** `NO` unless affected code changes.
- **Provider/private access:** `NO`.
- **Credentials:** `NO`.
- **Product Owner authority:** `NO` for maintaining the invariant.
- **Capital exposure:** `NO`.

### FP-13 — Stale pre-reconcile snapshot invalidation

- **Failure class:** code reconciles newer truth but continues using an older Position/order/fill object in the same authority path or after restart.
- **SWAP invariant:** authority is bound to exact observation/evidence identity; any newer/different Position observation or reduction-order result/fill invalidates the older lifecycle authority until E5 reinterprets/re-attests.
- **Implementation:** exact `position_observed_at` matching in protection/close actions and E4 consumer validation; `POSITION_LIFECYCLE_EXECUTION_EVIDENCE_BINDING_V0_1` hashes all current reduction request/result/fill evidence; E6 recomputes and refuses `READY` on mismatch.
- **Tests:** `tests/safety/test_gate_b_durable_lifecycle_freshness.py` explicitly covers newer partial protection Fill, canceled protection, newer raw Position observation and missing binding; `tests/execution/test_close.py` covers Position observation mismatch.
- **Accepted local evidence:** E7-095 `execution`, `position`, `storage`, `integration`, `safety` PASS; E7-064 Gate B PASS.
- **Classification:** `IMPLEMENTED_AND_LOCALLY_VERIFIED`.
- **Residual gap:** no material audited interface/restart gap. Future orchestration must not cache around these exact-object guards.
- **Owner:** E5 / E6 / E7; E4 supplies new truth.
- **Smallest safe follow-up:** no duplicate mechanism; retain exact-observation/freshness tests when future provider orchestration is introduced.
- **Executable-source change:** `NO`.
- **New credential-free requalification:** `NO` unless code changes.
- **Provider/private access:** `NO`.
- **Credentials:** `NO`.
- **Product Owner authority:** `NO`.
- **Capital exposure:** `NO`.

### FP-14 — Bounded stable waiting/retry states

- **Failure class:** stable non-actionable provider condition is retried in a tight loop.
- **SWAP invariant:** ambiguity/minimum/residual/replacement conditions become explicit stable states; retry requires new evidence, bounded schedule, or operator action, never immediate unchanged resubmission.
- **Implementation:** ambiguous OKX Demo submit returns `RECONCILIATION_REQUIRED`; repeat ordinary submit does not send again; reconciliation evidence sets `retry_allowed=False`; provider absence is not inferred from arbitrary error code; E6 has explicit reconciliation-required recovery states.
- **Tests:** `tests/brokers/test_okx_demo_adapter.py` timeout/reconciliation/retry tests; safety/recovery tests.
- **Accepted local evidence:** E7-095 broker/storage/safety PASS.
- **Classification:** `PARTIAL`.
- **Residual gap:** no uniform waiting vocabulary/backoff for unrepresentable SWAP residual size, already-breached protection trigger, protection replacement pending state, or provider rate/availability windows.
- **Owner:** E4 retry mechanics; E5 semantic waiting/reconciliation state; E6 durable scheduling/status where needed.
- **Smallest safe follow-up:** define stable reason/state codes for each non-actionable class and a retry contract requiring changed observation or bounded elapsed interval; first verify with a fake clock/transport.
- **Executable-source change:** `YES`.
- **New credential-free requalification:** `YES`.
- **Provider/private access:** `NO`.
- **Credentials:** `NO`.
- **Product Owner authority:** `NO` for fail-closed implementation/tests.
- **Capital exposure:** `NO`.

### FP-15 — Staged breakeven / trailing / profit-protection maturity

- **Failure class:** profit protection is promoted too early or protection replacement becomes a fragile loop.
- **SWAP invariant:** breakeven/trailing/profit-protection changes are explicit E5-authorized state transitions, use fresh Position/market truth, preserve one protection registry lineage, perform bounded replacement, and verify provider result before lifecycle promotion.
- **Implementation present only as vocabulary:** `PositionLifecycleState.PROFIT_PROTECTED` and `PositionEvent.PROFIT_PROTECTION_VERIFIED` exist in `src/position/state_machine.py`; `src/position/protection_result.py` can preserve an already `PROFIT_PROTECTED` state if protection remains active.
- **Missing implementation:** no audited builder/contract for `MODIFY_PROTECTION`, breakeven, trailing threshold, replacement action/version, or provider replacement verification was found; `src/position/protection.py` supports initial `PROTECT` from `OPEN_UNPROTECTED` only.
- **Tests/local evidence:** E7-095 verifies existing vocabulary/protection behavior but cannot verify absent staged-management behavior.
- **Classification:** `MISSING`.
- **Residual gap:** the lifecycle state exists without the executable authority/state machine that safely reaches it through staged protection management.
- **Owner:** E5 policy/authority; E4 provider replacement; E6 audit persistence; E7 profile/integration.
- **Smallest safe follow-up:** define a separate versioned profit-protection action profile with trigger criteria, monotonic/no-widening stop rule, exact current Position/market proof, replacement identity and verification before `PROFIT_PROTECTED`.
- **Executable-source change:** `YES`.
- **New credential-free requalification:** `YES`.
- **Provider/private access:** `NO` for contract/source/tests; later replacement verification `YES` if authorized.
- **Credentials:** `NO` initially.
- **Product Owner authority:** `NO` for fail-closed implementation; strategy/risk policy thresholds that alter capital-risk behavior require Product Owner policy approval before use.
- **Capital exposure:** `NO`.

### FP-16 — Exact runtime identity / revision / mode / heartbeat preflight

- **Failure class:** wrong process, stale revision, wrong mode or dead/stale worker is considered healthy and permitted to access provider/runtime.
- **SWAP invariant:** before provider-capable runtime, prove exact executable revision/clean worktree, expected runtime identity/config, authoritative OperationalMode, single-instance/heartbeat freshness, and fail closed on any mismatch.
- **Implementation/evidence:** project OperationalMode is durable; AgentBridge exact-revision preparation is governed (`status/AGENTBRIDGE_EXACT_REVISION_PREPARATION_20260827.md`); E7-095 proves execution revision `8fbf5fca...` + clean worktree + approved Windows environment; local-action mailbox binds task/request/action identity.
- **Tests/evidence:** E7-095 local qualification; operator preparation evidence. These prove revision/worktree identity, not a complete long-running runtime heartbeat contract.
- **Classification:** `PARTIAL`.
- **Residual gap:** no accepted integrated preflight binds process PID/instance identity, runtime configuration fingerprint, OperationalMode revision, heartbeat age/scheduler liveness and exact project revision into one required provider-runtime admission decision. AgentBridge ADR-0010 consumer migration also remains a separate current prerequisite.
- **Owner:** E7 integration contract + external operator/AgentBridge runtime supervisor; E6 supplies OperationalMode truth.
- **Smallest safe follow-up:** define a sanitized preflight evidence schema and operator admission check with exact revision, clean state, mode revision, consumer version/config fingerprint, single-instance identity and heartbeat freshness; verify credential-free before any provider authorization.
- **Executable-source change:** `YES` externally; project source only if an E7 integration adapter is added.
- **New credential-free requalification:** `NO` for operator-only changes; `YES` if project executable code changes.
- **Provider/private access:** `NO`.
- **Credentials:** `NO`.
- **Product Owner authority:** `NO` for fail-closed preflight hardening; provider/runtime authorization remains separately required.
- **Capital exposure:** `NO`.

## Prioritized residual gaps

### P0_PRE_PROVIDER_RUNTIME

These should be closed before any future provider-capable SHADOW/session execution is considered technically mature:

1. **FP-03 — breached protection trigger geometry:** missing; cannot safely create/replace protection without fresh market-side validation.
2. **FP-02 — complete SWAP action-role provider capability matrix:** current entry/read-only controls do not prove protection/close provider translation.
3. **FP-05 — provider-native close/residual sizing:** exact canonical close quantity exists, but provider lot/minimum/reducible residual handling is absent.
4. **FP-04 — external/manual provider reconciliation:** detection exists, ownership/adopt/reject/manual-review policy is incomplete.
5. **FP-11 — unique active-protection registry:** lineage is strong, provider-set multiplicity/current intended protection is incomplete.
6. **FP-16 — process/revision/mode/heartbeat admission:** revision and mode pieces exist, integrated runtime admission evidence is incomplete.
7. **FP-10 — manual/external flat convergence:** core Paper closure truth exists, but provider-manual flat lifecycle integration is incomplete.

No provider access is required to implement the first deterministic version of these controls; all can begin with fixtures/fake transports and local-only verification. Any later private/provider verification remains separately authorized.

### P1_PRE_PAPER_OR_SHADOW

1. **FP-07 — durable financial kill-switch plane:** separate it from operational lock/reconciliation state.
2. **FP-06 — provenance/freshness-aware current-state read model:** avoid stale dashboard/operator claims.
3. **FP-09 — state-aware external restart/watchdog:** use E6 recovery/OperationalMode classifications before relaunch.

Existing `FP-01`, `FP-12`, and `FP-13` controls should be consumed, not recreated, by these follow-ups.

### P2_PRE_LIVE

1. **FP-14 — stable waiting/retry vocabulary:** extend beyond ambiguous entry to residual sizing, protection replacement and other stable provider conditions.
2. **FP-15 — staged breakeven/trailing/profit protection:** currently missing as an executable authority path; implement only after initial protection/registry/provider reduction boundaries are mature.

### P3_OPERATIONAL_HARDENING

- Continue improving operator-facing observability and last-known-good/current distinction after FP-06 minimum read model exists.
- Add long-running heartbeat/instance telemetry only as a supplement to, never a replacement for, exact revision/mode/reconciliation admission under FP-16.
- Preserve deterministic reason codes and sanitized evidence; never solve operability by exposing raw provider/account payloads or secrets.

## Bounded next tasks by owner

### E4 — Execution / broker

1. Create the OKX SWAP action-role capability matrix and fail-closed provider translation fixtures for entry/protection/close (`FP-02`).
2. Add provider reduction sizing/representability/residual classification using current SWAP metadata and current Position actual quantity (`FP-05`).
3. Define/implement external provider order/fill/position ownership reconciliation and unique protection-set observation surfaces (`FP-04`, `FP-11`).
4. Preserve existing ACK-is-not-fill and ambiguous-submit no-resubmit behavior (`FP-12`, covered) rather than replacing it.

### E5 — Risk / position

1. Define protection-trigger geometry/breached-trigger policy using fresh market and Position truth (`FP-03`).
2. Define the durable financial kill-switch state semantics consumed by Risk separately from OperationalMode (`FP-07`, with E6/E7).
3. Define residual/waiting and manual-flat reconciliation semantics without fabricating exposure (`FP-05`, `FP-10`, `FP-14`).
4. Define staged profit-protection action semantics only after initial protection/provider registry controls are complete (`FP-15`).

### E6 — Platform / storage

1. Persist/report financial kill-switch state independently from OperationalMode (`FP-07`).
2. Build a provenance/freshness-aware read model for current operator state (`FP-06`).
3. Persist intended/current protection registry/reconciliation evidence without inferring E5 lifecycle semantics (`FP-11`).
4. Expose sanitized restart-readiness facts for the external watchdog (`FP-09`, `FP-16`).

### E7 — Integration / architecture / release

1. Review/version any shared trigger-validity, external-ownership, protection-registry, kill-switch and profit-protection profiles required by FP-03/04/07/11/15.
2. Define cross-module credential-free integration/safety acceptance tests for each new invariant before provider verification.
3. Define the runtime admission/preflight evidence contract for FP-16 jointly with the external operator, without moving process supervision into project domain code unnecessarily.
4. Do not relabel credential-free PASS as provider PASS and do not weaken existing Gate B/Gate C fail-closed invariants to simplify implementation.

### External operator / AgentBridge

1. Migrate/review the SHADOW consumer against ADR-0010 before any future provider session (existing prerequisite).
2. Implement state-aware watchdog admission/restart and exact process/revision/mode/config/heartbeat preflight (`FP-09`, `FP-16`) using sanitized project recovery facts.
3. No provider/session execution may be inferred from completing these operator hardening tasks; a future provider session still requires its own authority.

## Already-covered controls that must not be reimplemented

- **OperationalMode append-only history and restart fresh-reconciliation requirement** (`FP-01`): reuse `OperationalModeStore/Recovery`; do not introduce a parallel mode file/flag.
- **Clock skew + ADR-0010 temporal ordering** (`FP-08`): preserve the existing 5-second skew fail-closed rule and separated strategy/provider/risk clocks.
- **ACK is not fill truth** (`FP-12`): preserve PENDING/zero-filled ACK semantics and Fill/Position-derived exposure.
- **Exact stale-evidence invalidation** (`FP-13`): preserve exact Position observation binding and lifecycle execution snapshot hashes; do not add heuristic “fresh enough” shortcuts.
- **Close truth requires authoritative flat Position**: preserve `CLOSE_TRADE_RESULT_PROFILE_V0_1`; filled order status alone must never become flat truth.
- **Provider quantity may never exceed E5-approved canonical exposure**: preserve floor-only entry sizing and the no-round-up rule.
- **Unknown/ambiguous state fails closed**: retain reconciliation-required/locked semantics rather than converting unknown into flat/safe.

## Literal Spot fixes that must not be transplanted into SWAP

1. **Do not set `tdMode=cash` as a SWAP rule.** Current R7 SWAP entry boundary uses isolated Futures-mode semantics; action-specific SWAP capabilities must be defined explicitly.
2. **Do not import a Spot-specific blanket prohibition of `reduceOnly`.** R7 shared protection/close contracts intentionally require reduction-only semantics; exact OKX SWAP provider encoding must be validated by role/mode rather than copied from Spot.
3. **Do not treat BTC wallet dust as SWAP Position flatness.** SWAP flatness is normalized Position exposure truth (`actual_quantity=0 / CONSISTENT`) plus appropriate execution/lifecycle evidence.
4. **Do not genericize Spot algo-order `ccy` parameters into SWAP protection.** SWAP protection/provider parameters require an explicit BTC-USDT-SWAP capability matrix and provider-specific validation.
5. **Do not convert Spot base-asset order quantity rules directly into SWAP contract counts.** R7 canonical quantity is BTC; provider contracts are an E4 translation using validated `ctVal/ctMult/lotSz/minSz` metadata.

## Release / authority interpretation

This audit does not change release gates or runtime authorization.

```text
Gate A = unchanged
Gate B = unchanged
Gate C historical/provider evidence = unchanged and remains bound to its recorded revision
8fbf5fca... credential-free qualification = unchanged / PM accepted
provider verification on 8fbf5fca... = NOT_RUN / NOT_INFERRED
PAPER = NOT AUTHORIZED
third/replacement SHADOW session = NOT AUTHORIZED / PRODUCT OWNER AUTHORITY REQUIRED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
capital exposure = NONE
```

Closing a gap in source/tests would create a new executable candidate when executable code changes; it must receive the appropriate approved-local credential-free requalification before being treated as verified. Provider/private evidence must be separately authorized and revision-bound. No gap may be “closed” by documentation alone when its classification requires runtime code.

## Completion confirmation

E7-098 performed only repository inspection and durable documentation/status work. It did not modify production source, tests, contracts, ADR semantics, AgentBridge source/config, local action catalog, credentials, Product Owner authorization artifacts, or release-gate criteria. It did not execute project code, create a Local Job Request, call OKX, read credentials, start PAPER/SHADOW, mutate provider/account state, submit/cancel/amend/close any order, or move/expose capital.
