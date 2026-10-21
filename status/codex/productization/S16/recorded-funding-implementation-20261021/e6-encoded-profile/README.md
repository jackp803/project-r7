# E6 new-run encoded storage and logical-reader component

Approved capacity subplan B. New migration0025 selects the versioned physical
codec only for an explicitly selected NEW run, in the same transaction as its
initial checkpoint. Old rows remain unchanged/readable; actual0024 read-only
store test proves no migration is needed to read legacy facts. UPDATE/DELETE/
REPLACE and adding a profile after checkpoint creation refuse.

Existing operation/effect/publication identities and exact logical hashes are
identical across the legacy and encoded profiles. All original journal contracts
rerun on the new profile, including transaction crash, partial publication,
concurrent/stale owner and retry behavior. Actual retained SQLite checkpoint text
is compared with full logical text; this small source test is not a30day budget.

Report history and native diagnostic helpers formerly compared the physical
JSON envelope against the logical hash. Three genuine intended cases failed.
They now use the same read-only E6 logical checkpoint reader, retaining all hash/
producer/lineage validation. Corrupt actual bytes with the original schema restored
refuse in both consumers. Source unit calls of native diagnostic methods are NOT
native execution/qualification. The initial test module also collected12existing
imported cases; final test module avoids that incidental duplication.

Final22profile tests,258storage suite before the additional read-only legacy case,
35report/outbox regressions and16new-profile funding/consumer cases PASS. These
scopes overlap and are not summed. The16 repeat actual LOCAL E4/E5/E6 flat pending,
successor finalization, original clocks and exact crash replay on encoded rows;
source/native measurement boundary and clocks are explicitly controlled.

The ordinary owner still selects legacy storage by default. No normal product
activation, bounded hot recovery, audit lease, financial permission, new Windows
qualification or observation is claimed here. Existing full historical validation
remains. Continue subplans C/D/E, whole-product capacity and all original remaining
source/emergency/policy/research/native/external gates on the same Master/branch.
