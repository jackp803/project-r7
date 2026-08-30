# Canonical Python Runtime Import Namespace

## Decision

For project-r7's current source layout and approved-local execution model, production packages under `src/<package>/` have exactly one canonical runtime import namespace:

```text
<package>[.<module>]
```

Examples:

```python
from position import CurrentProtectionRegistryAuthority
from position.protection_registry_policy import interpret_protection_registry_evidence
from execution.external_close_evidence import build_external_manual_close_convergence_evidence
from brokers.okx_close_sizing import evaluate_okx_close_residual_sizing
from integration.runtime_preflight import evaluate_runtime_preflight
from storage.protection_registry_currentness import open_protection_registry_currentness_store
```

The following form is non-canonical and forbidden for runtime/test imports when the same checkout is executed with `PYTHONPATH=src`:

```python
from src.position import ...
from src.position.protection_registry_policy import ...
from src.execution import ...
from src.brokers import ...
from src.integration import ...
```

This decision is an import-identity rule only. It does not change any shared contract schema/version, financial authority, lifecycle semantics, provider capability, runtime authorization, or release gate.

## Repository basis

The repository has a source-root layout:

```text
project-r7/
  src/
    brokers/
    execution/
    integration/
    market_data/
    position/
    risk/
    storage/
    strategy/
    ...
```

There is no repository-root Python package configuration making `src` the canonical application package. Approved-local qualification commands set:

```powershell
$env:PYTHONPATH = 'src'
```

Under that execution model, `src` itself is the import search root and each child directory is a top-level package. Therefore `src/position/protection_registry_policy.py` is canonically loaded as:

```text
position.protection_registry_policy
```

not as:

```text
src.position.protection_registry_policy
```

Because the repository root is also commonly present on `sys.path` when Python is launched from the repository root, Python can resolve both names if callers mix them. Those names are distinct keys in `sys.modules`; Python then creates distinct module objects and distinct dataclass/class objects from the same source file.

## Safety invariant

For any source file under `src/<package>/`, one logical runtime type must map to one Python class identity:

```text
one source module
= one canonical module key
= one class/dataclass identity
```

In particular:

```text
position.CurrentProtectionRegistryAuthority
is
position.protection_registry_policy.CurrentProtectionRegistryAuthority
```

must hold.

The same source file must never be loaded simultaneously as both:

```text
position.*
src.position.*
```

No compatibility shim may accept both class identities. Financial/currentness validation must remain strict.

## Prohibited remediation patterns

The duplicate-module defect must not be hidden by:

- `isinstance(x, (position.Type, src.position.Type))`;
- duplicate accepted-type lists;
- duck typing / `hasattr` in place of authoritative typed validation;
- importing both namespaces and trying either one;
- post-load `sys.modules` aliasing or monkey patching;
- catching `CURRENT_AUTHORITY_INVALID` and continuing;
- weakening E5/E6 authority/currentness validation.

The source of the duplicate load must be removed.

## Current deterministic defect

Approved-local credential-free qualification of exact revision:

```text
bacb5205ac9b895bb968459f88f148323bcc5da6
```

reproduced cross-module failures in which the same position package was present as both `position` and `src.position`. Equivalent dataclasses therefore had different Python class identities. A valid authority created through the canonical `position` namespace could be rejected by a consumer loaded through `src.position` with:

```text
CURRENT_AUTHORITY_INVALID
```

This is a module-identity defect, not evidence that the exact-type validator is too strict.

## Observed non-canonical production imports

Static audit identified E4-owned production imports that load `src.position.*`:

- `src/execution/protection_trigger.py`
- `src/execution/external_close_evidence.py`
- `src/execution/protection_registry_evidence.py`

These must be mechanically normalized by E4 to `position.*` while preserving behavior and validation.

## Observed E7 test namespace drift

Recent E7 P0 integration/safety/E2E definitions also use `src.<package>` imports, including `src.position`, `src.execution`, `src.brokers`, and `src.integration`. Those imports are non-canonical under `PYTHONPATH=src` and must be normalized to the top-level package names.

This shows the pattern is broader than one symbol: `position` is the confirmed class-identity failure, while the architectural rule applies to every package rooted under `src/`.

## Packaging and invocation rule

Until project-r7 introduces and explicitly approves a different packaging model, local test/runtime entrypoints must use:

```powershell
$env:PYTHONPATH = 'src'
python -m unittest ...
```

and source/test code must import source-root packages without the `src.` prefix.

A future packaging migration may change this rule only through an E7 architecture decision that updates all producers/consumers and qualification entrypoints atomically. Merely making `src.*` importable is not permission to use it as a parallel namespace.

## Regression requirement

E7 integration regression definitions must prove at minimum:

1. canonical `position` imports produce one module/class identity;
2. no production source imports `src.position`;
3. canonical E7 integration fixtures do not import `src.position`;
4. valid `CurrentProtectionRegistryAuthority` is accepted by the canonical consumer;
5. a truly wrong authority type still yields `CURRENT_AUTHORITY_INVALID`;
6. persistence/restart fixtures use the same canonical authority class;
7. importing E4 cross-module consumers does not create a second `src.position` module tree;
8. no provider/network/credential/trading-runtime dependency is required.

## Ownership

- E7 owns this architecture/import-identity rule and cross-module regression definitions.
- E4 owns mechanical normalization of non-canonical imports in E4 production modules.
- E5/E6 retain their strict authority/currentness validation semantics; no validator weakening is authorized.
- PM must wait for E4/E6/import remediations to converge before selecting a new integrated qualification candidate.
