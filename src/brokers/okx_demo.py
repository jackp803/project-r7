from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.parse import urlencode

from src.brokers.okx_sizing import (
    OKXEntrySizingAudit,
    OKXInstrumentMetadata,
    OKX_PROVIDER,
    OKX_INSTRUMENT_ID,
    instrument_metadata_from_okx_payload,
    size_okx_market_entry,
    validate_okx_submit_metadata,
)
from src.execution.gateway import CANONICAL_SYMBOL
from src.execution.models import (
    SCHEMA_VERSION,
    ExecutionHealthStatus,
    Fill,
    OrderRequest,
    OrderResult,
    OrderStatus,
    Side,
)

OKX_DEMO_REST_BASE_URL = "https://openapi.okx.com"
OKX_DEMO_HEADER = "x-simulated-trading"
OKX_DEMO_HEADER_VALUE = "1"
OKX_TRADE_MODE = "isolated"
OKX_ORDER_PATH = "/api/v5/trade/order"
OKX_ORDER_DETAILS_PATH = "/api/v5/trade/order"
OKX_PENDING_ORDERS_PATH = "/api/v5/trade/orders-pending"
OKX_POSITIONS_PATH = "/api/v5/account/positions"
OKX_FILLS_PATH = "/api/v5/trade/fills"
OKX_ACCOUNT_CONFIG_PATH = "/api/v5/account/config"
OKX_PUBLIC_INSTRUMENTS_PATH = "/api/v5/public/instruments"

# V1 is deliberately narrower than the provider's total capability surface.
# Current official OKX V5 guidance explicitly supports isolated SWAP trading in
# Futures mode (acctLv=2), and Futures mode supports both net and long/short
# position modes. Isolated is not available in multi-currency/portfolio modes.
_OKX_V1_SUPPORTED_ACCOUNT_MATRIX = {
    "2": frozenset({"net_mode", "long_short_mode"}),
}

_ALLOWED_PRIVATE_PATHS = frozenset(
    {
        OKX_ORDER_PATH,
        OKX_PENDING_ORDERS_PATH,
        OKX_POSITIONS_PATH,
        OKX_FILLS_PATH,
        OKX_ACCOUNT_CONFIG_PATH,
    }
)
_CL_ORD_ID_RE = re.compile(r"^[A-Za-z0-9]{1,32}$")
_PROVIDER_ORDER_STATE_MAP = {
    "live": OrderStatus.OPEN,
    "partially_filled": OrderStatus.PARTIALLY_FILLED,
    "filled": OrderStatus.FILLED,
    "canceled": OrderStatus.CANCELED,
    "mmp_canceled": OrderStatus.CANCELED,
}


class OKXDemoConfigurationError(ValueError):
    pass


class OKXProtocolError(ValueError):
    pass


class OKXPrerequisiteError(ValueError):
    pass


class OKXReconciliationError(RuntimeError):
    pass


@dataclass(frozen=True, repr=False)
class OKXCredentials:
    """Runtime-only private REST credentials; repr deliberately redacts values."""

    api_key: str
    secret_key: str
    passphrase: str

    def __post_init__(self) -> None:
        for name, value in (
            ("api_key", self.api_key),
            ("secret_key", self.secret_key),
            ("passphrase", self.passphrase),
        ):
            if not isinstance(value, str) or not value:
                raise OKXDemoConfigurationError(f"{name} must be runtime-injected and non-empty")

    def __repr__(self) -> str:
        return "OKXCredentials(<redacted>)"


@dataclass(frozen=True)
class OKXDemoAdapterConfig:
    expected_account_level: str
    expected_position_mode: str
    environment: str = "demo"
    rest_base_url: str = OKX_DEMO_REST_BASE_URL

    def __post_init__(self) -> None:
        if self.environment != "demo":
            raise OKXDemoConfigurationError("this bounded adapter rejects production/live mode")
        if self.rest_base_url != OKX_DEMO_REST_BASE_URL:
            raise OKXDemoConfigurationError("only the documented OKX Demo REST base URL is allowed")
        supported_modes = _OKX_V1_SUPPORTED_ACCOUNT_MATRIX.get(self.expected_account_level)
        if supported_modes is None:
            raise OKXDemoConfigurationError(
                "V1 isolated BTC-USDT-SWAP adapter supports only acctLv=2 Futures mode"
            )
        if self.expected_position_mode not in supported_modes:
            raise OKXDemoConfigurationError(
                "configured position mode is not supported by the V1 Futures-mode matrix"
            )


@dataclass(frozen=True, repr=False)
class PreparedOKXRequest:
    method: str
    request_path: str
    body_text: str
    headers: Mapping[str, str]
    authenticated: bool

    def __repr__(self) -> str:
        return (
            "PreparedOKXRequest(method={!r}, request_path={!r}, body_len={}, "
            "header_names={!r}, authenticated={!r})"
        ).format(
            self.method,
            self.request_path,
            len(self.body_text),
            tuple(sorted(self.headers.keys())),
            self.authenticated,
        )


class OKXTransport(Protocol):
    """Injected transport seam. No concrete network transport is provided."""

    def send(self, request: PreparedOKXRequest) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class OKXClientOrderIdentity:
    internal_client_order_id: str
    provider_cl_ord_id: str


@dataclass(frozen=True)
class OKXAccountConfigSnapshot:
    account_level: str
    position_mode: str
    uid: str
    main_uid: str


@dataclass(frozen=True)
class OKXPositionFact:
    instrument_id: str
    margin_mode: str
    position_side: str
    provider_contract_quantity: Decimal


@dataclass(frozen=True)
class OKXPendingOrderFact:
    instrument_id: str
    order_id: str
    client_order_id: str
    state: str


