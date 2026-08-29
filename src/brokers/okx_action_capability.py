from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

CAPABILITY_PROFILE_VERSION = "okx-swap-action-role-capability-v0.1"

REPO_EVIDENCED = "REPO_EVIDENCED"
UNRESOLVED_FAIL_CLOSED = "UNRESOLVED_FAIL_CLOSED"
FORBIDDEN = "FORBIDDEN"
NOT_APPLICABLE = "NOT_APPLICABLE"

ENTRY = "ENTRY"
PROTECTION_STOP = "PROTECTION_STOP"
POSITION_EXIT = "POSITION_EXIT"
EMERGENCY_EXIT = "EMERGENCY_EXIT"
READ_ONLY_RECONCILIATION = "READ_ONLY_RECONCILIATION"

ENTRY_OPERATION = "MUTATION: MARKET_ORDER_CREATE"
PROTECTION_OPERATION = "MUTATION: PROTECTION_TRIGGER_CREATE"
POSITION_EXIT_OPERATION = "MUTATION: REDUCE_POSITION_MARKET"
EMERGENCY_EXIT_OPERATION = "MUTATION: REDUCE_POSITION_MARKET_EMERGENCY"
READ_ONLY_OPERATION = "GET: OBSERVATION_ONLY"

OKX_PROVIDER = "OKX"
OKX_API_VERSION = "V5"
CANONICAL_SYMBOL = "BTC_USDT_PERP"
OKX_INSTRUMENT_ID = "BTC-USDT-SWAP"
OKX_INST_TYPE = "SWAP"
ACCOUNT_LEVEL = "2"
ISOLATED = "isolated"
NET_MODE = "net_mode"
LONG_SHORT_MODE = "long_short_mode"

CURRENT = "CURRENT"
UNKNOWN = "UNKNOWN"
RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
NOT_APPLICABLE_STATUS = "NOT_APPLICABLE"

FP03_ACTIONABLE = "ACTIONABLE"
FP11_CONVERGED = "CONVERGED_EXACTLY_ONE_INTENDED"
_FP05_SIZING_PROVEN = frozenset(
    {
        "FULLY_REDUCIBLE",
        "PARTIALLY_REDUCIBLE",
        "RESIDUAL_NONZERO_REPRESENTABLE",
    }
)

OKX_SWAP_CAPABILITY_PROFILE_UNSUPPORTED = "OKX_SWAP_CAPABILITY_PROFILE_UNSUPPORTED"
OKX_SWAP_ACTION_ROLE_UNSUPPORTED = "OKX_SWAP_ACTION_ROLE_UNSUPPORTED"
OKX_SWAP_INSTRUMENT_UNSUPPORTED = "OKX_SWAP_INSTRUMENT_UNSUPPORTED"
OKX_SWAP_ACCOUNT_LEVEL_UNSUPPORTED = "OKX_SWAP_ACCOUNT_LEVEL_UNSUPPORTED"
OKX_SWAP_POSITION_MODE_UNSUPPORTED = "OKX_SWAP_POSITION_MODE_UNSUPPORTED"
OKX_SWAP_MARGIN_MODE_UNSUPPORTED = "OKX_SWAP_MARGIN_MODE_UNSUPPORTED"
OKX_SWAP_SPOT_TRADE_MODE_FORBIDDEN = "OKX_SWAP_SPOT_TRADE_MODE_FORBIDDEN"
OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN = "OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN"
OKX_SWAP_CALLER_CAPABILITY_ASSERTION_REJECTED = "OKX_SWAP_CALLER_CAPABILITY_ASSERTION_REJECTED"
OKX_SWAP_TRIGGER_BASIS_UNPROVEN = "OKX_SWAP_TRIGGER_BASIS_UNPROVEN"
OKX_SWAP_REDUCIBLE_SIZE_UNPROVEN = "OKX_SWAP_REDUCIBLE_SIZE_UNPROVEN"
OKX_SWAP_PROTECTION_REGISTRY_NOT_CURRENT = "OKX_SWAP_PROTECTION_REGISTRY_NOT_CURRENT"
OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN = "OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN"
OKX_SWAP_RECONCILIATION_REQUIRED = "OKX_SWAP_RECONCILIATION_REQUIRED"

_REASON_ORDER = (
    OKX_SWAP_CAPABILITY_PROFILE_UNSUPPORTED,
    OKX_SWAP_ACTION_ROLE_UNSUPPORTED,
    OKX_SWAP_INSTRUMENT_UNSUPPORTED,
    OKX_SWAP_ACCOUNT_LEVEL_UNSUPPORTED,
    OKX_SWAP_POSITION_MODE_UNSUPPORTED,
    OKX_SWAP_MARGIN_MODE_UNSUPPORTED,
    OKX_SWAP_SPOT_TRADE_MODE_FORBIDDEN,
    OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN,
    OKX_SWAP_CALLER_CAPABILITY_ASSERTION_REJECTED,
    OKX_SWAP_TRIGGER_BASIS_UNPROVEN,
    OKX_SWAP_REDUCIBLE_SIZE_UNPROVEN,
    OKX_SWAP_PROTECTION_REGISTRY_NOT_CURRENT,
    OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN,
    OKX_SWAP_RECONCILIATION_REQUIRED,
)
_REASON_INDEX = {value: index for index, value in enumerate(_REASON_ORDER)}

_SUPPORTED_ROLES = frozenset(
    {ENTRY, PROTECTION_STOP, POSITION_EXIT, EMERGENCY_EXIT, READ_ONLY_RECONCILIATION}
)
_SUPPORTED_POSITION_MODES = frozenset({NET_MODE, LONG_SHORT_MODE})
_MUTATION_ROLES = frozenset({ENTRY, PROTECTION_STOP, POSITION_EXIT, EMERGENCY_EXIT})
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID_RE = re.compile(r"^okxswapcap_[0-9a-f]{64}$")

# E4-owner-authoritative immutable provenance for the only four positive rows.
# These values are repository identity, not caller capability assertions and not
# provider verification. A caller may present them for comparison, but cannot
# choose a different ref/generation and still obtain REPO_EVIDENCED.
_OWNER_ROW_PROVENANCE = {
    (ENTRY, NET_MODE): (
        "e4-repo-fieldset:okx-v5:BTC-USDT-SWAP:ENTRY:net_mode:v0.1",
        "e4-repo-generation:okx-swap-action-role-capability-v0.1:ENTRY:net_mode:1",
    ),
    (ENTRY, LONG_SHORT_MODE): (
        "e4-repo-fieldset:okx-v5:BTC-USDT-SWAP:ENTRY:long_short_mode:v0.1",
        "e4-repo-generation:okx-swap-action-role-capability-v0.1:ENTRY:long_short_mode:1",
    ),
    (READ_ONLY_RECONCILIATION, NET_MODE): (
        "e4-repo-fieldset:okx-v5:BTC-USDT-SWAP:READ_ONLY_RECONCILIATION:net_mode:v0.1",
        "e4-repo-generation:okx-swap-action-role-capability-v0.1:READ_ONLY_RECONCILIATION:net_mode:1",
    ),
    (READ_ONLY_RECONCILIATION, LONG_SHORT_MODE): (
        "e4-repo-fieldset:okx-v5:BTC-USDT-SWAP:READ_ONLY_RECONCILIATION:long_short_mode:v0.1",
        "e4-repo-generation:okx-swap-action-role-capability-v0.1:READ_ONLY_RECONCILIATION:long_short_mode:1",
    ),
}


class OKXActionCapabilityError(ValueError):
    """Fail-closed provider-local FP-02 resolver error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class OKXActionCapabilityFacts:
    capability_profile_version: str
    action_role: str
    provider: str
    api_version: str
    canonical_symbol: str
    provider_instrument_id: str
    inst_type: str
    account_level: str
    position_mode: str
    margin_mode: str
    operation_class: str
    evaluated_at: str | datetime
    provider_fieldset_ref: str | None = None
    provider_fieldset_hash: str | None = None
    provider_fieldset_generation_id: str | None = None
    provider_fieldset: Mapping[str, Any] | None = None
    reconciliation_status: str = CURRENT
    fp03_trigger_validity_ref: str | None = None
    fp03_trigger_validity_status: str = NOT_APPLICABLE_STATUS
    fp03_trigger_validity_currentness: str = NOT_APPLICABLE_STATUS
    fp05_close_sizing_ref: str | None = None
    fp05_close_sizing_status: str = NOT_APPLICABLE_STATUS
    fp05_close_sizing_currentness: str = NOT_APPLICABLE_STATUS
    fp11_registry_ref: str | None = None
    fp11_registry_status: str = NOT_APPLICABLE_STATUS
    fp11_registry_currentness: str = NOT_APPLICABLE_STATUS
    caller_capability_assertion: Any = None


def _canonicalize(value: Any) -> Any:
    if isinstance(value, datetime):
        return _utc_text(value, "datetime")
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise OKXActionCapabilityError("NONCANONICAL_KEY", "mapping keys must be strings")
            result[key] = _canonicalize(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, float):
        raise OKXActionCapabilityError("BINARY_FLOAT_FORBIDDEN", "binary floats are forbidden")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise OKXActionCapabilityError(
        "NONCANONICAL_VALUE",
        f"unsupported canonical value: {type(value).__name__}",
    )


def canonical_okx_action_capability_json(value: Any) -> str:
    return json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_okx_action_capability_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_okx_action_capability_json(value).encode("utf-8")
    ).hexdigest()


def _utc_text(value: str | datetime, field: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise OKXActionCapabilityError("INVALID_TIMESTAMP", f"{field} must be UTC")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if not isinstance(value, str) or not value.endswith("Z"):
        raise OKXActionCapabilityError("INVALID_TIMESTAMP", f"{field} must be RFC3339 UTC Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise OKXActionCapabilityError("INVALID_TIMESTAMP", f"{field} is invalid") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise OKXActionCapabilityError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise OKXActionCapabilityError("INVALID_TEXT", f"{field} must be non-empty canonical text")
    return value


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _text(value, field)


def _optional_hash(value: Any, field: str) -> str | None:
    if value is None:
        return None
    text = _text(value, field)
    if _HASH_RE.fullmatch(text) is None:
        raise OKXActionCapabilityError("INVALID_HASH", f"{field} must be sha256:<lowercase hex>")
    return text


def _sorted_reasons(values: list[str]) -> list[str]:
    if any(value not in _REASON_INDEX for value in values):
        raise OKXActionCapabilityError("UNKNOWN_REASON", "reason outside accepted FP-02 vocabulary")
    return sorted(set(values), key=_REASON_INDEX.__getitem__)


def _entry_fieldset(position_mode: str) -> dict[str, Any]:
    if position_mode == NET_MODE:
        pos_side_rule = "BUY=net|SELL=net"
    elif position_mode == LONG_SHORT_MODE:
        pos_side_rule = "BUY=long|SELL=short"
    else:
        raise OKXActionCapabilityError(
            OKX_SWAP_POSITION_MODE_UNSUPPORTED,
            "ENTRY fieldset exists only for net_mode or long_short_mode",
        )
    return {
        "method": "POST",
        "path": "/api/v5/trade/order",
        "fields": ["clOrdId", "instId", "ordType", "posSide", "side", "sz", "tdMode"],
        "fixed_values": {
            "instId": OKX_INSTRUMENT_ID,
            "ordType": "market",
            "tdMode": ISOLATED,
        },
        "side_rule": "LONG=buy|SHORT=sell",
        "pos_side_rule": pos_side_rule,
        "size_source": "validated_current_entry_sizing_metadata",
        "closed_fieldset": True,
    }


def _read_only_fieldset() -> dict[str, Any]:
    return {
        "method": "GET_ONLY",
        "private_allowlist": [
            "/api/v5/account/config",
            "/api/v5/account/balance?ccy=USDT",
            "/api/v5/account/positions?instId=BTC-USDT-SWAP",
            "/api/v5/account/leverage-info?instId=BTC-USDT-SWAP&mgnMode=isolated",
            "/api/v5/trade/orders-pending?instId=BTC-USDT-SWAP&instType=SWAP",
            "/api/v5/trade/fills?instId=BTC-USDT-SWAP&instType=SWAP",
        ],
        "public_allowlist": ["/api/v5/public/time"],
        "default_deny": True,
        "mutation_methods": [],
    }


def _owner_repository_row(action_role: str, position_mode: str) -> dict[str, Any] | None:
    provenance = _OWNER_ROW_PROVENANCE.get((action_role, position_mode))
    if provenance is None:
        return None
    if action_role == ENTRY:
        descriptor = _entry_fieldset(position_mode)
    elif action_role == READ_ONLY_RECONCILIATION:
        descriptor = _read_only_fieldset()
    else:
        return None
    ref, generation = provenance
    return {
        "capability_profile_version": CAPABILITY_PROFILE_VERSION,
        "action_role": action_role,
        "position_mode": position_mode,
        "provider_fieldset_ref": ref,
        "provider_fieldset_generation_id": generation,
        "provider_fieldset_hash": canonical_okx_action_capability_hash(descriptor),
        "provider_fieldset": descriptor,
    }


def expected_repo_fieldset(action_role: str, position_mode: str) -> dict[str, Any] | None:
    """Return only the resolver-owned descriptor; this is not capability authority."""

    row = _owner_repository_row(action_role, position_mode)
    if row is None:
        return None
    return deepcopy(row["provider_fieldset"])


def expected_repo_fieldset_identity(action_role: str, position_mode: str) -> dict[str, Any] | None:
    """Return a copy of the canonical E4-owner repository row identity.

    This helper exposes repository evidence material for deterministic consumers
    and tests. Callers cannot choose the positive ref/generation: the resolver
    separately compares supplied facts with its own immutable canonical row.
    """

    row = _owner_repository_row(action_role, position_mode)
    return None if row is None else deepcopy(row)


def _fieldset_is_repo_evidenced(facts: OKXActionCapabilityFacts) -> bool:
    owner_row = _owner_repository_row(facts.action_role, facts.position_mode)
    if owner_row is None or facts.provider_fieldset is None:
        return False
    supplied = _canonicalize(facts.provider_fieldset)
    return (
        supplied == owner_row["provider_fieldset"]
        and facts.provider_fieldset_hash == owner_row["provider_fieldset_hash"]
        and facts.provider_fieldset_ref == owner_row["provider_fieldset_ref"]
        and facts.provider_fieldset_generation_id == owner_row["provider_fieldset_generation_id"]
    )


def _base_evidence(facts: OKXActionCapabilityFacts) -> dict[str, Any]:
    _text(facts.capability_profile_version, "capability_profile_version")
    _text(facts.action_role, "action_role")
    _text(facts.provider, "provider")
    _text(facts.api_version, "api_version")
    _text(facts.canonical_symbol, "canonical_symbol")
    _text(facts.provider_instrument_id, "provider_instrument_id")
    _text(facts.inst_type, "inst_type")
    _text(facts.account_level, "account_level")
    _text(facts.position_mode, "position_mode")
    _text(facts.margin_mode, "margin_mode")
    _text(facts.operation_class, "operation_class")
    evaluated_at = _utc_text(facts.evaluated_at, "evaluated_at")

    for field, value in (
        ("provider_fieldset_ref", facts.provider_fieldset_ref),
        ("provider_fieldset_generation_id", facts.provider_fieldset_generation_id),
        ("fp03_trigger_validity_ref", facts.fp03_trigger_validity_ref),
        ("fp05_close_sizing_ref", facts.fp05_close_sizing_ref),
        ("fp11_registry_ref", facts.fp11_registry_ref),
    ):
        _optional_text(value, field)
    _optional_hash(facts.provider_fieldset_hash, "provider_fieldset_hash")

    return {
        "capability_profile_version": facts.capability_profile_version,
        "action_role": facts.action_role,
        "provider": facts.provider,
        "api_version": facts.api_version,
        "canonical_symbol": facts.canonical_symbol,
        "provider_instrument_id": facts.provider_instrument_id,
        "inst_type": facts.inst_type,
        "account_level": facts.account_level,
        "position_mode": facts.position_mode,
        "margin_mode": facts.margin_mode,
        "operation_class": facts.operation_class,
        "provider_fieldset_ref": facts.provider_fieldset_ref,
        "provider_fieldset_hash": facts.provider_fieldset_hash,
        "provider_fieldset_generation_id": facts.provider_fieldset_generation_id,
        "reconciliation_status": facts.reconciliation_status,
        "fp03_trigger_validity_ref": facts.fp03_trigger_validity_ref,
        "fp03_trigger_validity_status": facts.fp03_trigger_validity_status,
        "fp03_trigger_validity_currentness": facts.fp03_trigger_validity_currentness,
        "fp05_close_sizing_ref": facts.fp05_close_sizing_ref,
        "fp05_close_sizing_status": facts.fp05_close_sizing_status,
        "fp05_close_sizing_currentness": facts.fp05_close_sizing_currentness,
        "fp11_registry_ref": facts.fp11_registry_ref,
        "fp11_registry_status": facts.fp11_registry_status,
        "fp11_registry_currentness": facts.fp11_registry_currentness,
        "caller_capability_assertion_present": facts.caller_capability_assertion is not None,
        "evaluated_at": evaluated_at,
    }


def _common_failures(facts: OKXActionCapabilityFacts) -> tuple[str | None, list[str]]:
    if facts.capability_profile_version != CAPABILITY_PROFILE_VERSION:
        return UNRESOLVED_FAIL_CLOSED, [OKX_SWAP_CAPABILITY_PROFILE_UNSUPPORTED]
    if facts.action_role not in _SUPPORTED_ROLES:
        return UNRESOLVED_FAIL_CLOSED, [OKX_SWAP_ACTION_ROLE_UNSUPPORTED]
    if (
        facts.provider != OKX_PROVIDER
        or facts.api_version != OKX_API_VERSION
        or facts.canonical_symbol != CANONICAL_SYMBOL
        or facts.provider_instrument_id != OKX_INSTRUMENT_ID
        or facts.inst_type != OKX_INST_TYPE
    ):
        return UNRESOLVED_FAIL_CLOSED, [OKX_SWAP_INSTRUMENT_UNSUPPORTED]
    if facts.account_level != ACCOUNT_LEVEL:
        return UNRESOLVED_FAIL_CLOSED, [OKX_SWAP_ACCOUNT_LEVEL_UNSUPPORTED]
    if facts.position_mode not in _SUPPORTED_POSITION_MODES:
        return UNRESOLVED_FAIL_CLOSED, [OKX_SWAP_POSITION_MODE_UNSUPPORTED]
    if facts.margin_mode == "cash":
        return FORBIDDEN, [OKX_SWAP_SPOT_TRADE_MODE_FORBIDDEN]
    if facts.margin_mode != ISOLATED:
        return UNRESOLVED_FAIL_CLOSED, [OKX_SWAP_MARGIN_MODE_UNSUPPORTED]
    if facts.caller_capability_assertion is not None:
        return UNRESOLVED_FAIL_CLOSED, [OKX_SWAP_CALLER_CAPABILITY_ASSERTION_REJECTED]
    if facts.action_role in _MUTATION_ROLES and facts.reconciliation_status != CURRENT:
        return UNRESOLVED_FAIL_CLOSED, [OKX_SWAP_RECONCILIATION_REQUIRED]
    return None, []


def _derive_capability(facts: OKXActionCapabilityFacts) -> tuple[str, list[str]]:
    state, reasons = _common_failures(facts)
    if state is not None:
        return state, reasons

    if facts.action_role == ENTRY:
        if facts.operation_class != ENTRY_OPERATION or not _fieldset_is_repo_evidenced(facts):
            return UNRESOLVED_FAIL_CLOSED, [OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN]
        return REPO_EVIDENCED, []

    if facts.action_role == READ_ONLY_RECONCILIATION:
        if facts.operation_class != READ_ONLY_OPERATION:
            return FORBIDDEN, [OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN]
        if not _fieldset_is_repo_evidenced(facts):
            return UNRESOLVED_FAIL_CLOSED, [OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN]
        return REPO_EVIDENCED, []

    if facts.action_role == PROTECTION_STOP:
        reasons = [OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN, OKX_SWAP_TRIGGER_BASIS_UNPROVEN]
        if (
            facts.fp11_registry_ref is None
            or facts.fp11_registry_status != FP11_CONVERGED
            or facts.fp11_registry_currentness != CURRENT
        ):
            reasons.append(OKX_SWAP_PROTECTION_REGISTRY_NOT_CURRENT)
        if (
            facts.fp03_trigger_validity_ref is None
            or facts.fp03_trigger_validity_status != FP03_ACTIONABLE
            or facts.fp03_trigger_validity_currentness != CURRENT
        ):
            reasons.append(OKX_SWAP_TRIGGER_BASIS_UNPROVEN)
        return UNRESOLVED_FAIL_CLOSED, _sorted_reasons(reasons)

    if facts.action_role in {POSITION_EXIT, EMERGENCY_EXIT}:
        reasons = [OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN]
        if (
            facts.fp05_close_sizing_ref is None
            or facts.fp05_close_sizing_status not in _FP05_SIZING_PROVEN
            or facts.fp05_close_sizing_currentness != CURRENT
        ):
            reasons.append(OKX_SWAP_REDUCIBLE_SIZE_UNPROVEN)
        return UNRESOLVED_FAIL_CLOSED, _sorted_reasons(reasons)

    return UNRESOLVED_FAIL_CLOSED, [OKX_SWAP_ACTION_ROLE_UNSUPPORTED]


def _identity_payload(evidence: Mapping[str, Any]) -> dict[str, Any]:
    material = dict(evidence)
    material.pop("capability_evidence_id", None)
    material.pop("evaluated_at", None)
    return material


def _evidence_id(evidence: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(
        canonical_okx_action_capability_json(_identity_payload(evidence)).encode("utf-8")
    ).hexdigest()
    return "okxswapcap_" + digest


def resolve_okx_swap_action_capability(facts: OKXActionCapabilityFacts) -> dict[str, Any]:
    """Resolve only repository-evidenced provider-local capability facts.

    No I/O, credential access, provider request, mutation or runtime action is
    performed. PROTECTION_STOP/POSITION_EXIT/EMERGENCY_EXIT intentionally have
    no positive provider-dispatch path under the current repository baseline.
    """

    if not isinstance(facts, OKXActionCapabilityFacts):
        raise OKXActionCapabilityError("INPUT_TYPE_INVALID", "facts must be OKXActionCapabilityFacts")
    evidence = _base_evidence(facts)
    state, reasons = _derive_capability(facts)
    evidence["capability_state"] = state
    evidence["reason_codes"] = _sorted_reasons(reasons) if reasons else []
    evidence["capability_evidence_id"] = _evidence_id(evidence)
    validate_okx_swap_action_capability_evidence(evidence)
    return evidence


def _repo_evidenced_claim_matches_owner_row(evidence: Mapping[str, Any]) -> bool:
    owner_row = _owner_repository_row(evidence.get("action_role"), evidence.get("position_mode"))
    if owner_row is None:
        return False
    if (
        evidence.get("capability_profile_version") != CAPABILITY_PROFILE_VERSION
        or evidence.get("provider") != OKX_PROVIDER
        or evidence.get("api_version") != OKX_API_VERSION
        or evidence.get("canonical_symbol") != CANONICAL_SYMBOL
        or evidence.get("provider_instrument_id") != OKX_INSTRUMENT_ID
        or evidence.get("inst_type") != OKX_INST_TYPE
        or evidence.get("account_level") != ACCOUNT_LEVEL
        or evidence.get("margin_mode") != ISOLATED
        or evidence.get("caller_capability_assertion_present") is not False
        or evidence.get("provider_fieldset_ref") != owner_row["provider_fieldset_ref"]
        or evidence.get("provider_fieldset_hash") != owner_row["provider_fieldset_hash"]
        or evidence.get("provider_fieldset_generation_id")
        != owner_row["provider_fieldset_generation_id"]
    ):
        return False
    if evidence.get("action_role") == ENTRY:
        return (
            evidence.get("operation_class") == ENTRY_OPERATION
            and evidence.get("reconciliation_status") == CURRENT
        )
    if evidence.get("action_role") == READ_ONLY_RECONCILIATION:
        return evidence.get("operation_class") == READ_ONLY_OPERATION
    return False


def validate_okx_swap_action_capability_evidence(evidence: Mapping[str, Any]) -> None:
    required = {
        "capability_profile_version",
        "capability_evidence_id",
        "action_role",
        "provider",
        "api_version",
        "canonical_symbol",
        "provider_instrument_id",
        "inst_type",
        "account_level",
        "position_mode",
        "margin_mode",
        "operation_class",
        "provider_fieldset_ref",
        "provider_fieldset_hash",
        "provider_fieldset_generation_id",
        "reconciliation_status",
        "fp03_trigger_validity_ref",
        "fp03_trigger_validity_status",
        "fp03_trigger_validity_currentness",
        "fp05_close_sizing_ref",
        "fp05_close_sizing_status",
        "fp05_close_sizing_currentness",
        "fp11_registry_ref",
        "fp11_registry_status",
        "fp11_registry_currentness",
        "caller_capability_assertion_present",
        "capability_state",
        "reason_codes",
        "evaluated_at",
    }
    if not isinstance(evidence, Mapping) or set(evidence) != required:
        raise OKXActionCapabilityError("EVIDENCE_FIELDS_INVALID", "capability evidence fields mismatch")
    evidence_id = evidence.get("capability_evidence_id")
    if not isinstance(evidence_id, str) or _ID_RE.fullmatch(evidence_id) is None:
        raise OKXActionCapabilityError("EVIDENCE_ID_INVALID", "capability evidence id invalid")
    if evidence_id != _evidence_id(evidence):
        raise OKXActionCapabilityError("EVIDENCE_ID_INVALID", "capability evidence id/hash mismatch")
    if evidence["capability_state"] not in {
        REPO_EVIDENCED,
        UNRESOLVED_FAIL_CLOSED,
        FORBIDDEN,
        NOT_APPLICABLE,
    }:
        raise OKXActionCapabilityError("CAPABILITY_STATE_INVALID", "capability state unsupported")
    reasons = evidence["reason_codes"]
    if not isinstance(reasons, list) or reasons != _sorted_reasons(reasons):
        raise OKXActionCapabilityError("REASON_ORDER_INVALID", "reason_codes must be deterministic")
    if evidence["capability_state"] == REPO_EVIDENCED:
        if reasons or not _repo_evidenced_claim_matches_owner_row(evidence):
            raise OKXActionCapabilityError(
                "FALSE_REPO_EVIDENCED",
                "repo-evidenced capability must bind the exact E4-owner repository row",
            )
    _utc_text(evidence["evaluated_at"], "evaluated_at")
    _optional_hash(evidence["provider_fieldset_hash"], "provider_fieldset_hash")


def okx_swap_action_capability_evidence_is_current(
    evidence: Mapping[str, Any],
    current_facts: OKXActionCapabilityFacts,
) -> bool:
    """Return material currentness; evaluated_at alone is intentionally ignored."""

    try:
        validate_okx_swap_action_capability_evidence(evidence)
        fresh = resolve_okx_swap_action_capability(current_facts)
    except OKXActionCapabilityError:
        return False
    ignored = {"capability_evidence_id", "evaluated_at"}
    return all(evidence.get(key) == fresh.get(key) for key in evidence if key not in ignored)
