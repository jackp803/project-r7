# Product deployment control profile v0.2

This additive application/E6 view/control profile does not widen any v0.1
execution, LF/FP, human approval, preflight or financial-authority rule.

Approval preview is a short readonly actual E6 snapshot of the exact
READY_FOR_APPROVAL strategy revision, registered immutable deployment envelope,
current release, selected E5 policy and sealed E3 assessment. The strict
authenticated query supplies only envelope reference and expected revision.
Source/build/config/risk/capital identities come from these owning records.
Wrong/stale identity, reference, generation or release is denied. Preview data
and financial_confirmation_available do not constitute consent or admission.

Deployment identity is derived by E6 from canonical JSON
`[strategy_id,strategy_version,approval_record_id,envelope_hash]`: the identifier
is `deployment-` followed by the SHA-256 hexadecimal digest. It names original
immutable approval lineage without another lifecycle database. It remains stable
through pause, expiry/revocation and resumption. Rejected consent with no accepted
activation has no deployment; rejected strategy/audit history remains readable.

Authenticated pause delegates only to the existing E6 degrade method using the
original command ID, actor and expected revision. It disables NEW_EXPOSURE and
does not cancel orders/protection, close exposure, renew consent or terminate a
runtime. Original MANAGE_EXISTING still needs its current E6/E7/E5/E4 gates.
Pause remains a fail-closed control independent of new financial admission.

Activation/resumption delegates to the existing named E6 owner. Current server
reauthentication and all original exact-consent/current-release/E7 gates apply.
An audit can select the original ACTIVATE/RESUME operation for receipt recovery,
but the owning method independently matches identity, actor, command, original
revision and evidence. Retrying cannot create a new transition or renew current
permission from historical output. Returned receipts use the actual immutable E6
transition ID/time. Runtime attachment and current admission remain separate.

The Control Center shows original subject/limits, requires reauthentication and
explicit confirmation for financial writes, and submits original hashes/CAS.
Subject/revision/reference changes reset confirmation. Unknown outcomes retain
the original command for reconciliation. FIXTURE can exercise a logical pause
but cannot approve or activate financial authority through HTTP/UI; actual
fixture-owner tests remain explicitly simulated mechanics.

Transient product permits are rechecked after owner reads and at the final
provider effect guard. Mechanical preparation uses the current effect clock.
Expiry during validation is a gate denial before HTTP, not a provider ACK or
ambiguous response. A previously committed dispatch claim is retained and cannot
be blindly resubmitted. No clock check mints or renews a permission.

Real provider/native-vault/supervisor/cloud/forward commissioning is NOT_RUN.
Continuous trading/protection/settlement projections remain S12 work; this
profile and its development checks do not complete S12 or authorize capital.
