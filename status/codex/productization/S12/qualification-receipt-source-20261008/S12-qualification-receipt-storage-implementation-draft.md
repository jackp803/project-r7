# S12 internal software qualification receipt storage

Task `CODEX-R7-PRODUCTIZATION-MASTER-20261002`; baseline `r7-product-v0.2`.
This increment implements storage mechanics, with actual isolated canonical-store
tests. The owning fixed-check producer, current-release adapter and ordinary
native PAPER composition remain separate unfinished work. The production profile
remains `PROPOSED_NOT_ACTIVE`; these rows issue no `ReleaseBinding`, admission,
strategy readiness, restoration clearance, human consent or financial authority.

`storage.qualification.open_qualification_receipts` is an existing-store SQLite
`mode=ro`/`query_only` reader. It does not bind a namespace, migrate, create a
replacement database or expose an append method. The top-level supported
`storage.__all__` remains unchanged. Trusted producer composition uses a private,
capability-constructed writer; no HTTP/cloud receipt importer or caller PASS
parameter is added.

Migration0018 adds one table to the existing canonical E6 database, without a
ninth product database. It records an exact software subject, profile commitment,
ordered check inventory, actual outcome/count/cleanup/log commitments and UTC
execution interval. Checks may record historical failure. The computed `passed`
property means only that these recorded software-check outcomes succeeded; it
cannot establish accepted production-profile completeness or release authority.
The storage layer does not execute checks or resolve referenced logs: the pending
owning producer must capture/execute/bind them and the pending adapter must apply
the accepted exact profile before any release admission.

Opening requires the existing canonical namespace singleton and its immutable
guards. The reader verifies the recognized receipt schema and migration receipt.
The writer checks migration inventory inside `BEGIN IMMEDIATE`, applies only its
owned additive migration atomically, and verifies the resulting schema. A wrong,
missing, mutable or incompatible namespace/schema fails closed. Reads capture a
SQLite snapshot; strict bounded decoding then validates exact fields/types,
unique ordered check IDs, canonical JSON without duplicate keys, all hashes and
column/body agreement. No provider credentials or arbitrary report payload field
are accepted by these typed records.

The append transaction only compares/inserts bounded prevalidated bytes. Exact
replay returns the same record; changed content under the same execution identity
conflicts. UPDATE, DELETE and replacement INSERT are prohibited. The additional
BEFORE INSERT guard covers both execution and receipt identity collisions even
with SQLite's default `recursive_triggers=0`. Corrupted historical content is
decoded outside the writer transaction before returning a conflict.

Verification is recorded from actual output in the later source checkpoint:
initial14 missing-module failures; initial implementation14 tests with8 Windows
test-fixture cleanup errors caused by SQLite context managers not closing their
connections; explicit closing repairs followed by15PASS. Independent review
then found the INSERT OR REPLACE gap, reproduced by2 failing tests and repaired
with the extra immutable insert guard; final17 focused cases PASS. The first
194-storage/90-owner-backup regression predates that guard and remains historical.
The first after-repair196/90 run also remains historical: independent review found its launcher omitted consumed test/helper bindings and inherited ambient PYTHONPATH. Two actual external guard cases reproduced those defects and passed after repair. A fresh launcher binds the complete public source/test/tool/asset/doc/contract inventory and imported helper, and pins the exact repository src for child and descendant imports. Fresh affected counts and reviewed byte commitments are recorded separately. These2 external guard cases are separate from the17 storage cases and all product qualification counts.
Exact-clean full source/native qualification remains PENDING at this increment.

The source tests use synthetic FIXTURE canonical stores and local SQLite only.
Eight failed-cleanup fixture directories were preserved inside the project after
automatic approval rejected recursive deletion. No private database bytes enter
the Git evidence corpus. No real provider/credential/capital/cloud/forward activity,
runtime LLM call, hosted compute or main merge occurs. Ubuntu native and complete
PAPER/whole-product acceptance remain unexecuted.
