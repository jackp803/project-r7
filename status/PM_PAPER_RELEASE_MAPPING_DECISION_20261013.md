# PM decision: ordinary PAPER qualification mappings — 2026-10-13

## Disposition and authority

- Existing task: `CODEX-R7-PRODUCTIZATION-MASTER-20261002`.
- Existing baseline: `r7-product-v0.2`; no replacement task or program.
- Decision: `MAPPINGS_ACCEPTED_WITH_CLARIFICATIONS_FOR_IMPLEMENTATION`.
- Scope: the four technical mapping decisions requested in the existing S09/S12 proposal, under the already authorized v0.2 productization scope.
- Not a qualified executable receipt, E6 test sign-off, strategy promotion, workflow selection, financial approval, permission to merge product code, or whole-product acceptance.
- Ordinary PAPER eligibility: remains unavailable until the owning implementation and required target-specific evidence actually satisfy this profile.
- Real credentials/private-provider calls/orders/capital/LIVE: unchanged, not authorized.

This is the PM's technical disposition for implementation in the existing E6-owned boundaries. It does not impersonate an E6 execution/review result. Preserve canonical validators, E5 veto, namespace separation, and final independent architecture/contract review. A newly demonstrated canonical semantic conflict must be reported specifically rather than bypassed.

Governing authority remains `status/PRODUCT_OWNER_CODEX_R7_V02_SCOPE_AMENDMENT_20261002.md`, the existing master authorization, and `docs/product/v0_2/00_EXECUTION_BASELINE.md` through `07_ACCEPTANCE_MATRIX.json`. This decision resolves the four named proposal ambiguities only; it does not waive any other acceptance requirement.

## Evidence reviewed and its limits

Authoritative main reviewed: `9fd277798b1c51d1bc79b29a61bec81b552efeb1`.
Implementation snapshot reviewed: `9b2fb6551977a493dc4586036a26baf74d2111b4`.
Reported native checkpoint: `d36d916207b3a2ca4b1479c48c238e836def9dcb`.

Reviewed the current proposal and dependency bundle:

- `status/codex/productization/S12/QUALIFIED_PAPER_RELEASE_PROFILE_PROPOSAL.md`
- `status/codex/productization/S09/PRODUCT_USABILITY_DEPENDENCIES_20261008.md`

Cross-checked the actual `ReleaseBinding` in `src/registry/operational_authority.py`, software receipt models/store in `src/storage/qualification.py`, and `src/application/paper/owners.py` / `worker.py`, against APP-01/02 and OPS-01.

The user supplied a 2026-10-13 local demo report: CANDIDATE, REJECTED, and insufficient-evidence outcomes; a FIXTURE position protected, paused, recovered at generation 2, and closed with zero remaining quantity; zero provider calls and real-forward duration. Treat that as USER_REPORTED_DEMONSTRATION. PM has not independently opened the user's localhost interfaces, read the local login file, or rerun the executable. Do not turn the demonstration into whole-product or ordinary-PAPER qualification.

## D1 — fixed software qualification profile

Accept profile ID `r7-qualified-paper-release-v0.2` for per-target software eligibility only. Implement the following fixed, ordered inventory. These are grouped checks over existing acceptance obligations, not seven invented success flags. Each group needs a frozen command/test-case manifest and actual retained outcomes for the exact subject. Its member inventory, target predicate, tool/test identities, and this decision are committed before qualification and included in the profile hash.

