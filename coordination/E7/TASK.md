# E7 Current Task

- task_id: `E7-20260824-045`
- issued_at: `2026-08-24T15:42:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-paper-trade-result-integration-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate A evidence PR #33, Gate B static preflight PR #34, protection chain PR #37-#45, close/TradeResult contract PR #46, E5 close producer PR #47, E4 close consumer PR #48, E5 TradeResult builder PR #49, E7 blocker review PR #50, funding evidence contract PR #51, E4 funding producer PR #52, E5 funding consumer PR #53, accepted E4 protection-stop flat-truth PR #54

## Objective

Perform only the E7-owned **static cross-module integration review and deterministic integration/safety test-definition materialization** for the current in-memory Gate B Paper close-to-TradeResult chain.

Use real current production APIs to determine whether all three supported closure paths now compose without synthetic replacement truth:

```text
1. ordinary EXIT
2. EMERGENCY_EXIT
3. full PROTECTION_STOP trigger
```

For each supported path, the intended bounded chain is:

```text
exact E5 authority
-> canonical E4 OrderRequest
-> real PaperBroker submit/fill/order truth
-> real E4 same-position flat Position observation
-> real E4 funding-allocation-v0.1 Paper evidence
-> real E5 build_trade_result(...)
-> POSITION_CLOSED / CLOSED + canonical trade-result-v0.1
```

Stop at static integration/test-definition/release-gate reconciliation. Do **not** implement E1-E6 domain production, E6 persistence/restart/audit, provider/private APIs, approved-local execution, or PAPER/SHADOW/LIVE authorization.

## Accepted prerequisites

```text
PR #46 = close-v0.1 / trade-result-v0.1 contract
PR #47 = E5 EXIT / EMERGENCY_EXIT producer
PR #48 = E4 explicit close consumer + same-position residual/flat truth
PR #49 = E5 TradeResult builder
PR #51 = funding-allocation-v0.1 contract
PR #52 = E4 canonical Paper ZERO_CONFIRMED funding producer
PR #53 = E5 canonical funding consumer / TradeResult audit binding
PR #54 = E4 PROTECTION_STOP same-position full-fill flat truth
```

All executable verification for these chains remains `NOT_RUN`. No prerequisite source/test-definition acceptance is executable PASS.

## Required inspection before editing

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E7_INTEGRATION.md`;
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`;
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`;
- `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`;
- ADR-0005 and ADR-0006;
- current E4 production surfaces:
  - `src/execution/close.py`;
  - `src/execution/protection.py`;
  - `src/execution/funding.py`;
  - `src/execution/gateway.py` / models as needed;
  - `src/brokers/paper.py`;
- current E5 production surfaces:
  - close PositionAction producer/state machine;
  - protection producer/result bridge;
  - `src/position/trade_result.py`;
- current relevant E4/E5 tests and accepted handoffs PR #47-#54;
- `status/RELEASE_GATES.md`, `status/INTEGRATION_STATUS.md` and E7 review artifacts.

### Contract-first rule

If the real production chain cannot compose without a new shared serialized field/enum/authority/financial meaning, stop:

```text
BLOCKED / CONTRACT_OR_SEMANTIC_GAP
next_owner = E7 architecture/contracts
```

If the contract is sufficient but a domain production surface is still missing, stop with exact:

```text
BLOCKED / IMPLEMENTATION_GAP / next_owner = E4 | E5 | E6
```

Do not hand-construct synthetic `OrderResult`, `Fill`, flat Position, funding evidence or TradeResult merely to make an integration definition pass.

## Required integration definitions

### 1. Ordinary EXIT full close

Materialize an E7 integration definition using real APIs for:

```text
known open Position
+ exact ApprovedTradePlan
-> E5 EXIT PositionAction
-> E4 close-v0.1 POSITION_EXIT OrderRequest
-> PaperBroker submit
-> actual full Fill(s)
-> PaperBroker same-position flat observation
-> E4 canonical Paper ZERO_CONFIRMED FundingAllocationEvidence
-> E5 build_trade_result
-> POSITION_CLOSED / CLOSED
```

Assert exact lineage, opposite side, reduce-only MARKET mapping, quantity conservation, fee evidence, funding evidence profile/id/status audit binding and deterministic TradeResult identity.

### 2. EMERGENCY_EXIT full close

Materialize the same real chain for an E5 `EMERGENCY_EXIT` authority from lifecycle `EMERGENCY`.

Assert the emergency authority/reason survives into canonical TradeResult and E4 does not reinterpret risk semantics.

### 3. Full PROTECTION_STOP trigger -> TradeResult

Materialize the real protection-triggered chain without synthesizing flat truth:

```text
actual open Position
-> E5 PROTECT PositionAction
-> E4 protection-v0.1 PROTECTION_STOP request
-> PaperBroker submit/query truth establishing the exact protection path
-> E5 protection lifecycle evidence where required to establish OPEN_PROTECTED
-> actual full PROTECTION_STOP Fill(s)
-> E4 PaperBroker same-position full-fill flat observation from PR #54
-> E4 canonical Paper funding evidence
-> E5 build_trade_result using exact PROTECT authority/request/fills
-> PROTECTION_STOP_FILLED reason
-> POSITION_CLOSED / CLOSED
```

Use the actual E5 protection-result bridge where current system semantics require protection verification before trigger closure. Do not simply edit the source Position lifecycle to `OPEN_PROTECTED` inside the integration definition if the real current production chain can establish it.

If no real production path can establish the required protected lifecycle from current accepted E4/E5 APIs, classify that exact gap; do not bypass it.

