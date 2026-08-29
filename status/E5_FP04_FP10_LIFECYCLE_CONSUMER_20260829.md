# E5 FP-04 / FP-10 Lifecycle Consumer Handoff — 2026-08-29

- task_id: `E5-20260829-031`
- owner: `E5 Risk Management & Position Lifecycle`
- target_branch: `agent/e5-fp04-fp10-lifecycle-consumer-20260829`
- base_main_sha: `0d4ac0aa4ffbac22a37c37ffdb404a7885fa445a`
- source_test_head_before_this_evidence: `c4b508ebe2a3168beb823c8783f75f834a96461e`
- result: `PARTIAL / IMPLEMENTATION + TEST DEFINITIONS COMPLETE / EXECUTABLE VERIFICATION NOT_RUN`

## Scope

Implemented only the provider-neutral E5 lifecycle consumer / reinterpretation boundary required by accepted FP-04 and FP-10 evidence. No shared contract, E4 provider/broker implementation, E6 persistence, AgentBridge, provider configuration, credential surface, release criterion, risk limit, leverage/capital threshold, or runtime authorization was changed.

Changed implementation/test paths:

- `src/position/external_close_reinterpretation.py`
- `src/position/external_close_policy.py`
- `src/position/__init__.py`
- `tests/position/test_external_close_reinterpretation.py`

## Accepted authority consumed

- `external-provider-object-ownership-reconciliation-v0.1`
- `external-manual-close-lifecycle-convergence-v0.1`
- `protection-registry-multiplicity-v0.1` as input-evidence dependency only
- `position-lifecycle-projection-v0.1`
- `position-lifecycle-execution-binding-v0.1`
- E4 `okx-swap-close-residual-sizing-v0.1` state vocabulary only where already admitted by FP-10; no OKX/provider semantics were imported into E5.

## Implemented E5 boundary

```text
accepted FP-04 ownership/reconciliation evidence
+ accepted FP-10 convergence evidence
+ exact current normalized Position
+ exact current lifecycle projection/execution binding
+ current provider/execution/protection/runtime generation references
-> deterministic E5 lifecycle reinterpretation decision
```

The implementation validates the accepted immutable evidence identities (`extownrec_...`, `extcloseconv_...`), required profile/schema fields, deterministic reason/disposition ordering, relevant FP-04 local evidence currentness, exact Position/lifecycle/execution-binding references, provider/execution/FP-04/FP-05/terminal-protection/runtime currentness, and deterministic E5 decision identity (`e5extclose_...`).

## False-green / fail-closed semantics

- Terminal/ACK/FILLED close-order evidence is never flatness authority.
- Any positive authoritative `Position.actual_quantity` remains non-flat and cannot produce or preserve a green `CLOSED` result. A stale local `CLOSED` projection combined with positive current exposure is forced to the existing fail-closed reconciliation path.
- `RESIDUAL_NONZERO_REPRESENTABLE` remains open/non-flat.
- `RESIDUAL_NONZERO_UNREPRESENTABLE` is explicit fail-closed non-flat/HOLD-safe evidence; it is not rounded or written off.
- `LIFECYCLE_CLOSE_ELIGIBLE` remains input evidence only. When exact/current and compatible, E5 alone applies an existing accepted event: `POSITION_CLOSED` from allowed active/exit states or `RECONCILED_FLAT` from `RECONCILIATION_REQUIRED`.
- `OPEN_UNPROTECTED` is not given a new direct close transition.
- External/manual/prior-generation flat truth follows the FP-10 two-step reinterpretation/reconciliation boundary and is not silently adopted into current-generation execution lineage.
- Flat provider truth with contradictory/incomplete execution/fill evidence does not close.
- Flat provider truth with non-converged terminal protection does not close and creates no cleanup/cancel target.
- Terminal protection close eligibility is additionally required to be observed/accepted no earlier than the flat provider Position acceptance boundary.
- Missing local Position state and an empty/no-pending-order execution set are never treated as flatness evidence.
- `TRADE_RESULT_EVIDENCE_INCOMPLETE` remains explicit and never fabricates missing OrderRequest/Fill lineage.
- Unknown, stale, conflicting, malformed, superseded, or mismatched provider/FP-04/FP-10/lifecycle/runtime evidence routes fail closed to reconciliation/hold-safe behavior.
- Later material provider/Position/FP-04/FP-10/lifecycle/runtime generations invalidate prior reinterpretation authority; immutable evidence is never rewritten.

No lifecycle response emitted here authorizes provider mutation, provider cleanup, close retry, protection mutation, new exposure, or capital activity.

## Deterministic tests defined

`tests/position/test_external_close_reinterpretation.py` defines provider-free fixtures for at least:

- terminal close order with positive Position -> no close;
- manual partial reduction -> open/reinterpreted, no current-generation lineage adoption;
- representable residual -> no close;
- non-representable positive residual -> explicit fail-closed non-flat;
- valid current `LIFECYCLE_CLOSE_ELIGIBLE` -> existing `POSITION_CLOSED` path;
- valid current close eligibility from `RECONCILIATION_REQUIRED` -> existing `RECONCILED_FLAT` path;
- forged close eligibility with positive exposure -> structural rejection;
- stale local `CLOSED` + positive authoritative exposure -> reconciliation, no false green;
- flat + execution/fill ambiguity -> no forced close;
- flat + non-converged terminal protection -> no close;
- external/manual flat -> two-step reinterpretation;
- stale/mismatched/newer provider, FP-04, lifecycle, and runtime truth -> old FP-10 invalidated;
- newer FP-10 immutable evidence -> prior decision invalidated;
- missing local Position != flat;
- no pending order != flat;
- incomplete TradeResult evidence -> no fabricated execution lineage;
- deterministic decision identity.

## Executable verification

```text
project executable verification = NOT_RUN / NOT PASS
```

Reason: the authoritative LF-0 exact-revision approved-local preparation dependency remains blocked in `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`; no independently approved exact-revision local execution path is exposed to this worker.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.position.test_external_close_reinterpretation -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

No project code/test command was executed through GitHub or a hosted runner. `NOT_RUN != PASS`.

## Safety / authority record

```text
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER runtime = NOT_STARTED / NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
Gate D / LIVE = BLOCKED / UNAUTHORIZED
GitHub Actions / CI / hosted / GitHub-triggered compute = NOT_USED
```

## Known limitations / downstream dependencies

- FP-04/FP-10 provider evidence producers and provider-specific observation/mutation mapping remain E4/E7 integration work outside E5 scope.
- Durable persistence/current-index/restart consumption remains E6 scope.
- E7 cross-module integration, exact-revision requalification, and release interpretation remain separate and not started by E5.
- This task does not claim FP-04/FP-10 executable PASS, LF-2 PASS, SHADOW/PAPER readiness, bounded live-fire readiness, Gate D, or LIVE authority.

E5 stops at `PARTIAL` because implementation/test definitions are materialized but approved-local executable verification is `NOT_RUN / NOT PASS`.