| Order / check ID | Required concrete observations | Existing requirement mapping |
|---|---|---|
| 1 / PQR-01 | Complete exact-clean current credential-free source regression, including all applicable legacy LF/FP and new owner/application tests. Test discovery must not silently omit a suite. Positive and negative cases both required. | E2E-03; existing legacy regression obligations |
| 2 / PQR-02 | Actual named-platform native build/install identity; verify source commitment, binary/resources/migrations, pinned dependencies/licenses and UI assets; tampering denied and user data kept outside installation/cloud DB paths. | PLAT-01/02/08; OPS-02 |
| 3 / PQR-03 | Fresh normal public product entrypoints in isolated immutable FIXTURE mode: actual setup/authentication, intake, research/robustness/sealed OOS, CANDIDATE versus genuine REJECTED versus insufficient evidence. Candidate starts a separate Paper owner; negatives deny UI and authenticated API without creating a run. Positive path produces actual owner ACK/fill/protection/pause/restart/exit/flat TradeResult and renders truthful UI. No injected terminal state, factory override or stored PASS. Source coverage includes LONG and SHORT; the native proof must identify the direction actually exercised. | RES-01/02/07; LIFE-02; PAPER-01/03; UI-01/02/03; E2E-01 |
| 4 / PQR-04 | Native malformed/unsupported/conflicting/partial submissions and tactical expiry at discovery, enqueue, research checkpoint and before entry; incomplete sync retries and completed same-ID processing is idempotent. Expiry retains evidence and never abandons open protection. | CLOUD-01/02/03/04/05; STR-09/10; E2E-02 |
| 5 / PQR-05 | Native owner/supervisor exclusivity, stale generation fencing, graceful managed worker/control stop separately from forced cleanup, crash/restart with flat and protected/unprotected states, partial fill and duplicate-event behavior, missing/stale market or protection, consistent private backup and restored inhibition. Research timeout/resource faults must not stop separate protection. Bound capacity and resource measurement on the actual host; do not claim the user's 24GB target from another host. On Ubuntu additionally execute actual unprivileged systemd/service recovery; this subcase is explicitly OS-inapplicable on Windows, not a fabricated Ubuntu PASS. | PLAT-03/04/05/06/07; STR-12; LIFE-04; PAPER-02/04; OPS-01 |
| 6 / PQR-06 | Actual authentication/Host/Origin/CSRF and stale/idempotent-command guards; no cloud/API caller can supply PASS, execution inventory, arbitrary code, release generation or financial authority. Missing/mutated/wrong-subject receipts and current-runtime observations deny admission. Protected receipt storage replay/conflict and immutable namespace tests pass. No real secret material in the retained evidence. | API-01/02; LIFE-03; TRADE-02/04; OPS-02 |
| 7 / PQR-07 | Owner-generated research/Paper reports and durable outbox; simulated versus real elapsed time remains distinct; staged versus verified remote ACK remains distinct; failed publication retries without false ACK or duplicate logical effects; disclosure/redaction policy enforced. Accelerated software tests cannot satisfy real forward qualification. | CLOUD-06/08/09; PAPER-03; UI-03; E2E-01 |

Every group is mandatory on the target with the explicit OS applicability above. No empty inventory, zero-test test command, missing result, failed/error/skip/expected-failure outcome, or unreaped owned process may establish a group PASS. Build/inspection commands legitimately without test counts need their specified actual output/artifact assertions; zero exit alone is insufficient. Preserve failed attempts. A later completed passing attempt is distinct evidence, not deletion of failure history.

Reuse existing tests/tools wherever they satisfy the listed observations. Do not implement a new general-purpose certification platform. The source-to-command/test mapping may be completed by Codex within this fixed inventory, recorded before execution and reviewed with the implementation; it cannot change these required observations or thresholds. No additional PM wake is required merely to choose filenames or register existing commands. Material omissions or changes to this inventory need a separate documented decision.

The internal owning producer executes and binds the checks. Existing software receipt storage remains `SOFTWARE_CHECK_EXECUTION_ONLY`; a generic `.passed` property alone is not inventory completeness or release authority. The adapter must verify exact profile/hash, ordered inventory, artifact bindings and target. No public PASS-import endpoint or additional standalone database.

Full build/regression qualification is per changed software/target subject, not per strategy signal, heartbeat or trade. Runtime performs bounded currentness checks; expensive qualification must not run inside protective management. Metadata-only changes follow the existing explicit compatibility rules, not automatic transitive PASS.

## D2 — initial kind and native identity

Accept initially `NATIVE_QUALIFIED` only for ordinary `LOCAL_RESEARCH` PAPER on the platform actually covered by a complete PQR inventory. Keep `SOURCE_QUALIFIED` unavailable through this new ordinary adapter until a separate convention exists; source development/tests themselves remain allowed.

- `implementation_hash`, `executable_revision`: the measured installed distribution source commitment, exactly reconciled to the owning qualification subject.
- `build_hash`: current `verify_distribution` output, exactly matched to the receipt and installed bytes.
- `capability_hash`: current actual `build_capability_snapshot().snapshot_hash`, consistent with the qualified capability inventory.
- `namespace`: the existing immutable LOCAL_RESEARCH store. Never relabel/copy FIXTURE candidate, approval or trading-journal rows into it.

The producer may test software in an isolated FIXTURE store, but records that provenance explicitly. Such software-check evidence is not real strategy/Paper evidence. Ordinary qualification is a separate software subject checked by the adapter. An intact installation manifest by itself never qualifies anything.

Windows eligibility does not qualify Ubuntu. A per-target Paper software decision does not declare the cross-platform Master program complete or authorize merging its implementation. d36d916 is not automatically qualified by this decision: the current demo does not cover the complete inventory.

