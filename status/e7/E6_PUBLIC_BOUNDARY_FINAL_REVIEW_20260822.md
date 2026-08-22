# E7 Final Review — E6 Supported SQLite Public Authority Boundary

- Task: `E7-20260822-009`
- Date: `2026-08-22`
- Review branch: `agent/e7-e6-public-boundary-final-review-20260822`
- PR: `#16 platform: integrate early Slice 2 registry and evidence persistence`
- Exact corrected E6 source/tests/docs revision reviewed: `ca41cb92cfaf23c7c0d00a7802727fa28f5cca86`
- Observed PR head: `607feaf1663966cd0fac82a244d368822ea28214`
- Correction pin -> observed PR head delta: `coordination/E6/STATUS.md + status/E6_EARLY_SLICE2_HANDOFF.md + status/E6_STATUS.md only`
- Review-time latest `main`: `7014d271886b202fc0e39d7c12a5f3bf9d7f8ecb`
- Executable verification: `NOT_RUN`
- Project tests/migrations: `NOT_RUN`
- Provider requests: `NOT_SENT`
- GitHub project compute: `NOT_USED`

## Executive disposition

Under the authority model explicitly assigned by `E7-20260822-009` — a trusted-process Python modular monolith with controlled DB-file access — the corrected E6 source closes the supported-public/raw-persistence portion of `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`.

```text
E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001   CLOSED / PASS STATIC
E6-EVIDENCE-CONTRACT-001                 CLOSED / PASS STATIC / NO REGRESSION
PR #16 source disposition                PASS / STATIC ONLY
PR #16 merge recommendation              PM MAY MERGE
```

The supported production composition surface no longer exposes raw authoritative SQLite persistence writers, raw connections, or migration primitives. The safe factory returns only `StrategyPlatformService`; raw storage mechanics live in an underscore implementation module and require the E6-owned writer capability. Initial lifecycle projection and lifecycle projection mutation have Python plus SQL defense-in-depth guards. Promotion-relevant E2/E3 evidence is revalidated before authoritative lifecycle mutation, including inside the persistence transaction.

This review intentionally does **not** claim protection against arbitrary malicious in-process Python, deliberate underscore/private imports, introspection/monkey-patching, or direct SQLite-file compromise. Those cases are explicitly outside the TASK trust boundary and the E6 documentation states that limitation accurately.

No executable PASS is claimed.

---

## 1. Supported `storage` public API

**Disposition: `PASS / STATIC ONLY`**

At exact revision `ca41cb92...`, `src/storage/__init__.py` exports only:

```text
open_sqlite_platform
```

`storage.__all__` contains exactly that single name.

The previously authority-bearing supported names are no longer exposed:

```text
SQLiteRegistryStore
connect
apply_migrations
sqlite_registry
```

The supported factory in `src/storage/platform.py`:

```text
open_sqlite_platform(path, compatibility_boundary=...)
    -> StrategyPlatformService
```

It obtains the authorized internal store through `_open_authorized_store(...)` and returns only the service. It does not return a tuple containing the store, a SQLite connection, migration primitive, or writer capability.

The returned `StrategyPlatformService` does not expose supported public methods/attributes named:

```text
connection
store
register_strategy
save_compatibility
save_validation_evidence
append_transition
```

The service internally holds its implementation port as `_store`. Deliberate private-attribute access/introspection is outside the declared trusted-process supported-API boundary, so the existence of an underscore implementation attribute is not a blocker for this TASK.

### Configured E2 boundary

The factory accepts `compatibility_boundary` as the intended trusted composition dependency for the E2 compatibility adapter. Under the TASK authority model this is a trusted in-process composition point, not an untrusted data/API security boundary. Compatibility evidence becomes durable authority only through service intake plus later persistence/service revalidation; a DTO alone is not a supported persistence capability.

---

## 2. Internal SQLite writer / construction capability

**Disposition: `PASS / STATIC ONLY`**

Raw mechanics are located under:

```text
storage._sqlite_registry
```

and are underscore/internal symbols:

```text
_connect
_apply_migrations
_SQLiteRegistryStore
_open_authorized_store
_internal_store_for_tests
_WRITER_CAPABILITY
```

`_SQLiteRegistryStore.__init__()` rejects construction unless the provided capability is the module-owned `_WRITER_CAPABILITY` object.

Authoritative mutating methods also call `_require_writer_capability()` before mutation, including:

- `register_strategy(...)`
- `save_compatibility(...)`
- `save_intake_receipt(...)`
- `save_validation_evidence(...)`
- `append_transition(...)`

The supported `storage` package surface does not provide this capability, raw connection, or store to ordinary downstream project code.

`_internal_store_for_tests(...)` remains an explicit underscore/test-only helper. Per the TASK threat model, a deliberate import of underscore internals by arbitrary in-process Python is outside scope and is not misrepresented as prevented.

---

## 3. Caller-constructed DTO authority

**Disposition: `PASS / DATA ONLY THROUGH SUPPORTED API`**

The registry package still exposes data objects such as:

```text
CompatibilityEvidence
ValidationEvidenceRecord
LifecycleTransitionRecord
StrategyVersionRecord
```

This is acceptable because the supported platform service exposes no raw persistence methods for writing these DTOs directly.

In particular, the factory-returned service has no supported:

```text
save_compatibility
save_validation_evidence
append_transition
register_strategy
```

surface.

Therefore caller construction of an authority-looking DTO does not itself provide supported write authority to the production persistence instance. The raw writer that can persist such records is an internal capability-gated implementation surface.

---

## 4. Initial strategy projection authority

**Disposition: `PASS / STATIC ONLY`**

### Python persistence guard

`_SQLiteRegistryStore.register_strategy(...)` rejects a new record unless:

```text
current_lifecycle_state == DRAFT
registry_revision == 0
```

This check occurs before authoritative insertion.

Same-identity/same-content idempotency remains coherent: normal service intake proposes `DRAFT / 0`; if the immutable identity/version already exists, the existing stored version may be returned rather than manufacturing a new state.

### Database defense in depth

Migration `0001_strategy_registry.sql` defines:

```text
strategy_versions_initial_projection_guard
```

which rejects any `INSERT` whose initial lifecycle projection is not exactly `DRAFT / revision 0`.

Thus a supported production path cannot register a strategy directly as `BACKTESTING`, `REJECTED`, or `CANDIDATE`, and the database independently rejects the same incoherent initial projection.

---

## 5. Lifecycle vocabulary and exact edge authority

**Disposition: `PASS / STATIC ONLY`**

The lifecycle vocabulary remains capped to:

```text
DRAFT
BACKTESTING
REJECTED
CANDIDATE
```

The Python transition set is exactly:

```text
DRAFT       -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

`is_early_lifecycle_transition_allowed(...)` is based on that exact three-edge frozen set.

`_SQLiteRegistryStore.append_transition(...)` rejects any other edge before beginning authoritative mutation.

The SQL migration independently enforces the same edge set through:

```text
lifecycle_transitions_allowed_edge_insert
```

No `PAPER`, `READY_FOR_APPROVAL`, `APPROVED`, `SHADOW`, `LIVE`, `DEGRADED`, `RETIRED`, or generic later-state authority is introduced.

---

## 6. Lifecycle projection defense in depth / atomicity

**Disposition: `PASS / STATIC ONLY`**

The persistence path retains:

1. writer-capability check;
2. exact early-edge check;
3. `BEGIN IMMEDIATE` transaction;
4. authoritative strategy reload;
5. current-state equality check;
6. expected registry revision check;
7. resulting revision = current + 1 check;
8. durable transition-authority revalidation;
9. lifecycle-history INSERT;
10. lifecycle projection UPDATE;
11. exactly-one-row projection update requirement;
12. commit, or rollback on any exception.

Migration `strategy_versions_lifecycle_projection_guard` requires that a projection update:

- advances revision by exactly one; and
- has a matching already-inserted lifecycle transition row for the same identity, previous/new state, expected revision, and resulting revision.

The intended append path inserts the lifecycle transition row and then updates the projection inside one transaction, so the trigger is coherent with the source transaction ordering rather than blocking the legitimate atomic path.

Lifecycle transition history remains append-only through SQL UPDATE/DELETE rejection triggers.

A direct SQLite-file writer is outside the declared trust boundary, but these SQL triggers still provide defense in depth against incoherent direct operations.

---

## 7. Durable E2 authority — `DRAFT -> BACKTESTING`

**Disposition: `PASS / STATIC ONLY`**

`require_backtesting_authority(...)` requires durable compatibility evidence for the exact strategy identity and verifies:

```text
checker begins with E2
status = PASS
verification_kind = LOCAL_EXECUTION
source_revision non-empty
environment non-empty
command non-empty
result_ref non-empty
```

The public service calls this authority check before delegating to the base transition path when the current state is DRAFT.

The internal persistence path calls `require_transition_authority(...)` inside `append_transition(...)` before lifecycle history/projection mutation, so the durable E2 requirement is revalidated even at the authoritative writer boundary.

The same accepted semantics are therefore enforced at both service and persistence boundaries.

---

## 8. Durable E3 authority — `BACKTESTING -> CANDIDATE`

**Disposition: `PASS / STATIC ONLY`**

`require_candidate_authority(...)` requires the selected primary evidence to be a stored E3 `VALIDATION_DECISION` with:

```text
decision = PASS
verification_status = PASS
verification_kind = LOCAL_EXECUTION
complete source_revision/environment/command/result_ref
exact strategy identity
exact strategy content hash
```

It then re-decodes the stored canonical payload and runs the accepted `ValidationDecision` contract validator.

A stored parent E3 `BACKTEST_RESULT` is required and is independently checked for:

```text
verification_status = PASS
verification_kind = LOCAL_EXECUTION
complete source metadata
exact strategy identity/content hash
canonical BacktestResult validation
exact stored object id/schema match
```

The canonical ValidationDecision `backtest_result_id` must exactly equal the canonical parent BacktestResult ID.

The service checks candidate authority before base transition; the persistence writer checks it again inside the transaction before mutation.

BacktestResult alone cannot authorize CANDIDATE.

---

## 9. `E6-EVIDENCE-CONTRACT-001` regression review

**Disposition: `CLOSED / PASS STATIC / NO REGRESSION`**

Accepted critical validator blob remains exactly:

```text
src/registry/contract_validation.py
954d21c021c0885554ee650acced17610d958a0e
```

Accepted base service blob remains exactly:

```text
src/registry/service_base.py
3889ac156358f58c5fc3380865ad73844b874c3c
```

Canonical BacktestResult validation still requires all current contract identity/reproducibility/core metric fields, correct schema version, UTC timestamps, integer metric types where required, and decimal-string financial interchange shape.

Canonical ValidationDecision validation still requires all current fields, exact decision enum, reason-code sequence/string shape, and UTC decision timestamp.

The public `StrategyPlatformService` still executes the canonical validators and verification-enum validation before base persistence.

Invalid enum/type/required-field shape fails closed. Caller-supplied `PASS / LOCAL_EXECUTION` metadata cannot make an incomplete or incompatible BacktestResult/ValidationDecision survive canonical validation.

Exact strategy/content/backtest-parent binding remains enforced. No weakening of the previously accepted evidence contract was identified.

---

## 10. Test-definition static review

**Disposition: `PASS / DEFINITIONS PRESENT / NOT EXECUTED`**

`tests/storage/test_public_persistence_boundary.py` statically defines coverage for:

- `storage.__all__` exports only `open_sqlite_platform`;
- legacy raw storage exports are absent;
- factory returns `StrategyPlatformService`;
- factory-returned service exposes no supported raw writer/connection names;
- direct `_SQLiteRegistryStore` construction without internal capability fails;
- caller-created authority-looking DTOs do not gain public write methods;
- non-DRAFT/nonzero initial registration is rejected without mutation;
- direct SQL incoherent initial projection is rejected;
- naked lifecycle projection UPDATE is rejected;
- normal service intake creates `DRAFT / 0`;
- valid service-authorized BACKTESTING and CANDIDATE flows remain representable.

`tests/storage/test_lifecycle_evidence_authority.py` retains deterministic definitions for:

- missing/non-E2/non-PASS/non-local/incomplete E2 durable authority;
- rollback/no mutation on rejected backtesting authority;
- missing/wrong ValidationDecision primary evidence;
- FAIL/BLOCKED/NOT_RUN decision rejection;
- wrong strategy identity/content hash;
- missing/wrong BacktestResult parent;
- malformed/mismatched canonical decision/backtest binding;
- missing/non-local metadata on decision or backtest;
- rejected attempts leaving state/revision/lifecycle-row count unchanged;
- valid service-authorized BACKTESTING and CANDIDATE flows.

`tests/storage/test_registry_persistence.py` retains definitions for:

- exact three legal direct-store edges;
- forbidden Python edge rejection without state/history mutation;
- SQL forbidden-edge trigger;
- append-only transition history;
- migration idempotency and persisted state behavior.

Synthetic PASS fixture data is clearly labeled synthetic/test-only and is not project executable evidence.

No test or migration was executed by E7 in this task.

---

## 11. Trust-boundary documentation

**Disposition: `PASS / ACCURATE`**

`docs/platform/E6_STORAGE_AUTHORITY_BOUNDARY.md` accurately states:

- supported production API is the safe factory/service surface;
- raw persistence mechanics are underscore/internal implementation details;
- writer construction is capability-gated;
- DTOs are data, not supported write authority;
- E2/E3 evidence becomes durable authority only through the supported service/persistence flow and later revalidation;
- DB guards are defense in depth, not authentication.

It explicitly does **not** claim prevention of:

- arbitrary malicious Python already running in-process;
- deliberate private/underscore access;
- introspection/monkey-patching;
- direct filesystem/SQLite-file write compromise;
- external authentication/cryptographic/HSM boundaries not implemented in Slice 2.

This matches the authority model assigned by the E7 TASK.

---

## 12. PR #16 scope / synchronization

**Disposition: `PASS / NO MEANINGFUL DRIFT`**

PR #16 changed-file scope is limited to E6 registry/storage implementation, tests, platform docs, and E6 status/handoff files.

Confirmed absent from PR scope:

```text
contracts/** changes
E1/E2/E3/E4/E5 production edits
.github/workflows / CI additions
provider/API/credential/secret implementation
ApprovedTradePlan persistence
OrderRequest persistence
OrderResult persistence
Fill persistence
Position persistence
OKX provider-native sz persistence
execution reconciliation / Demo execution facts
PAPER/READY_FOR_APPROVAL/APPROVED/SHADOW/LIVE lifecycle expansion
unrelated feature expansion
```

The E6 synchronization commit `610cdc4edbcd3fdf3f74c1eed9691253b4453cc9` is a two-parent merge preserving the prior E6 branch and then-current main:

```text
parent 1 = e7d1f3d9a99043107824a3c64d1d37663db8ff53
parent 2 = 36d1b5f3baee298dc33da444e0a31782a8cc6d7e
```

No force rewrite/destructive rebase evidence was identified.

Correction pin `ca41cb92...` to observed PR head `607feaf1...` changes only:

```text
coordination/E6/STATUS.md
status/E6_EARLY_SLICE2_HANDOFF.md
status/E6_STATUS.md
```

At review time:

```text
latest main = 7014d271886b202fc0e39d7c12a5f3bf9d7f8ecb
E6 branch vs latest main = ahead 75 / behind 2
latest-main-only delta = coordination/E6/TASK.md + coordination/E7/TASK.md
meaningful production/shared-contract drift = NONE
PR #16 mergeable = TRUE
```

Per the TASK, coordination-only TASK drift is not a reason to bounce E6 through another synchronization cycle.

---

## 13. Final finding disposition

### `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`

**Final disposition: `CLOSED / PASS STATIC` under the documented trusted-process modular-monolith authority model.**

The previous blocker was that the supported package API exported raw writer/connection surfaces that could manufacture the same durable authority later trusted by promotion checks. That supported-API bypass is now closed:

```text
supported downstream API
    -> storage.open_sqlite_platform(...)
    -> StrategyPlatformService
    -> canonical E2/E3 service gates
    -> capability-owned internal RegistryStore
    -> in-transaction durable authority revalidation
    -> exact edge/history/projection mutation
```

Raw store/connection/capability mechanics are not supported public authority surfaces. Initial projection and lifecycle projection have independent database defense-in-depth guards.

No reachable supported production API bypass was found at the reviewed revision.

---

## 14. Merge / verification / release state

```text
PR #16 source disposition: PASS / STATIC ONLY
PR #16 merge recommendation: PM MAY MERGE
Executable verification: NOT_RUN
Project tests: NOT_RUN
Migrations: NOT_RUN
Backtests: NOT_RUN
Provider requests: NOT_SENT
GitHub project compute: NOT_USED
Gate A: BLOCKED / UNCHANGED
Gate B: BLOCKED / UNCHANGED
Gate C: BLOCKED / UNCHANGED
Gate D: BLOCKED / UNCHANGED
PAPER/SHADOW/LIVE advancement: NONE
```

Static merge acceptance does not establish Gate A PASS and does not authorize later lifecycle states or execution/provider activity.

E7 stops after this final exact-revision review and waits for PM. E7 does not merge PR #16 and does not start another task automatically.
