# S13 managed stop and health implementation

Task: CODEX-R7-PRODUCTIZATION-MASTER-20261002. S12/S13 remain IN_PROGRESS.
Accepted full executable remains cf6bd8d until this change is exact-clean
qualified. Its233 retained Git blobs were verified at2c5f3cb and pushed.

Tests first:4 managed-signal tests failed for the missing scope;2 research
stop tests and1 actual control-server stop test failed for the missing stop
integration. The focused26-test signal/control/research/supervision group then
passed in17.826 seconds. It exercises actual owned descendants, clean stop,
configuration drift, exclusion and stale-generation retention. No signal
handler raises through an owner transaction. Exact completed owner results
are preserved; interrupted app jobs are explicitly disposed after reaping.
An additional actual signal-under-held-lock test reproduced a deadlock in a
bounded owned child (exit124/reaped). The signal handler now only sets a flag,
without Event.set or another lock. The27-test group then passed, followed by
all6 managed-signal tests including an actual signal during bounded idle wait.

Health:3 display tests failed before the translation, and actual browser
assertions failed on raw ONLINE/PROCESS_RECENT_HEARTBEAT/QUEUE_AVAILABLE_WORKER_NOT_STARTED.
The first display implementation passed15 UI tests and11 actual browser cases.
Unknown prototype-property names were then separately reproduced and denied
as known codes. Missing/unknown/failure states remain distinct; no display
label or heartbeat grants financial permission. Final clean UI verification
and screenshots are still required for the new candidate.

Next: commit the source candidate; complete full source, exact-clean UI and
fresh native verification; retain RED/GREEN evidence and push. Then continue
consistent backup/restore generation, service/SSH, continuous runtime/cloud
and S14-S16. Native Ubuntu/systemd/real cloud/real forward/provider commissioning
remain NOT_RUN. No main merge, hosted compute, real credentials or capital.
