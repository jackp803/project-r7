# Private complete core-history audit component — D still IN_PROGRESS

Actual E6 audit progress/proof belongs to the exact journal instance and a private
issuer identity. Progress is not an importable proof. Reopening or transplanting
another instance's state has no eligibility. CURRENT_FACTS_ONLY remains distinct.

Bounded keyset batches validate all operations, effects, checkpoints, publication
inventory, prefix inventory and process generations. Independent inventory phases
find orphan effects/publications not reachable from valid operations. No terminal
unbounded COUNT/anti-join is used. Packaged relevant schema and migration ledger
are checked read-only. Root/prefix/original logical and publication facts remain
mandatory. E4 current broker validation occurs after releasing read snapshots.

Schema/data_version/total_changes changes conservatively invalidate both partial
progress and completed readiness. Unknown migration ledger change first regained
eligibility incorrectly; a genuine RED then owning compatibility check corrected
it. Unknown external/own changes, malformed schema and older corruption now refuse.
This component deliberately invalidates on NORMAL writes too: own-write extension
and resource scheduling/integration remain mandatory before product activation.

A separate injected encoding mismatch revealed a committed unreadable checkpoint:
the old code detected it only on postcommit readback. Precommit write-roundtrip now
verifies exact logical state/hash using the owner-verified base and rolls the whole
effect/checkpoint transaction back. The pure write verifier is not a stored-reader
or audit shortcut; persisted reads still verify original predecessor chains.

Final59focused,291storage and31encoded funding/outbox tests PASS,0fail/error/skip;
overlapping scopes not summed. No ordinary product activation, timing/resource
qualification, new native receipt or real elapsed observation. Existing qualified
bffc executable remains the only accepted native subject; changed source is not.
Continue D and E continuously within explicit human scope approval.
