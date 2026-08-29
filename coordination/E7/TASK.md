# E7 Current Task

- task_id: `E7-20260829-099`
- issued_at: `2026-08-29T13:30:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-fp03-protection-trigger-contract-20260829`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, accepted `E7-20260829-098`, `status/e7/MATURE_OKX_FAILURE_PREVENTION_GAP_AUDIT_20260829.md`, `status/PM_E7_098_REVIEW_20260829.md`, `status/PM_MATURE_OKX_BOT_FAILURE_PREVENTION_BASELINE_20260829.md`, current shared contracts/ADRs

## Objective

Define the **shared contract-first safety boundary for FP-03 only**: protection-trigger validity and already-breached-trigger handling for project-r7's OKX `BTC-USDT-SWAP` architecture.

Do not implement E4/E5 runtime behavior in this task. The purpose is to give E5 policy and E4 execution one authoritative, deterministic contract so later domain tasks cannot invent incompatible trigger/freshness semantics.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E7_INTEGRATION.md`;
- `agents/E4_EXECUTION.md`;
- `agents/E5_RISK_POSITION.md`;
- `agents/E1_MARKET_DATA.md` only for current `MarketSnapshot`/freshness semantics;
- `contracts/README.md`;
- `contracts/SHARED_CONTRACTS_V1.md`;
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`;
- current Position lifecycle/execution-evidence binding profiles;
- relevant ADRs including ADR-0010 temporal ordering;
- current `src/position/protection.py`, `src/execution/protection.py`, and relevant tests for evidence only;
- accepted E7-098 FP-03 audit evidence.

Do not read another Worker's TASK mailbox.

## Contract requirements

Create an additive V0.1 protection-trigger validity profile that defines, without provider calls:

1. **Required evidence inputs**
   - exact Position identity/revision or equivalent current lifecycle binding;
   - intended protection action/role and stop trigger;
   - Position side/direction;
   - a canonical current-market observation/evidence reference using existing project market semantics;
   - market observation timestamp/freshness classification;
   - deterministic evaluation timestamp/order consistent with existing temporal rules.

2. **Trigger geometry semantics**
   - define the side-correct condition for a protective trigger to remain actionable relative to the accepted canonical reference price;
   - define boundary/equality behavior explicitly;
   - do not copy Spot `cash`, Spot `reduceOnly`, wallet-dust, or Spot algo `ccy` rules;
   - do not silently choose an OKX provider trigger-price type if the shared project contract does not already authorize one. If provider trigger basis is a broker capability concern, define that as an E4 mapping dependency rather than inventing it here.

3. **Fail-closed outcomes / reason vocabulary**
   At minimum distinguish:
   - valid/actionable protection trigger;
   - stale or unknown market evidence;
   - Position/evidence mismatch or stale Position authority;
   - invalid side/geometry;
   - trigger already breached/crossed before create/replace;
   - unsupported/unknown trigger reference semantics.

   Names may follow existing project vocabulary, but meanings must be deterministic and non-overlapping.

4. **Already-breached behavior**
   - an already-breached/contradictory trigger must never be interpreted as permission to blindly submit/re-submit the same protection mutation;
   - define the required fail-closed handoff category back to E5 lifecycle/reconciliation/emergency policy without making the policy decision on E4's behalf;
   - define that retry requires materially new evidence or a new E5 action, not a tight loop on unchanged truth.

5. **Freshness / temporal binding**
   - reuse existing E1/E7 freshness and ADR-0010 temporal principles where possible;
   - do not invent a new numeric freshness threshold unless an authoritative current policy already defines one;
   - specify how a newer market/Position observation invalidates older trigger-validity evidence.

6. **Ownership boundary**
   - E1 owns canonical market observation/freshness facts;
   - E5 owns whether invalid/breached protection leads to HOLD, EXIT, EMERGENCY_EXIT, RECONCILIATION_REQUIRED, or another approved lifecycle action;
   - E4 owns provider capability/parameter translation and must reject execution that violates the shared validity evidence;
   - E6 may later persist/display validity evidence and reason codes but must not reinterpret them;
   - E7 owns this shared profile and cross-module compatibility.

## Required durable artifacts

Create:

`contracts/PROTECTION_TRIGGER_VALIDITY_PROFILE_V0_1.md`

Update `contracts/README.md` so the new profile and ownership are discoverable.

Create an ADR only if necessary to resolve a genuinely architectural ambiguity; do not create one merely to duplicate the contract profile.

Create:

`status/e7/FP03_PROTECTION_TRIGGER_CONTRACT_HANDOFF_20260829.md`

The handoff must identify:

- exact contract/profile version;
- whether any existing shared profile is amended or only referenced;
- E5 implementation obligations;
- E4 implementation obligations;
- any E1 evidence dependency;
- any E6 persistence/display follow-up;
- exact deterministic test scenarios that later E5/E4 tasks must add, including LONG/SHORT valid, equality boundary, breached trigger, stale market, stale Position evidence, mismatched side, and retry-on-unchanged-evidence rejection;
- whether executable changes will require fresh approved-local credential-free requalification (`YES` expected after E5/E4 implementation);
- provider/credential/PO/capital requirements for this contract task (`NO`).

Update `coordination/E7/STATUS.md` on the task branch.

## Verification boundary

This is a contract/docs task only.

- Do not execute project code/tests.
- Do not create a Local Job Request.
- Do not call OKX/provider endpoints.
- Do not read/request/use credentials.
- Do not modify E4/E5 executable source or tests.
- Do not start SHADOW/PAPER runtime.
- Do not mutate provider/account state or submit/cancel/amend/close orders.
- Do not move/expose capital.
- Do not use GitHub Actions/CI/hosted/GitHub-triggered compute.

Record executable verification as:

`NOT_RUN / NOT REQUIRED FOR CONTRACT-DOCS TASK`

This is not executable PASS.

## Writable scope

Only:

- `contracts/PROTECTION_TRIGGER_VALIDITY_PROFILE_V0_1.md`;
- `contracts/README.md`;
- one E7-owned ADR only if strictly necessary;
- `status/e7/FP03_PROTECTION_TRIGGER_CONTRACT_HANDOFF_20260829.md`;
- `coordination/E7/STATUS.md`.

Do not modify production source, E1-E6 tests/source, provider config, AgentBridge, local action catalog, Product Owner authorization artifacts, risk thresholds, release criteria, or runtime mode.

## Completion

### DONE

Use `DONE` only when the V0.1 shared profile is complete, internally consistent with current market/Position/temporal contracts, and the E5/E4 implementation handoff is precise enough for separate bounded domain tasks.

### PARTIAL

Use `PARTIAL` if an authoritative cross-module ambiguity remains and cannot be resolved safely within E7 contract ownership. Record the exact unresolved dependency and do not guess.

### BLOCKED

Use `BLOCKED` only if authoritative repository requirements conflict such that no safe shared trigger-validity contract can be defined.

Stop after E7-099. Do not self-start E5/E4 implementation, local executable verification, provider verification, AgentBridge work, SHADOW/PAPER, Gate D, LIVE, mutation, order action, or capital movement/exposure.
