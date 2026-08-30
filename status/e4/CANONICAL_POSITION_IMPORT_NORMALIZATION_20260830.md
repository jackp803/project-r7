# E4 Canonical Position Import Normalization — 2026-08-30

## Authority / scope

```text
owner = E4 — Execution / Broker Integration Engineer
authority = Product Owner direct bounded remediation based on accepted E7 canonical-import audit
canonical runtime namespace = position.*
forbidden duplicate namespace = src.position.*
branch = agent/e4-canonical-position-import-normalization-20260830
baseline_main = 2fe9912429cad3eebebac1fa46f933b78f024b78
result = PARTIAL / IMPORT NORMALIZATION + REGRESSION DEFINITIONS COMPLETE / LOCAL EXECUTION NOT_RUN
```

This remediation addresses only the E4-owned cross-module Python module/dataclass identity defect identified by E7. It does not modify lifecycle, risk, FP-03/04/10/11 business semantics, provider behavior, financial/currentness authority, shared contracts, credentials, runtime launch, or capital policy.

## Root cause

Under the accepted execution environment:

```powershell
$env:PYTHONPATH='src'
```

`src/<package>` maps to canonical runtime package `<package>.*`. Therefore the Position domain canonical namespace is:

```text
position.*
```

The affected E4 production modules imported the same source package through:

```text
src.position.*
```

Python can then load `position.*` and `src.position.*` as distinct module objects. Classes/dataclasses defined from those module objects have distinct Python identity even when their source text is the same. Exact `isinstance` / type authority validation can therefore reject an otherwise valid canonical authority with `CURRENT_AUTHORITY_INVALID`.

The defect is an import identity defect, not a reason to accept both types or weaken validation.

## Files normalized

Only these E4 production modules were normalized:

```text
src/execution/protection_trigger.py
src/execution/external_close_evidence.py
src/execution/protection_registry_evidence.py
```

Mechanical replacements:

```text
from src.position.protection_trigger_validity ...
-> from position.protection_trigger_validity ...

from src.position.external_close_policy ...
-> from position.external_close_policy ...

from src.position.external_close_reinterpretation ...
-> from position.external_close_reinterpretation ...

from src.position.lifecycle_execution_binding ...
-> from position.lifecycle_execution_binding ...

from src.position.lifecycle_projection ...
-> from position.lifecycle_projection ...
```

No dual imports, aliasing, `sys.modules` patching, duck typing, `hasattr` acceptance, exception bypass, or broadened `isinstance` validation was introduced.

## Production diff proof

Compared with baseline `2fe9912429cad3eebebac1fa46f933b78f024b78`, the three production files contain only import-line replacements:

```text
protection_trigger.py              +1 / -1
external_close_evidence.py         +4 / -4
protection_registry_evidence.py    +2 / -2
```

No production logic line changed.

## Regression definition

Added E4-owned credential-free regression definition:

```text
tests/execution/test_canonical_position_import_identity.py
```

It locks the following boundaries:

1. all three affected E4 production files contain no `src.position` import;
2. FP-03 imported validator/error/currentness callables are the exact objects from `position.protection_trigger_validity`;
3. FP-04/FP-10 imported validators/errors are the exact objects from canonical `position.*` modules;
4. lifecycle projection and lifecycle execution-binding validators consumed by E4 are exact canonical objects;
5. FP-11 imported ownership validator/error objects are exact canonical `position.*` objects;
6. a genuine wrong E4 FP-11 input type remains rejected with `INPUT_TYPE_INVALID`, proving no authority-validation weakening;
7. canonical imports are used regardless of whether caller code imports canonical Position modules before or after E4—the E4 source contains only the single canonical namespace and therefore cannot intentionally select the duplicate namespace;
8. existing FP-03 behavior remains covered by `tests/execution/test_protection_trigger_consumer.py`;
9. existing FP-04/FP-10 behavior remains covered by `tests/execution/test_external_close_evidence.py`;
10. existing FP-11 behavior remains covered by `tests/execution/test_protection_registry_evidence.py`;
11. no provider, network, credential, runtime, or capital dependency is introduced.

If/when E7's canonical-import integration test exists on the integrated revision, it remains an E7-owned integration verification dependency and is not modified by this E4 task.

## Expected defect resolution

After normalization, the E4 consumer imports the same canonical Position modules used by producer/runtime code under `PYTHONPATH=src`:

```text
producer canonical class/callable
IS
E4 consumer canonical class/callable
```

Therefore the previously observed duplicate-module identity path to:

```text
CURRENT_AUTHORITY_INVALID
```

is expected to be resolved by import normalization alone.

This task does not claim that every possible `CURRENT_AUTHORITY_INVALID` is impossible; a genuinely wrong dataclass/type must still be rejected by the existing exact validation semantics.

## Local verification

No approved-local Windows checkout/execution surface is available in this ChatGPT session. GitHub Actions/CI/hosted/GitHub-triggered compute is forbidden and was not used.

Post-fix executable state:

```text
NOT_RUN / NOT_PASS
```

Required approved-local Windows commands:

```powershell
$env:PYTHONPATH='src'

python -m unittest discover -s tests/execution -p 'test_canonical_position_import_identity.py' -v
python -m unittest discover -s tests/execution -p 'test_protection_trigger_consumer.py' -v
python -m unittest discover -s tests/execution -p 'test_external_close_evidence.py' -v
python -m unittest discover -s tests/execution -p 'test_protection_registry_evidence.py' -v
python -m unittest discover -s tests/integration -p 'test_canonical_import_identity.py' -v
```

The final integration command is conditional on the E7-owned file existing in the integrated revision. Absence of that file does not authorize E4 to create or modify E7 integration ownership.

## Independent remediations

This branch does not include or alter:

```text
E6 FP-11 timestamp canonicalization remediation
E4 FP-02 reason/provenance aggregation remediation
```

Those remain independent branch/task results for PM/E7 integration sequencing.

## Safety boundary

```text
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order/protection provider actions = 0
process/runtime launch = 0
SHADOW/PAPER/LIVE = NOT_STARTED
capital exposure = NONE
GitHub compute = NOT_USED
```

## Handoff

Static import normalization and E4 regression definitions are complete. Executable PASS is not claimed because approved-local execution is unavailable in this session.

```text
NEXT = Return to PM/E7 for integration and approved-local requalification.
```