### 4. Partial/ambiguous protection remains fail closed

Materialize cross-module definitions proving at least:

- partial PROTECTION_STOP Fill cannot yield a normal `CONSISTENT` residual flat/closure truth;
- zero/untriggered/terminal-failed/ambiguous/degraded protection state cannot produce TradeResult closure;
- `OrderStatus.FILLED` alone remains insufficient without the later same-position flat observation;
- no invalid funding evidence or missing funding evidence can be converted to zero by E5;
- invalid lineage/quantity/fee/funding evidence blocks `POSITION_CLOSED`.

### 5. Funding producer -> consumer compatibility

Use the actual E4 `produce_paper_zero_funding_evidence(...)` output directly as the canonical serialized object passed to E5 `build_trade_result(...)`.

Do not recreate the funding mapping manually in the positive integration path. Verify the exact E4 evidence ID/profile/status reaches TradeResult and `calculated_at`-only audit metadata is not treated as a new financial identity where replay is represented.

### 6. No durable claims

This task does not implement or prove:

- restart recovery;
- durable Position/PositionAction/Order/Fill/FundingAllocationEvidence/TradeResult persistence;
- durable duplicate/conflicting funding-evidence detection;
- immutable audit replay after restart;
- full Paper runtime scheduling/operation.

Those remain E6/E7 later dependencies.

## Required release-gate reconciliation

Update E7-owned integration/release status strictly from static evidence.

If the real current production APIs now materialize all three in-memory closure paths and no additional domain/contract gap remains, classify them as:

```text
IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
executable status = NOT_RUN
```

Never convert them to PASS without approved-local execution evidence.

`Restart/persistence preserves required state` must remain `BLOCKED` unless real E6 durability exists.

`Paper E2E closes to TradeResult and persists audit` must remain `BLOCKED` while E6 durable runtime persistence/audit and approved-local E2E evidence are absent, even if the in-memory close-to-TradeResult chain is statically complete.

If static integration is complete, identify the exact next E6 persistence/restart/audit boundary for PM assignment, including the canonical objects/identities that must survive restart and the funding-evidence conflict/idempotency rule. E7 does not implement that E6 work in this task.

## Required deterministic E7 test definitions

Add/update E7-owned definitions under `tests/integration/**` and/or cross-module `tests/safety/**` covering at minimum:

- ordinary EXIT full in-memory chain to canonical TradeResult;
- EMERGENCY_EXIT full in-memory chain to canonical TradeResult;
- full PROTECTION_STOP trigger through real flat observation and real E4 funding evidence to canonical TradeResult;
- exact funding evidence audit refs in TradeResult;
- deterministic TradeResult replay identity for same immutable evidence;
- `OrderStatus.FILLED` without flat observation cannot finalize;
- partial PROTECTION_STOP cannot finalize;
- ambiguous/degraded/terminal failed protection cannot finalize;
- cross-plan/cross-position/action/Fill/funding lineage mismatch fails closed;
- missing/corrupt funding evidence fails closed;
- quantity conservation and fee evidence remain required;
- no provider/private credentials/network behavior;
- no persistence/restart or release authority is faked.

Use sanitized deterministic fixtures only. Definitions may call real E4/E5 production surfaces; they must not copy production algorithms into E7 test helpers in a way that makes the integration self-fulfilling.

## Writable scope

E7-owned only:

- `tests/integration/**`;
- cross-module `tests/safety/**`;
- `status/INTEGRATION_STATUS.md`;
- `status/RELEASE_GATES.md`;
- E7-specific `status/e7/**` evidence;
- `coordination/E7/STATUS.md` on the target branch;
- contracts/ADR only if a genuine contract gap is discovered and this task is explicitly classified BLOCKED before implementation expansion. Prefer blocker evidence over opportunistic contract edits.

Forbidden:

- E1-E6 production code;
- E6 storage implementation;
- provider/private API/network/credentials;
- `.github/workflows/**` or any GitHub CI/compute;
- PAPER/SHADOW/LIVE authority changes.

## Executable verification

This task is **STATIC / TEST-DEFINITION ONLY**. Do not request or run a Local Runner action in this task.

Record:

```text
project_executable_verification = NOT_RUN
```

and preserve exact future approved-local commands for the relevant E4/E5/integration/safety suites. Do not use GitHub Actions/CI, hosted runners, GitHub-triggered self-hosted compute, Computer Adapter, provider/private APIs, or credentials.

`NOT_RUN` is not PASS.

## Acceptance

### DONE

- all three supported in-memory Paper closure paths are shown through real current production APIs without synthetic replacement truth;
- canonical E4 funding evidence is directly consumable by E5 in the positive paths;
- failure/partial/ambiguous paths remain fail closed;
- release status is reconciled without promoting any `NOT_RUN` to PASS;
- remaining Gate B blockers are stated exactly;
- if no further domain gap remains, next E6 durability/restart/audit requirements are bounded for PM handoff;
- no E1-E6 production or provider/release scope is crossed.

### BLOCKED

- record the exact first non-materialized real dependency and classify it as contract/semantic or E4/E5/E6 implementation gap;
- do not fabricate a synthetic integration success;
- do not start the next dependency yourself.

## Completion / mailbox rule

Commit/push E7-owned tests/evidence/status to `agent/e7-gate-b-paper-trade-result-integration-20260824`.

Worker-owned terminal STATUS must be written/pushed to `coordination/E7/STATUS.md` on that target branch, not main.

Then stop. Do not self-start E6 persistence, approved-local verification, Gate C, PAPER, SHADOW or LIVE.
