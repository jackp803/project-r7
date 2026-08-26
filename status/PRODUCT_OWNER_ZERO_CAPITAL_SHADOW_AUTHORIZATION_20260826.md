# Product Owner Authorization — Bounded Zero-Capital SHADOW Runtime

- authorized_at: `2026-08-26T15:52:39+08:00`
- authority_source: `Product Owner confirmation in the active local Codex conversation`
- state: `AUTHORIZED / BOUNDED / FAIL-CLOSED`
- current_release_gate: `Gate C — SHADOW_READY = PASS`
- qualified_revision: `ab725965e96cac7a9769fd1ab15a3e626f920b95`

## Authorized phase

The Product Owner authorizes PM to plan and dispatch one bounded **zero-capital SHADOW runtime** session using the accepted Gate C implementation and evidence.

The session may observe market/account state and persist sanitized SHADOW evidence. It must not submit, simulate as provider execution, or mutate any provider/account action.

## Hard runtime boundary

```text
environment                 = OKX production read-only shadow
official REST hostname      = openapi.okx.com
approved computer           = current registered local Windows computer only
maximum session duration    = 30 minutes
maximum HTTPS GET requests  = 300
available capital           = exactly zero
capital exposure            = forbidden
order submission            = forbidden
provider/account mutation   = forbidden
PAPER runtime               = not authorized by this decision
Gate D / LIVE               = not authorized
GitHub compute              = forbidden
```

Only HTTPS GET operations already allowed by the governed read-only adapter may be used. POST, PUT, PATCH, DELETE, order place/cancel/amend/close, leverage or position-mode changes, transfers, deposits, withdrawals, funding actions, and browser/provider UI automation are forbidden.

Credentials may be read only from the existing approved local secure store. Credential values, exact balances, UID, signatures, tokens, cookies, raw private responses, and browser authentication material must not be displayed, committed, or included in evidence.

## Mandatory fail-closed conditions

The session must stop without expanding scope if any of the following occurs:

- available balance is not explicitly observed as zero;
- any unexpected position, exposure, pending order, or unreconciled fill is observed;
- permission is not read-only;
- the hostname, account identity/category, position mode, or clock-health checks fail;
- a mutation or submit path is attempted or cannot be proven structurally disabled;
- the exact qualified revision or clean dedicated worktree cannot be verified;
- the time or GET-request limit is reached;
- credentials, provider responses, or evidence cannot be handled without disclosure.

## PM authority granted

PM may issue the minimum E1-E7 tasks necessary to prepare, execute, review, and reconcile this single bounded SHADOW session. PM must preserve dependency order, Git as SSOT, approved-local execution, canonical AgentBridge actions, durable evidence, and independent E7 review. PM may set stricter limits but may not relax this authorization.

This authorization does not grant a second SHADOW session, recurring/continuous operation, PAPER runtime, Demo execution, provider mutation, order submission, capital movement/exposure, Gate D work, or LIVE. Any such expansion requires a new explicit Product Owner decision.
