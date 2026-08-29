# E7 Current Task

- task_id: `E7-20260829-103`
- issued_at: `2026-08-29T14:45:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-bounded-live-fire-readiness-profile-20260829`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, `status/PM_10U_BOUNDED_LIVE_FIRE_READINESS_PLAN_20260829.md`, `status/e7/MATURE_OKX_FAILURE_PREVENTION_GAP_AUDIT_20260829.md`, accepted FP-03 contract/candidates, and the active exact-revision preparation blocker

## Objective

Create the shared **bounded live-fire readiness/release profile** that defines what R7 must prove before PM may even request Product Owner authorization for a future 10 USDT real-money end-to-end integration session.

This is a contract/docs/status task only. It does **not** authorize provider/private access, credentials, provider/account mutation, order submission, SHADOW/PAPER runtime, capital exposure, Gate D, or LIVE. It must preserve the active FP-03 exact-revision preparation blocker and every current `NOT_RUN / NOT_PASS` classification.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E7_INTEGRATION.md`;
- `agents/PROJECT_MANAGER.md`;
- `contracts/README.md`;
- current Position lifecycle / execution evidence / protection trigger validity profiles;
- `status/PM_10U_BOUNDED_LIVE_FIRE_READINESS_PLAN_20260829.md`;
- `status/PM_MATURE_OKX_BOT_FAILURE_PREVENTION_BASELINE_20260829.md`;
- `status/e7/MATURE_OKX_FAILURE_PREVENTION_GAP_AUDIT_20260829.md`;
- `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`;
- current accepted Gate B/Gate C credential-free/read-only evidence and ADR-0010 only as needed to preserve revision/authority boundaries.

Do not read or execute another Worker's TASK mailbox.

## Required profile

Create:

`contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`

Profile identifier:

`bounded-live-fire-readiness-v0.1`

The profile must be fail-closed and define at minimum:

### 1. Readiness gates LF-0 through LF-6

Preserve the PM plan stages as distinct evidence gates:

- `LF-0_EXACT_REVISION_INFRASTRUCTURE`
- `LF-1_CREDENTIAL_FREE_QUALIFICATION`
- `LF-2_P0_FAILURE_PREVENTION_CLOSURE`
- `LF-3_FAILURE_INJECTION_AND_RECOVERY`
- `LF-4_PROVIDER_READ_ONLY_VERIFICATION`
- `LF-5_SHADOW_AND_PAPER_READINESS`
- `LF-6_BOUNDED_LIVE_FIRE_AUTHORIZATION`

Define stable gate states such as:

- `NOT_STARTED`
- `BLOCKED`
- `NOT_RUN`
- `PARTIAL`
- `PASS`
- `REJECTED`

Do not make `NOT_RUN`, `PARTIAL`, merge status, design review, or historical evidence equivalent to `PASS`.

### 2. Exact revision/evidence binding

Every executable/read-only/runtime/live-fire gate must bind to the exact project revision/configuration/evidence generation it actually tested.

Historical provider or qualification evidence from another revision may not be rebound by similarity or by unchanged-looking code.

Docs-only revisions may be cited as governance evidence but must never create executable PASS for an unqualified executable revision.

### 3. P0 failure-prevention closure map

Map the accepted mature-bot P0 items into required pre-provider-runtime closure:

- FP-02 SWAP action-role capability matrix;
- FP-03 protection-trigger geometry;
- FP-04 external/manual provider activity ownership/reconciliation;
- FP-05 provider-native close/residual quantity handling;
- FP-10 authoritative external/manual close lifecycle convergence;
- FP-11 unique active-protection registry/multiplicity reconciliation;
- FP-16 runtime process/revision/mode/heartbeat preflight.

For each item define:

- primary owner(s);
- cross-module dependency owner(s);
- smallest safe implementation boundary;
- deterministic tests/evidence required;
- whether fresh credential-free requalification is required after executable changes;
- whether later provider/private verification is required;
- explicit statement that provider credentials/capital are not required for deterministic implementation unless genuinely unavoidable.

### 4. Required sequencing / dependency graph

Produce the safest implementation order that minimizes cross-module ambiguity and repeated requalification.

At minimum evaluate and either accept or replace this dependency hypothesis with evidence:

```text
FP-02 capability contract/table -> E4 implementation
FP-16 runtime preflight contract -> E7/E6/external operator implementation
FP-04 ownership/reconciliation policy -> E5/E4/E6 implementation
FP-11 protection registry/multiplicity contract -> E4/E6/E5 implementation
FP-05 residual/close sizing semantics -> E4/E5 implementation
FP-10 close lifecycle convergence -> E5/E4/E6 implementation
then combined fresh credential-free qualification
```

If dependencies permit parallel work, state exactly which tasks are independent. Do not assign executable work in this E7 task; only define the sequencing.

### 5. Failure-injection/recovery evidence matrix

Define the required deterministic local scenarios before provider mutation may be proposed, including at least:

- ACK/pending vs fill truth;
- ambiguous outcome modeling;
- partial fill;
- stale market/Position/execution evidence;
- breached/equality protection trigger;
- duplicate/orphan/missing protection;
- restart flat/open-protected/open-unprotected/reconciliation-required;
- unchanged failure evidence cannot create unbounded retry;
- clock/temporal ordering;
- external/manual provider objects are not silently adopted;
- close requires authoritative flat truth, not only order status.

Map each scenario to expected fail-closed state/evidence owner.

### 6. Provider read-only boundary

Define provider read-only verification as a separate gate requiring its own future Product Owner authority/secure credentials, with zero mutation.

List the minimum facts that later read-only verification must prove for the exact candidate revision, including account/position/margin mode, instrument metadata, balances, positions, pending orders, fills/reconciliation state, provider/local clock health, GET allowlist, and zero mutation capability.

Do not authorize or invoke it.

### 7. SHADOW/PAPER boundary

Define explicit prerequisites, including ADR-0010 AgentBridge consumer migration/review, watchdog/restart compliance, current-state provenance/freshness, distinct financial kill switch vs operational lock, and full lifecycle/recovery simulation.

Historical consumed SHADOW authorizations remain non-reusable.

### 8. Future 10 USDT live-fire boundary

Define a bounded session as an integration/recovery qualification, **not strategy deployment**.

The profile must require a future explicit Product Owner authorization artifact before any provider mutation/capital exposure and must require concrete bounded values before authorization for:

- deposited test capital ceiling;
- maximum concurrent positions;
- maximum session duration;
- maximum provider mutations/orders;
- maximum realized-loss stop;
- leverage/size derived from current OKX metadata + E5 risk policy rather than guessed now;
- instrument fixed to BTC-USDT-SWAP unless a later contract changes it;
- no averaging down, martingale, revenge/increasing size after loss, or continuous unbounded retries;
- unknown/desync/protection ambiguity -> immediate fail-closed/no new exposure;
- withdrawal/transfer capability forbidden;
- successful bounded session does not imply recurring LIVE authorization.

Do not invent numeric leverage/order size/SL distance or a realized-loss amount beyond the 10 USDT deposited-capital ceiling stated by the PM plan; those values require later current provider metadata/risk evidence and explicit Product Owner authorization.

### 9. Live-fire evidence lifecycle

Define required durable evidence for:

preflight -> reconcile -> E5 approval -> E4 exact binding -> entry submit -> ACK -> fill -> Position truth -> FP-03 -> protection mutation -> provider readback -> registry/lifecycle reconciliation -> controlled/protection exit -> flat truth -> orphan cleanup -> restart recovery.

At any unknown/inconsistent stage, no new exposure is permitted.

### 10. Current-state declaration

The profile/handoff must explicitly record current state as of this task:

```text
FP-03 combined candidate = IMPLEMENTED / UNQUALIFIED
candidate revision = 9462b2594675b2e28388f55a2af189100b7cbdfc
exact clean candidate = NOT_ESTABLISHED
credential-free combined qualification = NOT_RUN / NOT_PASS
active blocker = PREPARE_EXACT_REVISION local allowlist/infrastructure
provider-facing verification on candidate = NOT_RUN / NOT_INFERRED
SHADOW/PAPER = NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
```

## Required artifacts

- `contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`;
- update `contracts/README.md`;
- `status/e7/BOUNDED_LIVE_FIRE_READINESS_HANDOFF_20260829.md` containing:
  - exact gate definitions;
  - owner/dependency sequencing for FP-02/04/05/10/11/16 plus FP-03 qualification;
  - deterministic evidence/test matrix;
  - explicit future Product Owner authority boundaries;
  - recommended next Worker task(s) that are safe while the exact-revision infrastructure blocker remains, but **do not issue or execute those tasks yourself**;
  - statement whether any new ADR is genuinely required.
- update `coordination/E7/STATUS.md`.

An ADR is optional only if an architectural decision cannot be represented by the existing governance/profiles. Do not create one merely for documentation volume.

## Verification boundary

This is contract/docs/status only:

```text
project code execution = NOT_RUN / NOT REQUIRED
Local Job Request = NONE
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER runtime = NOT_STARTED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

