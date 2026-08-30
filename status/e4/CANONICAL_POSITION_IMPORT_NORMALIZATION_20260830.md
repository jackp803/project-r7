# E4 Canonical Position Import Convergence — 2026-08-30

## Authority / scope

```text
task_id = E4-20260830-037
owner = E4 — Execution / Broker Integration Engineer
branch = agent/e4-canonical-position-import-convergence-20260830
baseline_main = b783fd68d057705fd1c08d063fad26809b066d72
canonical runtime namespace = position.*
forbidden duplicate namespace = src.position.*
result = PARTIAL / STATIC CONVERGENCE COMPLETE / LOCAL EXECUTION NOT_RUN / NOT_PASS
```

This task performs only the accepted E4 canonical Position import convergence on latest `main`. It is not new architecture or feature work.

Latest `main` ancestry was verified to include:

```text
PR #126 merge = e5732b9dbe78e33fff6a9301969ee4240ae62666
PR #127 merge = 4ea6f4a2016f80af084ef7c7a2e50ad20177b51b
PR #128 merge = 970e5a5ebe2402d651bc74bea3bc08c489a6ab4e
current task baseline = b783fd68d057705fd1c08d063fad26809b066d72
```

The old accepted-but-unmerged import branch/PR was used only as the source of the already accepted mechanical import blobs and regression definition:

```text
old branch = agent/e4-canonical-position-import-normalization-20260830
old head = 3ef910c5bb98cf15a55d341a031ea4cca9f8a133
PR = #129 / CLOSED / NOT_MERGED
```

## Root cause and accepted fix

Under:

```powershell
$env:PYTHONPATH='src'
```

canonical package identity is `<package>.*`; therefore Position runtime identity is `position.*`. Importing the same source package as `src.position.*` can create duplicate Python module/class identities and cause otherwise valid strict authority checks to fail.

The accepted fix is mechanical namespace normalization only. No dual imports, duck typing, `hasattr` acceptance, `sys.modules` aliasing, exception bypass, or broader type acceptance is introduced.

## Production convergence

Only these E4-owned production files changed:

```text
src/execution/protection_trigger.py
src/execution/external_close_evidence.py
src/execution/protection_registry_evidence.py
```

Only equivalent import spellings changed:

```text
src.position.* -> position.*
```

PR #129 per-file patches were rechecked before convergence and showed only:

```text
protection_trigger.py              +1 / -1
external_close_evidence.py         +4 / -4
protection_registry_evidence.py    +2 / -2
```

No function, validator, type check, reason code, lifecycle semantic, provider semantic, authority validation, or financial behavior changed.

## Regression definition

Carried forward unchanged from the accepted old E4 branch:

```text
tests/execution/test_canonical_position_import_identity.py
```

The regression definition requires:

- no `src.position.*` imports in the three E4 production targets;
- exact callable/class identity with canonical `position.*` producer/consumer modules;
- strict FP-11 wrong-input-type rejection remains `INPUT_TYPE_INVALID`;
- no authority validation weakening.

E7-owned `tests/integration/test_canonical_import_identity.py` is not modified.

## FP-02 reason aggregation preserved

The merged PR #128 remediation is intentionally untouched. Blob identity against latest `main` was checked for all three protected paths:

```text
src/brokers/okx_action_capability.py
sha = ff499291bced02adc5a9bc8739131f22de6253ed

tests/brokers/test_okx_action_capability.py
sha = b3ff572b66c1f84b9c5efa710c2f393a4f0b4d57

status/e4/FP02_REASON_AGGREGATION_REMEDIATION_20260830.md
sha = e7b654ae2a735b0d82dba500e03c327eba98b28d
```

The convergence branch carries the exact same blobs. FP-02 state precedence, ordered/deduplicated reason aggregation, E4-035 provenance hardening, READ_ONLY default-deny behavior, and unresolved PROTECTION_STOP/POSITION_EXIT/EMERGENCY_EXIT semantics remain merged and unchanged.

## Verification

No approved-local Windows execution surface is available in this ChatGPT session. GitHub Actions/CI/hosted/GitHub-triggered compute was not used.

```text
executable verification = NOT_RUN / NOT_PASS
```

Required approved-local commands:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests/execution -p 'test_canonical_position_import_identity.py' -v
python -m unittest discover -s tests/execution -p 'test_protection_trigger_consumer.py' -v
python -m unittest discover -s tests/execution -p 'test_external_close_evidence.py' -v
python -m unittest discover -s tests/execution -p 'test_protection_registry_evidence.py' -v
python -m unittest discover -s tests/integration -p 'test_canonical_import_identity.py' -v
```

`NOT_RUN` is not PASS.

## Safety boundary

```text
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order/protection actions = 0
process/runtime launch = 0
SHADOW/PAPER/LIVE = NOT_STARTED / NOT_AUTHORIZED
capital exposure = NONE
GitHub compute = NOT_USED
```

## Handoff

Static convergence is complete on the latest-main ancestry. Executable qualification remains pending approved-local execution.

```text
NEXT = Return to PM/E7 for approved-local requalification/integration handling only.
```
