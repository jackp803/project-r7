# Source fingerprint cost remediation

Task: CODEX-R7-PRODUCTIZATION-MASTER-20261002. Windows11 / CPython3.12.10.

The exact-clean f2e9703 full source run passed its first31 commands, then
timed out at the existing900-second product-suite watchdog. Its complete
report remains FAIL; registry was NOT_RUN. No partial test output is promoted.
All owned descendants were reaped. The earlier23e3f99 Git provenance errors
remain historical failures with their transient observation cause unproven.

A separately owned cProfile reproduction of
`test_local_stop_after_1000_claims_remains_unknown_without_cleanup` passed.
It made862 fresh implementation-fingerprint calls;77.021 of83.993 profiler
seconds were spent there. The context's actual current-owner guards dominate
this workload; the historical claim stream does not dominate the profile.

The fingerprint now constructs relative names once per directory and filters
non-executable names before metadata access. It still traverses the current
source inventory and reads every Python/SQL file on every call. No content,
metadata, owner or admission cache was introduced. Sorting, relative ASCII
names, byte framing and CRLF normalization retain the existing hash protocol.
New/changed/deleted code and SQL continue to invalidate the identity. Public
financial, currentness, claim-generation and timeout rules are unchanged.

Tests first: the non-executable metadata regression failed before the fix;
the exact sorted-byte/inventory-change case passed. All10 capability tests
then passed. The same separately owned profiled scenario passed after the
fix in36.162 profiler seconds, with862 fresh fingerprint calls taking29.279
seconds. These are development measurements, not native benchmarks or full
qualification. Original and new profiles/logs remain in project artifacts
and will be retained with the next qualification evidence.

Establish a new exact-clean source candidate and rerun the complete source
qualification under the unchanged900-second watchdog. Rebuild and rerun
native scenarios for that new source; f2e9703's scoped native PASS cannot
qualify another executable. S12/S13 remain IN_PROGRESS; Ubuntu and real
cloud/provider/forward commissioning remain NOT_RUN.
