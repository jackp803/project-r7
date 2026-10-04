# S13 actual local research worker implementation

S12/S13 remain IN_PROGRESS on the existing master task/branch. Native first-run
checkpoint1f322735a49fb76e7ea0b2408b2f045c13684f61 is scoped historical evidence;
the current worker source requires a new native build and later full qualification.
Accepted complete executable remains965bfb7bf8eca83831325a3ebce562764599dc1d.

LocalOwners composes actual E6/intake/research selection/queue/owner services.
Missing selections remain NOT_CONFIGURED; hostile/duplicate/unknown/local-path
input fails before canonical database initialization. Actual control entrypoint
uses this composition. Source/package hashes and selected-file drift remain
checked by the existing queue/resolver and actual research service.

research-worker runs actual jobs in a separate owned child, with measured resource
admission, finite timeout, lower research priority and durable queue generation.
The CLI has no fixture/executable override. A private child command consumes only
the already claimed exact job/generation through existing actual owners.
Observed process death is recorded through the app dispatch ledger only, guarded
by actual OwnedProcess reaping and exact owner/job/generation; it never resets
sealed OOS observations, changes financial state or overwrites a successor claim.

Observed TDD/development results:

- Local composition RED:4 tests/7 missing-module errors;4 PASS after implementation.
- Worker RED:5 missing-worker errors; separate generation-disposition RED failed
  on the missing actual termination seam.6 worker cases then passed.
- A zero-exit child without owner publication reproduced JOB_FINISHED incorrectly;
  corrected wrapper requires the actual published job state, and records FAILED.
-22 combined worker/composition/first-run/API contract cases PASS.
- Affected application inventory112 PASS; actual owner/authenticated control API
  regression20 PASS. Zero failures/errors/skips in these passing runs.

The positive child runs the actual E2/E3/E6 pipeline to CANDIDATE in explicit
synthetic FIXTURE scope. Resource pressure retains QUEUED and starts no child.
Controlled timeout reaps the process and records FAILED; an expired old generation
cannot overwrite a successor. Unconfigured production worker remains truthful.
These mechanics do not certify real datasets, real forward time, provider access,
native worker packaging, actual host OOM or Linux execution.

Next: actual supervisor/exclusive process scopes, heartbeat/currentness, service
and SSH setup, consistent SQLite backup/restore generation handling, new native
worker/recovery tests, then full exact-clean product/native qualification. Final
S15 native harness must add per-command actual UTC/config provenance. No milestone
exit. SELF_REVIEW; whole-branch independent review remains S16. Real provider
requests0, credentialsNONE, capitalNONE, runtime LLM0, GitHub computeNOT_USED;
main has not been merged.
