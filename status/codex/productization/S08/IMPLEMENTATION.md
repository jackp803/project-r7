# S08 in-progress owner checkpoint

Task/branch/spec remain CODEX-R7-PRODUCTIZATION-MASTER-20261002,
codex/r7-productization-master-20261002 and approved v0.2 at
9fd277798b1c51d1bc79b29a61bec81b552efeb1. S08 is IN_PROGRESS, not PASS.
Last full qualified executable remains1d5b9a07c83eed7efe767aedaf36cbb898633349.

First bounded repair: actual E6 validation-evidence persistence now uses a
short BEGIN IMMEDIATE transaction to find/save the immutable upstream identity.
Exact retries return the original evidence_id/recorded_at. Different payload,
subject, producer, parent, source or verification metadata under the same
upstream identity is an EvidenceGateError and never an overwrite/upgrade.
The service returns the actual stored record; both BacktestResult and
ValidationDecision use the same owner store boundary.

Observed RED:3 tests /6 error occurrences reproduce duplicate backtest/decision
after restart, conflicting same upstream inputs and a crash after actual E6 save
before the application receipt. The repaired focused3 tests passed. A separate
two-connection/thread contention check passes, returning the same original
record. It is characterization of the newly implemented atomic transaction,
not claimed as a prior RED. Regression checks: registry26, storage136 and the
actual application crash-recovery test1 all pass, zero failures/errors/skips.
The job-clock expiry is explicitly injected in the fixture and supplies no
real elapsed forward/PAPER evidence. No original test or threshold was removed.

Remaining S08 execution brief:

1. Extend the actual E6 canonical model/store/migrations to all accepted legal
   edges, preserving old early-slice tests and immutable definition/history.
   No duplicate application lifecycle database or generic public transition API.
2. Product-managed registries and v0.2 subjects must require actual complete
   E3 product assessment at the owner service AND store authority, including
   through legacy mark_candidate paths. Author-supplied LOCAL_EXECUTION/PASS
   metadata alone must not satisfy the stronger gate. Legacy credential-free
   early-slice fixtures retain their historical research-only boundary.
3. Configure a private trusted application assessment boundary that resolves
   immutable actual ResearchJournal/holdout results by reference, checks exact
   namespace/subject/source/dataset/policy/independent OOS and materializes E6
   assessment evidence. Never accept an arbitrary assessment mapping via HTTP.
4. Preserve FAIL (quantitative rejection) versus BLOCKED (no forced rejection)
   and exact family/result lineage. A selected local risk policy must reuse
   E5 RiskPolicy with declared units and hash; missing real policy is diagnostic.
5. Implement named guarded PAPER/ready/approval/deployment/degrade/resume/retire
   methods. Typed downstream evidence ports default to denied/NOT_RUN until
   actual owning producer exists. Full forward producer integration is S09;
   actual authenticated command/session binding is S10. Fixture mechanics may
   use conspicuously isolated fixture authority, never reusable real approval.
6. Approval/envelope binds exact strategy/hash/version, source/build/config,
   capability/provider/profile, selected risk and explicit financial ceilings,
   generation, actor role, expiry/revocation and command/expected revision.
   A JSON actor='ProductOwner' is not authenticated human authority. Runtime
   generation/restart or credentials alone never clear LIVE/reconciliation gates.
7. TDD every legal/illegal edge, legacy bypass, forged/stale/wrong-subject
   approval and direct-store bypass. Then actual owner integration, full clean
   qualification, evidence and bounded push; continue S09 automatically.

Read canonical contracts/SHARED_CONTRACTS_V1.md sections18/21 and v0.2
04_RESEARCH_LIFECYCLE.md /05_PRODUCT_OPERATIONS_UI.md before implementing.
ResearchService S07 positive/negative fixture reports still have E6 BACKTESTING;
do not silently reinterpret their provisional candidate gate as operational
authorization or transplant1d5b9a0 PASS to later source changes.

Second bounded checkpoint (2026-10-03, still IN_PROGRESS):

- The canonical ten states/nineteen edges and named retirement now use the
  actual E6 model/service/store. Migration0008 preserves populated0001-0007
  identities, compatibility, intake, evidence and transition rows. Its tagged
  runner follows SQLite's generalized rebuild procedure: foreign keys off,
  BEGIN IMMEDIATE, copy/drop/rename, recreate objects, foreign-key check,
  migration receipt and commit, then foreign keys on. An injected SQL failure
  rolls back schema/data/receipt and a subsequent real upgrade succeeds.
  Primary procedure: https://www.sqlite.org/lang_altertable.html#otheralter.
- Source commitments now cover Python AND executable SQL resources using LF
  canonical bytes. A changed authority migration invalidates prior research.
  Runtime SQLite data is excluded; this is source identity, not a native build.
- Both service and store reject legacy candidate metadata in FIXTURE and
  LOCAL_RESEARCH registries. An unclassified v0.2 subject cannot escape these
  gates. Historical unclassified v0.1 early-slice research tests remain intact;
  that compatibility does not supply any operational permission.
- The configured actual application adapter resolves immutable ResearchJournal,
  finalist and sealed-result lineage by run reference, outside E6 writer locks.
  E6 persists append-only product evidence and actual canonical sealed backtest
  and validation records. Request bodies cannot submit product PASS objects.
- Explicit pre-run local risk selection uses existing E5 RiskPolicy, fixed
  declared units, namespace and generation. Missing selection remains diagnostic;
  no fixture policy becomes a real default. The frozen run-input commitment binds
  risk selection even though E3's financial validation thresholds stay distinct.