@dataclass(frozen=True)
class OKXPrerequisiteSnapshot:
    account: OKXAccountConfigSnapshot
    positions: tuple[OKXPositionFact, ...]
    pending_orders: tuple[OKXPendingOrderFact, ...]


@dataclass(frozen=True)
class OKXOrderMaterialization:
    order_request_id: str
    trade_plan_id: str
    internal_client_order_id: str
    provider_cl_ord_id: str
    provider_instrument_id: str
    provider_side: str
    provider_position_side: str
    provider_contract_quantity: Decimal
    effective_canonical_quantity: Decimal
    canonical_approved_quantity: Decimal
    instrument_metadata_ref: str
    instrument_metadata_observed_at: datetime
    body: Mapping[str, str]


@dataclass(frozen=True)
class _IssuedOKXPreparation:
    """Adapter-owned immutable submit authority for one prepared materialization.

    The public materialization remains useful for audit/reconciliation, but it is
    not execution authority. Submit is authorized only when the exact object
    instance is present in the issuing adapter's registry and all public facts
    still match these copied immutable preparation facts.
    """

    materialization: OKXOrderMaterialization
    order_request_id: str
    trade_plan_id: str
    internal_client_order_id: str
    provider_cl_ord_id: str
    provider_instrument_id: str
    provider_side: str
    provider_position_side: str
    provider_order_type: str
    provider_trade_mode: str
    provider_contract_quantity: Decimal
    effective_canonical_quantity: Decimal
    canonical_approved_quantity: Decimal
    instrument_metadata_ref: str
    instrument_metadata_observed_at: datetime
    metadata_freshness_policy_version: str
    prepared_at: datetime
    environment: str
    account_level: str
    position_mode: str


@dataclass(frozen=True)
class OKXOrderLookup:
    found: bool
    result: OrderResult | None
    lookup_status: str
    provider_error_code: str | None = None


@dataclass(frozen=True)
class OKXReconciliationEvidence:
    """Audit evidence only; never an execution authorization token."""

    provider_cl_ord_id: str
    order_lookup: OKXOrderLookup
    positions: tuple[OKXPositionFact, ...]
    fills: tuple[Fill, ...]
    pending_orders: tuple[OKXPendingOrderFact, ...]
    retry_allowed: bool
    reason: str


def _format_decimal(value: Decimal) -> str:
    return format(value, "f")


