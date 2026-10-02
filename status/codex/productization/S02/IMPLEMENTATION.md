# S02 cloud intake implementation checkpoint

Spec r7-product-v0.2; task CODEX-R7-PRODUCTIZATION-MASTER-20261002.
Review: SELF_REVIEW. Exact-clean qualification is pending this executable commit.

Separate strict v0.1/v0.2 adapters validate bounded JSON, UTC, identity and
payload declarations. Byte SHA-256 and E2 semantic content hashes remain distinct.
The v0.2 runtime reference uses the canonical runtime_family/runtime_version
object. V0.1 never infers capability or tactical authority. A v0.2 intake needs
a locally bound exact capability snapshot; absent configuration is BLOCKED.

The folder transport verifies a pre-provisioned root marker and never initializes
a replacement cloud mount. Windows reads pin ancestor handles and reject reparse
points; Linux reads use directory descriptors and O_NOFOLLOW. Execution parses
the sealed verified local bytes through the actual E2 parser. Changing cloud
bytes after sealing cannot change that parse. Corrupt local snapshots fail closed.

E6 now supports a bounded optional intake operation key. Registration,
compatibility record, receipt and operation binding commit in one E6 transaction;
replay returns the same receipt. The legacy intake call remains compatible.
App lease/outbox state is a separate local SQLite store with WAL/FULL durability,
busy timeout, generation/owner/revision/deadline fencing, bounded pending outbox,
and atomic effect-reference/outbox commit. Cross-database recovery reuses the
canonical E6 effect. Default compatibility remains NOT_RUN and lifecycle DRAFT.
No public connection or raw writer is exposed.

Incomplete delivery uses persisted 5-300 second backoff; unchanged incompleteness
after 24 hours surfaces SYNC_STALLED. Observation history is retained. Result
payloads finalize from staged writes before the readiness manifest. Conflicting
immutable destination bytes are never overwritten. Transport receipt identity
and aggregate byte hash are checked. Folder writes report LOCAL_STAGED only.
Runtime-owned partial staging files are retained; no source/cloud deletion is
performed. Explicit housekeeping and native backup/retention remain later work.

Observed TDD: initial cloud/claim/outbox modules failed for their missing required
components; the E6 operation keyword was initially unsupported. Additional red
tests covered missing durable retry, wrong transport acknowledgment hash, missing
partial-write fault handling/budget settings, and a raw readonly-root exception.
After implementation: 37 application and two new E6 atomic-intake tests PASS,
zero failures/errors/skips. Earlier affected regressions: registry 21, strategy
21, storage 136 tests PASS; fresh exact-clean regression is still required.

Fault probes cover real E6 registration followed by crash/restart, lease expiry,
stale worker rejection, concurrent claims, outbox commit crash, upload-before-ack
crash, content conflict, missing/changed bytes, root marker loss, actual Windows
junction escape, case collisions, corrupt snapshots, injected disk-full partial
write and injected readonly snapshot root. These are OFFLINE_TRANSPORT_SIMULATION.
Native Ubuntu and real cloud round-trip remain NOT_RUN. No real provider/private
request, credential, capital, runtime LLM, GitHub compute or main merge.

Next after qualification: S03 explicit strategy profile routing and capability
registry. Executed research compatibility belongs to S06; intake does not invent
LOCAL_EXECUTION PASS to advance a lifecycle.
