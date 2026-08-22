# E6 Registry / Lifecycle Tests

These test definitions are now executable in an approved local checkout. They have **not** been run by this GPT session.

## Coverage

`test_strategy_inbox.py` defines checks for:

- exact `contracts-v0.1` StrategyDefinition envelope intake;
- default E2 compatibility status remains `NOT_RUN`;
- `DRAFT -> BACKTESTING` requires explicit local E2 PASS evidence metadata;
- static/declaration-only PASS is insufficient;
- same identity/same content idempotence;
- same identity/different content conflict rejection;
- unsupported schema rejection before Registry write;
- secret-like StrategyDefinition field rejection before persistence.

`test_validation_lifecycle.py` defines checks for:

- a legal-looking BacktestResult does not imply executable PASS;
- even `ValidationDecision.decision = PASS` cannot promote while verification remains `NOT_RUN`;
- `BACKTESTING -> CANDIDATE` requires local PASS evidence for both BacktestResult and ValidationDecision;
- exact strategy/content-hash binding;
- rejected strategies remain persisted;
- early service exposes no approval/LIVE/generic transition path.

Synthetic `LOCAL_EXECUTION PASS` fixtures exist only to exercise E6 gate logic. They are not evidence that E2, E3, Gate A, or Slice 1 actually passed.

## Local-only commands

From repository root in an integration checkout containing the E6 branch:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_*.py" -v
```

Current result:

```text
NOT_RUN
```

Reason: this ChatGPT GitHub environment is not the Product-Owner-approved local execution environment.

Never use GitHub Actions/CI/hosted runners to execute these tests.