def _parse_decimal(value: Any, field: str, *, allow_zero: bool = False) -> Decimal:
    if not isinstance(value, str) or not value:
        raise OKXProtocolError(f"{field} must be a decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise OKXProtocolError(f"{field} is not a valid decimal") from exc
    if not parsed.is_finite() or parsed < 0 or (not allow_zero and parsed == 0):
        relation = ">= 0" if allow_zero else "> 0"
        raise OKXProtocolError(f"{field} must be finite and {relation}")
    return parsed


def _parse_signed_decimal(value: Any, field: str) -> Decimal:
    if not isinstance(value, str) or not value:
        raise OKXProtocolError(f"{field} must be a decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise OKXProtocolError(f"{field} is not a valid decimal") from exc
    if not parsed.is_finite():
        raise OKXProtocolError(f"{field} must be finite")
    return parsed


def _parse_epoch_ms(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.isdigit():
        raise OKXProtocolError(f"{field} must be a millisecond epoch string")
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


def _require_iso_timestamp(value: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise OKXDemoConfigurationError("timestamp must be ISO 8601 UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise OKXDemoConfigurationError("timestamp must be valid ISO 8601 UTC") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise OKXDemoConfigurationError("timestamp must be UTC")
    return value


def _canonical_body(body: Mapping[str, Any] | None) -> str:
    if body is None:
        return ""
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _request_path(path: str, query: Mapping[str, str] | None) -> str:
    if not path.startswith("/api/v5/"):
        raise OKXDemoConfigurationError("unexpected OKX API path")
    if not query:
        return path
    items = sorted((str(key), str(value)) for key, value in query.items())
    return path + "?" + urlencode(items)


def sign_okx_rest_request(
    *,
    secret_key: str,
    timestamp: str,
    method: str,
    request_path: str,
    body_text: str = "",
) -> str:
    """OKX V5 REST signature: Base64(HMAC-SHA256(timestamp+method+path+body))."""
    _require_iso_timestamp(timestamp)
    if not isinstance(secret_key, str) or not secret_key:
        raise OKXDemoConfigurationError("secret_key must be runtime-injected")
    upper_method = method.upper()
    if upper_method not in {"GET", "POST"}:
        raise OKXDemoConfigurationError("only GET/POST are allowed in this bounded adapter")
    prehash = f"{timestamp}{upper_method}{request_path}{body_text}"
    digest = hmac.new(secret_key.encode(), prehash.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def prepare_demo_private_request(
    credentials: OKXCredentials,
    *,
    method: str,
    path: str,
    timestamp: str,
    query: Mapping[str, str] | None = None,
    body: Mapping[str, Any] | None = None,
) -> PreparedOKXRequest:
    if path not in _ALLOWED_PRIVATE_PATHS:
        raise OKXDemoConfigurationError("private endpoint is outside the bounded Demo adapter allowlist")
    upper_method = method.upper()
    if upper_method == "GET" and body is not None:
        raise OKXDemoConfigurationError("GET body is forbidden; query belongs in requestPath")
    if upper_method == "POST" and query:
        raise OKXDemoConfigurationError("POST query parameters are not used by the bounded order path")
    full_path = _request_path(path, query)
    body_text = _canonical_body(body)
    signature = sign_okx_rest_request(
        secret_key=credentials.secret_key,
        timestamp=timestamp,
        method=upper_method,
        request_path=full_path,
        body_text=body_text,
    )
    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": credentials.api_key,
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": credentials.passphrase,
        OKX_DEMO_HEADER: OKX_DEMO_HEADER_VALUE,
    }
    return PreparedOKXRequest(
        method=upper_method,
        request_path=full_path,
        body_text=body_text,
        headers=headers,
        authenticated=True,
    )


def prepare_public_instrument_request() -> PreparedOKXRequest:
    return PreparedOKXRequest(
        method="GET",
        request_path=_request_path(
            OKX_PUBLIC_INSTRUMENTS_PATH,
            {"instId": OKX_INSTRUMENT_ID, "instType": "SWAP"},
        ),
        body_text="",
        headers={"Accept": "application/json"},
        authenticated=False,
    )


def stable_okx_cl_ord_id(internal_client_order_id: str) -> OKXClientOrderIdentity:
    if not isinstance(internal_client_order_id, str) or not internal_client_order_id:
        raise OKXDemoConfigurationError("internal client_order_id must be non-empty")
    provider_id = "R7" + hashlib.sha256(internal_client_order_id.encode()).hexdigest()[:30]
    if not _CL_ORD_ID_RE.fullmatch(provider_id):
        raise OKXDemoConfigurationError("generated OKX clOrdId violates current provider constraints")
    return OKXClientOrderIdentity(
        internal_client_order_id=internal_client_order_id,
        provider_cl_ord_id=provider_id,
    )


def _require_ok_response(response: Mapping[str, Any], context: str) -> Sequence[Any]:
    if not isinstance(response, Mapping):
        raise OKXProtocolError(f"{context} response must be a mapping")
    if response.get("code") != "0":
        raise OKXProtocolError(f"{context} provider code is not success: {response.get('code')!r}")
    data = response.get("data")
    if not isinstance(data, Sequence) or isinstance(data, (str, bytes)):
        raise OKXProtocolError(f"{context} data must be an array")
    return data


def parse_public_instrument_response(
    response: Mapping[str, Any],
    *,
    observed_at: datetime,
    metadata_ref: str,
) -> OKXInstrumentMetadata:
    data = _require_ok_response(response, "instrument")
    matches = [
        item
        for item in data
        if isinstance(item, Mapping) and item.get("instId") == OKX_INSTRUMENT_ID
    ]
    if len(matches) != 1:
        raise OKXProtocolError("instrument response must contain exactly one BTC-USDT-SWAP item")
    return instrument_metadata_from_okx_payload(
        matches[0], observed_at=observed_at, metadata_ref=metadata_ref
    )


def parse_account_config_response(response: Mapping[str, Any]) -> OKXAccountConfigSnapshot:
    data = _require_ok_response(response, "account config")
    if len(data) != 1 or not isinstance(data[0], Mapping):
        raise OKXProtocolError("account config must contain exactly one object")
    item = data[0]
    required = ("acctLv", "posMode", "uid", "mainUid")
    if any(not isinstance(item.get(name), str) or not item.get(name) for name in required):
        raise OKXProtocolError("account config is missing required identity/mode fields")
    return OKXAccountConfigSnapshot(
        account_level=item["acctLv"],
        position_mode=item["posMode"],
        uid=item["uid"],
        main_uid=item["mainUid"],
    )


def parse_positions_response(response: Mapping[str, Any]) -> tuple[OKXPositionFact, ...]:
    data = _require_ok_response(response, "positions")
    facts: list[OKXPositionFact] = []
    for item in data:
        if not isinstance(item, Mapping):
            raise OKXProtocolError("position item must be a mapping")
        inst_id = item.get("instId")
        if inst_id != OKX_INSTRUMENT_ID:
            raise OKXProtocolError("position response contains an unexpected instrument")
        mgn_mode = item.get("mgnMode")
        pos_side = item.get("posSide")
        if mgn_mode not in {"isolated", "cross"}:
            raise OKXProtocolError("unknown position margin mode")
        if pos_side not in {"net", "long", "short"}:
            raise OKXProtocolError("unknown position side")
        facts.append(
            OKXPositionFact(
                instrument_id=inst_id,
                margin_mode=mgn_mode,
                position_side=pos_side,
                provider_contract_quantity=_parse_signed_decimal(item.get("pos"), "position.pos"),
            )
        )
    return tuple(facts)


def parse_pending_orders_response(response: Mapping[str, Any]) -> tuple[OKXPendingOrderFact, ...]:
    data = _require_ok_response(response, "pending orders")
    facts: list[OKXPendingOrderFact] = []
    for item in data:
        if not isinstance(item, Mapping):
            raise OKXProtocolError("pending order item must be a mapping")
        if item.get("instId") != OKX_INSTRUMENT_ID:
            raise OKXProtocolError("pending order response contains an unexpected instrument")
        state = item.get("state")
        if state not in {"live", "partially_filled"}:
            raise OKXProtocolError("pending-order endpoint returned an unknown/non-pending state")
        ord_id = item.get("ordId")
        cl_ord_id = item.get("clOrdId")
        if not isinstance(ord_id, str) or not ord_id:
            raise OKXProtocolError("pending order is missing ordId")
        if not isinstance(cl_ord_id, str):
            raise OKXProtocolError("pending order clOrdId must be a string")
        facts.append(
            OKXPendingOrderFact(
                instrument_id=OKX_INSTRUMENT_ID,
                order_id=ord_id,
                client_order_id=cl_ord_id,
                state=state,
            )
        )
    return tuple(facts)


def validate_demo_prerequisites(
    snapshot: OKXPrerequisiteSnapshot,
    *,
    config: OKXDemoAdapterConfig,
) -> None:
    supported_modes = _OKX_V1_SUPPORTED_ACCOUNT_MATRIX.get(snapshot.account.account_level)
    if supported_modes is None or snapshot.account.position_mode not in supported_modes:
        raise OKXPrerequisiteError(
            "provider account level/position mode is unsupported for V1 isolated SWAP entry"
        )
    if snapshot.account.account_level != config.expected_account_level:
        raise OKXPrerequisiteError("OKX acctLv does not match explicit adapter configuration")
    if snapshot.account.position_mode != config.expected_position_mode:
        raise OKXPrerequisiteError("OKX posMode does not match explicit adapter configuration")
    for position in snapshot.positions:
        if position.instrument_id != OKX_INSTRUMENT_ID:
            raise OKXPrerequisiteError("unexpected instrument in prerequisite position truth")
        if position.provider_contract_quantity != 0:
            raise OKXPrerequisiteError("existing provider exposure blocks the bounded new-entry flow")
        if position.margin_mode != OKX_TRADE_MODE:
            raise OKXPrerequisiteError("position margin mode is not isolated")
    if snapshot.pending_orders:
        raise OKXPrerequisiteError("pending provider orders must be reconciled before new exposure")


def _position_side(side: Side, position_mode: str) -> str:
    if position_mode == "net_mode":
        return "net"
    if position_mode == "long_short_mode":
        return "long" if side == Side.BUY else "short"
    raise OKXPrerequisiteError("unsupported position mode")


def _require_matching_sizing_evidence(
    supplied: OKXEntrySizingAudit,
    recomputed: OKXEntrySizingAudit,
) -> None:
    if not isinstance(supplied, OKXEntrySizingAudit):
        raise OKXProtocolError("sizing evidence must be an OKXEntrySizingAudit")
    if supplied != recomputed:
        raise OKXProtocolError(
            "caller sizing evidence does not exactly match sizing recomputed from current request/metadata"
        )


def materialize_demo_market_order(
    request: OrderRequest,
    sizing: OKXEntrySizingAudit,
    metadata: OKXInstrumentMetadata,
    prerequisites: OKXPrerequisiteSnapshot,
    *,
    config: OKXDemoAdapterConfig,
    now: datetime,
) -> OKXOrderMaterialization:
    """Materialize only after re-establishing sizing from current request + metadata."""
    if config.environment != "demo":
        raise OKXDemoConfigurationError("production/live mode is forbidden")
    validate_demo_prerequisites(prerequisites, config=config)
    checked_metadata = validate_okx_submit_metadata(metadata, now=now)

    if request.schema_version != SCHEMA_VERSION:
        raise OKXProtocolError("unsupported OrderRequest schema")
    if request.symbol != CANONICAL_SYMBOL:
        raise OKXProtocolError("canonical symbol mismatch")
    if request.order_type != "MARKET":
        raise OKXProtocolError("bounded adapter accepts MARKET only")
    if request.limit_price is not None or request.stop_price is not None or request.time_in_force is not None:
        raise OKXProtocolError("MARKET provider request cannot inherit executable price/TIF")

    # Finding E4-OKX-MATERIALIZATION-INTEGRITY-001: caller-supplied audit is
    # evidence only. Provider sz authority is recomputed here from the exact
    # canonical OrderRequest and the exact submit-validated metadata snapshot.
    recomputed = size_okx_market_entry(request, checked_metadata, now=now)
    _require_matching_sizing_evidence(sizing, recomputed)

    if not (Decimal("0") < recomputed.effective_canonical_requested_quantity <= request.quantity):
        raise OKXProtocolError("provider exposure exceeds or invalidates E5-approved BTC bound")

    identity = stable_okx_cl_ord_id(request.client_order_id)
    pos_side = _position_side(request.side, config.expected_position_mode)
    body = {
        "instId": OKX_INSTRUMENT_ID,
        "tdMode": OKX_TRADE_MODE,
        "clOrdId": identity.provider_cl_ord_id,
        "side": "buy" if request.side == Side.BUY else "sell",
        "posSide": pos_side,
        "ordType": "market",
        "sz": _format_decimal(recomputed.provider_requested_contract_quantity),
    }
    return OKXOrderMaterialization(
        order_request_id=request.order_request_id,
        trade_plan_id=request.trade_plan_id,
        internal_client_order_id=request.client_order_id,
        provider_cl_ord_id=identity.provider_cl_ord_id,
        provider_instrument_id=OKX_INSTRUMENT_ID,
        provider_side=body["side"],
        provider_position_side=pos_side,
        provider_contract_quantity=recomputed.provider_requested_contract_quantity,
        effective_canonical_quantity=recomputed.effective_canonical_requested_quantity,
        canonical_approved_quantity=request.quantity,
        instrument_metadata_ref=checked_metadata.metadata_ref,
        instrument_metadata_observed_at=checked_metadata.observed_at,
        body=body,
    )


def _materialization_semantic_facts(
    materialization: OKXOrderMaterialization,
) -> tuple[object, ...]:
    return (
        materialization.order_request_id,
        materialization.trade_plan_id,
        materialization.internal_client_order_id,
        materialization.provider_cl_ord_id,
        materialization.provider_instrument_id,
        materialization.provider_side,
        materialization.provider_position_side,
        materialization.provider_contract_quantity,
        materialization.effective_canonical_quantity,
        materialization.canonical_approved_quantity,
        materialization.instrument_metadata_ref,
        materialization.instrument_metadata_observed_at,
    )


def _issued_semantic_facts(issue: _IssuedOKXPreparation) -> tuple[object, ...]:
    return (
        issue.order_request_id,
        issue.trade_plan_id,
        issue.internal_client_order_id,
        issue.provider_cl_ord_id,
        issue.provider_instrument_id,
        issue.provider_side,
        issue.provider_position_side,
        issue.provider_contract_quantity,
        issue.effective_canonical_quantity,
        issue.canonical_approved_quantity,
        issue.instrument_metadata_ref,
        issue.instrument_metadata_observed_at,
    )


def _issued_preparation_fingerprint(issue: _IssuedOKXPreparation) -> tuple[object, ...]:
    return (
        *_issued_semantic_facts(issue),
        issue.provider_order_type,
        issue.provider_trade_mode,
        issue.metadata_freshness_policy_version,
        issue.prepared_at,
        issue.environment,
        issue.account_level,
        issue.position_mode,
    )


def _trusted_provider_body(issue: _IssuedOKXPreparation) -> dict[str, str]:
    return {
        "instId": issue.provider_instrument_id,
        "tdMode": issue.provider_trade_mode,
        "clOrdId": issue.provider_cl_ord_id,
        "side": issue.provider_side,
        "posSide": issue.provider_position_side,
        "ordType": issue.provider_order_type,
        "sz": _format_decimal(issue.provider_contract_quantity),
    }


def _reconciliation_required_result(
    materialization: OKXOrderMaterialization,
    *,
    observed_at: datetime,
    broker_order_id: str | None = None,
    reason: str,
) -> OrderResult:
    return OrderResult(
        schema_version=SCHEMA_VERSION,
        order_request_id=materialization.order_request_id,
        client_order_id=materialization.internal_client_order_id,
        broker_order_id=broker_order_id,
        order_status=OrderStatus.RECONCILIATION_REQUIRED,
        observed_at=observed_at,
        execution_health_status=ExecutionHealthStatus.DEGRADED,
        requested_quantity=materialization.effective_canonical_quantity,
        filled_quantity=Decimal("0"),
        reject_reason=reason,
    )


def parse_place_order_ack(
    response: Mapping[str, Any],
    materialization: OKXOrderMaterialization,
    *,
    observed_at: datetime,
) -> OrderResult:
    if not isinstance(response, Mapping):
        return _reconciliation_required_result(
            materialization, observed_at=observed_at, reason="MALFORMED_ACKNOWLEDGEMENT"
        )
    data = response.get("data")
    if not isinstance(data, Sequence) or isinstance(data, (str, bytes)) or len(data) != 1:
        return _reconciliation_required_result(
            materialization, observed_at=observed_at, reason="AMBIGUOUS_ACKNOWLEDGEMENT"
        )
    item = data[0]
    if not isinstance(item, Mapping):
        return _reconciliation_required_result(
            materialization, observed_at=observed_at, reason="MALFORMED_ACKNOWLEDGEMENT"
        )
    if item.get("clOrdId") != materialization.provider_cl_ord_id:
        return _reconciliation_required_result(
            materialization, observed_at=observed_at, reason="ACKNOWLEDGEMENT_ID_MISMATCH"
        )
    s_code = item.get("sCode")
    ord_id = item.get("ordId")
    if response.get("code") == "0" and s_code == "0" and isinstance(ord_id, str) and ord_id:
        return OrderResult(
            schema_version=SCHEMA_VERSION,
            order_request_id=materialization.order_request_id,
            client_order_id=materialization.internal_client_order_id,
            broker_order_id=ord_id,
            order_status=OrderStatus.PENDING,
            observed_at=observed_at,
            execution_health_status=ExecutionHealthStatus.HEALTHY,
            requested_quantity=materialization.effective_canonical_quantity,
            filled_quantity=Decimal("0"),
        )
    if isinstance(s_code, str) and s_code and s_code != "0":
        return OrderResult(
            schema_version=SCHEMA_VERSION,
            order_request_id=materialization.order_request_id,
            client_order_id=materialization.internal_client_order_id,
            broker_order_id=ord_id if isinstance(ord_id, str) and ord_id else None,
            order_status=OrderStatus.REJECTED,
            observed_at=observed_at,
            execution_health_status=ExecutionHealthStatus.HEALTHY,
            requested_quantity=materialization.effective_canonical_quantity,
            filled_quantity=Decimal("0"),
            reject_reason=str(item.get("sMsg") or s_code),
        )
    return _reconciliation_required_result(
        materialization, observed_at=observed_at, reason="UNKNOWN_ACKNOWLEDGEMENT"
    )


def _state_fill_consistent(state: str, filled_sz: Decimal, provider_sz: Decimal) -> bool:
    if state == "live":
        return filled_sz == 0
    if state == "partially_filled":
        return Decimal("0") < filled_sz < provider_sz
    if state == "filled":
        return filled_sz == provider_sz
    if state in {"canceled", "mmp_canceled"}:
        return Decimal("0") <= filled_sz <= provider_sz
    return False


def parse_order_lookup_response(
    response: Mapping[str, Any],
    materialization: OKXOrderMaterialization,
    *,
    observed_at: datetime,
    config: OKXDemoAdapterConfig | None = None,
) -> OKXOrderLookup:
    """Normalize provider order truth without treating error codes as absence authority."""
    if not isinstance(response, Mapping):
        raise OKXReconciliationError("order lookup response is malformed")
    code = response.get("code")
    if code != "0":
        return OKXOrderLookup(
            found=False,
            result=None,
            lookup_status="PROVIDER_ERROR_NOT_ABSENCE_PROOF",
            provider_error_code=code if isinstance(code, str) else None,
        )

    data = response.get("data")
    if not isinstance(data, Sequence) or isinstance(data, (str, bytes)):
        raise OKXReconciliationError("order lookup success data must be an array")
    if len(data) == 0:
        return OKXOrderLookup(
            found=False,
            result=None,
            lookup_status="SUCCESS_EMPTY_NOT_ABSENCE_PROOF",
        )
    if len(data) != 1:
        raise OKXReconciliationError("order lookup success must contain at most one matching order")
    item = data[0]
    if not isinstance(item, Mapping):
        raise OKXReconciliationError("order lookup item is malformed")
    if item.get("instId") != OKX_INSTRUMENT_ID:
        raise OKXReconciliationError("order lookup instrument mismatch")
    if item.get("clOrdId") != materialization.provider_cl_ord_id:
        raise OKXReconciliationError("order lookup clOrdId mismatch")
    ord_id = item.get("ordId")
    if not isinstance(ord_id, str) or not ord_id:
        raise OKXReconciliationError("order lookup missing ordId")
    state = item.get("state")
    mapped = _PROVIDER_ORDER_STATE_MAP.get(state)
    if mapped is None:
        return OKXOrderLookup(
            found=True,
            result=_reconciliation_required_result(
                materialization,
                observed_at=observed_at,
                broker_order_id=ord_id,
                reason=f"UNKNOWN_PROVIDER_ORDER_STATE:{state}",
            ),
            lookup_status="FOUND_UNKNOWN_STATE",
        )

    provider_sz = _parse_decimal(item.get("sz"), "order.sz")
    filled_sz = _parse_decimal(item.get("accFillSz"), "order.accFillSz", allow_zero=True)
    if provider_sz != materialization.provider_contract_quantity:
        raise OKXReconciliationError("provider order size contradicts materialized sz")
    if filled_sz > provider_sz:
        raise OKXReconciliationError("provider accumulated fill exceeds requested contracts")
    if not _state_fill_consistent(str(state), filled_sz, provider_sz):
        return OKXOrderLookup(
            found=True,
            result=_reconciliation_required_result(
                materialization,
                observed_at=observed_at,
                broker_order_id=ord_id,
                reason=f"CONTRADICTORY_PROVIDER_STATE_FILL:{state}:{filled_sz}:{provider_sz}",
            ),
            lookup_status="FOUND_CONTRADICTORY_STATE",
        )

    canonical_filled = filled_sz * (
        materialization.effective_canonical_quantity / materialization.provider_contract_quantity
    )
    if canonical_filled > materialization.effective_canonical_quantity:
        raise OKXReconciliationError("normalized fill exceeds effective canonical request")
    avg_px_raw = item.get("avgPx")
    avg_px = None
    if isinstance(avg_px_raw, str) and avg_px_raw:
        avg_px = _parse_decimal(avg_px_raw, "order.avgPx")
    if canonical_filled > 0 and avg_px is None:
        raise OKXReconciliationError("positive accumulated fill requires average fill price")

    return OKXOrderLookup(
        found=True,
        result=OrderResult(
            schema_version=SCHEMA_VERSION,
            order_request_id=materialization.order_request_id,
            client_order_id=materialization.internal_client_order_id,
            broker_order_id=ord_id,
            order_status=mapped,
            observed_at=observed_at,
            execution_health_status=ExecutionHealthStatus.HEALTHY,
            requested_quantity=materialization.effective_canonical_quantity,
            filled_quantity=canonical_filled,
            average_fill_price=avg_px,
        ),
        lookup_status="FOUND_CONSISTENT",
    )


def parse_fills_response(
    response: Mapping[str, Any],
    materialization: OKXOrderMaterialization,
) -> tuple[Fill, ...]:
    data = _require_ok_response(response, "fills")
    fills: list[Fill] = []
    total_contracts = Decimal("0")
    conversion = materialization.effective_canonical_quantity / materialization.provider_contract_quantity
    for item in data:
        if not isinstance(item, Mapping):
            raise OKXProtocolError("fill item must be a mapping")
        if item.get("instId") != OKX_INSTRUMENT_ID:
            continue
        if item.get("clOrdId") != materialization.provider_cl_ord_id:
            continue
        ord_id = item.get("ordId")
        trade_id = item.get("tradeId")
        if not isinstance(ord_id, str) or not ord_id or not isinstance(trade_id, str) or not trade_id:
            raise OKXProtocolError("fill is missing provider order/trade identity")
        fill_contracts = _parse_decimal(item.get("fillSz"), "fill.fillSz")
        fill_price = _parse_decimal(item.get("fillPx"), "fill.fillPx")
        total_contracts += fill_contracts
        if total_contracts > materialization.provider_contract_quantity:
            raise OKXProtocolError("provider fills exceed materialized contract quantity")
        canonical_quantity = fill_contracts * conversion
        if canonical_quantity <= 0:
            raise OKXProtocolError("normalized canonical fill must be positive")
        filled_at = _parse_epoch_ms(item.get("fillTime") or item.get("ts"), "fill time")
        fee = None
        if isinstance(item.get("fee"), str) and item.get("fee"):
            fee = _parse_signed_decimal(item.get("fee"), "fill.fee")
        fee_ccy = item.get("feeCcy") if isinstance(item.get("feeCcy"), str) else None
        fills.append(
            Fill(
                schema_version=SCHEMA_VERSION,
                fill_id=f"okx_trade_{trade_id}",
                broker_order_id=ord_id,
                client_order_id=materialization.internal_client_order_id,
                trade_plan_id=materialization.trade_plan_id,
                symbol=CANONICAL_SYMBOL,
                side=Side.BUY if materialization.provider_side == "buy" else Side.SELL,
                quantity=canonical_quantity,
                price=fill_price,
                filled_at=filled_at,
                fee=fee,
                fee_currency=fee_ccy,
                liquidity_role=None,
            )
        )
    return tuple(fills)


class OKXDemoAdapter:
    """Demo-only REST adapter using an injected transport; provider retry is disabled."""

    def __init__(
        self,
        *,
        credentials: OKXCredentials,
        config: OKXDemoAdapterConfig,
        transport: OKXTransport,
        timestamp_provider: Callable[[], str],
    ) -> None:
        if config.environment != "demo":
            raise OKXDemoConfigurationError("production/live mode is forbidden")
        self._credentials = credentials
        self._config = config
        self._transport = transport
        self._timestamp_provider = timestamp_provider
        self._submit_results: dict[str, OrderResult] = {}
        self._issued_preparations: dict[int, _IssuedOKXPreparation] = {}
        self._issued_fingerprints_by_cl_ord_id: dict[str, tuple[object, ...]] = {}

    def _private_get(self, path: str, query: Mapping[str, str] | None = None) -> Mapping[str, Any]:
        prepared = prepare_demo_private_request(
            self._credentials,
            method="GET",
            path=path,
            timestamp=self._timestamp_provider(),
            query=query,
        )
        return self._transport.send(prepared)

    def read_account_config(self) -> OKXAccountConfigSnapshot:
        return parse_account_config_response(self._private_get(OKX_ACCOUNT_CONFIG_PATH))

    def read_positions(self) -> tuple[OKXPositionFact, ...]:
        return parse_positions_response(
            self._private_get(OKX_POSITIONS_PATH, {"instId": OKX_INSTRUMENT_ID})
        )

    def read_pending_orders(self) -> tuple[OKXPendingOrderFact, ...]:
        return parse_pending_orders_response(
            self._private_get(
                OKX_PENDING_ORDERS_PATH,
                {"instId": OKX_INSTRUMENT_ID, "instType": "SWAP"},
            )
        )

    def read_prerequisites(self) -> OKXPrerequisiteSnapshot:
        return OKXPrerequisiteSnapshot(
            account=self.read_account_config(),
            positions=self.read_positions(),
            pending_orders=self.read_pending_orders(),
        )

    def read_public_instrument_metadata(
        self,
        *,
        observed_at: datetime,
        metadata_ref: str,
    ) -> OKXInstrumentMetadata:
        response = self._transport.send(prepare_public_instrument_request())
        return parse_public_instrument_response(
            response, observed_at=observed_at, metadata_ref=metadata_ref
        )

    def _register_issued_preparation(
        self,
        materialization: OKXOrderMaterialization,
        *,
        metadata: OKXInstrumentMetadata,
        prerequisites: OKXPrerequisiteSnapshot,
        prepared_at: datetime,
    ) -> None:
        issue = _IssuedOKXPreparation(
            materialization=materialization,
            order_request_id=materialization.order_request_id,
            trade_plan_id=materialization.trade_plan_id,
            internal_client_order_id=materialization.internal_client_order_id,
            provider_cl_ord_id=materialization.provider_cl_ord_id,
            provider_instrument_id=materialization.provider_instrument_id,
            provider_side=materialization.provider_side,
            provider_position_side=materialization.provider_position_side,
            provider_order_type="market",
            provider_trade_mode=OKX_TRADE_MODE,
            provider_contract_quantity=materialization.provider_contract_quantity,
            effective_canonical_quantity=materialization.effective_canonical_quantity,
            canonical_approved_quantity=materialization.canonical_approved_quantity,
            instrument_metadata_ref=materialization.instrument_metadata_ref,
            instrument_metadata_observed_at=materialization.instrument_metadata_observed_at,
            metadata_freshness_policy_version=metadata.freshness_policy_version,
            prepared_at=prepared_at,
            environment=self._config.environment,
            account_level=prerequisites.account.account_level,
            position_mode=prerequisites.account.position_mode,
        )
        fingerprint = _issued_preparation_fingerprint(issue)
        prior = self._issued_fingerprints_by_cl_ord_id.get(issue.provider_cl_ord_id)
        if prior is not None and prior != fingerprint:
            raise OKXProtocolError(
                "provider clOrdId already has a materially different adapter-issued preparation"
            )
        self._issued_preparations[id(materialization)] = issue
        self._issued_fingerprints_by_cl_ord_id[issue.provider_cl_ord_id] = fingerprint

    def _authorize_submit(
        self,
        materialization: OKXOrderMaterialization,
    ) -> tuple[_IssuedOKXPreparation, dict[str, str]]:
        issue = self._issued_preparations.get(id(materialization))
        if issue is None or issue.materialization is not materialization:
            raise OKXProtocolError(
                "submit requires the exact OKXOrderMaterialization instance issued by this adapter"
            )
        if _materialization_semantic_facts(materialization) != _issued_semantic_facts(issue):
            raise OKXProtocolError("issued materialization semantic facts changed after preparation")
        if issue.environment != "demo" or self._config.environment != issue.environment:
            raise OKXProtocolError("issued preparation Demo environment no longer matches adapter")
        if (
            issue.account_level != self._config.expected_account_level
            or issue.position_mode != self._config.expected_position_mode
        ):
            raise OKXProtocolError("issued account/position preparation context no longer matches adapter")
        if issue.provider_instrument_id != OKX_INSTRUMENT_ID:
            raise OKXProtocolError("issued provider instrument is not the bounded BTC-USDT-SWAP target")
        if issue.provider_order_type != "market" or issue.provider_trade_mode != OKX_TRADE_MODE:
            raise OKXProtocolError("issued provider order type/trade mode is outside bounded policy")
        expected_cl_ord_id = stable_okx_cl_ord_id(issue.internal_client_order_id).provider_cl_ord_id
        if expected_cl_ord_id != issue.provider_cl_ord_id:
            raise OKXProtocolError("issued provider clOrdId is not bound to internal client_order_id")
        if not (
            Decimal("0")
            < issue.effective_canonical_quantity
            <= issue.canonical_approved_quantity
        ):
            raise OKXProtocolError("issued provider exposure violates canonical BTC upper bound")
        if issue.provider_contract_quantity <= 0:
            raise OKXProtocolError("issued provider contract quantity must remain positive")

        trusted_body = _trusted_provider_body(issue)
        if not isinstance(materialization.body, Mapping):
            raise OKXProtocolError("materialization body is no longer a mapping")
        try:
            caller_body = dict(materialization.body)
        except (TypeError, ValueError) as exc:
            raise OKXProtocolError("materialization body cannot be normalized safely") from exc
        if caller_body != trusted_body:
            raise OKXProtocolError(
                "materialization body differs from adapter-issued trusted preparation facts"
            )
        return issue, trusted_body

    def prepare_entry(
        self,
        request: OrderRequest,
        sizing: OKXEntrySizingAudit,
        metadata: OKXInstrumentMetadata,
        prerequisites: OKXPrerequisiteSnapshot,
        *,
        now: datetime,
    ) -> OKXOrderMaterialization:
        materialization = materialize_demo_market_order(
            request,
            sizing,
            metadata,
            prerequisites,
            config=self._config,
            now=now,
        )
        self._register_issued_preparation(
            materialization,
            metadata=metadata,
            prerequisites=prerequisites,
            prepared_at=now,
        )
        return materialization

    def submit_entry(
        self,
        materialization: OKXOrderMaterialization,
        *,
        observed_at: datetime,
    ) -> OrderResult:
        # Provenance/integrity is checked before the idempotency cache so a
        # caller-constructed clone cannot borrow a prior result or reach transport.
        _issue, trusted_body = self._authorize_submit(materialization)
        prior = self._submit_results.get(materialization.provider_cl_ord_id)
        if prior is not None:
            return prior
        prepared = prepare_demo_private_request(
            self._credentials,
            method="POST",
            path=OKX_ORDER_PATH,
            timestamp=self._timestamp_provider(),
            body=trusted_body,
        )
        try:
            response = self._transport.send(prepared)
        except (TimeoutError, ConnectionError):
            result = _reconciliation_required_result(
                materialization,
                observed_at=observed_at,
                reason="AMBIGUOUS_PROVIDER_TRANSPORT_FAILURE",
            )
        else:
            result = parse_place_order_ack(response, materialization, observed_at=observed_at)
        self._submit_results[materialization.provider_cl_ord_id] = result
        return result

    def query_order(
        self,
        materialization: OKXOrderMaterialization,
        *,
        observed_at: datetime,
    ) -> OKXOrderLookup:
        return parse_order_lookup_response(
            self._private_get(
                OKX_ORDER_DETAILS_PATH,
                {"clOrdId": materialization.provider_cl_ord_id, "instId": OKX_INSTRUMENT_ID},
            ),
            materialization,
            observed_at=observed_at,
            config=self._config,
        )

    def read_fills(self, materialization: OKXOrderMaterialization) -> tuple[Fill, ...]:
        return parse_fills_response(
            self._private_get(
                OKX_FILLS_PATH,
                {"instId": OKX_INSTRUMENT_ID, "instType": "SWAP"},
            ),
            materialization,
        )

    def reconcile_ambiguous(
        self,
        materialization: OKXOrderMaterialization,
        *,
        observed_at: datetime,
    ) -> OKXReconciliationEvidence:
        order_lookup = self.query_order(materialization, observed_at=observed_at)
        positions = self.read_positions()
        fills = self.read_fills(materialization)
        pending = self.read_pending_orders()

        matching_pending = tuple(
            item for item in pending if item.client_order_id == materialization.provider_cl_ord_id
        )
        nonzero_positions = tuple(
            item for item in positions if item.provider_contract_quantity != 0
        )

        if order_lookup.found:
            reason = "PROVIDER_ORDER_FOUND_RETRY_DISABLED"
        elif fills:
            reason = "PROVIDER_FILL_FOUND_RETRY_DISABLED"
        elif nonzero_positions:
            reason = "PROVIDER_EXPOSURE_FOUND_RETRY_DISABLED"
        elif matching_pending:
            reason = "PROVIDER_PENDING_ORDER_FOUND_RETRY_DISABLED"
        else:
            reason = "ORDER_ABSENCE_NOT_AUTHORITATIVELY_PROVEN_RETRY_DISABLED"

        return OKXReconciliationEvidence(
            provider_cl_ord_id=materialization.provider_cl_ord_id,
            order_lookup=order_lookup,
            positions=positions,
            fills=fills,
            pending_orders=pending,
            retry_allowed=False,
            reason=reason,
        )

    def retry_entry(
        self,
        materialization: OKXOrderMaterialization,
        evidence: OKXReconciliationEvidence,
        *,
        observed_at: datetime,
    ) -> OrderResult:
        """Provider retry is intentionally unavailable in V1.

        Reconciliation evidence is audit data only. No caller-constructible,
        mutated, replayed, or cross-materialization evidence can authorize a
        second provider submit until an E7-accepted order-absence policy exists.
        """
        raise OKXReconciliationError(
            "provider retry is structurally disabled until authoritative order-absence semantics are accepted"
        )
