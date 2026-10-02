# S10 execution ledger

Task: CODEX-R7-PRODUCTIZATION-MASTER-20261002. Plan: docs/product/v0_2/06_EXECUTION_PLAN.md. Binding spec: docs/product/v0_2/05_PRODUCT_OPERATIONS_UI.md.

BASE: cd540cb (S09 evidence); qualified S09 executable: 08737899f82480e8de2933273eb7a643edb66d74. S09 exact-clean qualification: 33 commands, 1434 tests, no failures/errors/skips, all owned trees reaped; 97 committed evidence blob hashes verified and branch pushed.

S10 is IN_PROGRESS. Execute inline with TDD; one fresh whole-branch review at S16. No real provider calls, remote compute, automatic OAuth enrollment or capital.

1. Actual local authentication: trusted first-run owner creation, Argon2id hashes, opaque server sessions, expiry/revocation, bounded failed-login throttling, CSRF and issuer-local E6 reauthentication.
2. Durable command identity, exact actor/subject/request/revision binding, stale-tab conflicts, immutable receipts and recoverable owner effects outside SQL transactions.
3. Versioned FastAPI DTOs, bounded strict JSON, loopback/Host/Origin checks, sanitized errors and response provenance; no actor/PASS injection.
4. Actual E6/research/intake/PAPER service adapters, durable asynchronous research queue/cancel and truthful GET views. Missing configured owners/transport remain NOT_CONFIGURED/NOT_CONNECTED.
5. Required routes, committed OpenAPI snapshot and affected/full exact-clean qualification, sanitized evidence, push and self-advance to S11.

Ruling: product commands use command_id/expected_revision. Authentication is a session protocol with bounded single-use login identity and session revision; password material and raw tokens never enter the product command ledger or reports. First-run enrollment is trusted local CLI composition, unavailable over HTTP. Fixture sessions cannot authorize real deployment.

Ruling: install FastAPI without standard/cloud/telemetry exporter extras. Runtime product code does not configure an exporter or make remote telemetry calls. Pin FastAPI 0.142.2 and argon2-cffi 25.1.0; native wheel/license verification remains S13.

Ruling: approval DTOs reference trusted locally registered immutable envelopes and actual current E6 subjects; clients cannot submit evidence PASS, actor, roles, financial defaults or an alternative release. Protected remote access remains uncommissioned; loopback plus SSH tunnel is the supported default.

Pre-flight: E6 handles canonical lifecycle/approval CAS and immutable owner commands; API command recovery must replay those same owner IDs. ResearchJournal owns stage effects/trials/OOS; queued jobs must call ResearchService, never duplicate replay/lifecycle logic. PaperService pause disables entries while its separate runtime retains protection. Active SQLite stays local.

Source implementation complete, pending exact-clean qualification. Focused/affected Windows CPython3.12.10 results: product101, application76, registry44, storage153, safety66 all PASS. A final namespace-corruption regression exposed acceptance of the first metadata row. Serialized namespace initialization and reject-ambiguous binding now pass the auth/API/CSRF32-test suite. The original RED also exposed a test connection cleanup error; the fixture now explicitly closes its connection, with no weakened assertion. Final product inventory is determined by the subsequent clean runner.

Actual-owner HTTP coverage scans a sealed package, enqueues without inline replay, completes research through E1/E2/E3/E6 to CANDIDATE, retains cancellation, and reads actual evidence/catalog. PAPER start records the E6 effect with generation0; readonly reads/pause do not attach a runtime. Lost pause acknowledgment stays PREPARED and recovers the same durable effect. E5 published trade results feed the existing E3 metrics without a second slippage debit. Actual LocalAuth reauthentication binds E6 approvals; fixture HTTP financial operations remain denied.

OpenAPI is generated from actual routes and compared by the API drift test. It documents cookie/CSRF and write-only password fields. Operational defaults are explicit NOT_CONFIGURED/NOT_CONNECTED; native CLI/process wiring and current production projections remain S12/S13. No invented runtime health, forward elapsed time, cloud acknowledgment or global flatness. Detailed operator semantics: docs/product/CONTROL_API_V0_2.md. SELF_REVIEW; whole-branch independent review remains S16.
