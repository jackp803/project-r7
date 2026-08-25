# E7 Current Task

- task_id: `E7-20260825-074`
- issued_at: `2026-08-25T21:53:00+08:00`
- state: `HOLD`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate C baseline PR #75, accepted Phase-1/2/3 work through PR #81, accepted E6 remediation PR #84, accepted credential-free requalification PR #85 merge `e8d0c956b4e504acb91f6aa9323526d2fea4d2e9`, accepted E7-073 operator-blocker evidence PR #86 merge `5bf0fd9d87c3f6202bbd98c6f0dd10a8eb3073a3`, Product Owner Gate C / SHADOW-only authorization

## Objective

Hold Gate C work after the accepted credential-dependent production read-only verification attempt stopped safely before provider traffic because required local operator prerequisites were not configured.

Current authoritative state:

```text
credential-free Gate C blocker = CLOSED / PASS
E7-073 production read-only verification = BLOCKED / OPERATOR_PREREQUISITES_MISSING
provider traffic = NOT PERFORMED
Gate C = BLOCKED
SHADOW runtime = NOT STARTED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
```

## Operator prerequisites required before PM may issue another verification task

The local operator must complete all of the following outside Git and outside chat:

1. create or confirm a dedicated R7 OKX sub-account for Gate C observation;
2. create API credentials for that sub-account with provider permission `Read only` and with no Trade/Withdraw permission;
3. store key/secret/passphrase only in an ignored local configuration/secret surface or OS/local secret store consumable by the approved AgentBridge/local execution mechanism;
4. explicitly confirm the official OKX REST hostname for the account-registration region in local configuration.

Never place secret values, raw UID/account identifiers, exact balances, provider order/fill IDs, cookies, tokens or browser-auth material into chat, Git, task/status files, screenshots or public evidence.

## Required actions while HOLD

- Preserve the accepted credential-free PASS and E7-073 BLOCKED evidence.
- Do not request or execute another provider verification job until PM replaces this HOLD after the operator confirms prerequisites are complete.
- Do not guess the regional hostname or invent credentials.
- Do not modify production code/tests/contracts/ADRs/provider implementation merely to bypass the operator blocker.
- Do not start PAPER/SHADOW runtime, provider mutation/order submission, Gate D or LIVE.
- Do not use GitHub Actions/CI/hosted/GitHub-triggered compute.

## Writable scope

Only `coordination/E7/STATUS.md` for HOLD acknowledgement if needed.

## Completion

Acknowledge HOLD if needed and stop. Do not self-start another verification attempt, remediation, SHADOW runtime, Gate D or LIVE work.
