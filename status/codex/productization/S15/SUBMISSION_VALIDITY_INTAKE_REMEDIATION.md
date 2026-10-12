# Native negative intake defect and bounded repair

The Windows package built from `dd533694df21bd3608e58408d14b5b05255b4d21`, observed against clean metadata descendant `5842a2a57eb5045ada5bb8b933f55c202d3d10d9` with all 636 executable inputs identical, accepted an already expired tactical submission. The other four negative intake scenarios passed. No research job, Paper run, approval or trading worker was created. Actual public CLI authoring, hidden TTY enrollment, packaged UI scanning and local HTTP owner reads produced this evidence.

The v0.2 STR-06 specification requires expired requests to receive EXPIRED rather than extend their operational workflow. The intake service verified validity structure but omitted the current-time decision before claiming and creating an E6 effect. The ledger observation allowlist also lacked EXPIRED.

The bounded repair applies the existing E2 temporal decision after sealed payload and capability verification and before the intake claim. EXPIRED is an application request observation, never an E6 strategy lifecycle. A future interval is BLOCKED/SUBMISSION_NOT_YET_VALID. Existing immutable receipts and DRAFT records remain readable. Existing summary `blocked` includes expired inadmissible requests; no transport/API count schema is changed. Explicit offline archival is not implemented by this change.

Five new regression tests first failed for the observed behavior. The focused 36-test run then passed without failures, errors or skips. These cover expiry, the exclusive upper boundary, previously accepted receipt preservation, future validity, partial sync recovered after expiry and finite evergreen validity. Raw red/green logs and the 22-file native failure corpus are retained beside this report.

This candidate requires fresh exact-clean full source execution and a new native build before receiving any new native PASS. Prior package and three-outcome Paper evidence remain historical and are not transferred to changed executable inputs. Remaining cases involving expiry after research enqueue or during validation/approval are separate STR-06/Master audit work; this repair does not claim that entire requirement complete. Ubuntu24/26, ordinary release acceptance, real cloud/dataset/time Paper and capital/provider activation remain unqualified. Master remains IN_PROGRESS.

Independent read-only review found 0 Critical / 1 Important in the first repair: the initial remote manifest and the later sealed manifest were not bound together. A real transport/snapshot/E6 probe reproduced a valid-to-expired replacement being accepted. The follow-up repair requires equal canonical manifest hashes before claiming and then uses the verified manifest for capability, validity and receipt identity. The sixth regression first failed; the updated focused run passed all 37 tests. The review and repair are bounded incoming-intake evidence, not whole-Master approval.

The first full source candidate `a3a6a1c501a12e58acbe80d88ce171583ee37066` failed after 31/33 groups and 1856 test executions, with 6 failures / 1 error in the 472-test application group. Its research resource gate observed 4695027712 available bytes, below the unchanged 5060439859 threshold; source inputs stayed unchanged. Preserve this failed attempt with no qualification credit. The second manifest-binding repair requires its own clean source qualification. No native package for either repaired candidate has yet received acceptance at this note's checkpoint.

- Baseline native outcome: `native-negative-intake-5842a2a/outcome.json` (4/5, expired=INTAKE_ACCEPTED).
- Baseline artifact manifest: `native-negative-intake-artifact-hashes-5842a2a.json`.
- Regression red: `submission-validity-red-5842a2a.log` (5 failures).
- Focused regression green: `submission-validity-green.log` (36 passed).
- Snapshot replacement red: `manifest-swap-red-a3a6a1c.log` (1 failure).
- Snapshot-bound focused green: `submission-validity-binding-green.log` (37 passed).
- Full failed source attempt: `source-a3a6a1c/qualification.json` and `source-artifact-hashes-a3a6a1c.json`.

The second full candidate `56ed85aa42658688a412e1168ce10f45ce90bb6c` reached 31/33 groups and 1857 executions, with one error in the 473-test application group: normal OOS-loss research was fenced by PROCESS_GENERATION_NOT_CURRENT. Available memory had recovered, so this was diagnosed separately. Live health sampled its clock before reading the durable heartbeat; a heartbeat updated between those reads looked like a future observation and was incorrectly labeled CLOCK_REGRESSION. A deterministic regression reproduced that ordering failure before repair.

The supervision repair samples the trusted live clock after the heartbeat snapshot. Explicit historical `now`, actual clock-regression inhibition, the 15-second freshness threshold and generation/config/failed-session checks remain intact. Both ProcessSupervisor and public owner health use that ordered observation. Focused 58-test supervision/native-worker/normal-fixture/API regression passed, including the new race and existing stale/future/true-regression cases. Independent bounded supervision recheck: 0 Critical / 0 Important, reviewer execution NONE. The failed second full attempt remains preserved with no qualification credit. A third exact-clean candidate must qualify before native acceptance.

- Second failed source: `source-56ed85a/qualification.json`, original producer bytes in `qualification.json.raw`, manifest `source-artifact-hashes-56ed85a.json`.
- Heartbeat ordering red: `heartbeat-sample-race-red-56ed85a.log` (1 failure).
- Heartbeat ordering green: `heartbeat-sample-race-green.log` (58 passed).
