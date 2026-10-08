# Current runtime identity read

This bounded S09/S12/S13 prerequisite implements `read_runtime_identity` for
the existing local process supervisor. It reads an already running `runtime`
generation; it does not attach a PAPER worker or construct a release binding.

The accessor uses SQLite `mode=ro`, `query_only` and one read transaction. It
validates the owned schema and migration receipt, bounded strict JSON, software
commitment shapes, exact current-row/history/counter agreement, configuration,
canonical UTC clocks, heartbeat freshness and actual process presence. Its
returned snapshot and scalar identity mapping are immutable. Missing, stopped,
inconsistent or unhealthy supervision denies the read without creating storage,
migrating, repairing a record, renewing a heartbeat or allocating a generation.

The snapshot reports persisted owner facts observed at one time. It cannot
prove that a mutable local database was authored honestly, that a PID has not
been reused, that a process will remain current, or that native files still
match their earlier inventory. A consuming release adapter must independently
verify its actual release and preserve the existing owner/effect fencing. This
accessor grants no qualification, financial, restart or trading authority.

Source provenance has no invented build hash. Native-shaped protocol fixtures
preserve a build hash and the existing distribution profile, but do not count
as a native package or worker execution. The production qualified PAPER release
profile remains `PROPOSED_NOT_ACTIVE`; no software-check inventory or PM/E6
mapping is introduced by this change.

The initial 19 focused tests first failed because the accessor was missing, then
passed against actual supervisor/SQLite fixtures. Independent review found a
per-field type gap: two additional regressions reproduced four malformed-text
acceptances and one unhandled numeric-token exception. All 21 focused tests then
passed after validating each field's required type before parsing. A subsequent
actual Windows regression reproduced a 64-bit PID wrapping to the current
process at the native DWORD boundary. The accessor now validates the actual
platform's PID range before the OS query; all 22 focused tests pass. They cover read-only behavior,
immutable snapshots, restart generations, absent/stopped processes, configuration
and clock drift, malformed or oversized identities, duplicate JSON keys,
column/history/counter disagreement, schema/migration changes and native-shaped
identity preservation. Full exact-clean source qualification and fresh native
verification are separate subsequent steps.
