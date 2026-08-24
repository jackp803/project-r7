# Gate B Protection Integration / Safety Review — E7-20260824-030

## Authority / scope

- task_id: `E7-20260824-030`
- target branch: `agent/e7-gate-b-protection-integration-20260824`
- reviewed main: `0617221eada56390db482ab3d758f39ea5f7457f`
- authoritative TASK blob: `6c6392b671de9bb5ab68099afae5c55c9ee5a635`
- contract baseline: `contracts-v0.1 / BASELINE`
- protection profile: `protection-v0.1`
- contract PR: `#37 / merge e6769b5b78f1b5f699ae4000204b803b2f8b69d5`
- E5 producer PR: `#38 / merge 268ac8708f84d0c856ac2d1d7436dcb100347a46 / head b98188691f7b9468204bf4f8f3164c07367741db`
- E4 consumer PR: `#39 / merge 44ec171817f6c13fa632f2e7658dccc6b518f777 / head 5dd502f53b3eeb564ee917a8c5fa2090074908bc`
- E5 risk-limit evidence PR: `#35 / merge 133e62b2ad8aa5c31d3f0aef1679c0449aa2a10c`
- project executable verification: `NOT_RUN / DEFERRED TO LATER APPROVED-LOCAL TASK`

This task is static/test-definition only. E7 did not execute project code, tests, PaperBroker runtime, provider/private APIs, migrations, backtests, Local Runner actions, GitHub Actions, CI, hosted runners, Computer Adapter, or arbitrary cloud compute.

## Terminal static disposition

