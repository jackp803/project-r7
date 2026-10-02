# S12 execution ledger and provider capability inventory

Task CODEX-R7-PRODUCTIZATION-MASTER-20261002; approved continuous v0.2 plan.
Base c339255; S11 exact-clean executable1ce69a7060fc47c39d16d8db6acb0781066046db
passed33 Python commands/1509 tests and6 pinned UI commands/unit10/browser8.
S12 IN_PROGRESS. No milestone exit or real activation is authorized.

Inventory was made before provider additions. Existing E4:

| Surface | Actual implementation | S12 delivery |
|---|---|---|
| Canonical entry | execution.gateway accepts actual E5 ApprovedTradePlan; MARKET only, deterministic identity | Reuse unchanged |
| Provider size and metadata | okx_sizing verifies linear BTC-USDT-SWAP/contract lot and freshness | Reuse; no quantity enlargement |
| Demo entry, signing, ACK/order/fill parsing | okx_demo exact issued materialization, synthetic transport seam, ambiguous retry structurally disabled | Share mechanical owner code; retain demo-only guard |
| Read-only production observations | okx_shadow fixed bounded endpoints, exact operator-confirmed OKX domain and safety checks | Preserve existing profile |
| FP-02 v0.1 | Four positive ENTRY/READ_ONLY rows; protection/exit/emergency unresolved | Keep v0.1 unchanged; additive explicitly versioned owner-issued provider proof |
| FP-03 | Actual E5 actionable/current LAST_PRICE; legacy provider-basis guard deliberately has no positive path | Reuse current trigger validation; separate v0.2 owner proof for native last trigger |
| FP-04/05 | Actual ownership and current reducible/residual sizing; metadata/applicability binding | Retain shared sizing semantics; explicit additive profile identity, never relabel v0.2 as v0.1 |
| FP-11/10 | Current intended protection set and terminal dependencies | No blind duplicate/orphan cancellation or guessed flatness |
| E6 approval | Exact immutable release/envelope, expiry/revocation, current risk/forward lineage | Public current-permission read through owner; browser audit is not admission |
| E7 runtime | v0.1 exact-clean/process/config/heartbeat/FP16/role authority; no recurring LIVE role | Add pinned v0.2 product role without changing legacy role policy; no bounded permission reused as recurring LIVE |
| Product runtime/native supervisor | PAPER actual owners present; trading composition absent | S12 admission/current projections and durable effects; actual native process commissioning S13 |
| Credentials/HTTP | Runtime-injected redacted structs; no production concrete transport/vault interface | Explicit local secure provider interface, bounded allowlisted HTTPS/no redirects/retries; fake transport only during development |