Record `NOT_RUN / NOT REQUIRED FOR CONTRACT-DOCS TASK`; do not call it PASS.

## Writable scope

Only:

- `contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`;
- `contracts/README.md`;
- at most one E7 ADR if genuinely required;
- `status/e7/BOUNDED_LIVE_FIRE_READINESS_HANDOFF_20260829.md`;
- `coordination/E7/STATUS.md`.

Do not modify executable source/tests, another worker's files, AgentBridge, local action catalog, provider config/credentials, authorization artifacts, risk limits, leverage/capital thresholds, or release status to claim readiness.

## Result classification

### DONE

Use DONE only if the versioned readiness profile and handoff are complete, internally consistent with current governance/contracts, preserve the active infrastructure blocker, and do not grant runtime/capital authority.

### PARTIAL

Use PARTIAL if a bounded shared-contract ambiguity is discovered that prevents deterministic gate/owner definition. Record the ambiguity and do not invent semantics.

### BLOCKED

Use BLOCKED only if current authoritative repository evidence is insufficient or contradictory enough that the profile cannot be safely defined.

## Completion

Read latest `main`, verify wake task ID `E7-20260829-103`, execute only this docs-only task, persist evidence, update STATUS, commit/push to the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start FP-02/04/05/10/11/16 implementation, exact-revision preparation, credential-free requalification, provider verification, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, mutation, order action, or capital movement/exposure.
