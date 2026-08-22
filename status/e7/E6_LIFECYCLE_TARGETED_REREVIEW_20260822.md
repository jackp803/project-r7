# E7 Targeted Re-Review — E6 Lifecycle Persistence Authority

- Task: `E7-20260822-005`
- Date: 2026-08-22
- Review branch: `agent/e7-e6-lifecycle-rereview-20260822`
- PR: `#16 platform: integrate early Slice 2 registry and evidence persistence`
- Corrected E6 source/tests/docs revision: `aab1639d6db1f94e915d1c4af3041be28e9a4b94`
- Observed PR head: `42c5d56996e0c4ff0e96edfc591726d9f9f34963`
- Latest main at review: `6de6c45cd3db3e1c449725c8a7721c133f3296fc`
- Executable verification: `NOT_RUN`
- Project tests/migrations: `NOT_RUN`

## Executive disposition

`E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` is **not fully closed**.

The correction successfully adds an early-Slice-2 lifecycle edge allowlist to the SQLite store and a database trigger that rejects forbidden edge pairs. It also preserves the existing concurrency/atomicity protections.

However, the public/direct persistence surface still allows a caller to perform the three legal edge pairs without the `StrategyPlatformService` evidence gates. In particular, a direct store caller can perform:

```text
DRAFT -> BACKTESTING -> CANDIDATE
```

without recorded/verified E2 compatibility evidence for the first edge and without the bound E3 `ValidationDecision` + parent `BacktestResult` `PASS / LOCAL_EXECUTION` evidence required by the service for the second edge.

Therefore the authoritative lifecycle projection can still be advanced by bypassing the service's promotion authority, even though service-forbidden edge pairs are now rejected.

```text
E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001  BLOCKING / NOT CLOSED
E6-EVIDENCE-CONTRACT-001                CLOSED / PASS STATIC / NO REGRESSION
PR #16 merge recommendation             DO NOT MERGE
```

## 1. Correctly fixed: bounded edge vocabulary

The corrected model defines exactly:

