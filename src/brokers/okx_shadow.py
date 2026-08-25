from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.parse import urlencode, urlparse

OKX_PROVIDER = "OKX"
OKX_API_VERSION = "V5"
OKX_INSTRUMENT_ID = "BTC-USDT-SWAP"
CANONICAL_SYMBOL = "BTC_USDT_PERP"
SHADOW_ENVIRONMENT = "production_read_only_shadow"
READ_ONLY_PERMISSION = "read_only"
CLOCK_SKEW_LIMIT_MS = 5_000

OKX_PUBLIC_TIME_PATH = "/api/v5/public/time"
OKX_ACCOUNT_CONFIG_PATH = "/api/v5/account/config"
OKX_BALANCE_PATH = "/api/v5/account/balance"
OKX_POSITIONS_PATH = "/api/v5/account/positions"
OKX_LEVERAGE_INFO_PATH = "/api/v5/account/leverage-info"
OKX_PENDING_ORDERS_PATH = "/api/v5/trade/orders-pending"
OKX_FILLS_PATH = "/api/v5/trade/fills"

_PRIVATE_ENDPOINTS: Mapping[str, tuple[str, tuple[tuple[str, str], ...]]] = {
    "account_config": (OKX_ACCOUNT_CONFIG_PATH, ()),
    "balance": (OKX_BALANCE_PATH, (("ccy", "USDT"),)),
    "positions": (OKX_POSITIONS_PATH, (("instId", OKX_INSTRUMENT_ID),)),
    "leverage": (
        OKX_LEVERAGE_INFO_PATH,
        (("instId", OKX_INSTRUMENT_ID), ("mgnMode", "isolated")),
    ),
    "pending_orders": (
        OKX_PENDING_ORDERS_PATH,
        (("instId", OKX_INSTRUMENT_ID), ("instType", "SWAP")),
    ),
    "fills": (
        OKX_FILLS_PATH,
        (("instId", OKX_INSTRUMENT_ID), ("instType", "SWAP")),
    ),
}
_ALLOWED_PRIVATE_REQUESTS = frozenset(_PRIVATE_ENDPOINTS.values())