## D3 — operational selection, risk and simulator identity

Accept the proposed mapping using a bounded canonical operational-selection envelope. Use existing canonical serialization/hashing, not string concatenation. Its committed schema contains the validated product-config commitment, complete `PaperOwnerSelection.selection_hash`, selected versioned simulator-profile hash and explicit simulator account reference. PaperOwnerSelection already binds simulation, promotion and exact selected risk policy, original submission validity, policy reference, actor and workflow selection. Do not omit those existing fields from validation.

- `config_hash`: hash of that complete versioned operational-selection envelope. Keep it distinct from the process supervisor's product-config hash; retain their explicit correspondence.
- `config_generation`: protected durable generation for that operational selection. Initialize once transactionally at 1; increment on material selection changes; an identical selection is idempotent. Reads do not allocate generations; no missing/invalid/overflow fallback to 1.
- `risk_policy_hash` / `risk_generation`: the exact selected ProductRiskPolicy and its existing explicit generation, validated by E5.
- `provider_profile_hash` / `provider_ref`: pinned local Paper simulator semantics, costs/funding/fill policy and implementation profile; not exchange-private credentials or endpoints.
- `account_ref`: explicit local simulator identity retaining existing `ISOLATED_PER_STRATEGY_RUN` behavior. This decision grants neither shared portfolio accounting nor simultaneous real exposure.

Selection changes invalidate dependent pending starts/permissions. Preserve existing positions and their original risk/binding under E5 management; do not silently rebind or flatten. Configuration change alone does not require rebuilding unchanged software, but does require current selection, strategy-policy compatibility and runtime revalidation under existing gates.

No formal financial defaults are selected here. Test policies, test quantity 0.001, demo prices, account balances and the demo's actor are not approved ordinary settings. Neither user-reported demo success nor this PM document supplies local workflow consent.

## D4 — independent runtime identity and bootstrap

Accept `runtime_generation` from the actual independent `runtime`-role ProcessSupervisor, with current installed source/build and validated product-config binding. Do not borrow a control/research generation, invent a PID, reset a counter, or treat an old immutable observed row as proof that its process still exists. Per-run E6 generations remain separate.

Avoid circular startup: an explicitly configured, qualified native Paper worker may acquire its own process scope and start idle with NO run/exposure. That provides real supervisor identity; only then may the read-only current-release adapter support a guarded PaperStart. The accepted candidate, selected policy/workflow and E6 checks must still pass before attaching a run or producing simulated effects. Idle process startup is not strategy or financial permission.

API reads do not start a worker or allocate generations. Currentness failure blocks new entry; existing management remains under its original E5/E6 rules. Reconciliation and successor fencing must precede recovery. Preserve pause, first-fill anchor, position identity and protection. Restored inhibition is not cleared by an intact build or newly issued software receipt. Do not add automatic restore/resume authority; report any still-unspecified restore reauthorization separately and precisely.

## Immediate continuation / closure of the named PM dependency

The four mapping-design questions above are now decided for implementation. This changes the proposal's mapping decision state, not any binary's qualification state. Codex should cite this main-branch decision rather than editing historical proposal or demo evidence to pretend they were previously accepted. Keep separate fields for mapping design accepted, issuer/adapter implemented, software target qualified, user workflow selected, and actual real-time forward observed.

Continue the SAME task/branch from the latest safe checkpoint:

1. Implement the owning fixed-inventory producer/current-release adapter and ordinary selected Paper owner wiring using the existing E6 store and current supervisor. Preserve the successful public FIXTURE path as regression, not the permanent only usable mode.
2. Complete native expiry/intake, graceful-stop/recovery/resource/capacity and current target evidence. Exercise a genuine positive admission and negative gates; do not only demonstrate perpetual denial.
3. Finish normal configuration and unattended supervision through the existing product entrypoints. A user should not need to hand-edit DB state or repeatedly launch separate workers for normal operation. One documented first-time secure setup is distinct from everyday operation.
4. Continue Ubuntu preparation/evidence and the full inherited/current acceptance mapping. Unavailable approved hosts remain NOT_RUN without silently reducing supported targets.

Real cloud, real public dataset commissioning and actual elapsed forward observation remain separately evidenced; no new account/OAuth/machine installation or private-provider authorization is inferred. No need to repeat the already reported demo solely to restate its three outcomes; rerun impacted cases when source/build changes require it.

Do not block unrelated implementation on missing external environments. Do not force a real strategy to pass or use financial activation to close software acceptance. PM has not started/restarted Codex or the user's running Control Centers as part of this review.
