# E2 TradeIntent Entry Profile — entry-v0.1

## Scope

Task `E2-20260821-002` adds the provider-neutral E2 TradeIntent production boundary required by `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md` and ADR-0002.

This is additive to the existing Slice 1 Strategy Runtime. It does not change StrategyDefinition parsing, DSL `0.1`, Runtime `0.1.0`, Signal semantics, Candle semantics, or the Issue #5 `contracts-v0.1` compatibility correction.

## Version namespaces

The following versions are independent:

- shared parent schema: `contracts-v0.1`
- executable entry profile: `entry-v0.1`
- E2 DSL: `0.1`
- E2 Runtime: `0.1.0`

Produced TradeIntent objects continue to carry:

```text
schema_version = contracts-v0.1
```

An executable-profile-eligible intent additionally declares:

```text
entry_profile_version = entry-v0.1
entry_order_type      = MARKET
```

No other executable entry order type is supported by this revision.

## API

With `PYTHONPATH=src`:

```python
from strategy import build_trade_intent

intent = build_trade_intent(
    signal,
    entry_profile_version="entry-v0.1",
    entry_order_type="MARKET",
)
```

`build_trade_intent()` consumes an E2 `Signal` mapping at shared schema `contracts-v0.1`. The Signal must be actionable (`LONG` or `SHORT`). It deterministically derives `intent_id` from the complete serialized intent material excluding the identifier itself.

If `generated_at` is omitted, it deterministically uses the Signal `evaluated_at` value rather than reading the wall clock.

## Executable profile rules

Fail closed when:

- `entry_profile_version` is unknown;
- `entry_order_type` is supplied without an explicit profile;
- `entry-v0.1` omits `entry_order_type`;
- the order type is anything other than exact shared enum `MARKET`;
- LIMIT/stop/trigger/TIF/post-only/trailing executable fields are requested;
- provider/exchange-specific semantics are requested;
- quantity, leverage, margin, broker credentials, risk approval, or direct order authority is requested.

Provider spellings such as OKX `market`, `ordType`, `sz`, instrument IDs, or exchange-specific fields do not belong in E2 TradeIntent.

## Legacy/advisory fields

The parent `contracts-v0.1` TradeIntent fields remain permitted as advisory strategy context:

- `entry_style`
- `entry_reference_price`
- `strategy_stop_level`
- `strategy_target_level`
- `max_hold_seconds`

They do not create executable semantics.

For example:

```python
legacy = build_trade_intent(signal, entry_style="MARKET")
```

produces a baseline historical/advisory TradeIntent with `entry_style`, but does **not** add `entry_profile_version` or `entry_order_type` and therefore is not automatically execution-eligible under `entry-v0.1`.

Likewise, `entry_reference_price` is preserved as advisory/audit context only. It is never copied into `limit_price`, `stop_price`, `trigger_price`, or another executable order price.

## Authority boundary

E2 produces candidate TradeIntent only.

E2 does not add or approve:

- quantity;
- leverage;
- margin mode;
- risk decision or approval;
- provider contract units;
- provider instrument IDs;
- broker credentials;
- OrderRequest fields;
- OKX/Pionex API behavior.

E5 remains the risk authority. E4 remains the execution/provider translation authority.

## Strategy Runtime preservation

`src/strategy/runtime.py` is unchanged by this task. The new entry-profile code lives in `src/strategy/trade_intent.py` and consumes the existing Signal output after strategy evaluation.

The local test suite retains the existing Slice 1 deterministic tests and adds a regression proving the same StrategyDefinition + exact Candle boundary + Runtime version still produces the same Signal after the TradeIntent module is introduced.

## Local verification

Executable verification is local-only. In this GPT repository session it remains `NOT_RUN`.

From repository root on Windows PowerShell:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests -p "test_*.py" -v
```

Focused E2 command:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/strategy -p "test_*.py" -v
```

No GitHub Actions, CI, hosted runner, or GitHub-triggered project execution is permitted.
