# E3 Slice 1 — Post-E1 Import Reconciliation

> Owner: E3 Backtest & Quantitative Validation Engineer  
> Contract baseline: `contracts-v0.1`  
> Task: `E3-20260822-003`  
> Branch: `agent/e3-backtest-validation`

## Reconciliation revisions

- latest `main` consumed: `47c7f3c24300b9ea21a8d50eba5be13884c88a7a`
- non-destructive reconciliation merge: `aee813855759cd63548d452a93de26fc208afa20`
- merge parents:
  - prior E3 HEAD: `4ad194520be0a9cc46d33b8ca9f72658158fccf4`
  - corrected current main: `47c7f3c24300b9ea21a8d50eba5be13884c88a7a`
- preserved prior E3 production/source correction: `54d40ae96e241f40367016e26b7bd5d03890e629`
- post-E1 reconciliation test revision: `185185fbb403b3622c96a218717d67a2eb41a684`

No force push, destructive rebase, branch recreation, shared-contract edit, or cross-agent production edit was used.

## E1 blocker disposition

The prior external E1 import/file-role blocker is cleared by corrected current-main source structure.

The supported E1 public surface now again exposes:

```python
from market_data import CONTRACT_SCHEMA_VERSION, Candle
```

and the corrected module identities are:

- `src/market_data/candle.py` blob `5605830b4da4fbe10e94cff72794a495db9ebf6e`
- `src/market_data/errors.py` blob `fb9cd216b83cd595304d23a5cec46fd9a2091894`
- `src/market_data/timeframes.py` blob `ac08d88dd327719b01babba098d78da0f34ab5bf`

E3 no longer needs the temporary canonical-mapping workaround in the cross-role integration test. The test definition now constructs actual E1 `Candle` instances and hashes `Candle.to_interchange_dict()` output for dataset identity.

## E3 production disposition

No E3 production source changed after the prior `54d40ae96e241f40367016e26b7bd5d03890e629` pin.

Preserved path:

```text
E1 canonical closed historical Candle
  -> E2 parse_strategy_definition
  -> actual E2 StrategyRuntime.evaluate
  -> E3 deterministic historical replay
  -> fees / slippage / funding assumptions
  -> replay metrics
  -> canonical contracts-v0.1 BacktestResult
```

`src/backtest/e2_runtime.py` remains a thin adapter. It does not implement indicators, DSL operators, strategy parameters, or strategy decisions.

## BacktestResult compatibility

Current E6 `validate_backtest_result_contract` still requires the same identity/reproducibility and core metric fields emitted by E3. E6 continues to permit `profit_factor = null`.

E3 preserves the locked edge behavior:

```text
aggregate losing PnL == 0
and at least one winning trade
-> profit_factor field exists
-> profit_factor == null
```

No ValidationDecision policy engine was added.

## Replay integrity preserved

- closed historical candles only;
- deterministic chronological ordering;
- E2 receives only information available at the evaluation boundary;
- Signal `evaluated_at` must equal the replay Candle-close boundary;
- LONG/SHORT entry fills no earlier than the next Candle open;
- opposite-direction exit fills no earlier than the next Candle open;
- final-bar signal cannot create a fill without a later bar;
- same-candle SL/TP ambiguity resolves conservatively to STOP;
- fees, adverse slippage, and funding assumptions remain explicit and versioned;
- required invalid/unsupported inputs fail closed;
- deterministic result identity retains strategy/runtime/dataset/cost/replay fingerprints.

The reconciled cross-role test definition also compares an earlier E2 boundary with and without materially altered later E1 Candles, verifying that later Candles are not allowed to change the earlier deterministic Signal.

## Scope exclusions

This task adds no:

- ValidationDecision policy;
- OOS;
- Walk Forward;
- Monte Carlo;
- optimization;
- regime classification;
- Registry lifecycle promotion;
- PAPER / SHADOW / LIVE behavior;
- broker/provider/API execution;
- shared contract change.

## Executable verification

Status: `NOT_RUN`.

No Product Owner-approved local environment was used in this ChatGPT/GitHub context. No import probe, test, replay, backtest, or metric verification was executed.

Exact local-only commands:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/backtest -p "test_*.py" -v
python tests/backtest/test_real_e2_research_skeleton.py -v
```

GitHub Actions, GitHub CI, hosted runners, GitHub-triggered self-hosted runners, and GitHub project compute remain forbidden and were not used.

## Review disposition

Static/source reconciliation is ready for PM/E7 exact-revision review. Executable evidence remains `NOT_RUN`; Gate A/B/C/D remain blocked. E3 stops here until a new task is issued.
