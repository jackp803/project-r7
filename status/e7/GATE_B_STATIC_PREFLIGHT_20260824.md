# Gate B / PAPER_READY Static Preflight — E7-20260824-026

## Authority / scope

- task_id: `E7-20260824-026`
- target branch: `agent/e7-gate-b-static-preflight-20260824`
- reviewed latest main: `6e166c4a3c8204617d920e6919c8d2b114917e0c`
- authoritative TASK blob: `57dc526ce67fdb1e1d2aa3a6c229df7bd6520e6b`
- contract baseline: `contracts-v0.1 / BASELINE`
- shared-contract blob: `7da3237d6274c5d27b8a6c11d59a23f9ef10fea6`
- Gate A execution evidence PR `#32` merge: `154b3164ce579672d601a23bbc17a485f3ebcbb1`
- Gate A execution branch head: `633261d58a4c86d7b6d760e23660b48c471bcc31`
- Gate A approved project source revision: `4da559bbbb569ea4f32246a40ef35f4bd8477a71`
- Gate A evidence review PR `#33` merge: `429e8961dc4c32996e12fa7258c734571ea7d823`
- Gate A review branch head: `e18f35b9513a4912390ed9920e98e9572be88cc7`
- accepted prerequisite: `GATE_A = PASS / RESEARCH-INTEGRATION ONLY`
- project executable verification for this task: `NOT_RUN / NOT REQUIRED FOR STATIC PREFLIGHT`

This is a static repository audit only. E7 did not execute unit tests, integration tests, E2E tests, safety tests, PaperBroker runtime, migrations, provider calls, backtests, or Local Runner actions.

## Terminal static-preflight disposition

```text
GATE_B_STATIC_PREFLIGHT = READY_FOR_BOUNDED_NEXT_TASKS
Gate A = PASS / RESEARCH-INTEGRATION ONLY
Gate B = BLOCKED / NOT YET PASS
Gate C = BLOCKED / UNCHANGED
Gate D = BLOCKED / UNCHANGED
PAPER = UNAUTHORIZED
SHADOW / LIVE = UNAUTHORIZED
provider/private API = NOT AUTHORIZED
```

`READY_FOR_BOUNDED_NEXT_TASKS` means the shared architecture/contracts are sufficiently explicit for PM to issue bounded implementation, E7 test-definition, and later local-verification tasks. It does **not** mean Gate B PASS and does not authorize Paper execution.

## Architecture / contract conclusion

No unresolved shared architecture or contract defect blocks planning the next Gate B tasks.

The current `contracts-v0.1` baseline already defines the required authority chain and shared semantics:

```text
Signal
  -> TradeIntent            (E2 -> E5; no sizing/risk/order authority)
  -> RiskDecision           (E5 veto/approval authority)
  -> ApprovedTradePlan      (only strategy-originated object E4 may execute)
  -> OrderRequest/Result
  -> Fill                   (actual quantity/price/time truth)
  -> Position / PositionAction
  -> TradeResult
```

The baseline additionally requires protective quantity to follow actual filled/open quantity and fail-closed behavior for unknown/stale state. The principal Gate B blockers are therefore missing Slice 3 implementation/orchestration, missing cross-module test materialization, and missing approved-local executable evidence—not an undefined shared semantic.

## Actual repository evidence inspected

### E2 TradeIntent producer

`src/strategy/trade_intent.py`

Static findings:

- produces provider-neutral `TradeIntent`;
- executable entry eligibility is explicit `entry-v0.1 / MARKET`;
- rejects provider/exchange-specific fields;
- rejects sizing, leverage, margin, risk-decision, broker-credential, and order authority fields;
- does not permit Strategy to manufacture E5/E4 authority.

### E5 risk / approval boundary

`src/risk/policy.py`, `src/risk/engine.py`

Static findings:

- explicit versioned policy includes margin/notional/leverage/cost caps, daily trade limit, open-position limit, max drawdown, consecutive-loss lock, intent age, hold/TTL, and margin mode;
- `RiskContext` requires safe/known market, account, position, and order state;
- stale/unknown/degraded market, unknown account/order/position, reconciliation/mismatch state, active kill switch, disabled exposure, same-symbol existing position, unavailable balance, limit violations, or missing sizing/protection facts fail closed;
- `evaluate_trade_intent()` emits `REJECT` when any reason exists;
- `build_approved_trade_plan()` requires an internally consistent `APPROVE` decision, exact intent/policy binding, safe state, explicit profiles, positive approved quantity, and protection bounds.

