# S13 native first-run foundation

Task CODEX-R7-PRODUCTIZATION-MASTER-20261002 continues on the existing bounded
branch. S13 is IN_PROGRESS; S12 continuous trading/protection and residual/funding
settlement composition remains IN_PROGRESS. Neither step is complete.

The native/source CLI now creates one non-secret diagnostic profile without
overwriting existing settings, enrolls the first local owner through hidden
interactive terminal input, and serves the actual authenticated E6 Control
Center. Data/configuration must be outside the frozen installation. Missing UI
fails before database initialization. Native startup performs actual canonical
migrations in LOCAL_RESEARCH; missing research/trading/cloud selections remain
explicit NOT_CONFIGURED. No trading or PAPER process is started.

Frozen owned-process bootstrap dispatch strips its reserved marker and preserves
the existing GO gate/Job Object or process-group ownership mechanism. Its native
descendant execution still requires separate package/worker verification.

The build inventory hashes the actual executable, libraries, source/SQL authority
resources, UI and license material. Frozen source commitment uses the complete
bundled source rather than an empty or unrelated directory. Frozen provenance
never borrows Git from its caller; recorded source revision and current package
build hash are separate, and worktree is UNAVAILABLE. This unsigned local
inventory is not an E7 admission proof, signed release or financial permission.
Tampering, missing/extra files, wrong interpreter/platform, unsafe relative paths,
duplicate JSON keys and linked/reparse content fail closed.

The local PyInstaller build tool requires exact CLEAN source, a fresh output root
outside the worktree, selected native CPython3.12/x86-64, installed exact wheel
pins and license material. Windows wheel hashes were resolved in a separate local
build environment; no global interpreter dependency was changed. The first-run
smoke invokes the native binary with an empty PATH and no PYTHONPATH, exercises
Chinese/spaced paths, real E6 migrations, control restart and loopback/auth denial,
and rejects a controlled tampered migration. Build/smoke results are still NOT_RUN
until actual output exists; scripts and source tests alone do not certify a package.

Observed development verification:

- First CLI RED:10 tests,9 missing-entrypoint errors. Initial implementation:10
  tests,1 missing data-directory error; after remediation10 PASS.
- Native distribution RED:7 tests,2 source identity failures and5 missing-module
  errors;18 combined CLI/distribution/source-resource tests then passed.
- Actual Windows junction-root RED reproduced a manifest read through the linked
  root. Root checks now precede manifest/source reads, and traversal checks each
  directory before descending. Combined focused verification:23 PASS.
- Actual build-input checks reject dirty/stale revisions, wrong Python minor and
  relative/inside/existing output roots without discarding contents.
- Affected application suite:98 PASS; legacy/additive strategy suite:64 PASS.
  Zero failures/errors/skips in these passing development runs.
- One invocation with an inappropriate unittest discovery top directory failed
  before test discovery; its log is retained separately. The corrected discovery
  command ran the actual application inventory; no test was skipped or weakened.

Full exact-clean qualification and native acceptance remain pending. Ubuntu24.04/
26.04 are NOT_RUN because no such local environment is attached. Supervisor,
isolated research-worker/runtime orchestration, systemd/SSH setup and consistent
backup/restore generation handling remain S13 work. SELF_REVIEW; whole-branch
independent review remains S16. Real provider requests0, credentialsNONE,
capitalNONE, runtime LLM0, GitHub computeNOT_USED; main has not been merged.
