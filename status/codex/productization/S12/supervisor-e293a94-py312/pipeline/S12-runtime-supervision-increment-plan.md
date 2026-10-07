# Authorized S12 runtime/cloud supervision increment

Status: PLANNED; development overlay only until reviewed and integrated.

Use the actual existing ProcessSupervisor and process-supervision.sqlite. Add runtime and cloud roles with the same complete-lifetime host lock, actual generation counter, heartbeat, configuration checking and restart reconciliation inhibition as control/research. A role heartbeat is never a PAPER process lease, qualified release, financial consent or runtime commissioning proof.

Preserve migration 0006 unchanged. Add migration 0008 to atomically rebuild only the two role-constrained supervision tables, preserving all columns and existing rows; history remains untouched. Apply the two owned scripts statement by statement within one SQLite transaction, bind the applied additive migration to its digest and reject unknown table shapes, changed migration receipts or nested transactions. Initialization must be idempotent and compatible with an active owner of another role. No ninth database, provider transport, UI permission, restoration clearance or installed service is introduced.

Sequence: observe new-role/migration regression failures against existing code; implement in the project-local development overlay; run new and affected existing tests; independent bounded review and repair; integrate the reviewed bytes; establish a new exact-clean executable candidate and qualify it before publishing sanitized evidence. Keep prior accepted S14 checkpoint and failed development evidence intact.

Required regressions: actual independent runtime/cloud generations and locks; duplicate-role denial; real heartbeat and configuration fencing; stolen-generation denial; untouched legacy control/research history and counters; current-role activity surviving additive migration; idempotence; migration fault rollback; migration digest mismatch; incompatible schema rejection; nested-transaction rejection; maintained role/state database constraints; read-only unstarted health.

Production release-profile acceptance remains pending separately. This implementation is authorized by the active master and cannot issue any qualified-release or financial authority.
