from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any, Dict, Optional, Tuple, Union

from indicators import sma

SUPPORTED_SHARED_SCHEMA_VERSION = "contracts-v0.1"
RUNTIME_FAMILY = "project-r7-e2-strategy-runtime"
RUNTIME_VERSION = "0.1.0"
DSL_VERSION = "0.1"

_REQUIRED_DEFINITION_FIELDS = {
    "schema_version",
    "strategy_id",
    "strategy_version",
    "name",
    "symbol",
    "required_timeframes",
    "parameters",
    "rules",
    "runtime_compatibility",
    "content_hash",
    "created_at",
}
_SUPPORTED_TIMEFRAMES = {"1m", "15m", "1h", "4h"}
_SUPPORTED_PRIMITIVES = {"SMA"}
_SUPPORTED_OPERATORS = {"GT", "LT", "AND"}


class StrategyError(ValueError):
    """Base structured E2 strategy error."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            result["details"] = dict(self.details)
        return result


class StrategyValidationError(StrategyError):
    pass


class UnsupportedPrimitiveError(StrategyValidationError):
    def __init__(self, primitive: str) -> None:
        super().__init__(
            "UNSUPPORTED_PRIMITIVE",
            f"Strategy primitive is not supported by runtime {RUNTIME_VERSION}: {primitive}",
            primitive=primitive,
            runtime_version=RUNTIME_VERSION,
        )


class MarketBoundaryError(StrategyError):
    pass


@dataclass(frozen=True)
class ParsedStrategyDefinition:
    schema_version: str
    strategy_id: str
    strategy_version: str
    name: str
    symbol: str
    required_timeframe: str
    parameters: Mapping[str, Any]
    rules: Mapping[str, Any]
    runtime_family: str
    runtime_version: str
    content_hash: str
    created_at: str
    canonical_json: str


@dataclass(frozen=True)
class _CandleView:
    schema_version: str
    symbol: str
    timeframe: str
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    source: str


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _json_object_no_duplicates(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrategyValidationError(
                "DUPLICATE_JSON_KEY",
                f"Duplicate JSON key is not allowed: {key}",
                key=key,
            )
        result[key] = value
    return result


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise StrategyValidationError(
            "NON_SERIALIZABLE_STRATEGY",
            "StrategyDefinition must be deterministically JSON serializable",
        ) from exc


def compute_content_hash(definition: Mapping[str, Any]) -> str:
    """Compute immutable strategy content identity excluding content_hash itself."""
    material = dict(definition)
    material.pop("content_hash", None)
    digest = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _require_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StrategyValidationError(
            "INVALID_FIELD",
            f"{field} must be a non-empty string",
            field=field,
        )
    return value


def _parse_utc(value: Any, field: str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise StrategyValidationError(
                "INVALID_UTC_TIMESTAMP",
                f"{field} must be timezone-aware UTC",
                field=field,
            )
        return value.astimezone(timezone.utc)

    if not isinstance(value, str) or not value.endswith("Z"):
        raise StrategyValidationError(
            "INVALID_UTC_TIMESTAMP",
            f"{field} must be RFC 3339 UTC ending in Z",
            field=field,
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise StrategyValidationError(
            "INVALID_UTC_TIMESTAMP",
            f"{field} must be valid RFC 3339 UTC",
            field=field,
        ) from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise StrategyValidationError(
            "INVALID_UTC_TIMESTAMP",
            f"{field} must be UTC",
            field=field,
        )
    return parsed.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc).isoformat()
    return normalized.replace("+00:00", "Z")


def _validate_parameter_reference(node: Any, parameters: Mapping[str, Any]) -> None:
    if not isinstance(node, Mapping) or set(node.keys()) != {"parameter"}:
        raise StrategyValidationError(
            "INVALID_DSL",
            "SMA window must be a parameter reference",
        )
    name = _require_non_empty_string(node["parameter"], "rules.window.parameter")
    if name not in parameters:
        raise StrategyValidationError(
            "UNKNOWN_PARAMETER",
            f"Rule references unknown parameter: {name}",
            parameter=name,
        )
    value = parameters[name]
    if type(value) is not int or value <= 0:
        raise StrategyValidationError(
            "INVALID_PARAMETER",
            f"SMA window parameter must be a positive integer: {name}",
            parameter=name,
        )


def _validate_numeric_expression(node: Any, parameters: Mapping[str, Any]) -> None:
    if not isinstance(node, Mapping):
        raise StrategyValidationError("INVALID_DSL", "Numeric expression must be an object")
    allowed = {"primitive", "field", "window"}
    if set(node.keys()) != allowed:
        raise StrategyValidationError(
            "INVALID_DSL",
            "SMA expression must contain exactly primitive, field, and window",
        )

    primitive = _require_non_empty_string(node["primitive"], "rules.primitive")
    if primitive not in _SUPPORTED_PRIMITIVES:
        raise UnsupportedPrimitiveError(primitive)
    if node["field"] != "close":
        raise StrategyValidationError(
            "UNSUPPORTED_FIELD",
            "Slice 1 SMA supports only canonical Candle.close",
            field=node["field"],
        )
    _validate_parameter_reference(node["window"], parameters)


def _validate_boolean_expression(node: Any, parameters: Mapping[str, Any]) -> None:
    if not isinstance(node, Mapping):
        raise StrategyValidationError("INVALID_DSL", "Boolean expression must be an object")
    operator = _require_non_empty_string(node.get("operator"), "rules.operator")
    if operator not in _SUPPORTED_OPERATORS:
        raise StrategyValidationError(
            "UNSUPPORTED_OPERATOR",
            f"Strategy operator is not supported by runtime {RUNTIME_VERSION}: {operator}",
            operator=operator,
            runtime_version=RUNTIME_VERSION,
        )

    if operator in {"GT", "LT"}:
        if set(node.keys()) != {"operator", "left", "right"}:
            raise StrategyValidationError(
                "INVALID_DSL",
                f"{operator} must contain exactly operator, left, and right",
            )
        _validate_numeric_expression(node["left"], parameters)
        _validate_numeric_expression(node["right"], parameters)
        return

    if set(node.keys()) != {"operator", "conditions"}:
        raise StrategyValidationError(
            "INVALID_DSL",
            "AND must contain exactly operator and conditions",
        )
    conditions = node["conditions"]
    if not isinstance(conditions, list) or not conditions:
        raise StrategyValidationError(
            "INVALID_DSL",
            "AND conditions must be a non-empty list",
        )
    for condition in conditions:
        _validate_boolean_expression(condition, parameters)


def _load_definition(payload: Union[str, bytes, bytearray, Mapping[str, Any]]) -> Mapping[str, Any]:
    if isinstance(payload, Mapping):
        return dict(payload)
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode("utf-8")
    if not isinstance(payload, str):
        raise StrategyValidationError(
            "INVALID_STRATEGY_PAYLOAD",
            "StrategyDefinition must be a mapping or JSON object string",
        )
    try:
        decoded = json.loads(payload, object_pairs_hook=_json_object_no_duplicates)
    except StrategyError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise StrategyValidationError(
            "INVALID_JSON",
            "StrategyDefinition JSON could not be parsed",
        ) from exc
    if not isinstance(decoded, Mapping):
        raise StrategyValidationError(
            "INVALID_STRATEGY_PAYLOAD",
            "StrategyDefinition JSON root must be an object",
        )
    return decoded


def parse_strategy_definition(
    payload: Union[str, bytes, bytearray, Mapping[str, Any]]
) -> ParsedStrategyDefinition:
    raw = _load_definition(payload)
    keys = set(raw.keys())
    missing = sorted(_REQUIRED_DEFINITION_FIELDS - keys)
    extra = sorted(keys - _REQUIRED_DEFINITION_FIELDS)
    if missing:
        raise StrategyValidationError(
            "MISSING_REQUIRED_FIELD",
            "StrategyDefinition is missing required fields",
            fields=missing,
        )
    if extra:
        raise StrategyValidationError(
            "UNKNOWN_TOP_LEVEL_FIELD",
            "Slice 1 runtime does not accept undeclared StrategyDefinition fields",
            fields=extra,
        )

    schema_version = _require_non_empty_string(raw["schema_version"], "schema_version")
    if schema_version != SUPPORTED_SHARED_SCHEMA_VERSION:
        raise StrategyValidationError(
            "UNSUPPORTED_SCHEMA_VERSION",
            "StrategyDefinition schema_version is not supported by this E2 runtime",
            object_type="StrategyDefinition",
            supported=SUPPORTED_SHARED_SCHEMA_VERSION,
            actual=schema_version,
        )
    strategy_id = _require_non_empty_string(raw["strategy_id"], "strategy_id")
    strategy_version = _require_non_empty_string(raw["strategy_version"], "strategy_version")
    name = _require_non_empty_string(raw["name"], "name")
    symbol = _require_non_empty_string(raw["symbol"], "symbol")
    created_at = _require_non_empty_string(raw["created_at"], "created_at")
    _parse_utc(created_at, "created_at")

    required_timeframes = raw["required_timeframes"]
    if not isinstance(required_timeframes, list) or len(required_timeframes) != 1:
        raise StrategyValidationError(
            "UNSUPPORTED_TIMEFRAME_COMPOSITION",
            "Slice 1 runtime supports exactly one required timeframe",
        )
    required_timeframe = _require_non_empty_string(
        required_timeframes[0], "required_timeframes[0]"
    )
    if required_timeframe not in _SUPPORTED_TIMEFRAMES:
        raise StrategyValidationError(
            "UNSUPPORTED_TIMEFRAME",
            f"Unsupported canonical timeframe: {required_timeframe}",
            timeframe=required_timeframe,
        )

    parameters = raw["parameters"]
    if not isinstance(parameters, Mapping):
        raise StrategyValidationError("INVALID_FIELD", "parameters must be an object")

    rules = raw["rules"]
    if not isinstance(rules, Mapping) or set(rules.keys()) != {"dsl_version", "long", "short"}:
        raise StrategyValidationError(
            "INVALID_DSL",
            "rules must contain exactly dsl_version, long, and short",
        )
    if rules["dsl_version"] != DSL_VERSION:
        raise StrategyValidationError(
            "UNSUPPORTED_DSL_VERSION",
            f"Unsupported DSL version: {rules['dsl_version']}",
            supported=DSL_VERSION,
        )
    _validate_boolean_expression(rules["long"], parameters)
    _validate_boolean_expression(rules["short"], parameters)

    runtime_compatibility = raw["runtime_compatibility"]
    if not isinstance(runtime_compatibility, Mapping) or set(runtime_compatibility.keys()) != {
        "runtime_family",
        "runtime_version",
    }:
        raise StrategyValidationError(
            "INVALID_RUNTIME_COMPATIBILITY",
            "runtime_compatibility must declare runtime_family and runtime_version",
        )
    runtime_family = _require_non_empty_string(
        runtime_compatibility["runtime_family"], "runtime_compatibility.runtime_family"
    )
    runtime_version = _require_non_empty_string(
        runtime_compatibility["runtime_version"], "runtime_compatibility.runtime_version"
    )
    if runtime_family != RUNTIME_FAMILY or runtime_version != RUNTIME_VERSION:
        raise StrategyValidationError(
            "RUNTIME_INCOMPATIBLE",
            "StrategyDefinition runtime compatibility does not match this E2 runtime",
            expected_family=RUNTIME_FAMILY,
            expected_version=RUNTIME_VERSION,
            actual_family=runtime_family,
            actual_version=runtime_version,
        )

    declared_hash = _require_non_empty_string(raw["content_hash"], "content_hash")
    computed_hash = compute_content_hash(raw)
    if declared_hash != computed_hash:
        raise StrategyValidationError(
            "CONTENT_HASH_MISMATCH",
            "StrategyDefinition content_hash does not match immutable serialized content",
            declared=declared_hash,
            computed=computed_hash,
        )

    canonical = _canonical_json(raw)
    return ParsedStrategyDefinition(
        schema_version=schema_version,
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        name=name,
        symbol=symbol,
        required_timeframe=required_timeframe,
        parameters=_freeze(parameters),
        rules=_freeze(rules),
        runtime_family=runtime_family,
        runtime_version=runtime_version,
        content_hash=declared_hash,
        created_at=_format_utc(_parse_utc(created_at, "created_at")),
        canonical_json=canonical,
    )


def validate_strategy_definition(
    payload: Union[str, bytes, bytearray, Mapping[str, Any]]
) -> Dict[str, Any]:
    """Return structured validation status; unsupported primitives are explicit."""
    try:
        parsed = parse_strategy_definition(payload)
    except StrategyError as exc:
        return {"valid": False, "error": exc.as_dict()}
    return {
        "valid": True,
        "strategy_id": parsed.strategy_id,
        "strategy_version": parsed.strategy_version,
        "content_hash": parsed.content_hash,
        "runtime_version": parsed.runtime_version,
    }


def _read_field(candle: Any, field: str) -> Any:
    if isinstance(candle, Mapping):
        if field not in candle:
            raise MarketBoundaryError(
                "INVALID_CANDLE_INPUT",
                f"Canonical Candle field is missing: {field}",
                field=field,
            )
        return candle[field]
    if hasattr(candle, field):
        return getattr(candle, field)
    raise MarketBoundaryError(
        "INVALID_CANDLE_INPUT",
        f"Canonical Candle field is missing: {field}",
        field=field,
    )


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, str):
        try:
            result = Decimal(value)
        except InvalidOperation as exc:
            raise MarketBoundaryError(
                "INVALID_CANDLE_DECIMAL",
                f"Candle.{field} is not a valid base-10 decimal",
                field=field,
            ) from exc
    else:
        raise MarketBoundaryError(
            "INVALID_CANDLE_DECIMAL",
            f"Candle.{field} must be Decimal internally or a decimal string at interchange",
            field=field,
        )
    if not result.is_finite():
        raise MarketBoundaryError(
            "INVALID_CANDLE_DECIMAL",
            f"Candle.{field} must be finite",
            field=field,
        )
    return result


def _candle_view(candle: Any, strategy: ParsedStrategyDefinition) -> _CandleView:
    schema_version = _require_non_empty_string(
        _read_field(candle, "schema_version"), "Candle.schema_version"
    )
    if schema_version != SUPPORTED_SHARED_SCHEMA_VERSION:
        raise MarketBoundaryError(
            "UNSUPPORTED_CANDLE_SCHEMA_VERSION",
            "Consumed Candle schema_version is not supported by this E2 runtime",
            supported=SUPPORTED_SHARED_SCHEMA_VERSION,
            actual=schema_version,
        )
    symbol = _require_non_empty_string(_read_field(candle, "symbol"), "Candle.symbol")
    timeframe = _require_non_empty_string(_read_field(candle, "timeframe"), "Candle.timeframe")
    source = _require_non_empty_string(_read_field(candle, "source"), "Candle.source")
    if symbol != strategy.symbol:
        raise MarketBoundaryError(
            "CANDLE_SYMBOL_MISMATCH",
            "Candle symbol does not match StrategyDefinition symbol",
            candle_symbol=symbol,
            strategy_symbol=strategy.symbol,
        )
    if timeframe != strategy.required_timeframe:
        raise MarketBoundaryError(
            "CANDLE_TIMEFRAME_MISMATCH",
            "Candle timeframe does not match the Slice 1 strategy timeframe",
            candle_timeframe=timeframe,
            strategy_timeframe=strategy.required_timeframe,
        )

    open_time = _parse_utc(_read_field(candle, "open_time"), "Candle.open_time")
    close_time = _parse_utc(_read_field(candle, "close_time"), "Candle.close_time")
    if open_time >= close_time:
        raise MarketBoundaryError(
            "INVALID_CANDLE_INTERVAL",
            "Canonical Candle requires open_time < close_time",
        )

    open_price = _decimal(_read_field(candle, "open"), "open")
    high = _decimal(_read_field(candle, "high"), "high")
    low = _decimal(_read_field(candle, "low"), "low")
    close = _decimal(_read_field(candle, "close"), "close")
    volume = _decimal(_read_field(candle, "volume"), "volume")
    if not (low <= open_price <= high and low <= close <= high):
        raise MarketBoundaryError(
            "INVALID_CANDLE_OHLC",
            "Canonical Candle OHLC invariant is violated",
        )
    if volume < 0:
        raise MarketBoundaryError(
            "INVALID_CANDLE_VOLUME",
            "Canonical Candle volume must be non-negative",
        )

    return _CandleView(
        schema_version=schema_version,
        symbol=symbol,
        timeframe=timeframe,
        open_time=open_time,
        close_time=close_time,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        source=source,
    )


def _visible_closed_candles(
    candles: Sequence[Any],
    strategy: ParsedStrategyDefinition,
    evaluated_at: datetime,
) -> Tuple[_CandleView, ...]:
    visible = []
    previous_open: Optional[datetime] = None

    for candle in candles:
        close_time = _parse_utc(_read_field(candle, "close_time"), "Candle.close_time")
        is_closed = _read_field(candle, "is_closed")
        if type(is_closed) is not bool:
            raise MarketBoundaryError(
                "INVALID_CANDLE_CLOSED_FLAG",
                "Candle.is_closed must be boolean",
            )

        # Future or provisional candles are outside the usable closed-candle boundary.
        # Their OHLCV values are deliberately not read, preventing future-data leakage.
        if close_time > evaluated_at or not is_closed:
            continue

        view = _candle_view(candle, strategy)
        if view.close_time > evaluated_at:
            raise MarketBoundaryError(
                "FUTURE_CANDLE_ACCESS",
                "Runtime attempted to include a Candle beyond evaluated_at",
            )
        if previous_open is not None and view.open_time <= previous_open:
            raise MarketBoundaryError(
                "NON_DETERMINISTIC_CANDLE_SEQUENCE",
                "Visible canonical Candle sequence must be strictly ordered with no duplicate open_time",
            )
        previous_open = view.open_time
        visible.append(view)

    return tuple(visible)


def _resolve_window(node: Mapping[str, Any], strategy: ParsedStrategyDefinition) -> int:
    name = node["parameter"]
    value = strategy.parameters[name]
    return int(value)


def _eval_numeric(
    node: Mapping[str, Any],
    strategy: ParsedStrategyDefinition,
    candles: Tuple[_CandleView, ...],
) -> Optional[Decimal]:
    primitive = node["primitive"]
    if primitive != "SMA":
        raise UnsupportedPrimitiveError(str(primitive))
    window = _resolve_window(node["window"], strategy)
    closes = [candle.close for candle in candles]
    return sma(closes, window)


def _eval_boolean(
    node: Mapping[str, Any],
    strategy: ParsedStrategyDefinition,
    candles: Tuple[_CandleView, ...],
) -> Optional[bool]:
    operator = node["operator"]
    if operator == "AND":
        values = [_eval_boolean(condition, strategy, candles) for condition in node["conditions"]]
        if any(value is None for value in values):
            return None
        return all(bool(value) for value in values)

    left = _eval_numeric(node["left"], strategy, candles)
    right = _eval_numeric(node["right"], strategy, candles)
    if left is None or right is None:
        return None
    if operator == "GT":
        return left > right
    if operator == "LT":
        return left < right
    raise StrategyValidationError(
        "UNSUPPORTED_OPERATOR",
        f"Unsupported operator reached runtime: {operator}",
        operator=operator,
    )


def _market_boundary_ref(
    strategy: ParsedStrategyDefinition,
    evaluated_at: datetime,
    candles: Tuple[_CandleView, ...],
) -> str:
    material = {
        "symbol": strategy.symbol,
        "timeframe": strategy.required_timeframe,
        "evaluated_at": _format_utc(evaluated_at),
        "candles": [
            {
                "schema_version": candle.schema_version,
                "symbol": candle.symbol,
                "timeframe": candle.timeframe,
                "open_time": _format_utc(candle.open_time),
                "close_time": _format_utc(candle.close_time),
                "open": format(candle.open, "f"),
                "high": format(candle.high, "f"),
                "low": format(candle.low, "f"),
                "close": format(candle.close, "f"),
                "volume": format(candle.volume, "f"),
                "is_closed": True,
                "source": candle.source,
            }
            for candle in candles
        ],
    }
    digest = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


class StrategyRuntime:
    """Single deterministic E2 semantic runtime for backtest/paper/live-compatible callers."""

    family = RUNTIME_FAMILY
    version = RUNTIME_VERSION

    def evaluate(
        self,
        strategy: ParsedStrategyDefinition,
        candles: Sequence[Any],
        evaluated_at: Union[str, datetime],
    ) -> Dict[str, Any]:
        if not isinstance(strategy, ParsedStrategyDefinition):
            raise StrategyValidationError(
                "UNPARSED_STRATEGY",
                "StrategyRuntime requires parse_strategy_definition output",
            )
        if strategy.runtime_family != self.family or strategy.runtime_version != self.version:
            raise StrategyValidationError(
                "RUNTIME_INCOMPATIBLE",
                "Parsed strategy is incompatible with this runtime instance",
            )
        if isinstance(candles, (str, bytes, bytearray)) or not isinstance(candles, Sequence):
            raise MarketBoundaryError(
                "INVALID_CANDLE_INPUT",
                "candles must be an ordered sequence of canonical Candle objects/mappings",
            )

        boundary = _parse_utc(evaluated_at, "evaluated_at")
        visible = _visible_closed_candles(candles, strategy, boundary)
        long_match = _eval_boolean(strategy.rules["long"], strategy, visible)
        short_match = _eval_boolean(strategy.rules["short"], strategy, visible)

        if long_match is None or short_match is None:
            direction = "NO_TRADE"
            reason_codes = ["INSUFFICIENT_HISTORY"]
        elif long_match and short_match:
            direction = "NO_TRADE"
            reason_codes = ["CONFLICTING_RULES"]
        elif long_match:
            direction = "LONG"
            reason_codes = ["LONG_RULE_MATCHED"]
        elif short_match:
            direction = "SHORT"
            reason_codes = ["SHORT_RULE_MATCHED"]
        else:
            direction = "NO_TRADE"
            reason_codes = ["NO_RULE_MATCHED"]

        boundary_ref = _market_boundary_ref(strategy, boundary, visible)
        identity_material = {
            "strategy_id": strategy.strategy_id,
            "strategy_version": strategy.strategy_version,
            "strategy_content_hash": strategy.content_hash,
            "runtime_family": self.family,
            "runtime_version": self.version,
            "market_boundary_ref": boundary_ref,
            "evaluated_at": _format_utc(boundary),
            "direction": direction,
            "reason_codes": reason_codes,
        }
        signal_id = "sig_" + hashlib.sha256(
            _canonical_json(identity_material).encode("utf-8")
        ).hexdigest()

        signal: Dict[str, Any] = {
            "schema_version": SUPPORTED_SHARED_SCHEMA_VERSION,
            "signal_id": signal_id,
            "strategy_id": strategy.strategy_id,
            "strategy_version": strategy.strategy_version,
            "strategy_content_hash": strategy.content_hash,
            "symbol": strategy.symbol,
            "evaluated_at": _format_utc(boundary),
            "direction": direction,
            "reason_codes": reason_codes,
            "market_boundary_ref": boundary_ref,
        }
        if visible:
            signal["reference_price"] = format(visible[-1].close, "f")
        return signal
