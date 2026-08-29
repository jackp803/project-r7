# Bounded Live-Fire Readiness Handoff — E7-20260829-103

## Scope

- task_id: `E7-20260829-103`
- profile: `bounded-live-fire-readiness-v0.1`
- profile artifact: `contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`
- parent shared contract set: `contracts-v0.1 / unchanged`
- task type: `CONTRACT / DOCS / STATUS ONLY`
- executable verification: `NOT_RUN / NOT REQUIRED FOR CONTRACT-DOCS TASK`

This handoff translates the accepted PM 10U readiness plan into one E7-owned fail-closed release/evidence profile. It grants no provider/private access, credentials, provider/account mutation, order action, SHADOW/PAPER runtime, capital exposure, Gate D or LIVE authority.

## Current authoritative state

```text
FP-03 shared contract = ACCEPTED
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

The active blocker remains `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`. E7-103 does not resolve, bypass, retry or soften it.

Historical evidence remains revision-bound:

- Gate B post-remediation local PASS: `d5ddb4cec47c15e8d3ed7045dce4bed043fb6aa8` / 450 tests;
- ADR-0010 credential-free requalification: `8fbf5fcae2eaf44accdf535121d8abf29ef5c93c` / 589 tests;
- historical production read-only Gate C evidence: `ab725965e96cac7a9769fd1ab15a3e626f920b95`;
- none of those create executable/provider PASS for `9462b259...`.

## LF gate definitions

| Gate | Purpose | PASS boundary | Current state |
|---|---|---|---|
| `LF-0_EXACT_REVISION_INFRASTRUCTURE` | Establish exact clean approved-local executable candidate | exact candidate `EXACT_CLEAN` with authoritative local evidence | `BLOCKED` |
| `LF-1_CREDENTIAL_FREE_QUALIFICATION` | Complete deterministic full-matrix qualification on exact candidate | all current required suites PASS on same exact clean candidate, zero provider/credential/mutation/runtime/capital | `NOT_RUN / NOT_PASS` |
| `LF-2_P0_FAILURE_PREVENTION_CLOSURE` | Close FP-02/03/04/05/10/11/16 before provider-capable runtime | all seven P0 invariants implemented + accepted local evidence on exact integrated candidate | `PARTIAL` |
| `LF-3_FAILURE_INJECTION_AND_RECOVERY` | Prove fail-closed ambiguity/restart/reconciliation behavior | full required deterministic matrix PASS locally on exact candidate | `NOT_RUN` |
| `LF-4_PROVIDER_READ_ONLY_VERIFICATION` | Verify current production OKX facts with zero mutation | separate future PO authority + secure credentials + exact-revision sanitized read-only evidence | `NOT_STARTED` |
| `LF-5_SHADOW_AND_PAPER_READINESS` | Prove authorized no-capital runtime/recovery behavior | ADR-0010 consumer migration, watchdog/preflight, provenance, kill-switch separation and full SHADOW/PAPER lifecycle evidence accepted | `NOT_STARTED / NOT_AUTHORIZED` |
| `LF-6_BOUNDED_LIVE_FIRE_AUTHORIZATION` | Permit one future bounded 10U integration/recovery session | LF-0..LF-5 accepted + explicit future PO authorization with concrete hard limits | `NOT_STARTED / NOT_AUTHORIZED` |

Gate-state vocabulary is fixed by the profile: `NOT_STARTED`, `BLOCKED`, `NOT_RUN`, `PARTIAL`, `PASS`, `REJECTED`. `NOT_RUN/PARTIAL/BLOCKED/merge/review/history != PASS`.

## P0 owner/dependency sequencing

### Recommended contract-first order while LF-0 remains blocked

The safest blocker-tolerant work is non-executable contract/design work only:

1. **FP-02 — SWAP action-role capability contract/table**  
   Primary: E4; shared/integration review: E7.  
   Define supported account/margin/position-mode + order-role parameter combinations for ENTRY, PROTECTION_STOP, POSITION_EXIT, EMERGENCY_EXIT and read-only reconciliation. Reject literal Spot `tdMode=cash`, Spot `reduceOnly`, wallet-dust and Spot algo-`ccy` transplants.

2. **FP-16 — runtime preflight identity contract** — may proceed in parallel with FP-02.  
   Primary: E7/E6/external operator.  
   Define exact revision, mode, config generation, process/single-instance identity, heartbeat freshness, allowed action capability and reconciliation-readiness evidence. Keep local paths/process internals out of public evidence.

3. **FP-04 — external/manual provider ownership/reconciliation contract** — may proceed in parallel with FP-02/FP-16.  
   Primary: E4/E5/E6; semantic compatibility: E7.  
   Define provider objects as system-owned, external/untracked, explicitly adoptable under policy, rejected/manual-review, or unknown; no silent adoption.

4. **FP-11 — protection registry/multiplicity contract** after FP-04 ownership semantics.  
   Primary: E4/E6/E5; contract: E7.  
   Define exact Position/action/request/provider linkage, allowed active protection count, missing/multiple/orphan handling and reconciliation rules.

5. **FP-05 — residual/close sizing semantics** after FP-02 provider capability/metadata vocabulary.  
   Primary: E4/E5; E6 visibility.  
   Define actual reducible exposure, provider quantization/minimums, residual classification, stable waiting/reconciliation state and no retry storm.

6. **FP-10 — external/manual close lifecycle convergence** after FP-04 + FP-05 and preferably FP-11 identity/cleanup semantics.  
   Primary: E5/E4/E6; contract integration: E7.  
   Preserve aggregate fills + authoritative flat Position truth as closure; order status alone never closes lifecycle.

FP-03 is already implemented as a merged candidate but remains unqualified. No new FP-03 executable expansion is recommended while LF-0 remains blocked.

### Executable implementation sequence after contracts settle

```text
FP-02 E4 implementation ─┬─> FP-05 E4/E5 implementation ─┐
                         └─> FP-11 provider mapping ───────┤