Relevant tests/handoff:

- `tests/risk/test_risk_engine.py`
- `tests/safety/test_e5_fail_closed.py`
- `status/E5_RISK_POSITION_HANDOFF.md`

The tests materially cover unknown state, kill switch, same-symbol-position blocking, consecutive-loss lock, missing stop, forged unsafe approval, and authority/profile boundaries. The current definitions do not provide equally explicit criterion-level coverage for every daily-trade/open-position/drawdown limit required by Gate B, so the aggregate limits criterion remains an evidence gap rather than static PASS.

### E4 execution authority / PaperBroker

`src/execution/gateway.py`, `src/execution/models.py`, `src/brokers/base.py`, `src/brokers/paper.py`

Static findings:

- `ExecutionGateway` accepts profiled `ApprovedTradePlan` and rejects raw `TradeIntent` at the execution authority boundary;
- entry translation is mechanical MARKET-only and preserves E5 quantity authority;
- Broker interface exposes submit/query/fills/reconcile/retry without inferring risk approval;
- `PaperBroker` is deterministic/in-memory and separates requested quantity from actual filled quantity;
- a fill cannot exceed remaining approved request quantity;
- ambiguous acknowledgement becomes reconciliation-required rather than blind retry;
- retry requires broker-issued reconciliation evidence;
- position exposure is derived from actual fills.

Relevant tests:

- `tests/execution/test_gateway.py`
- `tests/brokers/test_paper_broker.py`

Those are useful domain-level definitions, but they do not yet prove the full cross-module Paper lifecycle.

### E5 position lifecycle

`src/position/state_machine.py`, `tests/position/test_state_machine.py`

Static findings:

- first observed entry fill enters `OPEN_UNPROTECTED`;
- only verified protection moves to `OPEN_PROTECTED`;
- protection failure/loss enters `EMERGENCY`;
- unknown state enters `RECONCILIATION_REQUIRED`;
- unsafe/unknown states block new exposure.

This is lifecycle semantics only. It is not yet an integrated fill-to-protection operation: no complete current-main orchestration proves that protection quantity is derived from the actual fill, submitted through the authorized E5->E4 action path, and persisted/recovered.

### E6 persistence

`src/storage/README.md`, `status/E6_EARLY_SLICE2_HANDOFF.md`, `coordination/E6/STATUS.md`

Static findings:

- durable SQLite Registry/evidence authority exists for early research lifecycle;
- supported lifecycle remains explicitly capped at:

```text
DRAFT -> BACKTESTING -> REJECTED | CANDIDATE
```

- E6 explicitly states there is no `PAPER`, `READY_FOR_APPROVAL`, `APPROVED`, `SHADOW`, `LIVE`, `DEGRADED`, or `RETIRED` behavior in the current Slice 2 implementation;
- E6 explicitly states there is no Slice 3 execution/provider persistence.

Therefore current persistence/restart implementation is not sufficient for Gate B risk/position/order/trade runtime recovery/audit.

### E7 integration / safety definitions

Actual `tests/integration/` contains the Gate A research pipeline plus planning documentation, but no materialized full Paper integration test file.

`tests/integration/README.md` already specifies the intended Slice 3 requirements, including:

- TradeIntent -> E5 with no direct E4 bypass;
- REJECT -> no plan/order;
- APPROVE -> bounded plan;
- E4 approved-input enforcement;
- partial fill -> actual position/protection quantity;
- protection failure -> emergency;
- stale/unknown-state rejection;
- restart preservation;
- closed trade -> traceable TradeResult/persistence.

`tests/safety/README.md` likewise specifies cross-module safety groups, but the current executable safety materialization is primarily E5 domain fail-closed coverage rather than the complete Paper system-safety set.

## Criterion-by-criterion Gate B audit

Preflight classifications below are planning labels only. Canonical release evidence remains `PASS / FAIL / BLOCKED / NOT_RUN / NOT_APPLICABLE` in `status/RELEASE_GATES.md`.

