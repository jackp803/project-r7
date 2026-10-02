# Product runtime preflight v0.2

Additive S12 product implementation under the approved R7 v0.2 master scope.
The legacy `runtime-preflight-v0.1` contract and entry points remain unchanged,
including undefined bounded-live-fire mode policy and rejection of new roles.

`product-runtime-preflight-v0.2` uses the same canonical evidence shape, E7
identity/current-authority/heartbeat/config/FP16/dependency interpreter, and hash
construction. Its only role is `LIVE_RUNTIME`; its only operational mode is LIVE;
its exact authority class is `PERSISTENT_LIVE_RUNTIME`. A bounded-live-fire grant,
PAPER grant, caller PASS or current HTTP status cannot satisfy this role.

The product entry points accept this pinned profile only. Reconciliation and an
actual accepted exact external-consumer/supervisor compatibility proof are
mandatory. Native supervisor verification/commissioning is S13; absence is fail
closed. Evidence remains a pure interpretation, never provider/process/capital
permission. The application must additionally verify current exact E6 approval,
release/build/config/risk/runtime subject and actual E4 capability at every effect.

Real persistent permission has NOT_AUTHORIZED status in this development task.
Synthetic facts prove positive/negative interpreter mechanics only. New-exposure
permission and existing E5 protective management are separately scoped; revoking
entry permission cannot declare flatness or discard an active position. No native
process start, credentials, private request or capital follows from this contract.
