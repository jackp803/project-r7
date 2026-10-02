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