| # | Gate B criterion | Preflight classification | Canonical state | Evidence / gap | Responsible owner(s) |
|---|---|---|---|---|---|
| 1 | Gate A | `ALREADY_SATISFIED_STATICALLY` | `PASS` | PR #32 local matrix + PR #33 evidence acceptance | E7 / accepted |
| 2 | TradeIntent -> E5 RiskDecision boundary implemented | `STATIC_READY_LOCAL_EXEC_REQUIRED` | `NOT_RUN` | E2 producer and E5 consumer are statically aligned; bounded local E2/E5 proof still required | E2 + E5; E7 integration evidence |
| 3 | E5 can reject valid strategy intents | `STATIC_READY_LOCAL_EXEC_REQUIRED` | `NOT_RUN` | fail-closed E5 source/test definitions exist; approved-local execution required | E5 |
| 4 | ApprovedTradePlan is the only E4 strategy-originated execution input | `STATIC_READY_LOCAL_EXEC_REQUIRED` | `NOT_RUN` | E4 gateway rejects raw TradeIntent and validates ApprovedTradePlan; local safety proof required | E4 + E7 |
| 5 | PaperBroker conforms to broker contract | `STATIC_READY_LOCAL_EXEC_REQUIRED` | `NOT_RUN` | `Broker` + deterministic `PaperBroker` + broker tests exist; local execution required | E4 |
| 6 | Partial fill semantics preserve actual quantity | `INTEGRATION_TEST_DEFINITION_GAP` | `NOT_RUN` | E4 primitive/domain test preserves requested vs actual filled quantity, but required E4/E5 cross-module Paper definition/evidence is not materialized | E7 test definition; E4 primitive already present |
| 7 | Required protection follows actual filled quantity | `IMPLEMENTATION_GAP` | `BLOCKED` | contract rule exists, but current-main fill -> E5 protection quantity/action -> E4 protection execution orchestration is absent | E5 then E4; E7 integration test after interface materializes |
| 8 | Protection failure triggers emergency path | `IMPLEMENTATION_GAP` | `BLOCKED` | E5 lifecycle `PROTECTION_FAILED -> EMERGENCY` exists, but no integrated protection operation/failure path establishes system behavior | E5 + E4; E7 test after implementation |
| 9 | Stale/unknown market state blocks exposure | `STATIC_READY_LOCAL_EXEC_REQUIRED` | `NOT_RUN` | E5 engine/safety definitions fail closed on stale/unknown/degraded market state | E5; E7 cross-module evidence later |
| 10 | Unknown order/position state blocks new exposure | `STATIC_READY_LOCAL_EXEC_REQUIRED` | `NOT_RUN` | E5 fail-closed definitions cover UNKNOWN, mismatch, reconciliation-required order/position states | E5; E7 cross-module evidence later |
| 11 | Drawdown/daily/position/kill-switch rules enforced | `EVIDENCE_GAP` | `BLOCKED` | policy/engine implements all four classes; explicit tests exist for kill switch and related locks, but complete criterion-level targeted definition/evidence for daily trade, open-position, and drawdown limits is not established | E5 |
| 12 | Restart/persistence preserves required state | `IMPLEMENTATION_GAP` | `BLOCKED` | E6 persistence is Registry/CANDIDATE research state only; no Paper risk/position/order/protection/trade runtime persistence/restart | E6, consuming E5/E4 runtime state semantics |
| 13 | Paper E2E closes to TradeResult and persists audit | `IMPLEMENTATION_GAP` + `INTEGRATION_TEST_DEFINITION_GAP` | `BLOCKED` | no complete current-main close path to canonical TradeResult + durable audit, and no materialized Paper E2E test | E4 + E5 + E6 implementation, then E7 test definition |
| 14 | GitHub CI/Actions not used for verification | `ALREADY_SATISFIED_STATICALLY` | `PASS` | policy is explicit; static GitHub content lookup found no `.github` directory on reviewed main. No local repo scan was run in this task | E7 policy enforcement |

## Minimal dependency-ordered Gate B plan

This plan identifies dependency order only. E7 does **not** assign these tasks; PM remains tasking authority.