```text
DRAFT       -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

via `EARLY_LIFECYCLE_TRANSITIONS` and `is_early_lifecycle_transition_allowed(...)`.

No later lifecycle states are introduced. The vocabulary remains only:

```text
DRAFT
BACKTESTING
REJECTED
CANDIDATE
```

No `PAPER`, `READY_FOR_APPROVAL`, `APPROVED`, `SHADOW`, `LIVE`, `DEGRADED`, or `RETIRED` state exists in the reviewed registry/storage model.

`SQLiteRegistryStore.append_transition(...)` now rejects any pair outside the early allowlist before `BEGIN IMMEDIATE`, authoritative row lookup, history insert, or projection update.

This closes the previous one-step bypass class such as direct `DRAFT -> CANDIDATE`.

## 2. Correctly fixed: forbidden transition mutation safety

For accepted store calls, the existing concurrency sequence remains intact:

1. `BEGIN IMMEDIATE`;
2. reload authoritative strategy row;
3. verify authoritative current state equals `transition.previous_state`;
4. verify `registry_revision == expected_registry_revision`;
5. verify `resulting_registry_revision == current + 1`;
6. append lifecycle audit row;
7. update authoritative lifecycle projection under matching state/revision predicate;
8. require exactly one projection row updated;
9. commit;
10. rollback on any exception.

For forbidden edge pairs, rejection occurs before the transaction/mutation path. The deterministic definitions assert that transition-row count, lifecycle state, and registry revision remain unchanged.

## 3. Correctly fixed: database forbidden-edge guard

`0001_strategy_registry.sql` now has a `BEFORE INSERT` trigger on `lifecycle_transitions` that permits only the same three early edge pairs and aborts every other pair.

The existing lifecycle state enum checks remain limited to the four early states.

The existing append-only triggers continue to reject `UPDATE` and `DELETE` of lifecycle history.

The corrected test definitions include a direct-SQL `DRAFT -> CANDIDATE` insert and expect database rejection with no lifecycle projection or revision change.

Because PR #16 has not yet been merged and executable migrations remain `NOT_RUN`, this review treats the corrected `0001` as the pre-merge baseline migration rather than an already-released migration upgrade.

## 4. Remaining blocker: direct-store legal-edge evidence bypass

**Finding:** `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`  
**Owner:** E6  
**Disposition:** `BLOCKING / NOT CLOSED`

The direct persistence API remains reachable:

- `storage.SQLiteRegistryStore` is exported by `storage`;
- `registry.LifecycleTransitionRecord` is exported by `registry`;
- `RegistryStore.append_transition(...)` remains a persistence port method;
- `SQLiteRegistryStore.append_transition(...)` accepts any of the three allowed edge pairs when state/revision checks match.

The store does **not** establish the service evidence requirements for those legal edges.

### DRAFT -> BACKTESTING bypass

`StrategyPlatformService.begin_backtesting(...)` normally requires:

- recorded E2 compatibility evidence;
- E2 checker provenance;
- `status=PASS`;
- `verification_kind=LOCAL_EXECUTION`;
- source revision;
- environment;
- command;
- result reference.

A direct store caller can instead submit a legal `LifecycleTransitionRecord(DRAFT, BACKTESTING, ...)` with no compatibility evidence and update authoritative state/revision.

### BACKTESTING -> CANDIDATE bypass

`StrategyPlatformService.mark_candidate(...)` normally requires:

- stored E3 `ValidationDecision`;
- exact strategy/content binding;
- `decision=PASS`;
- `PASS / LOCAL_EXECUTION` metadata with source revision/environment/command/result reference;
- a bound parent `BacktestResult`;
- the same `PASS / LOCAL_EXECUTION` evidence metadata on that BacktestResult.

A direct store caller can instead submit a legal `LifecycleTransitionRecord(BACKTESTING, CANDIDATE, ...)` with `primary_evidence_id=None` and update authoritative state/revision.

The new test helper and legal-edge test definitions explicitly exercise direct-store legal transitions with synthetic `LifecycleTransitionRecord` objects; those definitions demonstrate edge restriction, but also demonstrate that the persistence layer itself does not enforce the service evidence authority.

Therefore a caller can chain:

```text
register_strategy(...)
append_transition(DRAFT -> BACKTESTING)
append_transition(BACKTESTING -> CANDIDATE)
```

and reach authoritative `CANDIDATE` without the E2/E3 evidence gates.

The SQL edge trigger does not close this gap because both pairs are legal edge shapes.

### Required correction outcome

E6 must ensure that a direct persistence caller cannot advance authoritative lifecycle state without the same evidence authority required by the service.

The exact implementation remains E6-owned, but the accepted outcome must prove at least:

- direct store cannot perform `DRAFT -> BACKTESTING` without the required verified E2 compatibility authority;
- direct store cannot perform `BACKTESTING -> CANDIDATE` without the required bound E3 ValidationDecision + BacktestResult local-execution evidence;
- service-authorized legal transitions remain possible;
- forbidden pairs remain rejected;
- failed authorization leaves audit rows, state, and revision unchanged.

Do not solve this by adding later lifecycle states or weakening evidence requirements.

## 5. Edge-authority maintainability note

`registry.models` now contains a central `EARLY_LIFECYCLE_TRANSITIONS` set used by the SQLite store.

`StrategyPlatformService._transition()` still contains a local duplicate of the same three edges rather than calling the shared helper. The values are currently identical, so no broader authority or present bypass is created by this duplication.

Disposition: `NON_BLOCKING_HARDENING` while the direct-store evidence-authority blocker above remains the merge blocker. A future correction should preferably avoid drift between service/store declarations.

The SQL trigger necessarily restates the edge pairs at the database boundary; static review confirmed it currently matches the Python allowlist.

## 6. `E6-EVIDENCE-CONTRACT-001` regression review

**Disposition: `CLOSED / PASS STATIC / NO REGRESSION`**

Critical accepted blobs remain unchanged at the corrected revision:

```text
src/registry/contract_validation.py
  954d21c021c0885554ee650acced17610d958a0e

src/registry/service.py
  3184452956e1540be44d5ea779be87ed573fbcae

src/registry/service_base.py
  3889ac156358f58c5fc3380865ad73844b874c3c