```text
E5 protection-v0.1 producer -> E4 protection-v0.1 consumer = PASS STATIC / COHERENT
shared contract contradiction = NONE FOUND
Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path = BLOCKED / IMPLEMENTATION_GAP
Drawdown/daily/position/kill-switch rules enforced = NOT_RUN
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

`PASS STATIC` above is an integration-review label only. It is not executable release evidence and does not convert any Gate B criterion to `PASS`.

## Accepted producer -> consumer review

### E5 producer

Reviewed `src/position/protection.py` from merged PR #38.

Static behavior:

- requires `protection-v0.1 / PROTECT`;
- source Position must be `OPEN_UNPROTECTED` and `reconciliation_status=CONSISTENT`;
- `PositionAction.quantity` is exactly `Position.actual_quantity`;
- quantity is positive/finite and must be `<=` parent ApprovedTradePlan maximum;
- canonical quantity profile remains `base-asset-v0.1 / BASE_ASSET / BTC` for `BTC_USDT_PERP`;
- parent `trade_plan_id`, `risk_decision_id`, risk policy, symbol/side and exact stop/target/max-hold values are bound into the action;
- action identity changes with authority-bearing material;
- action has its own expiry and does not reuse the parent entry TTL;
- legacy/unsupported profile, `MODIFY_PROTECTION`, unknown/mismatch/reconciliation-required truth, invalid quantity and bound tampering fail closed;
- producing the action does not mutate lifecycle state or claim `PROTECTION_VERIFIED`.

### E4 consumer

Reviewed `src/execution/protection.py` and additive `src/execution/models.py` changes from merged PR #39.

Static behavior:

- independently revalidates action, exact parent plan and exact current normalized Position truth;
- current Position must still be `OPEN_UNPROTECTED / CONSISTENT`;
- action quantity must equal current actual quantity and remain within parent maximum;
- action stop/target/max-hold values must equal exact parent protection bounds;
- parent entry TTL is checked only for structural consistency and is intentionally not compared to current time after exposure exists;
- PositionAction expiry controls current post-fill protection authority;
- translation is mechanical:

```text
LONG  -> SELL
SHORT -> BUY
order_type = STOP_MARKET
order_role = PROTECTION_STOP
quantity = exact action/current actual canonical quantity
stop_price = exact approved stop_level
reduce_only = true
limit_price = null
time_in_force = null
```

- request retains parent `trade_plan_id` plus immediate `position_action_id`, `position_id`, `risk_decision_id`, `authorization_type=POSITION_ACTION` and canonical quantity profile;
- client/order IDs are deterministic from the immediate PositionAction authority;
- provider-native sizing/trigger facts do not appear in the shared request;
- request creation does not claim protected lifecycle state.

### Static compatibility decision

No shared contract or architecture contradiction was found between PR #38 and PR #39 under `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md` and ADR-0004.

The materialized provider-neutral chain is now:

```text
known normalized Position actual exposure
-> E5 build_protect_position_action(...)
-> protection-v0.1 PositionAction.PROTECT
-> E4 prepare_protection_order(...)
-> canonical STOP_MARKET reduce-only OrderRequest
```

Therefore the prior implementation blocker for the Gate B criterion `Required protection follows actual filled quantity` is resolved. Executable evidence is still absent, so the canonical criterion moves only to `NOT_RUN`, never to `PASS`.

## E7 integration / safety test definitions materialized

### Integration

`tests/integration/test_gate_b_protection_boundary.py`

Commit:

```text
d7ff963c4e12bd800c42ea7c174a1f6b67742833
```

Uses the real accepted APIs:

- `position.build_protect_position_action`
- `src.execution.protection.prepare_protection_order`
- `src.brokers.paper.PaperBroker` only to define submit-vs-verification behavior

Definitions cover:

1. partial actual fill smaller than parent maximum propagates unchanged E5 -> E4;
2. full actual fill propagates exact canonical quantity/profile/unit/asset without provider-native leakage;
3. exact parent stop/target/max-hold is bound by E5, while E4 emits only the approved STOP_MARKET protective stop and does not invent target/OCO/timer behavior;
4. exact plan/risk/position/action lineage and deterministic immediate-action-scoped request identity;
5. materially changed PositionAction authority changes action/request identity/fingerprint;
6. expired parent entry TTL alone does not invalidate a still-valid post-fill PositionAction;
7. action creation, request preparation, and generic PaperBroker submit do not claim `PROTECTION_VERIFIED` or mutate `OPEN_UNPROTECTED`.

### Safety

`tests/safety/test_gate_b_protection_safety.py`

Commit:

```text
ee29ce9dfe99a3dd723681c1d12b38ffe00c865a
```

Uses the real accepted E5 producer and E4 consumer directly. Definitions cover:

- UNKNOWN/MISMATCH/RECONCILIATION_REQUIRED Position truth fails closed at producer and consumer boundaries;
- over-approved actual exposure cannot expand ordinary E5/E4 authority;
- stop/target/max-hold tampering fails at E4;
- missing/unsupported profile and `MODIFY_PROTECTION` remain non-executable;
- expired PositionAction fails closed;
- initial PROTECT consumer requires current `OPEN_UNPROTECTED` state.

No helper reimplements E5/E4 business semantics.

## Gate B risk-limit evidence reconciliation

Merged PR #35 adds explicit deterministic definitions in `tests/risk/test_risk_engine.py` for:

- daily-trade cap at and above configured policy boundary;
- open/simultaneous-position cap at and above configured policy boundary;
- drawdown lock at and above configured threshold;
- new TradeIntent identity cannot bypass active limit locks.

Existing `tests/safety/test_e5_fail_closed.py` already defines kill-switch rejection and related fail-closed state behavior.

The prior `EVIDENCE_GAP` is therefore no longer an implementation/test-definition blocker. Executable evidence is still `NOT_RUN`, so the canonical Gate B criterion `Drawdown/daily/position/kill-switch rules enforced` moves from `BLOCKED` to `NOT_RUN`, not PASS.

## Protection verification / failure chain classification

Required chain reviewed:

```text
protection OrderRequest
-> broker/PaperBroker result / active protective state truth
-> E5 consumes verified/failed/lost evidence
-> PROTECTION_VERIFIED or PROTECTION_FAILED / PROTECTION_LOST lifecycle event
```

### 1. E5 action production

```text
classification = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
```

PR #38 provides the callable producer and validator. Executable evidence remains NOT_RUN.

### 2. E4 protection request translation

```text
classification = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
```

PR #39 provides the callable consumer/translator. Executable evidence remains NOT_RUN.

### 3. Generic PaperBroker order result / query / reconciliation primitives

```text
classification = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
```

`PaperBroker.submit_order()`, `query_order()`, `query_position()`, `query_fills()` and `reconcile()` exist and return shared `OrderResult`/reconciliation primitives. Ambiguous acknowledgement does not permit blind retry.

This generic primitive existence is not equivalent to a complete protection lifecycle bridge.

### 4. E5 consumption of protection broker truth into lifecycle event

```text
classification = IMPLEMENTATION_GAP
```

No current callable E5 path consumes the exact protection `OrderRequest` plus authoritative E4/PaperBroker `OrderResult`/query/reconciliation truth and decides one of:

```text
PROTECTION_VERIFIED
PROTECTION_FAILED
PROTECTION_LOST
STATE_UNKNOWN / reconciliation-required behavior
```

The state-machine transitions exist, but no accepted result-to-event bridge invokes them from broker truth.

### 5. Protection failure -> EMERGENCY integrated behavior

```text
classification = IMPLEMENTATION_GAP
```

`OPEN_UNPROTECTED + PROTECTION_FAILED -> EMERGENCY` exists in `src/position/state_machine.py`, but no current callable bridge produces `PROTECTION_FAILED` from an exact failed protective request/result. A transition table alone is insufficient for Gate B.

### 6. Previously verified protection loss -> EMERGENCY integrated behavior

```text
classification = IMPLEMENTATION_GAP
```

`PROTECTION_LOST` transitions exist, but no callable broker-truth-to-event bridge is materialized.

### 7. Protection Fill lineage through PaperBroker

```text
classification = IMPLEMENTATION_GAP
```

The shared `Fill` model can now carry `position_action_id`, `position_id`, and `order_role`, but current `PaperBroker.record_fill()` constructs Fill without propagating those fields from the originating protection request. This is a later E4 requirement for full close/TradeResult/audit parity; it does not invalidate the request-construction criterion reviewed here.

### Contract status

```text
CONTRACT_OR_SEMANTIC_GAP = NO for the reviewed request-construction boundary
```

Existing shared `OrderRequest`, `OrderResult`, reconciliation and E5 lifecycle vocabulary are sufficient to issue a bounded follow-up for the Paper protection-result bridge. If that implementation proves a new shared serialized object is required, the domain owner must stop and return to E7 rather than invent a private cross-module contract.

## Safe next bounded dependency / PM recommendation

E7 does not assign agents. The next dependency order recommended to PM is:

1. **E5 protection-result lifecycle bridge** — consume exact canonical protection `OrderRequest` plus authoritative E4/PaperBroker `OrderResult`/query/reconciliation truth and map only unambiguous broker states into existing E5 lifecycle events. Unknown/reconciliation-required state must never become verified protection. Definitive pre-verification failure must reach `PROTECTION_FAILED`; previously verified protection disappearance/failure must reach `PROTECTION_LOST`.
2. **E7 cross-module verification/failure test definitions** — after the E5 bridge is materialized, define the real PaperBroker -> E5 event -> state-machine scenarios, including failed protection -> EMERGENCY and unknown truth -> reconciliation-required behavior.
3. **Approved-local execution task** — only after implementation/test definitions are complete, run relevant E4/E5/integration/safety suites under the approved local-only mechanism.
4. **E4 protection Fill lineage follow-up** remains required before full close-to-TradeResult / durable audit parity, but it is not the next dependency for proving protection activation/failure lifecycle semantics.

Rationale for E5-first: current E4 already emits/queries normalized shared `OrderResult` and reconciliation truth. E5 owns risk/lifecycle interpretation and therefore owns conversion of that normalized broker truth into `PROTECTION_VERIFIED`, `PROTECTION_FAILED`, `PROTECTION_LOST`, or fail-closed reconciliation lifecycle events. E7 must not make that domain decision inside integration glue.

## Post-review Gate B dependency map

```text
Gate A                                               PASS
TradeIntent -> E5 RiskDecision                      NOT_RUN
E5 reject                                            NOT_RUN
ApprovedTradePlan-only strategy execution boundary  NOT_RUN
PaperBroker contract                                 NOT_RUN
Partial fill actual quantity                         NOT_RUN
Required protection follows actual filled quantity  NOT_RUN
Protection failure -> emergency                      BLOCKED / IMPLEMENTATION_GAP
Stale/unknown market blocks exposure                 NOT_RUN
Unknown order/position blocks exposure               NOT_RUN
Drawdown/daily/position/kill-switch                  NOT_RUN
Restart/persistence                                  BLOCKED / IMPLEMENTATION_GAP
Paper E2E -> TradeResult + audit                     BLOCKED / IMPLEMENTATION_GAP
GitHub CI/Actions not used                           PASS

Gate B                                               BLOCKED / NOT YET PASS
PAPER                                                UNAUTHORIZED
```

## Verification / security / scope

```text
project executable verification = NOT_RUN / DEFERRED TO LATER APPROVED-LOCAL TASK
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered project compute = NOT_USED
Local Runner = NOT_REQUESTED
Computer Adapter = NOT_USED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
Paper/Shadow/Live runtime = NOT_USED / UNAUTHORIZED
E4/E5 production changes by E7 = NONE
contracts/ADR changes by E7 = NONE
Codex ticket = NONE
```

## Completion

E7 completes only `E7-20260824-030` after persisting E7-owned tests/evidence/status. Gate B remains blocked. No local execution, full Paper E2E, provider/private work, Gate C, PAPER, SHADOW, LIVE, or next implementation task is self-started.
