# E7 Current Task

- task_id: `E7-20260821-005`
- issued_at: `2026-08-21T10:58:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-e1-okx-review-20260821`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, Product Owner OKX decision

## Objective

Perform static integration review of E1's completed OKX public historical-market-data migration in PR #8 before it is merged into `main`.

E2 and E5 are now implementing the new execution object profiles in parallel; they are outside this review task.

## Review input

- PR: `#8 market-data: migrate V1 public history to OKX`
- branch: `agent/e1-market-data-okx`
- implementation/handoff revision reported by E1: `c782438ae7e895f2304498946970f2ee5dd5b18f`
- handoff: `status/e1/OKX_MIGRATION_HANDOFF.md`
- executable verification: `NOT_RUN`

## Required actions

1. Work only on fresh branch `agent/e7-e1-okx-review-20260821` from current `main`.
2. Statically review PR #8 against the Product Owner OKX decision and unchanged canonical Candle semantics, including:
   - `BTC_USDT_PERP -> BTC-USDT-SWAP` mapping isolated to E1 provider adapter;
   - canonical `1m/15m/1h/4h` mapping to official OKX bar labels;
   - provider `confirm=1` required for final/closed historical candles;
   - `confirm=0` never promoted to closed by local wall-clock inference;
   - UTC and half-open `[open_time, close_time)` behavior;
   - exact-range `after` pagination boundaries;
   - ascending canonical output;
   - duplicate/gap/malformed-data fail-closed behavior;
   - no manufactured candles;
   - no private/account/execution/credential logic;
   - no new Pionex-specific development.
3. Recheck the provider-dependent endpoint/finality/pagination facts against current official OKX documentation. Do not use community sources when official documentation is available.
4. Review E1 test definitions for the above static coverage. Do not execute them in GitHub.
5. Check PR #8 changed-file scope for contract collision, role-scope violation, unsafe default, secrets, workflow/CI additions, or unintended deletion of historical evidence.
6. Persist an E7-owned review artifact and update `coordination/E7/STATUS.md` with:
   - E1 static disposition `PASS | FAIL | BLOCKED`;
   - exact findings/owners if any;
   - PR #8 merge recommendation;
   - executable disposition `NOT_RUN`;
   - release gates unchanged.
7. Do not modify E1 production code in this task. If a defect exists, issue a bounded finding for E1 rather than fixing it yourself.
8. Do not review or modify the in-progress E2/E5 profile implementations in this task.
9. Do not advance Gate A/B/C/D and do not use GitHub Actions/CI/hosted runner/project compute.

## Acceptance

Task is complete when Git contains a static review of PR #8 that clearly states whether the E1 OKX migration is safe to merge into `main`, while preserving `NOT_RUN` for executable evidence.

## Writable scope

- E7-owned review/status/integration documentation
- `coordination/E7/STATUS.md`

## Forbidden scope

- E1/E2/E3/E4/E5/E6 production implementation edits;
- shared-contract changes;
- OKX private/Demo API implementation;
- PAPER/SHADOW/LIVE enablement;
- GitHub compute/CI;
- treating static PASS as executable PASS.

## Completion / status

Persist the review, update STATUS, then stop and wait for PM. Do not merge PR #8 yourself and do not start another review automatically.
