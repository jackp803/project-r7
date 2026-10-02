# S01 local qualification and remediation

The first exact-clean candidate was
`cbae796a86e242f0d591af685efbc5ab33a60926`. Its complete qualification stopped
at the application suite; it is FAIL, not an accepted executable. All earlier
focused and legacy suites passed, but those results do not certify a new revision.
The runner stopped before registry instead of hiding or skipping the failure.

Root cause was measured with the exact process sequence: four owned processes
were present before termination; Job Object accounting reached zero and the
adapter returned reaped while two descendant processes remained alive. Windows
process termination completes asynchronously. The corrected adapter captures
stable owned process handles before termination and waits for their kernel exit
within the same monotonic deadline. It never searches or kills by process name.

Regression includes automatic timeout followed by another parent/child/grandchild
tree, with an unrelated process surviving. All 19 application tests passed both
directly and inside the supervised runner after remediation. Fresh exact-clean
complete qualification is still required for the new executable checkpoint.

Traceback redaction now also covers repr-escaped Windows paths. Persisted failed
logs were sanitized again, and their recorded SHA-256 values were recomputed.
The report retains its original source revision and failed outcome.

Review: SELF_REVIEW. Native CPython 3.12 builds and both Ubuntu targets remain
NOT_RUN. Memory admission is SOFT_LIMIT_ONLY. No real provider/private API,
credentials, financial authority, capital or GitHub compute was used.

Primary API references:
https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs
https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject
