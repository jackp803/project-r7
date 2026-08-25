# E6 Gate C OperationalMode / Shadow Durability

Task: `E6-20260825-022`

Authority consumed:

- `contracts-v0.1` / `contracts/SHARED_CONTRACTS_V1.md` OperationalMode baseline;
- accepted Gate C baseline through PR #75;
- Product Owner Gate C / SHADOW-only authorization.

## Scope

This slice implements only E6-authoritative durable OperationalMode state and sanitized Shadow checkpoint/audit/restart behavior.

It does not implement provider transport, authentication/signing, market-data normalization, risk derivation, strategy logic, order planning/submission, account mutation, or LIVE authorization.

## OperationalMode persistence

The accepted shared vocabulary remains exact:

```text
RESEARCH
PAPER
SHADOW
LIVE
PAUSED
LOCKED
```

`operational_mode_transitions` is append-only and revisioned. Every durable row binds:

- previous mode;
- new/current mode;
- UTC change time;
- actor/source;
- reason codes;
- optional shared approval record reference;
- sanitized evidence reference;
- deterministic E6 audit identity/hash.

The supported Gate C service can initialize non-LIVE/non-SHADOW baseline state and can transition only to `SHADOW`, `PAUSED`, or `LOCKED`. `SHADOW` therefore requires an explicit audited transition.

No supported call can initialize or transition into `LIVE`. The migration also rejects any revisioned SQL transition into `LIVE`. The table retains `LIVE` as a distinct baseline value so pre-existing/future-authorized durable state remains representable; the Gate C recovery surface classifies any recovered `LIVE` row as `LIVE_UNAUTHORIZED` and never converts it into execution authority.

`LOCKED -> SHADOW` is rejected by this bounded Gate C surface rather than guessing lock-clear authority.

## Sanitized Shadow checkpoint

`shadow_provider_checkpoints` is an append-only E6 checkpoint history bound to an exact durable SHADOW mode revision.

The supported accepted checkpoint contains only bounded sanitized material:

```text
schema_version
provider = OKX
environment_classification = PRODUCTION_READ_ONLY_SHADOW
regional_hostname_ref
canonical_instrument = BTC_USDT_PERP
provider_instrument = BTC-USDT-SWAP
observed_at
permission_category = read_only
market_healthy
account_config_known
balance_known
position_truth_known
isolated_leverage_known
unexpected_exposure
pending_order_count
unreconciled_fill_count
provider_observation_ref
provider_observation_hash
reason_codes
```

An accepted checkpoint fails closed unless required truth is known, market evidence is healthy, permission is exactly `read_only`, unexpected exposure is false, pending-order count is zero, unreconciled-fill count is zero, and environment/instrument classification matches the accepted Gate C baseline.

The payload surface is exact-field. Raw credentials, passphrases, signatures, tokens, UIDs, API labels, bound IPs, exact balances, provider order/fill IDs, complete provider responses, browser-auth material, provider-presence flags, and similar extra material cannot enter the durable checkpoint.

## Restart freshness

Mode and the last accepted Shadow checkpoint survive database close/reopen exactly.

A persisted pre-restart checkpoint is historical evidence, not proof of current provider truth. Therefore a newly opened `OperationalModeStore` restores the checkpoint but returns:

```text
status = RECONCILIATION_REQUIRED
shadow_planning_safe = false
fresh_reconciliation_required = true
```

until a strictly newer accepted sanitized provider checkpoint is durably recorded in that process session.

Replaying the same old checkpoint after restart is idempotent storage replay and does not mark provider evidence fresh.

Missing or corrupt mode/checkpoint material is fail-closed (`MISSING`, `CONFLICT`, or `RECONCILIATION_REQUIRED`), never false-green.

## Separation rules

- Strategy lifecycle remains a separate Registry concept; `SHADOW` is not added to early StrategyLifecycleState.
- Paper runtime rows are not queried or interpreted as Shadow provider truth.
- Shadow checkpoint material has no submit/order/account-mutation method and cannot transition OperationalMode to LIVE.
- Credential or provider availability metadata cannot promote mode.
- No provider/private network request occurs in this storage slice.

## Migration

`0004_operational_mode_shadow.sql` is additive over the accepted Gate B `0001/0002/0003` migration set. Existing Registry/Paper tables and durability semantics are not modified.

## Verification

Product Owner authorized credential-free approved-local verification for this task, but this ChatGPT GitHub session has no approved local runner/computer execution surface.

```text
local_verification = NOT_RUN
```

Exact future Windows PowerShell commands:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
```

`NOT_RUN != PASS`.

No GitHub Actions/CI/hosted runner/GitHub-triggered compute, provider network, credentials, PAPER runtime start, SHADOW runtime start, LIVE path, order mutation, or capital movement was used.
