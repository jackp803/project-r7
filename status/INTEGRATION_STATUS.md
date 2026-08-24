# Integration Status

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Current review: `E7-20260824-030` / 2026-08-24  
> Reviewed main: `0617221eada56390db482ab3d758f39ea5f7457f`  
> Contract baseline: `contracts-v0.1 / BASELINE`  
> Protection profile: `protection-v0.1`

## Current integration target

**Gate B / Slice 3 Paper readiness — actual-fill protection producer/consumer integration**

This review is static/test-definition only. No project code, tests, Paper runtime, provider/private API, migration, Local Runner action, GitHub CI, SHADOW, or LIVE activity was executed.

## Release-gate state

```text
Gate A — RESEARCH_READY = PASS / RESEARCH-INTEGRATION ONLY
Gate B — PAPER_READY    = BLOCKED / NOT YET PASS
Gate C — SHADOW_READY   = BLOCKED / UNCHANGED
Gate D — LIVE_READY     = BLOCKED / UNCHANGED

PAPER / SHADOW / LIVE   = UNAUTHORIZED
provider/private API    = NOT AUTHORIZED
project executable verification = NOT_RUN / DEFERRED TO LATER APPROVED-LOCAL TASK
```

## Accepted Gate B protection prerequisites

- PR `#37` merge `e6769b5b78f1b5f699ae4000204b803b2f8b69d5` — `protection-v0.1` + ADR-0004.
- PR `#38` merge `268ac8708f84d0c856ac2d1d7436dcb100347a46` — E5 producer `src/position/protection.py`.
- PR `#39` merge `44ec171817f6c13fa632f2e7658dccc6b518f777` — E4 consumer `src/execution/protection.py` + additive request/fill lineage.
- PR `#35` merge `133e62b2ad8aa5c31d3f0aef1679c0449aa2a10c` — explicit daily/open-position/drawdown risk-limit test definitions.

All producer/consumer executable evidence remains `NOT_RUN`.

## E5 -> E4 protection boundary

Static disposition: **COHERENT / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE**.

Materialized path:

```text
normalized Position actual exposure
-> E5 build_protect_position_action(...)
-> protection-v0.1 PositionAction.PROTECT
-> E4 prepare_protection_order(...)
-> canonical STOP_MARKET / reduce_only protection OrderRequest
```

Verified statically:

- partial fill uses exact smaller `Position.actual_quantity`, not parent requested/approved maximum;
- full fill preserves exact canonical quantity;
- quantity profile/unit/asset remains `base-asset-v0.1 / BASE_ASSET / BTC` for `BTC_USDT_PERP`;
- exact parent stop/target/max-hold values are bound into the E5 action;
- E4 emits only the approved stop request and does not invent target/OCO/timer behavior;
- plan/risk/position/action lineage remains exact;
- identical action yields deterministic request identity; materially changed immediate authority changes identity/fingerprint;
- unknown/mismatch/reconciliation-required Position truth fails closed;
- over-approved actual exposure cannot expand ordinary protection authority;
- legacy/missing/unsupported profile and `MODIFY_PROTECTION` remain non-executable;
- expired parent entry TTL alone does not invalidate a fresh post-fill PositionAction;
- expired PositionAction fails closed;
- action creation/request preparation/submission intent does not equal `PROTECTION_VERIFIED` and does not change `OPEN_UNPROTECTED` to protected state.

No shared contract contradiction was found.

## E7-owned test definitions added

### Integration

`tests/integration/test_gate_b_protection_boundary.py`

- commit `d7ff963c4e12bd800c42ea7c174a1f6b67742833`
- uses real E5 producer, real E4 translator, and real PaperBroker where submit-vs-verification distinction is defined.

### Safety

`tests/safety/test_gate_b_protection_safety.py`

- commit `ee29ce9dfe99a3dd723681c1d12b38ffe00c865a`
- uses real E5/E4 production APIs for fail-closed cross-module definitions.

No test was executed by E7-030.

## Gate B evidence reconciliation

The following criteria now have implementation/test definitions and only approved-local executable evidence remains:

```text
Partial fill semantics preserve actual quantity                = NOT_RUN
Required protection follows actual filled quantity            = NOT_RUN
Drawdown/daily/position/kill-switch rules enforced             = NOT_RUN
```

