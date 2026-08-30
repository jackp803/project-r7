# E7 Python Canonical Import Identity Remediation — 2026-08-30

## Result

```text
RESULT = PARTIAL
CANONICAL_IMPORT_NAMESPACE = <src child package>.*
example = position.*
forbidden parallel namespace = src.position.*
```

The architecture/root cause is established and E7 regression definitions are persisted. The production defect cannot be declared resolved because E4-owned production modules still contain non-canonical `src.position.*` imports and no approved-local remediation regression has been executed for this branch.

## Qualification evidence received

Exact reproduced qualification revision:

```text
bacb5205ac9b895bb968459f88f148323bcc5da6
```

Observed qualification totals supplied by Product Owner:

```text
Phase 1: 11/16 commands PASS; 212 passed; 21 failed; 8 errors
Phase 2: 10/14 suites PASS; 828 passed; 21 failed; 8 errors; 0 skipped
failure concentration: storage / integration / e2e / safety
```

Confirmed deterministic root cause supplied and statically corroborated by repository imports:

```text
position
vs
src.position
```

The same source files can be loaded under different `sys.modules` keys. Dataclass/class definitions are then recreated as distinct Python objects. Strict exact-type validation correctly treats the foreign class identity as a different type and can emit `CURRENT_AUTHORITY_INVALID`.

## Architecture audit

### Production layout

Repository source layout is source-root based:

```text
src/backtest
src/brokers
src/execution
src/indicators
src/integration
src/market_data
src/position
src/risk
src/storage
src/strategy
...
```

No root `pyproject.toml` or `setup.py` was found during this bounded audit. The `src` directory itself has no `__init__.py` in the current source tree.

### Approved-local invocation model

Qualification manifest and current project practice use:

```powershell
$env:PYTHONPATH='src'
```

Therefore `src` is the import search root and production packages are canonically imported as:

```text
position.*
execution.*
brokers.*
integration.*
storage.*
...
```

not `src.<package>.*`.

### Position package internal convention

`src/position/__init__.py` uses package-relative imports (`from .module import ...`), which preserves one package identity when entered through canonical `position`.

### Confirmed E4 production namespace drift

Non-canonical `src.position.*` imports were identified in:

- `src/execution/protection_trigger.py`
- `src/execution/external_close_evidence.py`
- `src/execution/protection_registry_evidence.py`

These are E4-owned production paths and require owner remediation.

### E7 test namespace drift

Recent E7 P0 tests also demonstrate the broader parallel-namespace pattern:

- `tests/integration/test_p0_integrated_failure_prevention.py` uses `src.brokers`, `src.execution`, `src.position`;
- `tests/integration/test_p0_fp02_fp16_composition.py` uses `src.brokers`, `src.integration`;
- `tests/integration/test_runtime_preflight.py` uses `src.integration`;
- `tests/safety/test_p0_integrated_fail_closed.py` uses `src.brokers`, `src.execution`, `src.integration`, `src.position`;
- `tests/e2e/test_p0_reconciliation_restart_e2e.py` uses `src.execution`.

Thus the architectural pattern is not unique to `position`. `position` is the confirmed class-identity failure because authority dataclasses/classes cross module boundaries there. The canonical rule therefore applies to all packages rooted under `src/`.

## Durable architecture decision

Created:

```text
docs/architecture/CANONICAL_PYTHON_IMPORT_NAMESPACE.md
```

Rule:

```text
one source module
= one canonical top-level package name under PYTHONPATH=src
= one Python module object
= one class/dataclass identity
```

No shared contract version changed.

## E7 regression definition

Created:

```text
tests/integration/test_canonical_import_identity.py
```

Coverage defined:

1. canonical `position` package exposes the same `CurrentProtectionRegistryAuthority` class object as `position.protection_registry_policy`;
2. production source contains no `src.position` imports;
3. importing E4 consumers must not create any `src.position` module tree;
4. valid canonical current authority must not be rejected as `CURRENT_AUTHORITY_INVALID`;
5. truly wrong authority type must still be rejected with `CURRENT_AUTHORITY_INVALID`;
6. E6 restart/persistence fixture uses the same canonical E5 authority class;
7. source-root entrypoint expectation matches `PYTHONPATH=src` layout;
8. regression definition has no provider/network/process/trading-runtime dependency.

This test intentionally preserves strict financial/currentness type validation and does not accept dual identities.

## Owner remediation

Created bounded E4 request:

```text
status/e7/E4_CANONICAL_POSITION_IMPORT_REMEDIATION_REQUEST_20260830.md
```

Required E4 change is mechanical import normalization only. No E4 provider semantics, E5 lifecycle/risk policy, E6 currentness validation, or shared contract semantics are authorized to change.

## Independent bug boundary

Not addressed in this remediation:

```text
E6 FP-11 timestamp normalization bug
E4 FP-02 reason aggregation bug
```

They remain independent and must converge separately.

## Local regression state

No approved-local Windows execution channel is available inside this chat execution context for this remediation branch. Project tests were therefore not run here and no PASS is inferred from static inspection.

Required affected regression commands after E4 canonical import normalization is available in the integrated candidate:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests/integration -p 'test_canonical_import_identity.py' -v
python -m unittest discover -s tests/integration -p 'test_*.py' -v
python -m unittest discover -s tests/e2e -p 'test_*.py' -v
python -m unittest discover -s tests/safety -p 'test_*.py' -v
```

If the current integrated storage failures still include this identity root cause, additionally run the exact focused storage module(s) from the failed qualification transcript.

Current remediation-branch executable state:

```text
local regression = NOT_RUN / NOT_PASS
CURRENT_AUTHORITY_INVALID = STILL_REPRODUCIBLE UNTIL OWNER IMPORT NORMALIZATION + LOCAL REGRESSION
```

`NOT_RUN` is not PASS.

## Safety

```text
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
orders = 0
protection actions = 0
runtime trading process = NOT_STARTED
SHADOW/PAPER/LIVE = NOT_STARTED
capital exposure = NONE
GitHub compute = NOT_USED
```

## Next

Return to PM after:

1. E4 canonical `position.*` import remediation is merged;
2. E7-owned P0 test imports are normalized to canonical top-level package names;
3. E6 FP-11 timestamp normalization remediation converges;
4. E4 FP-02 reason aggregation remediation converges;
5. approved-local focused import-identity/integration/E2E/safety regression passes.

Do not self-start final integrated qualification from this task.
