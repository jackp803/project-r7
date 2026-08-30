# E4 Change Request — Canonical `position` Import Identity

## Classification

```text
OWNER_REMEDIATION_REQUIRED
owner = E4 Execution
scope = mechanical import-namespace normalization only
architecture = E7 canonical import rule
```

## Trigger

Approved-local credential-free qualification on exact revision:

```text
bacb5205ac9b895bb968459f88f148323bcc5da6
```

reproduced deterministic cross-module failures caused by loading the same Position package under both:

```text
position
src.position
```

Equivalent dataclasses/classes then have different Python identities and strict authority validation can reject a valid object as:

```text
CURRENT_AUTHORITY_INVALID
```

E7 architecture decision:

```text
docs/architecture/CANONICAL_PYTHON_IMPORT_NAMESPACE.md
```

Under the current approved-local invocation model:

```powershell
$env:PYTHONPATH = 'src'
```

canonical source-root imports are top-level package imports such as `position.*`, not `src.position.*`.

## Exact E4-owned production paths

Static audit identified these current E4-owned production imports:

1. `src/execution/protection_trigger.py`
   - current: `from src.position.protection_trigger_validity import ...`
   - required: `from position.protection_trigger_validity import ...`

2. `src/execution/external_close_evidence.py`
   - current: `from src.position.external_close_policy import ...`
   - current: `from src.position.external_close_reinterpretation import ...`
   - current: `from src.position.lifecycle_execution_binding import ...`
   - current: `from src.position.lifecycle_projection import ...`
   - required: same modules through `position.*`

3. `src/execution/protection_registry_evidence.py`
   - current: `from src.position.external_close_policy import ...`
   - current: `from src.position.external_close_reinterpretation import ...`
   - required: same modules through `position.*`

## Required implementation

Make only the mechanical namespace change required to load these dependencies through the canonical `position.*` package.

Do not change:

- validation logic;
- accepted authority types;
- FP-03/04/10/11 contract semantics;
- lifecycle behavior;
- provider capability semantics;
- risk policy;
- error handling except where import identity naturally removes the false `CURRENT_AUTHORITY_INVALID`;
- provider/auth/config/runtime behavior.

## Explicitly forbidden shortcuts

Do not implement:

```text
isinstance(x, (position.Type, src.position.Type))
```

Do not add:

- dual accepted-type lists;
- duck typing / `hasattr` authority admission;
- try-both-import fallback;
- `sys.modules` alias/monkey patching;
- catch-and-continue for `CURRENT_AUTHORITY_INVALID`;
- weakened E5/E6 validation.

## Required regression

After E4 normalization is merged into the integrated candidate, approved-local credential-free regression must include:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests/integration -p 'test_canonical_import_identity.py' -v
python -m unittest discover -s tests/integration -p 'test_*.py' -v
python -m unittest discover -s tests/e2e -p 'test_*.py' -v
python -m unittest discover -s tests/safety -p 'test_*.py' -v
```

Run the affected storage module too if the same identity failure is present in the current integrated candidate.

Success must show:

```text
no production import of src.position
no src.position module tree created by canonical E4 consumers
valid current authority accepted
truly wrong authority type still rejected as CURRENT_AUTHORITY_INVALID
provider requests = 0
credentials = NONE
mutation/order/runtime/capital = 0/NONE
GitHub compute = NOT_USED
```

## Independent bug boundary

This request does not modify or resolve:

- E6 FP-11 timestamp normalization bug;
- E4 FP-02 reason aggregation bug.

Those remain separate owner remediations and must converge before PM selects the next integrated qualification candidate.