The risk-limit move from `BLOCKED` to `NOT_RUN` is supported by PR #35 plus existing kill-switch safety definitions. The protection move from `BLOCKED` to `NOT_RUN` is supported by PR #37/#38/#39 plus the new E7 integration/safety definitions.

Neither is PASS.

## Protection verification / failure gap

Current callable pieces:

| Behavior | Classification | Evidence |
|---|---|---|
| E5 actual-exposure PositionAction producer | `IMPLEMENTED_NEEDS_LOCAL_EVIDENCE` | PR #38 |
| E4 PositionAction -> canonical protection OrderRequest | `IMPLEMENTED_NEEDS_LOCAL_EVIDENCE` | PR #39 |
| Generic PaperBroker submit/query/reconcile OrderResult primitives | `IMPLEMENTED_NEEDS_LOCAL_EVIDENCE` | `src/brokers/paper.py` |
| E5 broker-truth -> protection lifecycle-event bridge | `IMPLEMENTATION_GAP` | no callable accepted implementation |
| definitive protection failure -> `PROTECTION_FAILED` -> EMERGENCY | `IMPLEMENTATION_GAP` | transition exists; result-to-event bridge absent |
| previously verified protection loss -> `PROTECTION_LOST` -> EMERGENCY | `IMPLEMENTATION_GAP` | transition exists; result-to-event bridge absent |
| PaperBroker protection Fill lineage propagation | `IMPLEMENTATION_GAP` | Fill model supports lineage, but `record_fill()` does not populate it |

The state machine alone is not enough to close the Gate B `Protection failure triggers emergency path` criterion.

### Next bounded PM dependency

E7 does not assign work. Recommended next dependency is **E5 protection-result lifecycle bridge** using existing normalized E4 shared truth:

```text
exact protection OrderRequest
+ authoritative OrderResult/query/reconciliation state
-> E5 PROTECTION_VERIFIED | PROTECTION_FAILED | PROTECTION_LOST | fail-closed reconciliation event
```

Rationale: E4 already owns and exposes normalized broker/order truth; E5 owns lifecycle interpretation. Unknown/reconciliation-required truth must never become verified protection. If implementation demonstrates that a new cross-module serialized evidence object is actually required, the domain task must stop and return to E7 contract review rather than invent a private DTO.

After that bridge materializes, E7 can define the real PaperBroker result -> E5 event -> state-machine failure/verification integration scenarios. E4 protection Fill lineage remains a later dependency before full close-to-TradeResult/audit parity.

## Remaining Gate B blockers

| Blocker | Owner boundary | State |
|---|---|---|
| protection broker truth -> E5 verified/failed/lost lifecycle event | E5 consuming E4 normalized truth | `IMPLEMENTATION_GAP` |
| protection failure/loss -> integrated emergency behavior | E5 lifecycle bridge + E7 integration evidence | `IMPLEMENTATION_GAP` |
| Paper risk/position/order/protection/trade persistence + restart | E6 | `IMPLEMENTATION_GAP` |
| close path -> canonical TradeResult -> durable audit | E4 + E5 + E6 | `IMPLEMENTATION_GAP` |
| full Paper E2E/failure/restart suite | E7 after domain interfaces | `INTEGRATION_TEST_DEFINITION_GAP` |
| approved-local Gate B executable evidence | E7/PM after prerequisites | `NOT_RUN` |

Gate B remains blocked until all required criteria have actual PASS evidence.

## Verification / compute / safety

```text
project executable verification = NOT_RUN / DEFERRED TO LATER APPROVED-LOCAL TASK
provider/private requests        = NOT_SENT
exchange credentials             = NOT_USED
GitHub Actions / CI              = NOT_USED
hosted/GitHub-triggered compute  = NOT_USED
Local Runner                     = NOT_REQUESTED
Computer Adapter                 = NOT_USED
PAPER / SHADOW / LIVE            = UNAUTHORIZED
Registry real/live promotion     = NONE
E4/E5 production edits by E7     = NONE
contracts / ADR edits by E7      = NONE
Codex bug ticket                 = NONE
```

## Detailed evidence

`status/e7/GATE_B_PROTECTION_INTEGRATION_REVIEW_20260824.md`

## Completion

E7-030 stops after persisting bounded E7-owned test definitions/evidence/status. E7 does not self-start the E5 bridge, approved-local verification, full Paper E2E, provider/private work, Gate C, PAPER, SHADOW, LIVE, or another task.
