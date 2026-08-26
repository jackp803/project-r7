# Product Owner Reauthorization — One Replacement Zero-Capital SHADOW Session

- authorization_id: `PO-ZERO-CAPITAL-SHADOW-REAUTH-20260826-01`
- authorized_at: `2026-08-26T22:58:40+08:00`
- authority_source: `Product Owner explicit confirmation in the active local Codex conversation`
- authority_text: `我核准再執行一次相同安全範圍的零資金 SHADOW session。`
- state: `AUTHORIZED / BOUNDED / SINGLE REPLACEMENT / NOT YET CONSUMED`
- current_release_gate: `Gate C — SHADOW_READY = PASS`
- qualified_revision: `ab725965e96cac7a9769fd1ab15a3e626f920b95`
- supersedes_for_future_execution: `consumed first-session authority only; historical evidence remains unchanged`

## Authorized phase

The Product Owner authorizes exactly one replacement bounded **zero-capital SHADOW runtime**
session after the fail-closed E7-088 operator defect was repaired and verified. The prior
authorization and its consumption marker remain consumed and must not be deleted, reset,
overwritten, or reinterpreted.

This replacement may observe market/account state and persist sanitized SHADOW evidence. It
must not submit, simulate provider execution, mutate provider/account state, or expose capital.

## Hard runtime boundary

```text
environment                 = OKX production read-only shadow
official REST hostname      = openapi.okx.com
approved computer           = current registered local Windows computer only
qualified executable SHA    = ab725965e96cac7a9769fd1ab15a3e626f920b95
maximum monotonic duration  = 1800 seconds
maximum shared HTTPS GETs   = 300
available capital           = exactly zero
capital exposure            = forbidden
order submission            = forbidden
provider/account mutation   = forbidden
PAPER runtime               = not authorized
recurring SHADOW            = not authorized
Gate D / LIVE               = not authorized
GitHub compute              = forbidden
```

Only HTTPS GET operations already allowed by the governed read-only adapter may be used. POST,
PUT, PATCH, DELETE, order place/cancel/amend/close, leverage or position-mode changes,
transfers, deposits, withdrawals, funding actions, Demo execution, and browser/provider UI
automation are forbidden.

Credentials may be read only from the existing approved local secure store. Credential values,
exact balances, UID/mainUID, signatures, tokens, cookies, raw private responses, provider
order/fill IDs, browser authentication material, and unnecessary local paths must not be
displayed, committed, or included in evidence.

## Mandatory fail-closed conditions

The replacement session must stop without retry or scope expansion if any accepted E7-086
safety condition fails, including if:

- available balance is not explicitly observed as zero;
- any unexpected position, exposure, pending order, or unreconciled fill is observed;
- permission is not exactly read-only;
- hostname, subaccount, account level, position mode, leverage, clock or market health is unsafe or unknown;
- a mutation/submit path is attempted or cannot be proven structurally disabled;
- exact qualified revision, clean worktree, or approved local environment cannot be proven;
- the shared GET budget cannot fit the next complete cycle or the monotonic deadline is reached;
- credentials, provider responses, or evidence cannot remain sanitized;
- any unknown runtime/provider/storage exception prevents proving safe state.

## PM authority granted

PM may review the matching AgentBridge reauthorization registration evidence and issue one new
E7 execution task with a unique request ID using exactly the canonical action
`GATE_C_ZERO_CAPITAL_SHADOW_SESSION`. PM may set stricter limits but may not relax this scope.

If the new authorization's append-only consumption marker is reached, the authority is consumed
regardless of success or fail-closed termination. No retry, third session, recurring/continuous
SHADOW, PAPER, provider mutation, order submission, capital movement/exposure, Gate D, or LIVE
is authorized by this decision.
