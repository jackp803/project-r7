# Native negative intake defect and bounded repair

The Windows package built from `dd533694df21bd3608e58408d14b5b05255b4d21`, observed against clean metadata descendant `5842a2a57eb5045ada5bb8b933f55c202d3d10d9` with all 636 executable inputs identical, accepted an already expired tactical submission. The other four negative intake scenarios passed. No research job, Paper run, approval or trading worker was created. Actual public CLI authoring, hidden TTY enrollment, packaged UI scanning and local HTTP owner reads produced this evidence.

The v0.2 STR-06 specification requires expired requests to receive EXPIRED rather than extend their operational workflow. The intake service verified validity structure but omitted the current-time decision before claiming and creating an E6 effect. The ledger observation allowlist also lacked EXPIRED.

The bounded repair applies the existing E2 temporal decision after sealed payload and capability verification and before the intake claim. EXPIRED is an application request observation, never an E6 strategy lifecycle. A future interval is BLOCKED/SUBMISSION_NOT_YET_VALID. Existing immutable receipts and DRAFT records remain readable. Existing summary `blocked` includes expired inadmissible requests; no transport/API count schema is changed. Explicit offline archival is not implemented by this change.

Five new regression tests first failed for the observed behavior. The focused 36-test run then passed without failures, errors or skips. These cover expiry, the exclusive upper boundary, previously accepted receipt preservation, future validity, partial sync recovered after expiry and finite evergreen validity. Raw red/green logs and the 22-file native failure corpus are retained beside this report.

This candidate requires fresh exact-clean full source execution and a new native build before receiving any new native PASS. Prior package and three-outcome Paper evidence remain historical and are not transferred to changed executable inputs. Remaining cases involving expiry after research enqueue or during validation/approval are separate STR-06/Master audit work; this repair does not claim that entire requirement complete. Ubuntu24/26, ordinary release acceptance, real cloud/dataset/time Paper and capital/provider activation remain unqualified. Master remains IN_PROGRESS.

- Baseline native outcome: `native-negative-intake-5842a2a/outcome.json` (4/5, expired=INTAKE_ACCEPTED).
- Baseline artifact manifest: `native-negative-intake-artifact-hashes-5842a2a.json`.
- Regression red: `submission-validity-red-5842a2a.log` (5 failures).
- Focused regression green: `submission-validity-green.log` (36 passed).