FP-04 E4/E5/E6 implementation -> FP-11 registry ──────────┤
                               -> FP-10 convergence ────────┤
FP-05 implementation -------------------------------------> FP-10
FP-16 E7/E6/operator implementation (parallel) ------------┤
FP-03 existing E5/E4 candidate -----------------------------┤
                                                           v
                                      exact integrated P0 candidate
                                                           |
                                                           v
                               fresh complete credential-free matrix
```

The exact implementation tasks are future PM/owner assignments; E7-103 issues none.

## Requalification strategy

Every executable P0 change requires fresh local verification appropriate to its domain. For release evidence, the preferred strategy is one final complete credential-free requalification on the exact integrated P0 candidate, after the exact-revision local infrastructure is restored.

This minimizes repeated 14-suite runs without weakening evidence provenance.

If PM chooses to first qualify FP-03 at `9462b259...`, that PASS would remain valid only for that exact revision. Any later combined P0 executable candidate still requires another fresh complete qualification.

## Deterministic evidence / test matrix

| Scenario | Required assertion | Owner(s) |
|---|---|---|
| ACK/PENDING vs Fill | ACK/PENDING does not mutate filled exposure; only Fill/authoritative Position does | E4; E5/E6 consume |
| Ambiguous result | `UNKNOWN/RECONCILIATION_REQUIRED`; reconcile before retry; no blind duplicate | E4/E5 |
| Partial fill | protection/remaining quantity follows actual fill, never requested quantity | E4/E5/E6 |
| Stale market | no trade/protection mutation from stale/unknown market truth | E1/E5/E4 |
| Stale Position | newer broker Position invalidates old action/lifecycle authority | E4/E5/E6 |
| Stale execution evidence | newer OrderResult/Fill invalidates old lifecycle execution binding | E4/E5/E6 |
| LONG/SHORT breached/equality trigger | FP-03 fail closed; equality breached; no blind create/replace | E5/E4 |
| Unchanged breached truth | later clock time alone does not make same failed mutation retryable | E5/E4 |
| Duplicate protection | multiplicity conflict blocks new mutation/exposure until reconciled | E4/E6/E5 |
| Orphan/external protection | classified by FP-04; never silently trusted/adopted | E4/E6/E5 |
| Missing protection | no false `OPEN_PROTECTED`; E5 emergency/reconciliation policy applies | E5/E4 |
| Restart flat | exact preflight + fresh reconciliation required before new exposure | E6/E7/operator |
| Restart open protected | exact lifecycle/execution/protection truth restored and current | E5/E6/E4 |
| Restart open unprotected | no new exposure; E5 emergency/reconciliation policy required | E5/E6/E4 |
| Restart reconciliation-required | remain fail closed; restart does not clear state | E6/E7/E5 |
| Clock skew | unsafe provider/local skew rejects provider-capable progression | E4/E7 |
| ADR-0010 temporal ordering | post-observation decision time; old pre-observation timestamp reuse fails | E7/E5 |
| External/manual order/fill/position | explicit ownership policy; no silent adoption | E4/E5/E6 |
| Close order status without flat truth | lifecycle cannot close; aggregate fills + authoritative flat Position required | E4/E5/E6 |
| Residual below provider actionable size | stable residual/wait/reconciliation state; no tight retry loop | E4/E5/E6 |
| Wrong runtime revision/mode/config/heartbeat | preflight rejects before provider mutation | E7/E6/operator |

LF-3 requires accepted local evidence for the complete applicable matrix on the exact integrated candidate.

## Provider read-only verification boundary

LF-4 is future work requiring separate Product Owner authority and secure local credentials. E7-103 does not authorize or execute it.

A later LF-4 generation must prove, for the exact candidate/configuration:

- provider/API/environment and official hostname classification;
- account level/mode;
- position mode;
- margin/leverage facts needed by FP-02;
- current BTC-USDT-SWAP instrument metadata used by sizing/precision/close/protection rules;
- balance-known classification;
- positions;
- pending/open orders;
- fills and reconciliation checkpoint state;
- external/manual object classifications required by FP-04;
- protection multiplicity/readback facts required by FP-11 where applicable;
- provider/local clock health;
- admitted GET allowlist;
- zero mutation and zero submit capability/results;
- exact candidate revision/configuration binding;
- no secret values in durable evidence.

Historical `ab725965...` provider evidence is not rebound to the new candidate.

## SHADOW/PAPER prerequisites

Before LF-5 can PASS:

- AgentBridge ADR-0010 consumer migration/review accepted;
- FP-16 watchdog/runtime preflight accepted;
- restart obeys durable OperationalMode and fresh reconciliation;
- reporting exposes provenance/source time/freshness/lifecycle revision/last-known-good;
- financial kill switch and operational/reconciliation lock are distinct state planes;
- SHADOW uses real read-only provider observations with separate explicit authority and zero mutation;
- PAPER/simulation exercises complete entry/fill/protection/exit/flat/restart/recovery/failure lifecycle;
- historical consumed SHADOW authorization markers remain non-reusable.

## Future Product Owner authority boundary

Only after LF-0 through LF-5 are accepted may PM request one explicit Product Owner authorization artifact for LF-6.

That future artifact must set concrete bounded values for:

- deposited test capital ceiling: no more than 10 USDT;
- max concurrent positions: no more than 1;
- finite session duration;
- finite provider mutation/order budget;
- maximum realized-loss stop below deposited capital;
- current-metadata/E5-policy-derived leverage/order size/SL distance;
- exact revision/configuration/authorization generation.

It must also preserve:

```text
instrument = BTC-USDT-SWAP
withdrawal/transfer = forbidden
averaging down = forbidden
martingale = forbidden
revenge/increasing size after loss = forbidden
continuous/unbounded retry = forbidden
unknown/desync/protection ambiguity = fail closed / no new exposure
success = evidence for one session only / not recurring LIVE
```

No numeric leverage/order size/SL distance, duration, mutation count or realized-loss amount is authorized by E7-103.

## Live-fire durable evidence lifecycle

A future authorized LF-6 session must preserve sanitized evidence for:

```text
preflight
-> reconcile
-> E5 approval
-> E4 exact binding
-> entry submit
-> ACK
-> fill
-> authoritative Position truth
-> FP-03 trigger validity
-> bounded protection mutation
-> provider protection readback
-> registry/lifecycle reconciliation
-> controlled/protection exit
-> aggregate fills + flat Position truth
-> orphan cleanup verification
-> restart recovery
```

Any unknown, stale, inconsistent or unreconciled stage stops progression and forbids new exposure.

## Recommended next Worker task(s) while LF-0 remains blocked

These recommendations are safe because they are contract/docs-only and require no local code execution, provider access, credentials, runtime, mutation or capital:

1. **E7 + E4 contract task for FP-02** — define the versioned OKX SWAP action-role capability matrix and provider-mapping vocabulary without implementing E4 runtime behavior.
2. **E7 contract task for FP-16** — define the runtime preflight evidence profile; include E6/operator consumer obligations but do not modify AgentBridge/operator source in the same task.
3. **E7 cross-module contract task for FP-04** — define external/manual provider object ownership/reconciliation vocabulary and authority boundaries.

After FP-04 is settled, a separate E7 contract task may define FP-11 registry/multiplicity semantics. FP-05 follows FP-02 vocabulary. FP-10 follows FP-04 + FP-05 and should consume FP-11 cleanup identity if available.

No worker task is issued by E7-103; these are PM handoff recommendations only.

## ADR decision

```text
new ADR required = NO
```

Reason: E7-103 adds a release/readiness evidence profile while preserving existing module authority, lifecycle semantics, risk veto, provider boundaries, ADR-0010 ordering and Product Owner authority. No new architectural dependency direction or state-machine authority is introduced.

A later change to runtime architecture, provider mutation semantics, lifecycle authority or release authority must independently evaluate ADR necessity.

## Verification / safety boundary

```text
project code execution = NOT_RUN / NOT REQUIRED FOR CONTRACT-DOCS TASK
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

`NOT_RUN` is not PASS.

## Completion boundary

E7-103 is complete only as a contract/readiness handoff. It does not self-start FP-02/04/05/10/11/16 implementation, exact-revision preparation, requalification, provider verification, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, mutation, order action or capital movement.