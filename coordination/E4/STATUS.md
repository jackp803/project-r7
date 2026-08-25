# E4 Status

- task_id: `E4-20260825-015`
- agent: `E4`
- state: `DONE`
- branch: `agent/e4-gate-b-test-remediation-20260825`
- baseline_main_sha: `10d3eaedc0606c7e8c484376e7d58a27cf951899`
- head_sha: `9e6c3d36e8c3ef25ead2886bbe73e884d3b6176c` (test-remediation HEAD immediately before this terminal STATUS-only commit)
- summary: `Remediated only the two E4-owned stale test-definition defects proven by E7-20260825-061. Valid OKX Demo normal submit/reconciliation fixtures now obtain the exact materialization from the same OKXDemoAdapter.prepare_entry(...) instance that later submits/reconciles it; adapter-issued provenance and cross-adapter fail-closed coverage remain explicit. The explicit EMERGENCY_EXIT flat-position compatibility assertion now validates a serialized Decimal string whose numeric value is zero rather than requiring lexical "0", while PROTECTION_STOP exact-zero assertions remain unchanged. No src/** production semantics were modified.`
- files_changed: `tests/brokers/test_okx_demo_adapter.py; tests/brokers/test_paper_broker_protection_stop_flat_truth.py; coordination/E4/STATUS.md`
- contracts_changed: `NO`
- production_changed: `NO`
- local_verification: `NOT_RUN`
- not_run: `This assignment grants no new project execution authority. Required later approved-local Windows PowerShell command from repository root: $env:PYTHONPATH="src" ; python -m unittest discover -s tests/brokers -p "test_*.py" -v`
- blockers: `NONE for bounded test-definition remediation. E7-20260825-061 is diagnostic pre-remediation evidence only and is not post-remediation PASS evidence.`
- diagnostic_reference: `status/e7/GATE_B_BOUNDED_DIAGNOSTIC_RERUN_20260825.md`

## Wake / authority verification

Wake message task ID:

```text
E4-20260825-015
```

Latest `main:coordination/E4/TASK.md` matched exactly before any work began.

Authoritative files read first:

- `README.md`
- `agents/README.md`
- `agents/E4_EXECUTION.md`
- `coordination/E4/TASK.md`

Only E4's TASK was read; no other Agent TASK was read or executed.

## Baseline / scope

At task start:

```text
main = 10d3eaedc0606c7e8c484376e7d58a27cf951899
target branch did not yet exist
```

The target branch was created from that exact `main` revision. No rebase, force update, GitHub Actions, CI, hosted runner, GitHub-triggered compute, Computer Adapter, provider/private API, or credentials were used.

Writable scope remained test-only plus this worker-owned STATUS. No `src/**`, `contracts/**`, ADR, E5/E6/E7 code/tests, or release authority was changed.

## Cause A remediation — OKX Demo materialization provenance

E7-20260825-061 proved four normal submit/reconciliation tests were using free `materialize_demo_market_order(...)` output that the submitting adapter had never issued.

Added a test helper that builds the same request/metadata/sizing/prerequisite fixtures but obtains the materialization via:

```text
same OKXDemoAdapter.prepare_entry(...)
-> same adapter submit/reconciliation path
```

Updated the affected normal cases:

- success acknowledgement remains `PENDING`, not Fill truth;
- timeout remains `RECONCILIATION_REQUIRED` and repeat submit remains idempotent/no second transport call;
- reconciliation still queries truth and never authorizes provider retry;
- forged/replayed reconciliation evidence remains rejected.

Cross-adapter provenance rejection is now explicit: a materialization legitimately issued by a second adapter is rejected by the first adapter's `submit_entry(...)` with `OKXProtocolError` before transport. The production `_authorize_submit(...)` provenance/integrity guard was not weakened or bypassed.

Free `materialize_demo_market_order(...)` remains used only by tests that exercise materialization itself and provider-neutral parsing, not as valid same-adapter submit authority.

## Cause B remediation — Decimal-equivalent zero

Only the stale explicit EMERGENCY_EXIT compatibility assertion was changed.

Previous over-constrained assertion:

```text
flat["actual_quantity"] == "0"
```

Current contract-appropriate assertion:

```text
actual_quantity is a serialized string
Decimal(actual_quantity) == Decimal("0")
```

This accepts scale-preserving explicit-close output such as `"0.0000"` while still requiring valid numerical flatness. Existing PROTECTION_STOP-specific exact serialized `"0"` assertions were intentionally left unchanged. PaperBroker production serialization and position-reduction semantics were not modified.

## Static evidence

Commits before terminal STATUS:

```text
4a0598deb0ca758e9db75dd873fbcf3f5961d47c  test(e4): use adapter-issued OKX materializations
9e6c3d36e8c3ef25ead2886bbe73e884d3b6176c  test(e4): accept Decimal-equivalent explicit close zero
```

Diff before STATUS contained only:

```text
tests/brokers/test_okx_demo_adapter.py
tests/brokers/test_paper_broker_protection_stop_flat_truth.py
```

## Verification state

```text
local_verification = NOT_RUN
GitHub Actions / CI = NOT_USED
hosted / GitHub-triggered runner = NOT_USED
project code/tests executed by E4 = NO
provider/private network = NOT_USED
credentials = NOT_USED
```

Required later approved-local command:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

`NOT_RUN` is not PASS. This task does not claim Gate B/PAPER_READY PASS and does not authorize PAPER, SHADOW, LIVE, or Gate C.

## Completion boundary

The bounded E4 test remediation is complete. E4 stops here and does not self-start verification, integration remediation, provider/private work, PAPER, SHADOW, LIVE, or another task.
