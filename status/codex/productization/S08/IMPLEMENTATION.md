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
