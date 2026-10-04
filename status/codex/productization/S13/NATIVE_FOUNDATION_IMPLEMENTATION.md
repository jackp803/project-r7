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

The first actual native build candidate da55207298973b6670d388fc66e462a8915d5799
failed before PyInstaller process launch with actual Windows error206: per-file
absolute resource arguments exceeded the Windows command-line limit. Failed
build directories/logs were preserved. Resource staging now copies only .py/.sql
into fresh source/runtime-resource trees and passes directory arguments; it never
copies environment/data/cache payloads. The resource-staging regression first
failed with the missing helper before the fix. A repaired exact-clean candidate
and fresh native build are required; no earlier PASS is transferred.

Repaired candidate423f30a36bd9405a4f74772aa88fa1dc1979079e built natively on
Windows11/Python3.12.10 with1034 retained files. Its first native smoke verified
empty-PATH hardware diagnostics and Chinese profile creation/preservation, then
failed on a harness assertion that incorrectly expected403 for rejected Host.
The actual existing security contract returns400/HOST_NOT_ALLOWED; the API was
not loosened. A real ASGI regression first failed on the missing shared native
denial table, then verifies exact400/403/401 Host/Origin/anonymous boundaries.
The harness now also retains actual HTTP status/hash assertions and failed server
command/reaping records. Native acceptance and full qualification remain pending.

Candidate a9bcf37b3d29490b19b99d5616812e28474c69b3 subsequently passed actual
native first-run smoke:5 scenarios/6 commands, empty PATH/PYTHONPATH unset,
actual16 E6 migrations, control restart and tampered migration denial; all owned
trees reaped. Its native build had1034 files. Inspection then found the package
license inventory omitted CPython's license, although Python libraries and JavaScript
runtime dependency licenses were retained. Before broader package acceptance the
selected interpreter license must be copied and hashed; the smoke now requires
matching dependency/interpreter license versions and actual sealed file hashes.
This regression first failed on the missing retention helper. A fresh build and
qualification are required; this earlier smoke is scoped historical evidence only.

Candidate1f322735a49fb76e7ea0b2408b2f045c13684f61 has1035 actual native files,
including the selected CPython license. Its fresh native5-scenario/6-command smoke
passed with exact dependency/interpreter versions and sealed license hashes;
all owned command trees were reaped. See NATIVE_FIRST_RUN_RESULT.md and
native-first-run-1f32273/. This is scoped first-run/control evidence, not full
S13/native acceptance. Full exact-clean qualification remains pending; accepted
complete executable remains965bfb7. Continue S13 supervision/recovery and remaining
S12 composition before final product acceptance. Native per-command UTC timing
was not recorded in this initial harness and remains a required S15 addition.
