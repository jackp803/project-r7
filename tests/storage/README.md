# E6 Persistence / Migration Tests

These test definitions are executable in an approved local checkout. They have **not** been run by this GPT session.

## Coverage

`test_registry_persistence.py` defines checks for:

- migration idempotence;
- immutable StrategyVersion content at the database layer;
- append-only lifecycle transition history;
- restart persistence of current lifecycle state and revision;
- migration-backed Registry reconstruction.

Additional Registry tests cover identity conflicts, evidence binding, lifecycle gates, and rejection retention.

## Local-only command

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

Combined E6 local command:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

Current result:

```text
NOT_RUN
```

Reason: this ChatGPT GitHub environment is not the Product-Owner-approved local execution environment.

Never use GitHub Actions/CI/hosted runners for migration, persistence, restart, Registry, or lifecycle verification.