### Phase 1 — domain implementation/evidence gaps before full Paper E2E

1. **E5 risk evidence completion**
   - materialize targeted test definitions for daily-trade cap, open-position cap, and drawdown lock so the aggregate Gate B risk-limit criterion is explicitly covered alongside kill-switch/consecutive-loss behavior.
2. **E5/E4 actual-fill protection path**
   - derive required protection quantity from actual filled/open quantity, not requested quantity;
   - preserve E5 authority for protective action/risk bounds;
   - E4 mechanically executes only the authorized protective action/order quantity.
3. **E5/E4 protection-failure emergency path**
   - connect protection operation failure/loss to the existing `EMERGENCY` lifecycle semantics and block further exposure.
4. **E6 Slice 3 persistence/restart**
   - persist/recover the minimum Paper runtime state required for order/fill/position/protection/risk/trade audit;
   - do not silently advance strategy lifecycle to PAPER as authority merely because persistence exists.
5. **E4/E5/E6 close-to-TradeResult path**
   - materialize canonical TradeResult creation from actual close/fill facts and durable audit persistence.

### Phase 2 — E7-owned integration/safety/E2E test definitions

Once the Phase 1 interfaces are stable, materialize bounded local-only definitions for:

- `TradeIntent -> RiskDecision -> ApprovedTradePlan -> ExecutionGateway -> PaperBroker` authority chain;
- REJECT producing no plan/order;
- partial entry fill -> actual exposure -> exact protection quantity;
- protection failure -> EMERGENCY -> no new exposure;
- stale/unknown market/order/position cross-module veto;
- restart/recovery preserving required Paper state;
- close -> canonical TradeResult -> durable audit/persistence;
- no Strategy/UI bypass to broker and no risk-bound loosening.

### Phase 3 — local-only suites that are already runnable once explicitly authorized

Current source already has bounded domain suites that can be executed in a Product Owner-approved local environment when PM explicitly tasks that verification:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

These commands were **not run** by E7-026. Passing them later would prove existing primitives only; it would not by itself close implementation/test-definition gaps for Gate B.

### Phase 4 — Gate B local integration/E2E/safety matrix

Only after required implementation and E7 test definitions exist should PM authorize a bounded local-only Gate B matrix. That later task must record exact revision/environment/commands/results and stop on failure. Gate B cannot become PASS from static review alone.

## Provider naming / scope drift

`status/RELEASE_GATES.md` still contains historical Pionex wording in Gate C. The active Product Owner decision is `docs/architecture/BROKER_TARGET_OKX_DECISION_20260821.md`, which makes OKX the V1 target and leaves `PaperBroker` provider-neutral.

Disposition for this task:

```text
DOCUMENTATION / GOVERNANCE DRIFT
NON-BLOCKING FOR GATE B PAPER-ONLY SEMANTICS
DEFERRED — DO NOT BROADEN INTO GATE C / PRIVATE PROVIDER WORK
```

No provider/private API implementation or credential work is authorized by this preflight.

## GitHub compute / security state

- GitHub Actions / CI / hosted runners / GitHub-triggered compute used for this task: `NO`
- project executable verification: `NOT_RUN / NOT REQUIRED FOR STATIC PREFLIGHT`
- static `.github` directory lookup on reviewed main: `NOT FOUND`
- local repository policy scan: `NOT_RUN`
- provider/private requests: `NOT_SENT`
- exchange credentials: `NOT_USED`
- PaperBroker runtime: `NOT_RUN`
- PAPER/SHADOW/LIVE: `UNAUTHORIZED`
- production/test/contract changes by E7-026: `NONE`
- Codex bug ticket: `NONE` — current gaps are missing implementation/test materialization, not a reproduced defect under an approved design.

## Completion

```text
GATE_B_STATIC_PREFLIGHT = READY_FOR_BOUNDED_NEXT_TASKS
```

There is enough static evidence for PM to issue bounded next tasks in dependency order. Gate B remains blocked/not-PASS until the missing Slice 3 implementation/test definitions exist and the required local-only executable evidence passes. E7 stops after persisting this preflight and does not start implementation, Gate B execution, provider work, PAPER, SHADOW, LIVE, or another task automatically.
