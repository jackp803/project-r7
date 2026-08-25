# E4 Current Task

- task_id: `E4-20260825-015`
- issued_at: `2026-08-25T09:10:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-gate-b-test-remediation-20260825`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate B chain through PR #69 merge `a044ff6e382b4fd93308f73169f0952705f922f4`, E7 diagnostic evidence `status/e7/GATE_B_BOUNDED_DIAGNOSTIC_RERUN_20260825.md`

## Objective

Remediate only the two E4-owned test-definition defects proven by E7-20260825-061. Preserve production execution semantics.

### Cause A — OKX Demo adapter-issued materialization provenance

Affected E4 tests are the four failing/error normal submit/reconciliation cases in `tests/brokers/test_okx_demo_adapter.py`.

The accepted production guard in `src/brokers/okx_demo.py` requires submit materialization to be the exact instance issued by that adapter through `OKXDemoAdapter.prepare_entry(...)`. The stale fixtures currently create materialization through the free `materialize_demo_market_order(...)` helper before constructing the adapter.

Required remediation:

- valid normal submit/reconciliation fixtures must obtain materialization through the same adapter's `prepare_entry(...)` path;
- preserve separate forged/mutated/replayed/cross-adapter rejection coverage;
- do not weaken, bypass, or remove `_authorize_submit(...)`, adapter-issued provenance, idempotency, reconciliation, Demo-only, exposure, or credential safety guards.

### Cause B — Decimal-equivalent zero assertion

Affected E4 test: `tests/brokers/test_paper_broker_protection_stop_flat_truth.py` explicit POSITION_EXIT / EMERGENCY_EXIT flat observation assertion.

Shared contract requires base-10 Decimal strings and numerical flatness, not lexical collapse of every zero to exactly `"0"`. E4 explicit close currently preserves Decimal scale (for example `"0.0000"`) while PROTECTION_STOP has its own exact serialized zero path.

Required remediation:

- replace the stale exact-string zero assertion only where the contract permits scale-preserving Decimal zero;
- assert valid Decimal numerical zero while preserving all existing lineage, order-role, fill, health, reconciliation, quantity-conservation, and broker-fact assertions;
- do not change PaperBroker production serialization or position-reduction semantics in this task.

## Writable scope

Only:

- `tests/brokers/test_okx_demo_adapter.py`;
- `tests/brokers/test_paper_broker_protection_stop_flat_truth.py`;
- E4-owned test helpers in `tests/brokers/**` only if strictly necessary for these proven defects;
- `coordination/E4/STATUS.md`.

Forbidden:

- `src/**` production changes;
- contracts/ADR changes;
- E1/E2/E3/E5/E6/E7 tests or production;
- provider/private network calls or credentials;
- GitHub Actions/CI/hosted runners/GitHub-triggered compute;
- PAPER/SHADOW/LIVE/Gate C;
- unrelated test cleanup.

## Executable verification

This remediation assignment does not grant new project execution authority.

Record:

```text
local_verification = NOT_RUN
```

and provide the exact later approved-local command:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

Do not treat E7-061 diagnostic execution as post-remediation PASS evidence.

## Acceptance

### DONE

- only the proven stale E4 test fixtures/assertions are corrected;
- production provenance/fail-closed and PaperBroker semantics remain unchanged;
- forged/cross materialization rejection remains explicitly covered;
- Decimal-equivalent zero is checked numerically where contract-appropriate;
- no scope expansion;
- executable verification remains `NOT_RUN` unless separately authorized;
- commit/push to target branch and update terminal E4 STATUS.

### BLOCKED

If the bounded test-only remediation cannot be made without changing production semantics or a new shared contract rule, stop with exact evidence; do not broaden scope.

## Completion

Execute only this TASK, update `coordination/E4/STATUS.md`, commit/push to the target branch, and stop. Do not start another task.