Public official documentation checked locally on2026-10-03; no private API was called.
[OKX API reference](https://www.okx.com/docs-v5/) documents contract quantities,
net-mode reduceOnly and conditional stop fields. [OKX best practices](https://www.okx.com/docs-v5/trick_en/)
separates ACK from terminal order/fill facts, pending versus historical observations,
and notes client IDs are unique only among pending orders. A successful cancel ACK
does not prove cancellation. The shared last-price semantic maps explicitly to
the native last trigger; a price of-1 requests market execution. These are protocol
inputs, not current account capability/financial approval. Main reference fetch
exceeded the browser content limit; targeted official index results and the fetched
best-practices page were inspected. Regional domains and hedge/cross/other products
remain outside the first production profile, with explicit non-executable gaps.

Approved implementation sequence (inline, tests before code):

1. Add credential/HTTPS request boundary tests: trusted handle only, redacted
   errors, exact host/path/method/body, no redirects/environment proxy/autoretry,
   response byte/shape limits and synthetic signing; observe RED, implement.
2. Add exact current E6/E7 runtime admission tests for absent/wrong/stale/revoked
   approval, code/build/config/policy/process generations, fixture production
   denial and restricted fake-provider verification. Additive v0.2 authority must
   not widen v0.1. No caller PASS/boolean/callback may mint an HTTP authority.
3. Implement actual E4 translation/readback under a bounded net/isolated/linear
   BTC swap profile, with immutable issued preparations. Protection uses actual
   E5 action and current FP03; close uses actual E5 action/FP04/FP05 size. Retain
   unsupported combinations as non-executable with explicit reason codes.
4. Add durable dispatch-before-I/O journal and fake-provider scenarios for lost
   ACK/restart, partial fill, duplicate/orphan protection, residual and exit.
   A DISPATCHING/ambiguous operation is reconciled, never blindly resubmitted;
   stable provider IDs do not provide historical deduplication authority.
5. Wire readonly actual trading/process/protection/alert projections and exact
   approval/deployment ports through actual E6 owners. Existing-position management
   and new-exposure admission remain separate. No browser or research failure
   may erase remaining exposure. Financial approval preview must show exact
   source/build/config/risk/capital subject; stale tabs conflict server-side.
6. Run affected actual owners plus complete credential-free matrix at a new exact
   clean executable; retain sanitized evidence/build identities, commit/push and
   automatically continue S13. Fresh whole-branch independent review is S16.

No real credentials are read, no real provider transport is composed/executed,
no real runtime/cloud/forward/capital is commissioned. Fake HTTP tests prove
request/translation/recovery mechanics only. Actual provider capability and
persistent LIVE authorization remain separate owner acceptance/commissioning.

Foundation implemented and development-verified: bounded production request/HTTPS
and trusted secure-reader interface6 tests; pinned additive E7 profile6 tests;
actual E6 accepted-activation/current-consent/read-snapshot port and transient
E6/E7 admission4 tests. Legacy runtime29, all brokers205, integration90 and
registry44 tests PASS. Missing-module/typed-input/readback-scope/process-permit
failures were observed before their fixes. Imported legacy fixture classes were
kept module-qualified to avoid duplicate discovery. The original29 legacy
preflight tests still execute separately; bounded mode remains undefined.

The current-permission read uses one short readonly SQLite snapshot and closes it
before any effect. NEW_EXPOSURE checks current exact consent; MANAGE_EXISTING
retains original accepted activation/approval after expiry/revocation, never
renewing entry permission. Issuer-local one-second permits recheck actual owners
and bind subject, execution purpose and process identity/generation. Fixture
permits cannot authorize production. HTTPS tests use fake connections and secrets.
Native secure-vault composition and actual supervisor acceptance remain S13.

This is a stable S12 foundation checkpoint pending full exact-clean qualification,
not S12 completion. Continue the provider role/translation/readback/durable effect
and recovery stages above on the same task/branch after this checkpoint.

Exact-clean foundation qualification PASS: executable `370bdcbfaa9a6301b2f88cba722268f775821d41`, commands33, phase1 247, phase2 1278, total1525; see FOUNDATION_RESULT.md and machine report. S12 remains IN_PROGRESS and continues the remaining stages automatically.

Next checkpoint implements additive pure E4 roles/readback and E6 durable dispatch
mechanics. The existing market-entry mapper and FP05 arithmetic are shared behind
pinned legacy wrappers; no v0.1 enum/profile is widened. New actual E5/E4 tests:
close9, entry/close translation4, initial protection4, strict market/algo readback6.
Actual FP11 owner fixtures gate empty/multiple/orphan/unknown/stale sets. Exact
native stop tick/lot representation is required. ACK, partial fill and triggered
child identity stay distinct; private rejection text is discarded. An observed
in-place proof mutation defect was fixed with independently stored fingerprints.
Invalid role/body/naive-clock shapes were observed RED before stable rejection.

E6 dispatch7 tests use actual migrated SQLite files, two concurrent connections,
committed claim/crash/reopen, historical client-ID reservation across runs,
namespace binding and old-process fencing. synchronous=FULL is verified. These
records alone never authorize effects or infer canonical exposure. A recovered
claim cannot obtain a second POST. Run/source/app current owners must still be
composed before any fake or real effect; native credentials/network were not used.

Affected development regression: brokers228, storage160, execution127, position168
PASS. See the explicit profile in
contracts/OKX_PRODUCT_ACTION_ROLE_PROFILE_V0_2.md. Actual application dispatch/
canonical publication, spawned stop child-fill binding, full fake-provider E2E,
readonly projections and approval/control integration remain IN_PROGRESS. This
checkpoint is not S12 completion and does not start S13 or actual runtime.

Exact-clean roles checkpoint PASS: executable `ac2bc686b8f230d3592990242247877b7a4a0053`, commands33, phase1 247, phase2 1308, total1555; see ROLES_RESULT.md and machine report. S12 remains IN_PROGRESS and continues automatically.
