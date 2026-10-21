# E6 pure state codec component

Approved E6 capacity subplan A only.16 final tests pass, including260 deterministic
mixed revisions and128-boundary/127-predecessor reconstruction. Original missing
component failures, the corrected invalid assumption that a full rolling array
must compress better as a delta, and real missing aggregate/delta memory limits
are retained. Larger delta uses an early keyframe; no evidence is dropped.

Logical raw JSON and hash are exact; bool/int and Unicode remain distinct.
Wrong run/base/revision/hash, duplicates, malformed/bomb/trailing compressed data,
unsupported versions and hostile patch types refuse. The pure module has no DB,
provider, execution or permission side effects. Storage237 regression passed before
two local allocation guards/refactors; final16 reran on the retained source hash.
No new E6 persistence, hot recovery, ordinary profile or native qualification is
claimed. Existing full audit remains. Continue B–E continuously on the same task.
