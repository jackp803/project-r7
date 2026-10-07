# Bounded historical PAPER publication composition

Parent authority: existing continuous CODEX-R7-PRODUCTIZATION-MASTER-20261002,
S14 cloud/feedback and S12 independent worker composition. Accepted source
checkpoint e293a947f886d9814c89983fd9e03151c1695788, evidence HEAD885d531.

Compose the already implemented PaperFeedbackOutbox into cloud-publish-outbox.
Use the configured existing canonical E6 database, existing cloud host scope,
copy-only transport and one total batch limit shared with intake and research.
Keep intake then research priority. Open the PAPER journal only when the
existing database is present and a positive batch budget remains; no new DB.
Publishing historical committed reports must not attach a runtime, renew a
process lease, compute a new report, change a checkpoint or grant authority.
COMPLETE continues to mean this bounded batch completed, not global queue empty.

Owned changes: src/application/cli.py; new
tests/product/test_paper_feedback_cli.py; existing PAPER feedback implementation
documentation; existing storage/_sqlite_registry.py and storage/paper_process.py
existing-only connection option with tests/storage/test_paper_process_existing.py.
The initial independent review found a missing-store race in the creating
opener; repair uses SQLite URI mode=rw, not a check-then-open filesystem guard.
Default owner initialization remains unchanged. Codex performs all edits. The existing independent reviewer is
read-only; preserve others' work and do not reset the branch.

1. Add real-owner historical fixture tests: configured-store publication and
   idempotency without runtime attachment; outage/retry; immutable conflict;
   single shared three-outbox budget; absent DB; exhausted budget; scope denial.
2. Observe intended RED before modifying the CLI. Retain owned/reaped source
   diagnostics and unchanged runner/test/source bindings.
3. Add minimal CLI composition, then focused and affected regression GREEN.
4. Independent bounded source/test/runner review; address material findings.
5. Commit an exact executable checkpoint, qualify CLEAN with original full
   source limits and separate native/browser scopes, retain and push evidence.

All execution is local Windows and controlled fake transport. No real cloud,
provider/private API, credentials, capital, financial release issuance or
normal continuous PAPER start is authorized by this increment. The proposed
production qualification profile remains non-active; source/native historical
publication evidence does not activate it. Ubuntu and real commissioning
remain NOT_RUN until actually executed.