class OKXShadowConfigurationError(ValueError):
    """Static/configuration failure with intentionally sanitized messages."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class OKXShadowProtocolError(ValueError):
    """Provider/parse failure that never includes raw provider payload material."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class OKXShadowSafetyError(RuntimeError):
    """Fail-closed Shadow safety condition with a stable sanitized reason code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, repr=False)
class OKXShadowCredentials:
    """Runtime-only read credentials. Values are never represented or persisted."""

    api_key: str
    secret_key: str
    passphrase: str

    def __post_init__(self) -> None:
        for value in (self.api_key, self.secret_key, self.passphrase):
            if not isinstance(value, str) or not value:
                raise OKXShadowConfigurationError("CREDENTIALS_REQUIRED")

    def __repr__(self) -> str:
        return "OKXShadowCredentials(<redacted>)"


def _normalize_base_url(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise OKXShadowConfigurationError("REST_DOMAIN_REQUIRED")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise OKXShadowConfigurationError("REST_DOMAIN_INVALID")
    if parsed.username or parsed.password or parsed.port is not None:
        raise OKXShadowConfigurationError("REST_DOMAIN_INVALID")
    if parsed.query or parsed.fragment or parsed.params:
        raise OKXShadowConfigurationError("REST_DOMAIN_INVALID")
    if parsed.path not in {"", "/"}:
        raise OKXShadowConfigurationError("REST_DOMAIN_INVALID")
    hostname = parsed.hostname.lower()
    if hostname != "okx.com" and not hostname.endswith(".okx.com"):
        raise OKXShadowConfigurationError("REST_DOMAIN_NOT_OKX")
    return f"https://{hostname}"


@dataclass(frozen=True)
class OKXShadowReaderConfig:
    """Operator-confirmed production REST identity and bounded account expectations."""

    rest_base_url: str
    operator_confirmed_rest_base_url: str
    expected_account_level: str = "2"
    expected_position_mode: str = "net_mode"

    def __post_init__(self) -> None:
        configured = _normalize_base_url(self.rest_base_url)
        confirmed = _normalize_base_url(self.operator_confirmed_rest_base_url)
        if configured != confirmed:
            raise OKXShadowConfigurationError("REST_DOMAIN_CONFIRMATION_MISMATCH")
        if self.expected_account_level != "2":
            raise OKXShadowConfigurationError("ACCOUNT_LEVEL_UNSUPPORTED")
        if self.expected_position_mode not in {"net_mode", "long_short_mode"}:
            raise OKXShadowConfigurationError("POSITION_MODE_UNSUPPORTED")
        object.__setattr__(self, "rest_base_url", configured)
        object.__setattr__(self, "operator_confirmed_rest_base_url", confirmed)

    @property
    def hostname(self) -> str:
        return urlparse(self.rest_base_url).hostname or ""


@dataclass(frozen=True, repr=False)
class PreparedOKXShadowRequest:
    base_url: str
    method: str
    request_path: str
    body_text: str
    headers: Mapping[str, str]
    authenticated: bool

    def __repr__(self) -> str:
        return (
            "PreparedOKXShadowRequest(base_url={!r}, method={!r}, request_path={!r}, "
            "body_len={}, header_names={!r}, authenticated={!r})"
        ).format(
            self.base_url,
            self.method,
            self.request_path,
            len(self.body_text),
            tuple(sorted(self.headers.keys())),
            self.authenticated,
        )


class OKXShadowTransport(Protocol):
    """Injected transport seam. This module intentionally provides no network client."""

    def send(self, request: PreparedOKXShadowRequest) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class ShadowFillCheckpoint:
    """Sanitized recent-fill checkpoint containing no provider order/fill identifiers."""

    latest_fill_timestamp_ms: int | None
    records_at_latest_timestamp: int = 0

    def __post_init__(self) -> None:
        if self.latest_fill_timestamp_ms is None:
            if self.records_at_latest_timestamp != 0:
                raise OKXShadowConfigurationError("FILL_CHECKPOINT_INVALID")
            return
        if isinstance(self.latest_fill_timestamp_ms, bool) or self.latest_fill_timestamp_ms < 0:
            raise OKXShadowConfigurationError("FILL_CHECKPOINT_INVALID")
        if (
            isinstance(self.records_at_latest_timestamp, bool)
            or self.records_at_latest_timestamp <= 0
        ):
            raise OKXShadowConfigurationError("FILL_CHECKPOINT_INVALID")


@dataclass(frozen=True)
class OKXShadowObservation:
    """Sanitized Gate C provider observation; no secret/raw sensitive identifiers."""

    provider: str
    api_version: str
    environment: str
    rest_hostname: str
    canonical_symbol: str
    provider_instrument_id: str
    observed_at: datetime
    provider_time: datetime | None
    clock_skew_ms: int | None
    clock_status: str
    permission_category: str | None
    account_config_known: bool
    account_level: str | None
    position_mode: str | None
    subaccount_status: str
    usdt_balance_known: bool
    position_known: bool
    unexpected_exposure: bool | None
    isolated_leverage_known: bool
    isolated_leverage_ok: bool | None
    pending_order_count: int | None
    recent_fill_window_count: int | None
    fill_checkpoint: ShadowFillCheckpoint | None
    new_unreconciled_fill_count: int | None
    private_get_count: int
    health_status: str
    reason_codes: tuple[str, ...]

    @property
    def healthy(self) -> bool:
        return self.health_status == "HEALTHY"


@dataclass
class _ObservationState:
    observed_at: datetime
    provider_time: datetime | None = None
    clock_skew_ms: int | None = None
    clock_status: str = "UNKNOWN"
    permission_category: str | None = None
    account_config_known: bool = False
    account_level: str | None = None
    position_mode: str | None = None
    subaccount_status: str = "UNKNOWN"
    usdt_balance_known: bool = False
    position_known: bool = False
    unexpected_exposure: bool | None = None
    isolated_leverage_known: bool = False
    isolated_leverage_ok: bool | None = None
    pending_order_count: int | None = None
    recent_fill_window_count: int | None = None
    fill_checkpoint: ShadowFillCheckpoint | None = None
    new_unreconciled_fill_count: int | None = None
    private_get_count: int = 0


def _require_utc(value: datetime, code: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise OKXShadowConfigurationError(code)
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise OKXShadowConfigurationError(code)
    return value.astimezone(timezone.utc)


def _format_okx_timestamp(value: datetime) -> str:
    value = _require_utc(value, "LOCAL_CLOCK_NOT_UTC")
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _validate_iso_timestamp(value: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise OKXShadowConfigurationError("SIGNING_TIMESTAMP_INVALID")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise OKXShadowConfigurationError("SIGNING_TIMESTAMP_INVALID") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise OKXShadowConfigurationError("SIGNING_TIMESTAMP_INVALID")
    return value


def _canonical_query(query: Mapping[str, str] | None) -> tuple[tuple[str, str], ...]:
    if not query:
        return ()
    return tuple(sorted((str(key), str(value)) for key, value in query.items()))


def _request_path(path: str, query: Mapping[str, str] | None) -> str:
    if not isinstance(path, str) or not path.startswith("/api/v5/"):
        raise OKXShadowConfigurationError("PRIVATE_PATH_INVALID")
    items = _canonical_query(query)
    if not items:
        return path
    return path + "?" + urlencode(items)


def sign_okx_shadow_get(
    *,
    secret_key: str,
    timestamp: str,
    request_path: str,
) -> str:
    """OKX V5: Base64(HMAC-SHA256(timestamp + GET + requestPath + empty body))."""

    _validate_iso_timestamp(timestamp)
    if not isinstance(secret_key, str) or not secret_key:
        raise OKXShadowConfigurationError("CREDENTIALS_REQUIRED")
    prehash = f"{timestamp}GET{request_path}"
    digest = hmac.new(secret_key.encode(), prehash.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def _prepare_shadow_private_request(
    credentials: OKXShadowCredentials,
    config: OKXShadowReaderConfig,
    *,
    method: str,
    path: str,
    query: Mapping[str, str] | None,
    timestamp: str,
) -> PreparedOKXShadowRequest:
    """Private default-deny constructor used internally and by bounded unit tests."""

    upper_method = method.upper() if isinstance(method, str) else ""
    if upper_method != "GET":
        raise OKXShadowConfigurationError("PRIVATE_METHOD_DENIED")
    query_items = _canonical_query(query)
    if (path, query_items) not in _ALLOWED_PRIVATE_REQUESTS:
        raise OKXShadowConfigurationError("PRIVATE_ENDPOINT_DENIED")
    full_path = _request_path(path, dict(query_items))
    signature = sign_okx_shadow_get(
        secret_key=credentials.secret_key,
        timestamp=timestamp,
        request_path=full_path,
    )
    headers = {
        "Accept": "application/json",
        "OK-ACCESS-KEY": credentials.api_key,
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": credentials.passphrase,
    }
    return PreparedOKXShadowRequest(
        base_url=config.rest_base_url,
        method="GET",
        request_path=full_path,
        body_text="",
        headers=headers,
        authenticated=True,
    )


def _prepare_public_time_request(config: OKXShadowReaderConfig) -> PreparedOKXShadowRequest:
    return PreparedOKXShadowRequest(
        base_url=config.rest_base_url,
        method="GET",
        request_path=OKX_PUBLIC_TIME_PATH,
        body_text="",
        headers={"Accept": "application/json"},
        authenticated=False,
    )


def _require_success_data(response: Mapping[str, Any], code: str) -> Sequence[Any]:
    if not isinstance(response, Mapping):
        raise OKXShadowProtocolError(f"{code}_MALFORMED")
    if response.get("code") != "0":
        raise OKXShadowProtocolError(f"{code}_PROVIDER_ERROR")
    data = response.get("data")
    if not isinstance(data, Sequence) or isinstance(data, (str, bytes)):
        raise OKXShadowProtocolError(f"{code}_MALFORMED")
    return data


def _parse_decimal(value: Any, code: str, *, signed: bool = False) -> Decimal:
    if not isinstance(value, str) or not value:
        raise OKXShadowProtocolError(code)
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise OKXShadowProtocolError(code) from exc
    if not parsed.is_finite() or (not signed and parsed < 0):
        raise OKXShadowProtocolError(code)
    return parsed


def _parse_provider_time(response: Mapping[str, Any]) -> datetime:
    data = _require_success_data(response, "PUBLIC_TIME")
    if len(data) != 1 or not isinstance(data[0], Mapping):
        raise OKXShadowProtocolError("PUBLIC_TIME_MALFORMED")
    ts = data[0].get("ts")
    if not isinstance(ts, str) or not ts.isdigit():
        raise OKXShadowProtocolError("PUBLIC_TIME_MALFORMED")
    return datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc)


def _parse_account_config(
    response: Mapping[str, Any],
    config: OKXShadowReaderConfig,
) -> tuple[str, str, str, str]:
    data = _require_success_data(response, "ACCOUNT_CONFIG")
    if len(data) != 1 or not isinstance(data[0], Mapping):
        raise OKXShadowProtocolError("ACCOUNT_CONFIG_MALFORMED")
    item = data[0]
    permission = item.get("perm")
    if permission != READ_ONLY_PERMISSION:
        raise OKXShadowSafetyError("PERMISSION_NOT_READ_ONLY")
    account_level = item.get("acctLv")
    position_mode = item.get("posMode")
    uid = item.get("uid")
    main_uid = item.get("mainUid")
    if not all(isinstance(value, str) and value for value in (account_level, position_mode, uid, main_uid)):
        raise OKXShadowProtocolError("ACCOUNT_CONFIG_MALFORMED")
    if account_level != config.expected_account_level:
        raise OKXShadowSafetyError("ACCOUNT_LEVEL_MISMATCH")
    if position_mode != config.expected_position_mode:
        raise OKXShadowSafetyError("POSITION_MODE_MISMATCH")
    if uid == main_uid:
        raise OKXShadowSafetyError("DEDICATED_SUBACCOUNT_NOT_CONFIRMED")
    return permission, account_level, position_mode, "SUBACCOUNT"


def _parse_usdt_balance_known(response: Mapping[str, Any]) -> bool:
    data = _require_success_data(response, "BALANCE")
    if len(data) != 1 or not isinstance(data[0], Mapping):
        raise OKXShadowProtocolError("BALANCE_MALFORMED")
    details = data[0].get("details")
    if not isinstance(details, Sequence) or isinstance(details, (str, bytes)):
        raise OKXShadowProtocolError("BALANCE_MALFORMED")
    matches = [item for item in details if isinstance(item, Mapping) and item.get("ccy") == "USDT"]
    if len(matches) != 1:
        raise OKXShadowProtocolError("BALANCE_USDT_UNKNOWN")
    _parse_decimal(matches[0].get("availBal"), "BALANCE_USDT_MALFORMED")
    return True


def _parse_positions(
    response: Mapping[str, Any],
    *,
    expected_position_mode: str,
) -> bool:
    data = _require_success_data(response, "POSITIONS")
    unexpected_exposure = False
    for item in data:
        if not isinstance(item, Mapping) or item.get("instId") != OKX_INSTRUMENT_ID:
            raise OKXShadowProtocolError("POSITIONS_MALFORMED")
        if item.get("mgnMode") != "isolated":
            raise OKXShadowSafetyError("POSITION_MARGIN_MODE_UNEXPECTED")
        pos_side = item.get("posSide")
        if expected_position_mode == "net_mode" and pos_side != "net":
            raise OKXShadowSafetyError("POSITION_SIDE_MODE_MISMATCH")
        if expected_position_mode == "long_short_mode" and pos_side not in {"long", "short"}:
            raise OKXShadowSafetyError("POSITION_SIDE_MODE_MISMATCH")
        quantity = _parse_decimal(item.get("pos"), "POSITION_QUANTITY_MALFORMED", signed=True)
        if quantity != 0:
            unexpected_exposure = True
    return unexpected_exposure


def _parse_leverage_known(response: Mapping[str, Any]) -> bool:
    data = _require_success_data(response, "LEVERAGE")
    if not data:
        raise OKXShadowProtocolError("LEVERAGE_UNKNOWN")
    for item in data:
        if not isinstance(item, Mapping):
            raise OKXShadowProtocolError("LEVERAGE_MALFORMED")
        if item.get("instId") != OKX_INSTRUMENT_ID or item.get("mgnMode") != "isolated":
            raise OKXShadowSafetyError("LEVERAGE_MARGIN_PREREQUISITE_MISMATCH")
        leverage = _parse_decimal(item.get("lever"), "LEVERAGE_MALFORMED")
        if leverage <= 0:
            raise OKXShadowProtocolError("LEVERAGE_MALFORMED")
    return True


def _parse_pending_order_count(response: Mapping[str, Any]) -> int:
    data = _require_success_data(response, "PENDING_ORDERS")
    for item in data:
        if not isinstance(item, Mapping) or item.get("instId") != OKX_INSTRUMENT_ID:
            raise OKXShadowProtocolError("PENDING_ORDERS_MALFORMED")
    return len(data)


def _fill_timestamp_ms(item: Mapping[str, Any]) -> int:
    value = item.get("fillTime") or item.get("ts")
    if not isinstance(value, str) or not value.isdigit():
        raise OKXShadowProtocolError("FILLS_MALFORMED")
    return int(value)


def _parse_fill_window(
    response: Mapping[str, Any],
    previous: ShadowFillCheckpoint | None,
) -> tuple[int, ShadowFillCheckpoint, int]:
    data = _require_success_data(response, "FILLS")
    timestamps: list[int] = []
    for item in data:
        if not isinstance(item, Mapping) or item.get("instId") != OKX_INSTRUMENT_ID:
            raise OKXShadowProtocolError("FILLS_MALFORMED")
        timestamps.append(_fill_timestamp_ms(item))

    if not timestamps:
        checkpoint = previous or ShadowFillCheckpoint(None, 0)
        return 0, checkpoint, 0

    latest = max(timestamps)
    at_latest = sum(1 for value in timestamps if value == latest)
    candidate = ShadowFillCheckpoint(latest, at_latest)
    if previous is None or previous.latest_fill_timestamp_ms is None:
        return len(timestamps), candidate, len(timestamps)

    prior_latest = previous.latest_fill_timestamp_ms
    if latest < prior_latest:
        raise OKXShadowSafetyError("FILL_CHECKPOINT_REGRESSED")
    if latest == prior_latest:
        if at_latest < previous.records_at_latest_timestamp:
            raise OKXShadowSafetyError("FILL_CHECKPOINT_REGRESSED")
        new_count = at_latest - previous.records_at_latest_timestamp
    else:
        new_count = sum(1 for value in timestamps if value > prior_latest)
    return len(timestamps), candidate, new_count


class OKXShadowProviderReader:
    """Production/private Gate C reader with no submit or mutation capability surface."""

    __slots__ = ("_credentials", "_config", "_transport", "_utc_now_provider")

    def __init__(
        self,
        *,
        credentials: OKXShadowCredentials,
        config: OKXShadowReaderConfig,
        transport: OKXShadowTransport,
        utc_now_provider: Callable[[], datetime],
    ) -> None:
        if not isinstance(credentials, OKXShadowCredentials):
            raise OKXShadowConfigurationError("CREDENTIALS_REQUIRED")
        if not isinstance(config, OKXShadowReaderConfig):
            raise OKXShadowConfigurationError("SHADOW_CONFIG_REQUIRED")
        if not callable(getattr(transport, "send", None)):
            raise OKXShadowConfigurationError("TRANSPORT_REQUIRED")
        if not callable(utc_now_provider):
            raise OKXShadowConfigurationError("CLOCK_PROVIDER_REQUIRED")
        self._credentials = credentials
        self._config = config
        self._transport = transport
        self._utc_now_provider = utc_now_provider

    def __repr__(self) -> str:
        return (
            "OKXShadowProviderReader(provider='OKX', environment='production_read_only_shadow', "
            f"rest_hostname={self._config.hostname!r})"
        )

    @property
    def provider(self) -> str:
        return OKX_PROVIDER

    @property
    def environment(self) -> str:
        return SHADOW_ENVIRONMENT

    def _send(self, request: PreparedOKXShadowRequest, failure_code: str) -> Mapping[str, Any]:
        try:
            response = self._transport.send(request)
        except Exception:  # transport/provider detail is deliberately discarded
            raise OKXShadowProtocolError(failure_code) from None
        if not isinstance(response, Mapping):
            raise OKXShadowProtocolError(failure_code)
        return response

    def _private_get(self, endpoint_name: str, *, state: _ObservationState) -> Mapping[str, Any]:
        endpoint = _PRIVATE_ENDPOINTS.get(endpoint_name)
        if endpoint is None:
            raise OKXShadowConfigurationError("PRIVATE_ENDPOINT_DENIED")
        path, query_items = endpoint
        timestamp = _format_okx_timestamp(_require_utc(self._utc_now_provider(), "LOCAL_CLOCK_NOT_UTC"))
        request = _prepare_shadow_private_request(
            self._credentials,
            self._config,
            method="GET",
            path=path,
            query=dict(query_items),
            timestamp=timestamp,
        )
        state.private_get_count += 1
        return self._send(request, f"{endpoint_name.upper()}_TRANSPORT_FAILURE")

    def _observation(self, state: _ObservationState, *, reason_codes: tuple[str, ...]) -> OKXShadowObservation:
        return OKXShadowObservation(
            provider=OKX_PROVIDER,
            api_version=OKX_API_VERSION,
            environment=SHADOW_ENVIRONMENT,
            rest_hostname=self._config.hostname,
            canonical_symbol=CANONICAL_SYMBOL,
            provider_instrument_id=OKX_INSTRUMENT_ID,
            observed_at=state.observed_at,
            provider_time=state.provider_time,
            clock_skew_ms=state.clock_skew_ms,
            clock_status=state.clock_status,
            permission_category=state.permission_category,
            account_config_known=state.account_config_known,
            account_level=state.account_level,
            position_mode=state.position_mode,
            subaccount_status=state.subaccount_status,
            usdt_balance_known=state.usdt_balance_known,
            position_known=state.position_known,
            unexpected_exposure=state.unexpected_exposure,
            isolated_leverage_known=state.isolated_leverage_known,
            isolated_leverage_ok=state.isolated_leverage_ok,
            pending_order_count=state.pending_order_count,
            recent_fill_window_count=state.recent_fill_window_count,
            fill_checkpoint=state.fill_checkpoint,
            new_unreconciled_fill_count=state.new_unreconciled_fill_count,
            private_get_count=state.private_get_count,
            health_status="HEALTHY" if not reason_codes else "DEGRADED",
            reason_codes=reason_codes,
        )

    def observe(
        self,
        *,
        previous_fill_checkpoint: ShadowFillCheckpoint | None = None,
    ) -> OKXShadowObservation:
        """Read one fail-closed production Shadow batch using only the fixed GET allowlist."""

        if previous_fill_checkpoint is not None and not isinstance(
            previous_fill_checkpoint, ShadowFillCheckpoint
        ):
            raise OKXShadowConfigurationError("FILL_CHECKPOINT_INVALID")
        observed_at = _require_utc(self._utc_now_provider(), "LOCAL_CLOCK_NOT_UTC")
        state = _ObservationState(observed_at=observed_at)

        try:
            time_response = self._send(
                _prepare_public_time_request(self._config),
                "PUBLIC_TIME_TRANSPORT_FAILURE",
            )
            state.provider_time = _parse_provider_time(time_response)
            local_for_skew = _require_utc(self._utc_now_provider(), "LOCAL_CLOCK_NOT_UTC")
            state.clock_skew_ms = int(
                round(abs((local_for_skew - state.provider_time).total_seconds()) * 1000)
            )
            if state.clock_skew_ms > CLOCK_SKEW_LIMIT_MS:
                raise OKXShadowSafetyError("CLOCK_SKEW_EXCEEDED")
            state.clock_status = "HEALTHY"

            permission, account_level, position_mode, subaccount_status = _parse_account_config(
                self._private_get("account_config", state=state),
                self._config,
            )
            state.permission_category = permission
            state.account_level = account_level
            state.position_mode = position_mode
            state.subaccount_status = subaccount_status
            state.account_config_known = True

            state.usdt_balance_known = _parse_usdt_balance_known(
                self._private_get("balance", state=state)
            )

            state.unexpected_exposure = _parse_positions(
                self._private_get("positions", state=state),
                expected_position_mode=self._config.expected_position_mode,
            )
            state.position_known = True
            if state.unexpected_exposure:
                raise OKXShadowSafetyError("UNEXPECTED_POSITION_EXPOSURE")

            state.isolated_leverage_ok = _parse_leverage_known(
                self._private_get("leverage", state=state)
            )
            state.isolated_leverage_known = True

            state.pending_order_count = _parse_pending_order_count(
                self._private_get("pending_orders", state=state)
            )
            if state.pending_order_count != 0:
                raise OKXShadowSafetyError("UNEXPECTED_PENDING_ORDER")

            (
                state.recent_fill_window_count,
                state.fill_checkpoint,
                state.new_unreconciled_fill_count,
            ) = _parse_fill_window(
                self._private_get("fills", state=state),
                previous_fill_checkpoint,
            )
            if state.new_unreconciled_fill_count != 0:
                raise OKXShadowSafetyError("NEW_UNRECONCILED_FILL_ACTIVITY")

        except (OKXShadowProtocolError, OKXShadowSafetyError) as exc:
            return self._observation(state, reason_codes=(exc.code,))

        return self._observation(state, reason_codes=())