- Actual fixture positive E1/E2/E3/E6 execution enters CANDIDATE with selected
  risk. Actual adverse OOS enters REJECTED; insufficient final sample remains
  BACKTESTING and retains the legacy numeric FAIL. All are isolated mechanics,
  not real forward/provider/capital acceptance. Candidate grants no LIVE right.
- Wrong version, changed executable source, an unconfigured producer, private
  writer-capability mismatch and SQL update/delete do not create/overwrite proof.

Observed corrected RED: source/legacy bypass6 tests with4 failure occurrences;
product binding5 tests with5 failure occurrences. The first bypass harness held
SQLite open past TemporaryDirectory cleanup; it was fixed before the clean RED.
The first quantitative fixture changed a threshold that blocked walk-forward
selection; it was replaced with the existing actual adverse sealed data so the
RED tests the missing rejection edge, not sample inadequacy. Neither correction
changes a production threshold or hides unfavorable results.

Final affected checks at this checkpoint: registry32, storage138,
application74, strategy64, validation43, safety66, all zero failures/errors/skips.
These are local working-tree checks, not a full exact-clean qualification.
S08 approval/PAPER/deployment/degrade/resume gates remain to be implemented.
No native Ubuntu, cloud, real dataset, real forward or provider evidence is added.

Task S08 Ruling: real LOCAL_RESEARCH promotion requires actual clean Git/source
provenance; dirty-source FIXTURE execution proves isolated mechanics only.
Task S08 Ruling: a quantitative early robustness failure may reject with its
actual retained owner assessment; incomplete/missing prerequisites cannot be
relabelled as financial FAIL. Cost if wrong: unnecessary rejected history,
never permission for a new exposure.

Third source checkpoint: operational owner boundaries implemented, pending
the final exact-clean qualification before declaring S08 PASS.

Named start_paper/mark_ready_for_approval/record_approval/activate_deployment/
degrade/resume_authorized/reject now use the actual E6 service/store. No generic
public transition API or application lifecycle database is introduced. The
canonical model has nineteen legal edges; operational tests execute eighteen
and the actual adverse E3 pipeline covers BACKTESTING -> REJECTED. All eighty-one
illegal state pairs are rejected in owner persistence.

Lifecycle owner evidence binds exact subject, source/build/config/capability/
provider/risk/runtime generations, actor, command and expected revision. The
trusted composition resolves owner references before SQLite writer locks. The
current release reader is a bounded local snapshot reader. Real admission needs
a separately configured current E7/E5/E4 verifier; absence is denied. S09 supplies
actual PAPER/forward producers, S10 the actual local authentication workflow,
and S12 the production admission integration. Legacy E7 preflight roles are not
reinterpreted as product LIVE permission. No provider client is created here.

Human capabilities are opaque, issuer-local and short-lived, issued only after
the configured server verifier returns an authenticated ProductOwner identity.
Actor/role strings and request dictionaries are rejected as human proof. LIVE
activation/resumption requires fresh reauthentication and current immutable
approval/envelope. The strict envelope includes explicit USDT ceilings, selected
E5 limits, permissions, expiry and exact release/runtime generations. Revocation
is append-only; old consent cannot clear a changed generation or expired envelope.

PAPER requires a locally selected immutable policy and PAPER_ONLY owner evidence.
The adapter reuses existing E3 ValidationPolicy amount-valued thresholds, with
explicit elapsed/sample/health/gap/expectancy/null-handling units. Real readiness
rejects accelerated/synthetic clocks, insufficient duration/samples, stale or
unhealthy observations, quantitative failures and impossible financial metrics.
The currently selected policy is checked again at persistence and approval;
amending it cannot transplant an old READY assessment into new consent.

FIXTURE owner evidence is explicitly SIMULATED_MECHANICS, with entries_enabled
false and release_kind FIXTURE in an immutable FIXTURE registry. Its simulated
READY/APPROVED/LIVE transitions exercise canonical mechanics only. They neither
start a trading runtime nor supply real forward/provider/build/capital proof.
Pure guard fixtures use declared clocks without publication or lifecycle writes;
the real elapsed-time producer remains S09. Selected fixture thresholds remain
test inputs, not installed defaults.

Observed new REDs: operational boundary3 failures; orphan approval1 failure;
duplicate completed command1 failure; interrupted product migrations2 failures;
missing selected PAPER policy/profile2 failures; missing public schemas and stale
PAPER policy approval2 failures; impossible forward metrics2 failures; migration
factory connection leak1 failure. Each corresponding focused repair passed.
Additional already-implemented guard cases are characterization, not prior RED.

Approval, owner evidence, canonical transition/projection and immutable command
receipt now commit in one BEGIN IMMEDIATE transaction. A crash rolls them all
back; identical completed commands return the original response without a new
transition, while changed consent under the same ID conflicts. Owner production
does not run inside this transaction. Both product migrations use atomic DDL/
receipt transactions; failed factory migration closes its owned connection.

The historical migration fixture now seeds the accepted eleven-column old
transition before upgrade and compares every original named column afterward,
also checking the added owner reference is NULL for old rows. It cannot use a
new writer against the pre-upgrade schema. No historical data check was removed.

Retirement characterization seeds a same-strategy historical canonical exposure/
protection graph through the real E6 PaperRuntimeJournal. Every runtime table and
recovery result remains unchanged after retirement; no assertion of flatness or
protection cancellation is added. Continuous E5 management after retirement is
still integrated and tested by the actual scheduler in S09.

Task S08 Ruling: fixture-only canonical operational states qualify isolated state
mechanics, not real operational mode or native/provider authorization. Cost if
wrong: a commissioning gate remains blocked; no real mutation is authorized.
Task S08 Ruling: a completed duplicate command returns its historical immutable
response even if the current projection later advances. S10 must show command
receipt versus current observed state distinctly; returning it performs no new
state change and is not renewed authority.
