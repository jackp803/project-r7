# Engineering Handoff Template

Use this format whenever one GPT engineer finishes a task, transfers work to another role, or asks E7 / Project Manager for review.

## Handoff Header

- **Agent:** E# / role name
- **Branch:**
- **Commit / PR:**
- **Task:**
- **Status:** COMPLETE / PARTIAL / BLOCKED / NEEDS_REVIEW

## 1. Objective

State the exact requested outcome and what was intentionally out of scope.

## 2. Changes Made

List the implementation/documentation changes in concrete terms.

## 3. Files Changed

List paths grouped by created / modified / deleted.

## 4. Contracts

### Consumed

List shared contracts/interfaces consumed by this work.

### Produced

List outputs exposed to other modules.

### Contract Change Requested

If applicable, describe the requested change. Domain agents must not silently modify shared semantics.

## 5. Tests

State exact tests run and results.

Example:

- Unit: PASS — 28/28
- Integration: PASS — 6/6
- Safety: NOT APPLICABLE
- Manual verification: describe what was verified

Never write only "tests pass" without identifying what was run.

## 6. Acceptance Criteria

For each acceptance criterion, state PASS / FAIL and supporting evidence.

## 7. Known Limitations

Describe behavior not yet supported, assumptions, temporary stubs, unsupported edge cases, or technical debt.

## 8. Dependencies / Blockers

Name the responsible role where possible.

Example:

- E7 must approve `Candle.close_time` semantics before E2 can consume the new field.
- E4 private Futures API work is blocked until account/API access is available.

## 9. Security / Live-Trading Impact

State one of:

- NONE
- PUBLIC-REPO SECURITY RELEVANT
- LIVE-TRADING SAFETY RELEVANT
- BOTH

Explain any implications. Never include secrets in this section.

## 10. Requested Next Action

Specify exactly what should happen next and which role should own it.

## 11. Bug Handoff to Codex

If the work is complete in design but a reproducible defect remains, provide:

- Bug ID/title
- Expected behavior
- Actual behavior
- Reproduction steps
- Failing tests
- Suspected affected files
- Writable scope for Codex
- Explicit instruction: **bug fix only; no architecture redesign unless separately approved**