```

The public `StrategyPlatformService` still validates canonical `BacktestResult` and `ValidationDecision` contracts before persistence.

Preserved static guarantees include:

- incomplete/incompatible `BacktestResult` fails before evidence persistence;
- canonical identity/reproducibility/core metrics remain required;
- financial interchange values remain decimal strings where required;
- timestamps remain UTC/RFC3339 constrained;
- `ValidationDecision` requires canonical fields, exact enum, reason-code sequence shape, and exact strategy/backtest binding;
- caller-supplied `PASS / LOCAL_EXECUTION` metadata cannot bypass the canonical payload validators;
- a BacktestResult alone cannot authorize `CANDIDATE` through the service;
- `mark_candidate()` still requires bound E3 ValidationDecision + parent BacktestResult and local-execution evidence metadata.

Synthetic PASS fixtures remain test input only. No executable evidence is inferred from them.

## 7. Persistence / inbox boundaries

No regression found in the prior accepted boundaries:

- immutable `(strategy_id, strategy_version)` content semantics remain;
- same identity + same content is registry-idempotent;
- same identity + conflicting content fails closed;
- default/unwired E2 compatibility remains `NOT_RUN`, not manufactured PASS;
- lifecycle history retains append-only UPDATE/DELETE protection;
- SQLite remains an E6 implementation detail, not a shared-contract semantic change.

## 8. Slice 3 / provider scope review

PR #16 still does not persist or introduce lifecycle authority for:

- `ApprovedTradePlan`;
- `OrderRequest`;
- `OrderResult`;
- `Fill`;
- `Position` execution audit;
- provider-native OKX `sz`;
- provider requested/filled contract counts;
- execution reconciliation;
- Demo execution facts.

No provider contract quantity is reinterpreted as canonical BTC quantity.

No provider call, broker execution, credentials, account mutation, or asset-movement surface is introduced by this E6 PR.

## 9. Test-definition review

No tests were executed.

Static deterministic definitions now cover:

- all three allowed direct-store edge pairs;
- direct `DRAFT -> CANDIDATE` rejection;
- direct `DRAFT -> REJECTED` rejection;
- forbidden transitions out of `CANDIDATE`;
- forbidden transitions out of `REJECTED`;
- self-transition rejection for all four states;
- no transition-row/state/revision mutation after forbidden edge rejection;
- direct-SQL forbidden lifecycle-edge INSERT rejection;
- existing migration idempotency;
- immutable content;
- append-only history;
- restart persistence.

The legal direct-store edge test is also the evidence for the remaining blocker: it permits service-authorized edge *shapes* without requiring the corresponding service evidence authority.

Missing for closure:

- direct-store `DRAFT -> BACKTESTING` rejection when verified E2 compatibility authority is absent;
- direct-store `BACKTESTING -> CANDIDATE` rejection when bound E3 ValidationDecision/BacktestResult local evidence is absent;
- proof that the service path can provide whatever persistence authorization the corrected design requires without exposing caller-forgeable promotion authority.

## 10. Repository / synchronization review

E6 correction synchronization merge:

```text
c3d756b46af547b4ea0bb36aa653cc8b9081163f
```

has two parents:

```text
df15109dcb8594b1182bf6fc09cb5ad6681d74b5
06752b83c18f6579b06c1f3b7e1d5837a2d6949a
```

This is non-destructive merge history; no force rewrite/destructive rebase evidence was found.

Correction pin -> observed PR head contains only E6 status/handoff documentation:

```text
coordination/E6/STATUS.md
status/E6_EARLY_SLICE2_HANDOFF.md
status/E6_STATUS.md
```

Current PR #16 changed-file scope remains E6 registry/storage/tests/docs/status only. No `contracts/**`, E1/E2/E3/E4/E5 production, `.github/workflows`, secret, provider, or unrelated implementation change was found.

At review time:

```text
PR #16 mergeable = TRUE
E6 branch vs latest main = ahead 46 / behind 2
latest-main-only delta = coordination/E6/TASK.md + coordination/E7/TASK.md
meaningful production/shared-contract drift = NONE
```

The coordination-only behind state is not a synchronization blocker. The remaining direct-store evidence-authority bypass is the source blocker.

## 11. Merge / release disposition

```text
E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001: BLOCKING / NOT CLOSED
E6-EVIDENCE-CONTRACT-001:                CLOSED / PASS STATIC
PR #16 source disposition:               FAIL / BLOCKED
PR #16 merge recommendation:             DO NOT MERGE
Executable verification:                 NOT_RUN
Project tests:                           NOT_RUN
Migrations executed:                     NOT_RUN
Provider requests:                       NOT_SENT
Gate A:                                  BLOCKED / UNCHANGED
Gate B:                                  BLOCKED / UNCHANGED
Gate C:                                  BLOCKED / UNCHANGED
Gate D:                                  BLOCKED / UNCHANGED
```

This finding does not authorize lifecycle expansion. Even after a future static closure/merge, it would not imply Gate A PASS or authorize PAPER/APPROVED/SHADOW/LIVE.

## 12. Next action

E6 should correct only the remaining direct-store evidence-authority bypass within the early Slice 2 lifecycle boundary and return an exact source/test revision for E7 re-review.

E7 does not modify E6 production code, does not merge PR #16, does not run tests/migrations, and does not start another task automatically.
