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
