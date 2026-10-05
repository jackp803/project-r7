# S14 cloud bridge and feedback implementation plan

> For agentic workers: use `superpowers:executing-plans` inline on the existing branch. Continue the master task; retain S12/S13 recovery/runtime/service gaps and do not treat this independent work package as final acceptance.

Goal: feed `SyncedFolderCloudTransport` with an operator-configured Ubuntu-compatible rclone copy bridge, preserve durable publication semantics, and deliver offline authoring/feedback artifacts.

Spec: PLAT-05, `docs/product/v0_2/03_CLOUD_SECURITY.md` CLOUD-01 through CLOUD-09, and execution plan S14. Official rclone `copy`, `copyto`, `lsjson`, `cat` and Drive documentation are protocol references; no real cloud/tool commissioning PASS is inferred from them.

Architecture: local non-secret allowlisted profile binds an exact executable/hash, protected rclone config reference, fixed alias, selected Drive root folder identity, staging marker, private work root and bounded budgets. Python checks the reference's metadata/permissions without reading OAuth contents. All process argv are fixed per operation, with no shell, remote flags from packages, environment-derived rclone overrides, destructive sync/delete/dedupe or whole-drive fallback. Development uses local fake transport and owned Python fixtures only. Missing real rclone/cloud remains NOT_RUN / CLOUD_NOT_CONNECTED.

Files and interfaces:

- `src/application/cloud/command_runner.py`: `run_bounded(argv, *, private_root, timeout_seconds, stdout_limit) -> CommandResult`. Actual owned child/tree, private bounded stdout, discarded stderr, fixed environment, deadline/overflow cleanup and reaping. Raw output is never printed or logged by a CLI error.
- `src/application/cloud/rclone_bridge.py`: strict `BridgeProfile` / `load_bridge_profile`, `RcloneBridge.pull_once()` and `push_bundle(logical_path)`. A trusted runner seam permits local fake transport tests; only profile-controlled production argv reach rclone.
- `src/application/cloud/bridge_transport.py`: stage through the existing folder publisher, then return CLOUD_ACKNOWLEDGED only after actual bounded remote byte readback matches every payload and manifest. Local stage alone remains LOCAL_STAGED.
- `src/application/cli.py`: bounded explicit bridge commands; no automatic OAuth setup or real commissioning during development.
- `src/application/cloud/feedback.py`, `src/application/cloud/authoring.py`: allowlisted, versioned owner-derived feedback and offline packages with actual E2/implemented capabilities; opt-in performance policy and holdout observation bookkeeping.
- `tests/application/test_cloud_command_runner.py`, `test_cloud_bridge.py`, `test_authoring_roundtrip.py`, `test_feedback_redaction.py`; documentation under `docs/strategy/authoring-v0.2/` and `docs/product/`.

Review focus: stdout/child hangs cannot exhaust or strand owned processes; duplicate/case-colliding remote paths never select an arbitrary Drive object; evolving unaccepted input manifests may be recopied without altering sealed snapshots; upload success without verified readback cannot acknowledge an outbox; secrets/private provider IDs and local paths never enter default feedback. Each has an actual regression, not a source-text assertion.

## Task 1: bounded local process execution

- [ ] Write real child success, nonzero/stderr, overflow, timeout/grandchild and invalid budget tests; observe missing-feature failures.
- [ ] Implement owner-private bounded capture and cleanup with existing `OwnedProcess` APIs.
- [ ] Pass focused application/process regressions. Output limits are application soft bounds; do not claim kernel disk caps.

## Task 2: safe copy bridge and durable acknowledgment

- [ ] Write fake-remote roundtrip, missing marker/config, duplicate names, malicious paths, incomplete input evolution, outages and exact remote-ack tests; verify RED.
- [ ] Implement profile/argv validation, fresh private download generations and atomic author-input staging; consumer hash/readiness and E6 idempotency stay authoritative.
- [ ] Publish only immutable runtime-owned bundles, payloads first/manifest last; reject differing existing objects and verify remote bytes before ACK.
- [ ] Integrate trusted CLI and existing transport/publisher without cloud-dependent trading or research computation.

## Task 3: authoring and feedback

- [ ] Write legacy/4h/multitimeframe/tactical/missing-feature roundtrips through actual E2 and intake; verify RED.
- [ ] Build actual JSON artifacts, schemas, capability examples and self-contained sanitized feedback with exact Decimal strings/nulls/NOT_RUN.
- [ ] Test private fields/paths/provider IDs, default performance opt-out, and holdout observation after exposed OOS feedback.
- [ ] Commit exact candidate; complete source/native/browser qualification as affected, retain sanitized evidence, verify Git blob hashes and push. Return to pending S12/S13 and S15/S16; real cloud/Ubuntu/forward/provider commissioning remains NOT_RUN.
