from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from typing import Any, Mapping, Sequence

from src.execution.gateway import (
    CANONICAL_SYMBOL,
    ENTRY_ORDER_TYPE,
    QUANTITY_ASSET,
    QUANTITY_PROFILE_VERSION,
    QUANTITY_UNIT,
)
from src.execution.models import OrderRequest, Side

OKX_PROVIDER = "OKX"
OKX_INSTRUMENT_ID = "BTC-USDT-SWAP"
OKX_INST_TYPE = "SWAP"
OKX_SUPPORTED_CT_TYPE = "linear"
OKX_METADATA_FRESHNESS_POLICY_VERSION = "okx-instrument-metadata-freshness-v0.2"
OKX_METADATA_MAX_AGE_SECONDS = 300
OKX_SUBMIT_METADATA_MAX_AGE_SECONDS = 5
OKX_SCHEDULED_CHANGE_GUARD_SECONDS = 60
_OKX_KNOWN_UPCOMING_CHANGE_PARAMS = frozenset({"tickSz", "minSz", "maxMktSz"})
_OKX_SIZING_RELEVANT_UPCOMING_CHANGE_PARAMS = frozenset({"minSz", "maxMktSz"})


class OKXMetadataValidationError(ValueError):
    pass


class OKXUnsupportedConversionError(ValueError):
    pass


class OKXSizingError(ValueError):
    pass


@dataclass(frozen=True)
class OKXScheduledInstrumentChange:
    param: str
    new_value: str
    effective_at: datetime


@dataclass(frozen=True)
class OKXInstrumentMetadata:
    """Validated local OKX instrument snapshot; no networking behavior."""

    provider: str
    canonical_symbol: str
    instrument_id: str
    inst_type: str
    ct_val: Decimal
    ct_mult: Decimal
    ct_val_ccy: str
    ct_type: str
    lot_sz: Decimal
    min_sz: Decimal
    tick_sz: Decimal
    state: str
    observed_at: datetime
    metadata_ref: str
    freshness_policy_version: str = OKX_METADATA_FRESHNESS_POLICY_VERSION
    upcoming_changes: tuple[OKXScheduledInstrumentChange, ...] = ()


@dataclass(frozen=True)
class OKXEntrySizingAudit:
    """Separates canonical exposure facts from provider-native contract sizing."""

    trade_plan_id: str
    canonical_symbol: str
    canonical_approved_quantity: Decimal
    quantity_profile_version: str
    quantity_unit: str
    quantity_asset: str
    provider: str
    provider_instrument_id: str
    provider_order_type: str
    provider_side: str
    provider_requested_contract_quantity: Decimal
    effective_canonical_requested_quantity: Decimal
    base_per_contract: Decimal
    instrument_metadata_ref: str
    instrument_metadata_observed_at: datetime
    freshness_policy_version: str


def _require_utc(value: datetime, field: str) -> None:
    if not isinstance(value, datetime):
        raise OKXMetadataValidationError(f"{field} must be datetime")
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise OKXMetadataValidationError(f"{field} must be timezone-aware UTC")


def _require_positive_decimal(value: object, field: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise OKXMetadataValidationError(f"{field} must be Decimal")
    if not value.is_finite() or value <= 0:
        raise OKXMetadataValidationError(f"{field} must be finite and > 0")
    return value


def _parse_positive_decimal_string(value: Any, field: str) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise OKXMetadataValidationError(f"{field} must be a non-empty decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise OKXMetadataValidationError(f"{field} must be a valid decimal string") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise OKXMetadataValidationError(f"{field} must be finite and > 0")
    return parsed


def _parse_epoch_ms(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.isdigit():
        raise OKXMetadataValidationError(f"{field} must be a millisecond epoch string")
    millis = int(value)
    if millis < 0:
        raise OKXMetadataValidationError(f"{field} must be non-negative")
    return datetime.fromtimestamp(millis / 1000, tz=timezone.utc)


def _is_integral(value: Decimal) -> bool:
    return value == value.to_integral_value()


def instrument_metadata_from_okx_payload(
    item: Mapping[str, Any],
    *,
    observed_at: datetime,
    metadata_ref: str,
) -> OKXInstrumentMetadata:
    """Materialize the one configured OKX SWAP metadata item from public API data."""
    _require_utc(observed_at, "observed_at")
    if not isinstance(item, Mapping):
        raise OKXMetadataValidationError("instrument metadata item must be a mapping")

    raw_changes = item.get("upcChg", [])
    if not isinstance(raw_changes, Sequence) or isinstance(raw_changes, (str, bytes)):
        raise OKXMetadataValidationError("upcChg must be an array when present")
    changes: list[OKXScheduledInstrumentChange] = []
    for raw in raw_changes:
        if not isinstance(raw, Mapping):
            raise OKXMetadataValidationError("upcChg entries must be mappings")
        param = raw.get("param")
        new_value = raw.get("newValue")
        if not isinstance(param, str) or not param:
            raise OKXMetadataValidationError("upcChg.param must be non-empty")
        if not isinstance(new_value, str) or not new_value:
            raise OKXMetadataValidationError("upcChg.newValue must be non-empty")
        changes.append(
            OKXScheduledInstrumentChange(
                param=param,
                new_value=new_value,
                effective_at=_parse_epoch_ms(raw.get("effTime"), "upcChg.effTime"),
            )
        )

    return OKXInstrumentMetadata(
        provider=OKX_PROVIDER,
        canonical_symbol=CANONICAL_SYMBOL,
        instrument_id=str(item.get("instId", "")),
        inst_type=str(item.get("instType", "")),
        ct_val=_parse_positive_decimal_string(item.get("ctVal"), "ctVal"),
        ct_mult=_parse_positive_decimal_string(item.get("ctMult"), "ctMult"),
        ct_val_ccy=str(item.get("ctValCcy", "")),
        ct_type=str(item.get("ctType", "")),
        lot_sz=_parse_positive_decimal_string(item.get("lotSz"), "lotSz"),
        min_sz=_parse_positive_decimal_string(item.get("minSz"), "minSz"),
        tick_sz=_parse_positive_decimal_string(item.get("tickSz"), "tickSz"),
        state=str(item.get("state", "")),
        observed_at=observed_at,
        metadata_ref=metadata_ref,
        upcoming_changes=tuple(changes),
    )


def validate_okx_instrument_metadata(
    metadata: OKXInstrumentMetadata | None,
    *,
    now: datetime,
) -> OKXInstrumentMetadata:
    """Validate a cached snapshot for deterministic sizing calculations."""
    if metadata is None or not isinstance(metadata, OKXInstrumentMetadata):
        raise OKXMetadataValidationError("OKX instrument metadata is missing")
    _require_utc(now, "now")
    _require_utc(metadata.observed_at, "observed_at")

    if metadata.provider != OKX_PROVIDER:
        raise OKXMetadataValidationError("provider mismatch")
    if metadata.canonical_symbol != CANONICAL_SYMBOL:
        raise OKXMetadataValidationError("canonical symbol mismatch")
    if metadata.instrument_id != OKX_INSTRUMENT_ID:
        raise OKXMetadataValidationError("provider instrument mismatch")
    if metadata.inst_type != OKX_INST_TYPE:
        raise OKXMetadataValidationError("OKX instrument type must be SWAP")
    if metadata.state != "live":
        raise OKXMetadataValidationError("OKX instrument must be in live state for MARKET entry")
    if metadata.freshness_policy_version != OKX_METADATA_FRESHNESS_POLICY_VERSION:
        raise OKXMetadataValidationError("unsupported metadata freshness policy version")
    if not isinstance(metadata.metadata_ref, str) or not metadata.metadata_ref.strip():
        raise OKXMetadataValidationError("metadata_ref must be non-empty")

    age_seconds = (now - metadata.observed_at).total_seconds()
    if age_seconds < 0:
        raise OKXMetadataValidationError("metadata observation is in the future")
    if age_seconds > OKX_METADATA_MAX_AGE_SECONDS:
        raise OKXMetadataValidationError("OKX instrument metadata is stale")

    ct_val = _require_positive_decimal(metadata.ct_val, "ctVal")
    ct_mult = _require_positive_decimal(metadata.ct_mult, "ctMult")
    lot_sz = _require_positive_decimal(metadata.lot_sz, "lotSz")
    min_sz = _require_positive_decimal(metadata.min_sz, "minSz")
    _require_positive_decimal(metadata.tick_sz, "tickSz")

    if not _is_integral(min_sz / lot_sz):
        raise OKXMetadataValidationError("minSz must be an exact lotSz multiple")
    if metadata.ct_type != OKX_SUPPORTED_CT_TYPE:
        raise OKXUnsupportedConversionError("only linear OKX SWAP conversion is supported")
    if metadata.ct_val_ccy != QUANTITY_ASSET:
        raise OKXUnsupportedConversionError(
            "ctValCcy must equal canonical BTC quantity asset for direct V1 conversion"
        )
    if not (ct_val * ct_mult).is_finite() or ct_val * ct_mult <= 0:
        raise OKXMetadataValidationError("base_per_contract must be finite and > 0")

    for change in metadata.upcoming_changes:
        if not isinstance(change, OKXScheduledInstrumentChange):
            raise OKXMetadataValidationError("upcoming_changes contains an invalid entry")
        _require_utc(change.effective_at, "upcoming change effective_at")
        if change.param not in _OKX_KNOWN_UPCOMING_CHANGE_PARAMS:
            raise OKXMetadataValidationError(
                f"unsupported scheduled instrument change parameter: {change.param}"
            )
        if not isinstance(change.new_value, str) or not change.new_value:
            raise OKXMetadataValidationError("scheduled change new_value must be non-empty")
    return metadata


def validate_okx_submit_metadata(
    metadata: OKXInstrumentMetadata | None,
    *,
    now: datetime,
) -> OKXInstrumentMetadata:
    """Stricter submit-boundary validation for E4-OKX-FRESHNESS-HARDEN-001.

    The historical 300-second cache TTL is not used as permission to submit. A
    provider observation must be at most five seconds old when a Demo order is
    materialized. Sizing-relevant scheduled changes entering a 60-second guard
    window block materialization; unknown scheduled change parameters block at
    all times because their execution impact is not safely defined.
    """
    checked = validate_okx_instrument_metadata(metadata, now=now)
    age_seconds = (now - checked.observed_at).total_seconds()
    if age_seconds > OKX_SUBMIT_METADATA_MAX_AGE_SECONDS:
        raise OKXMetadataValidationError(
            "submit preparation requires a fresh provider metadata observation within 5 seconds"
        )

    guard_end = now + timedelta(seconds=OKX_SCHEDULED_CHANGE_GUARD_SECONDS)
    for change in checked.upcoming_changes:
        if change.effective_at <= now:
            raise OKXMetadataValidationError(
                "metadata snapshot contains a scheduled change whose effTime has already arrived"
            )
        if (
            change.param in _OKX_SIZING_RELEVANT_UPCOMING_CHANGE_PARAMS
            and change.effective_at <= guard_end
        ):
            raise OKXMetadataValidationError(
                f"scheduled {change.param} change is too close to submit preparation"
            )
        # tickSz is retained/audited but does not create a MARKET execution price.
    return checked


def size_okx_market_entry(
    request: OrderRequest,
    metadata: OKXInstrumentMetadata | None,
    *,
    now: datetime,
) -> OKXEntrySizingAudit:
    """Quantize canonical BTC exposure down to OKX contract size without networking."""
    if request.symbol != CANONICAL_SYMBOL:
        raise OKXSizingError("unsupported canonical symbol")
    if request.order_type != ENTRY_ORDER_TYPE:
        raise OKXSizingError("current OKX sizing path supports MARKET only")
    if request.quantity_profile_version != QUANTITY_PROFILE_VERSION:
        raise OKXSizingError("unsupported quantity profile")
    if request.quantity_unit != QUANTITY_UNIT:
        raise OKXSizingError("unsupported quantity unit")
    if request.quantity_asset != QUANTITY_ASSET:
        raise OKXSizingError("unsupported quantity asset")
    if not isinstance(request.quantity, Decimal) or not request.quantity.is_finite() or request.quantity <= 0:
        raise OKXSizingError("canonical approved quantity must be finite and > 0")
    if request.limit_price is not None or request.stop_price is not None or request.time_in_force is not None:
        raise OKXSizingError("MARKET entry cannot carry executable price or TIF")

    checked = validate_okx_instrument_metadata(metadata, now=now)
    base_per_contract = checked.ct_val * checked.ct_mult
    raw_contracts = request.quantity / base_per_contract
    lot_units = (raw_contracts / checked.lot_sz).to_integral_value(rounding=ROUND_FLOOR)
    provider_sz = lot_units * checked.lot_sz

    if provider_sz <= 0:
        raise OKXSizingError("approved BTC quantity is not representable at current lotSz")
    if provider_sz < checked.min_sz:
        raise OKXSizingError("round-down provider size is below minSz; rounding up is forbidden")
    if not _is_integral(provider_sz / checked.lot_sz):
        raise OKXSizingError("provider size is not a valid lotSz multiple")

    effective_base = provider_sz * base_per_contract
    if not effective_base.is_finite() or effective_base <= 0:
        raise OKXSizingError("effective canonical requested quantity must be finite and > 0")
    if effective_base > request.quantity:
        raise OKXSizingError("provider quantization would exceed E5-approved BTC exposure")

    return OKXEntrySizingAudit(
        trade_plan_id=request.trade_plan_id,
        canonical_symbol=request.symbol,
        canonical_approved_quantity=request.quantity,
        quantity_profile_version=request.quantity_profile_version,
        quantity_unit=request.quantity_unit,
        quantity_asset=request.quantity_asset,
        provider=checked.provider,
        provider_instrument_id=checked.instrument_id,
        provider_order_type="market",
        provider_side="buy" if request.side == Side.BUY else "sell",
        provider_requested_contract_quantity=provider_sz,
        effective_canonical_requested_quantity=effective_base,
        base_per_contract=base_per_contract,
        instrument_metadata_ref=checked.metadata_ref,
        instrument_metadata_observed_at=checked.observed_at,
        freshness_policy_version=checked.freshness_policy_version,
    )
