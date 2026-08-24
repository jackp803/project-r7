from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from src.brokers.base import Broker
from src.execution.models import (
    SCHEMA_VERSION,
    ExecutionHealthStatus,
    Fill,
    OrderRequest,
    OrderResult,
    OrderStatus,
    PositionExposureSnapshot,
    ReconciliationResult,
    Side,
    require_utc,
)


class IdempotencyConflictError(RuntimeError):
    pass


class ReconciliationRequiredError(RuntimeError):
    pass


class ExposureLimitError(RuntimeError):
    pass


class UnknownOrderError(KeyError):
    pass


class InvalidOrderTransitionError(RuntimeError):
    pass


@dataclass
class _PaperOrder:
    request: OrderRequest
    result: OrderResult
    fills: list[Fill]


def _paper_order_id(client_order_id: str) -> str:
    return "paper_" + hashlib.sha256(client_order_id.encode("utf-8")).hexdigest()[:32]


def _retry_token(client_order_id: str) -> str:
    material = f"{client_order_id}\x1forder-not-found\x1fno-exposure".encode("utf-8")
    return "reconcile_" + hashlib.sha256(material).hexdigest()[:32]


def _decimal_fact(value: Any, field: str, *, allow_zero: bool = False) -> Decimal:
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ReconciliationRequiredError(f"{field} is not a valid decimal") from exc
    else:
        raise ReconciliationRequiredError(f"{field} must be Decimal or decimal string")
    if not parsed.is_finite() or parsed < 0 or (parsed == 0 and not allow_zero):
        comparator = ">= 0" if allow_zero else "> 0"
        raise ReconciliationRequiredError(f"{field} must be finite and {comparator}")
    return parsed


def _utc_text(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ReconciliationRequiredError(f"{field} must be RFC 3339 UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ReconciliationRequiredError(f"{field} must be valid RFC 3339 UTC") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ReconciliationRequiredError(f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _fmt_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class PaperBroker(Broker):
    """Deterministic in-memory broker for E4 contract and failure-path tests.

    ``ambiguous_outcomes`` maps client_order_id -> whether the broker actually
    accepted the order while the caller received an ambiguous acknowledgement.
    ``rejected_outcomes`` maps client_order_id -> deterministic rejection reason
    for a first submit that is definitively rejected before Paper acceptance.

    These are Paper-only simulation controls. They do not alter the shared Broker
    interface, infer E5 lifecycle meaning, or model provider/private semantics.
    """

    _POSITION_REDUCTION_ROLES = frozenset(
        {"POSITION_EXIT", "EMERGENCY_EXIT", "PROTECTION_STOP"}
    )
    _ORDINARY_CLOSE_STATES = frozenset(
        {"OPEN_UNPROTECTED", "OPEN_PROTECTED", "PROFIT_PROTECTED"}
    )
    _PROTECTION_CLOSE_STATES = frozenset({"OPEN_PROTECTED", "PROFIT_PROTECTED"})

    def __init__(
        self,
        *,
        ambiguous_outcomes: Mapping[str, bool] | None = None,
        rejected_outcomes: Mapping[str, str] | None = None,
    ) -> None:
        self._ambiguous_outcomes = dict(ambiguous_outcomes or {})
        self._rejected_outcomes = dict(rejected_outcomes or {})
        overlap = set(self._ambiguous_outcomes) & set(self._rejected_outcomes)
        if overlap:
            raise ValueError(
                "one client_order_id cannot be configured for both ambiguous and rejected outcomes"
            )
        self._submissions: dict[str, tuple[OrderRequest, OrderResult]] = {}
        self._orders: dict[str, _PaperOrder] = {}
        self._retry_tokens: dict[str, tuple[object, ...]] = {}

    def _new_open_order(self, request: OrderRequest) -> _PaperOrder:
        broker_order_id = _paper_order_id(request.client_order_id)
        result = OrderResult(
            schema_version=SCHEMA_VERSION,
            order_request_id=request.order_request_id,
            client_order_id=request.client_order_id,
            broker_order_id=broker_order_id,
            order_status=OrderStatus.OPEN,
            observed_at=request.created_at,
            execution_health_status=ExecutionHealthStatus.HEALTHY,
            requested_quantity=request.quantity,
            filled_quantity=Decimal("0"),
        )
        return _PaperOrder(request=request, result=result, fills=[])

    def _new_rejected_order(self, request: OrderRequest, reason: str) -> _PaperOrder:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Paper rejection reason must be a non-empty sanitized string")
        result = OrderResult(
            schema_version=SCHEMA_VERSION,
            order_request_id=request.order_request_id,
            client_order_id=request.client_order_id,
            broker_order_id=None,
            order_status=OrderStatus.REJECTED,
            observed_at=request.created_at,
            execution_health_status=ExecutionHealthStatus.HEALTHY,
            requested_quantity=request.quantity,
            filled_quantity=Decimal("0"),
            reject_reason=reason,
        )
        return _PaperOrder(request=request, result=result, fills=[])

    def _store_order_result(self, order: _PaperOrder, result: OrderResult) -> None:
        # Keep _submissions as the original submit acknowledgement. Current
        # authoritative order truth lives in _orders and may evolve later.
        order.result = result

    def submit_order(self, request: OrderRequest) -> OrderResult:
        if request.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported OrderRequest schema_version")
        if request.quantity <= 0 or not request.quantity.is_finite():
            raise ValueError("OrderRequest quantity must be finite and > 0")
        require_utc(request.created_at, "created_at")

        existing = self._submissions.get(request.client_order_id)
        if existing is not None:
            previous_request, previous_result = existing
            if previous_request.safety_fingerprint() != request.safety_fingerprint():
                raise IdempotencyConflictError(
                    "same client_order_id cannot identify a different logical order"
                )
            if previous_result.order_status in {
                OrderStatus.UNKNOWN,
                OrderStatus.RECONCILIATION_REQUIRED,
            }:
                return previous_result
            actual = self._orders.get(request.client_order_id)
            return actual.result if actual is not None else previous_result

        rejection_reason = self._rejected_outcomes.get(request.client_order_id)
        if rejection_reason is not None:
            rejected = self._new_rejected_order(request, rejection_reason)
            self._orders[request.client_order_id] = rejected
            self._submissions[request.client_order_id] = (request, rejected.result)
            return rejected.result

        if request.client_order_id in self._ambiguous_outcomes:
            accepted = self._ambiguous_outcomes[request.client_order_id]
            if accepted:
                self._orders[request.client_order_id] = self._new_open_order(request)
            ambiguous = OrderResult(
                schema_version=SCHEMA_VERSION,
                order_request_id=request.order_request_id,
                client_order_id=request.client_order_id,
                broker_order_id=None,
                order_status=OrderStatus.RECONCILIATION_REQUIRED,
                observed_at=request.created_at,
                execution_health_status=ExecutionHealthStatus.DEGRADED,
                requested_quantity=request.quantity,
                filled_quantity=Decimal("0"),
            )
            self._submissions[request.client_order_id] = (request, ambiguous)
            return ambiguous

        order = self._new_open_order(request)
        self._orders[request.client_order_id] = order
        self._submissions[request.client_order_id] = (request, order.result)
        return order.result

    def query_order(self, client_order_id: str) -> OrderResult | None:
        order = self._orders.get(client_order_id)
        return None if order is None else order.result

    def query_position(self, symbol: str) -> PositionExposureSnapshot:
        net = Decimal("0")
        for order in self._orders.values():
            if order.request.symbol != symbol:
                continue
            filled = sum((fill.quantity for fill in order.fills), Decimal("0"))
            net += filled if order.request.side == Side.BUY else -filled
        return PositionExposureSnapshot(symbol=symbol, net_quantity=net)

    def query_fills(self, client_order_id: str) -> tuple[Fill, ...]:
        order = self._orders.get(client_order_id)
        return () if order is None else tuple(order.fills)

    def _validate_position_reduction_baseline(
        self,
        request: OrderRequest,
        source_position: Mapping[str, Any],
    ) -> tuple[Decimal, datetime, bool]:
        if not isinstance(source_position, Mapping):
            raise ReconciliationRequiredError("source Position must be a mapping")
        required = {
            "schema_version",
            "position_id",
            "symbol",
            "side",
            "actual_quantity",
            "average_entry_price",
            "opened_at",
            "broker_state_observed_at",
            "reconciliation_status",
            "lifecycle_state",
            "quantity_profile_version",
            "quantity_unit",
            "quantity_asset",
        }
        missing = sorted(required - set(source_position.keys()))
        if missing:
            raise ReconciliationRequiredError(
                "source Position missing required fields: " + ", ".join(missing)
            )
        if source_position.get("schema_version") != SCHEMA_VERSION:
            raise ReconciliationRequiredError("source Position schema_version is unsupported")
        if request.schema_version != SCHEMA_VERSION:
            raise ReconciliationRequiredError("position-reduction request schema_version is unsupported")
        if request.authorization_type != "POSITION_ACTION":
            raise ReconciliationRequiredError(
                "position-reduction request authorization_type must be POSITION_ACTION"
            )
        if request.order_role not in self._POSITION_REDUCTION_ROLES:
            raise ReconciliationRequiredError(
                "request is not an accepted position-reduction order role"
            )
        for field, value in (
            ("trade_plan_id", request.trade_plan_id),
            ("position_action_id", request.position_action_id),
            ("position_id", request.position_id),
            ("risk_decision_id", request.risk_decision_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ReconciliationRequiredError(
                    f"position-reduction request {field} lineage is incomplete"
                )

        is_protection_stop = request.order_role == "PROTECTION_STOP"
        if is_protection_stop:
            if request.order_type != "STOP_MARKET" or request.reduce_only is not True:
                raise ReconciliationRequiredError(
                    "PROTECTION_STOP request must be reduce-only STOP_MARKET"
                )
            if request.limit_price is not None or request.time_in_force is not None:
                raise ReconciliationRequiredError(
                    "PROTECTION_STOP request forbids limit_price/time_in_force"
                )
            _decimal_fact(request.stop_price, "PROTECTION_STOP request.stop_price")
        else:
            if request.order_type != "MARKET" or request.reduce_only is not True:
                raise ReconciliationRequiredError(
                    "explicit close request must be reduce-only MARKET"
                )
            if (
                request.limit_price is not None
                or request.stop_price is not None
                or request.time_in_force is not None
            ):
                raise ReconciliationRequiredError(
                    "close-v0.1 forbids executable price/TIF fields"
                )

        if source_position.get("position_id") != request.position_id:
            raise ReconciliationRequiredError(
                "source Position position_id does not match position-reduction request"
            )
        if source_position.get("symbol") != request.symbol:
            raise ReconciliationRequiredError(
                "source Position symbol does not match position-reduction request"
            )
        if source_position.get("reconciliation_status") != "CONSISTENT":
            raise ReconciliationRequiredError(
                "source Position must be reconciliation_status=CONSISTENT"
            )
        if request.quantity_profile_version != "base-asset-v0.1":
            raise ReconciliationRequiredError(
                "position-reduction request quantity profile must be base-asset-v0.1"
            )
        if request.quantity_unit != "BASE_ASSET":
            raise ReconciliationRequiredError(
                "position-reduction request quantity unit must be BASE_ASSET"
            )
        if request.quantity_asset != "BTC":
            raise ReconciliationRequiredError(
                "BTC_USDT_PERP position-reduction request quantity asset must be BTC"
            )
        if source_position.get("quantity_profile_version") != request.quantity_profile_version:
            raise ReconciliationRequiredError(
                "source Position quantity profile does not match position-reduction request"
            )
        if source_position.get("quantity_unit") != request.quantity_unit:
            raise ReconciliationRequiredError(
                "source Position quantity unit does not match position-reduction request"
            )
        if source_position.get("quantity_asset") != request.quantity_asset:
            raise ReconciliationRequiredError(
                "source Position quantity asset does not match position-reduction request"
            )

        side = source_position.get("side")
        if side not in {"LONG", "SHORT"}:
            raise ReconciliationRequiredError("source Position side must be LONG or SHORT")
        expected_order_side = Side.SELL if side == "LONG" else Side.BUY
        if request.side != expected_order_side:
            raise ReconciliationRequiredError(
                "position-reduction request side does not reduce the source Position"
            )

        lifecycle = source_position.get("lifecycle_state")
        if request.order_role == "POSITION_EXIT":
            if lifecycle not in self._ORDINARY_CLOSE_STATES:
                raise ReconciliationRequiredError(
                    "POSITION_EXIT source lifecycle is not an ordinary open state"
                )
        elif request.order_role == "EMERGENCY_EXIT":
            if lifecycle != "EMERGENCY":
                raise ReconciliationRequiredError(
                    "EMERGENCY_EXIT requires source lifecycle EMERGENCY"
                )
        else:
            if lifecycle not in self._PROTECTION_CLOSE_STATES:
                raise ReconciliationRequiredError(
                    "PROTECTION_STOP flat proof requires OPEN_PROTECTED or PROFIT_PROTECTED source lifecycle"
                )

        source_quantity = _decimal_fact(
            source_position.get("actual_quantity"),
            "source Position.actual_quantity",
        )
        if source_quantity != request.quantity:
            raise ReconciliationRequiredError(
                "position-reduction request quantity must equal exact source Position.actual_quantity"
            )
        _decimal_fact(
            source_position.get("average_entry_price"),
            "source Position.average_entry_price",
        )
        opened_at = _utc_text(source_position.get("opened_at"), "source Position.opened_at")
        source_observed_at = _utc_text(
            source_position.get("broker_state_observed_at"),
            "source Position.broker_state_observed_at",
        )
        if source_observed_at < opened_at:
            raise ReconciliationRequiredError(
                "source Position observation cannot precede opened_at"
            )
        if is_protection_stop:
            if request.created_at > source_observed_at:
                raise ReconciliationRequiredError(
                    "protected source Position observation cannot precede the protective request"
                )
        elif request.created_at < source_observed_at:
            raise ReconciliationRequiredError(
                "explicit close request cannot predate source Position observation"
            )
        return source_quantity, source_observed_at, is_protection_stop

    def observe_position_after_close(
        self,
        request: OrderRequest,
        source_position: Mapping[str, Any],
        *,
        observed_at: datetime,
    ) -> dict[str, Any]:
        """Refresh one existing Position from exact position-reduction Fill truth.

        Explicit POSITION_EXIT/EMERGENCY_EXIT retain their accepted residual
        observation semantics. PROTECTION_STOP is stricter: until residual
        protection semantics are defined, only exact full protection execution
        can yield authoritative flat Position truth. Symbol-level net exposure
        and OrderStatus.FILLED are never substitutes for same-position truth.
        The E5-owned lifecycle_state is always preserved unchanged.
        """

        require_utc(observed_at, "observed_at")
        (
            source_quantity,
            source_observed_at,
            is_protection_stop,
        ) = self._validate_position_reduction_baseline(request, source_position)

        submitted = self._submissions.get(request.client_order_id)
        if submitted is None:
            raise ReconciliationRequiredError(
                "position-reduction request has no Paper submit evidence"
            )
        submitted_request, submit_result = submitted
        if submitted_request.safety_fingerprint() != request.safety_fingerprint():
            raise IdempotencyConflictError(
                "position-reduction observation request identity changed"
            )
        if submit_result.order_status in {
            OrderStatus.UNKNOWN,
            OrderStatus.RECONCILIATION_REQUIRED,
        }:
            raise ReconciliationRequiredError(
                "ambiguous position-reduction submit cannot produce definitive Position truth"
            )

        order = self._orders.get(request.client_order_id)
        if order is None:
            raise ReconciliationRequiredError(
                "position-reduction order is not queryable in PaperBroker"
            )
        if order.request.safety_fingerprint() != request.safety_fingerprint():
            raise IdempotencyConflictError(
                "stored position-reduction order identity does not match request"
            )
        if order.result.execution_health_status != ExecutionHealthStatus.HEALTHY:
            raise ReconciliationRequiredError(
                "position-reduction order execution health is not HEALTHY"
            )
        if order.result.order_status in {
            OrderStatus.UNKNOWN,
            OrderStatus.RECONCILIATION_REQUIRED,
        }:
            raise ReconciliationRequiredError(
                "position-reduction order state is not definitive"
            )
        if order.result.requested_quantity != request.quantity:
            raise ReconciliationRequiredError(
                "position-reduction OrderResult requested_quantity mismatch"
            )
        if order.result.filled_quantity < 0 or order.result.filled_quantity > request.quantity:
            raise ReconciliationRequiredError(
                "position-reduction OrderResult filled_quantity is invalid"
            )
        if observed_at < source_observed_at or observed_at < order.result.observed_at:
            raise ReconciliationRequiredError(
                "position observation time cannot precede source/order broker truth"
            )

        # Any other same-symbol fill after the source Position observation could
        # alter the exact position quantity. Fail closed rather than infer from
        # symbol-level net exposure or silently mix another logical order.
        for other_order in self._orders.values():
            if other_order.request.client_order_id == request.client_order_id:
                continue
            for fill in other_order.fills:
                if fill.symbol == request.symbol and fill.filled_at >= source_observed_at:
                    raise ReconciliationRequiredError(
                        "another same-symbol Fill occurred after the source Position observation"
                    )

        total_reduction_filled = Decimal("0")
        latest_fill_at = source_observed_at
        for fill in order.fills:
            if fill.trade_plan_id != request.trade_plan_id:
                raise ReconciliationRequiredError(
                    "position-reduction Fill trade_plan_id mismatch"
                )
            if fill.position_action_id != request.position_action_id:
                raise ReconciliationRequiredError(
                    "position-reduction Fill position_action_id mismatch"
                )
            if fill.position_id != request.position_id:
                raise ReconciliationRequiredError(
                    "position-reduction Fill position_id mismatch"
                )
            if fill.order_role != request.order_role:
                raise ReconciliationRequiredError(
                    "position-reduction Fill order_role mismatch"
                )
            if fill.symbol != request.symbol or fill.side != request.side:
                raise ReconciliationRequiredError(
                    "position-reduction Fill symbol/side mismatch"
                )
            if fill.filled_at < source_observed_at:
                raise ReconciliationRequiredError(
                    "position-reduction Fill predates the source Position observation"
                )
            if fill.filled_at > observed_at:
                raise ReconciliationRequiredError(
                    "position observation cannot precede a position-reduction Fill"
                )
            if fill.quantity <= 0 or not fill.quantity.is_finite():
                raise ReconciliationRequiredError(
                    "position-reduction Fill quantity must be finite and > 0"
                )
            total_reduction_filled += fill.quantity
            if fill.filled_at > latest_fill_at:
                latest_fill_at = fill.filled_at

        if total_reduction_filled != order.result.filled_quantity:
            raise ReconciliationRequiredError(
                "position-reduction Fill set does not equal authoritative OrderResult.filled_quantity"
            )
        if total_reduction_filled > source_quantity:
            raise ExposureLimitError(
                "position-reduction fills cannot exceed exact source Position quantity"
            )

        if is_protection_stop:
            if total_reduction_filled == Decimal("0"):
                raise ReconciliationRequiredError(
                    "PROTECTION_STOP has no trigger Fill truth; flat Position cannot be proven"
                )
            if total_reduction_filled < source_quantity:
                if order.result.order_status != OrderStatus.PARTIALLY_FILLED:
                    raise ReconciliationRequiredError(
                        "partial PROTECTION_STOP Fill truth requires PARTIALLY_FILLED order status"
                    )
                raise ReconciliationRequiredError(
                    "partial PROTECTION_STOP execution has unresolved residual-protection semantics"
                )
            if order.result.order_status != OrderStatus.FILLED:
                raise ReconciliationRequiredError(
                    "full PROTECTION_STOP Fill truth requires FILLED order status"
                )
        else:
            if total_reduction_filled == Decimal("0"):
                if order.result.order_status in {
                    OrderStatus.PARTIALLY_FILLED,
                    OrderStatus.FILLED,
                }:
                    raise ReconciliationRequiredError(
                        "close order status contradicts zero Fill truth"
                    )
            elif total_reduction_filled < request.quantity:
                if order.result.order_status != OrderStatus.PARTIALLY_FILLED:
                    raise ReconciliationRequiredError(
                        "partial close Fill truth requires PARTIALLY_FILLED order status"
                    )
            elif order.result.order_status != OrderStatus.FILLED:
                raise ReconciliationRequiredError(
                    "full close Fill truth requires FILLED order status"
                )

        if observed_at < latest_fill_at:
            raise ReconciliationRequiredError(
                "position observation predates latest position-reduction Fill"
            )

        residual = source_quantity - total_reduction_filled
        if residual < 0:
            raise ExposureLimitError(
                "position-reduction observation cannot produce negative residual exposure"
            )
        if is_protection_stop and residual != Decimal("0"):
            raise ReconciliationRequiredError(
                "PROTECTION_STOP may emit authoritative Position truth only for exact full closure"
            )

        refreshed = dict(source_position)
        refreshed["actual_quantity"] = format(residual, "f")
        refreshed["broker_state_observed_at"] = _fmt_utc(observed_at)
        refreshed["reconciliation_status"] = "CONSISTENT"
        # E5 owns lifecycle interpretation. Do not emit CLOSED/EXIT_REQUESTED or
        # invent closed_at here; only E4-owned broker facts are refreshed.
        return refreshed

    def _terminalize_open_order(
        self,
        client_order_id: str,
        *,
        terminal_status: OrderStatus,
        observed_at,
    ) -> OrderResult:
        if terminal_status not in {OrderStatus.CANCELED, OrderStatus.EXPIRED}:
            raise ValueError("Paper terminal transition supports CANCELED or EXPIRED only")
        require_utc(observed_at, "observed_at")
        order = self._orders.get(client_order_id)
        if order is None:
            raise UnknownOrderError(client_order_id)

        current = order.result.order_status
        if current == terminal_status:
            return order.result
        if current == OrderStatus.PARTIALLY_FILLED:
            raise InvalidOrderTransitionError(
                "PARTIALLY_FILLED cannot be terminalized by this bounded Paper protection task"
            )
        if current == OrderStatus.FILLED:
            raise InvalidOrderTransitionError(
                "FILLED cannot be rewritten to CANCELED or EXPIRED"
            )
        if current in {OrderStatus.REJECTED, OrderStatus.CANCELED, OrderStatus.EXPIRED}:
            raise InvalidOrderTransitionError(
                f"terminal order {current.value} cannot transition to {terminal_status.value}"
            )
        if current != OrderStatus.OPEN:
            raise InvalidOrderTransitionError(
                f"only exact OPEN Paper orders can transition to {terminal_status.value}"
            )
        if observed_at < order.result.observed_at:
            raise InvalidOrderTransitionError(
                "terminal observation cannot precede the current order observation"
            )

        terminal = replace(
            order.result,
            order_status=terminal_status,
            observed_at=observed_at,
            execution_health_status=ExecutionHealthStatus.HEALTHY,
        )
        self._store_order_result(order, terminal)
        return terminal

    def cancel_order(self, client_order_id: str, *, observed_at) -> OrderResult:
        """Paper-only deterministic OPEN -> CANCELED observation."""
        return self._terminalize_open_order(
            client_order_id,
            terminal_status=OrderStatus.CANCELED,
            observed_at=observed_at,
        )

    def expire_order(self, client_order_id: str, *, observed_at) -> OrderResult:
        """Paper-only deterministic OPEN -> EXPIRED observation.

        Expiry is an explicit Paper event. No ApprovedTradePlan or protection
        authority TTL is consulted or reinterpreted here.
        """
        return self._terminalize_open_order(
            client_order_id,
            terminal_status=OrderStatus.EXPIRED,
            observed_at=observed_at,
        )

    def record_fill(
        self,
        client_order_id: str,
        *,
        quantity: Decimal,
        price: Decimal,
        filled_at,
        fee: Decimal | None = None,
        fee_currency: str | None = None,
        liquidity_role: str | None = None,
    ) -> Fill:
        order = self._orders.get(client_order_id)
        if order is None:
            raise UnknownOrderError(client_order_id)
        require_utc(filled_at, "filled_at")
        if order.result.order_status not in {
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED,
        }:
            raise InvalidOrderTransitionError(
                f"cannot record a fill after order is {order.result.order_status.value}"
            )
        if quantity <= 0 or not quantity.is_finite():
            raise ValueError("fill quantity must be finite and > 0")
        if price <= 0 or not price.is_finite():
            raise ValueError("fill price must be finite and > 0")
        already_filled = order.result.filled_quantity
        remaining = order.request.quantity - already_filled
        if quantity > remaining:
            raise ExposureLimitError(
                "actual fills cannot exceed the approved OrderRequest quantity"
            )

        sequence = len(order.fills) + 1
        fill_material = (
            f"{order.result.broker_order_id}|{sequence}|{quantity}|{price}|"
            f"{filled_at.isoformat()}"
        )
        fill_id = "fill_" + hashlib.sha256(fill_material.encode("utf-8")).hexdigest()[:32]
        fill = Fill(
            schema_version=SCHEMA_VERSION,
            fill_id=fill_id,
            broker_order_id=order.result.broker_order_id or "",
            client_order_id=client_order_id,
            trade_plan_id=order.request.trade_plan_id,
            symbol=order.request.symbol,
            side=order.request.side,
            quantity=quantity,
            price=price,
            filled_at=filled_at,
            fee=fee,
            fee_currency=fee_currency,
            liquidity_role=liquidity_role,
            position_action_id=order.request.position_action_id,
            position_id=order.request.position_id,
            order_role=order.request.order_role,
        )
        order.fills.append(fill)

        new_filled = already_filled + quantity
        prior_notional = (
            (order.result.average_fill_price or Decimal("0")) * already_filled
        )
        average = (prior_notional + price * quantity) / new_filled
        status = (
            OrderStatus.FILLED
            if new_filled == order.request.quantity
            else OrderStatus.PARTIALLY_FILLED
        )
        updated = replace(
            order.result,
            order_status=status,
            observed_at=filled_at,
            requested_quantity=order.request.quantity,
            filled_quantity=new_filled,
            average_fill_price=average,
        )
        self._store_order_result(order, updated)
        return fill

    def reconcile(
        self,
        request: OrderRequest,
        *,
        order_snapshot: OrderResult | None,
        position_snapshot: PositionExposureSnapshot,
    ) -> ReconciliationResult:
        submitted = self._submissions.get(request.client_order_id)
        if submitted is None:
            raise ReconciliationRequiredError("no local submit intent exists to reconcile")
        previous_request, previous_result = submitted
        if previous_request.safety_fingerprint() != request.safety_fingerprint():
            raise IdempotencyConflictError("reconciliation request identity changed")
        if previous_result.order_status not in {
            OrderStatus.UNKNOWN,
            OrderStatus.RECONCILIATION_REQUIRED,
        }:
            authoritative_order = self.query_order(request.client_order_id)
            resolved_status = (
                authoritative_order.order_status
                if authoritative_order is not None
                else previous_result.order_status
            )
            return ReconciliationResult(
                client_order_id=request.client_order_id,
                resolved_status=resolved_status,
                retry_allowed=False,
                reason="ORDER_DEFINITIVE_NO_RETRY",
            )

        authoritative_order = self.query_order(request.client_order_id)
        authoritative_position = self.query_position(request.symbol)
        if order_snapshot != authoritative_order or position_snapshot != authoritative_position:
            raise ReconciliationRequiredError(
                "reconciliation evidence must match explicit broker order and position queries"
            )

        if order_snapshot is not None:
            return ReconciliationResult(
                client_order_id=request.client_order_id,
                resolved_status=order_snapshot.order_status,
                retry_allowed=False,
                reason="BROKER_ORDER_FOUND_NO_RETRY",
            )
        if position_snapshot.net_quantity != 0:
            return ReconciliationResult(
                client_order_id=request.client_order_id,
                resolved_status=OrderStatus.RECONCILIATION_REQUIRED,
                retry_allowed=False,
                reason="EXPOSURE_PRESENT_NO_RETRY",
            )

        token = _retry_token(request.client_order_id)
        self._retry_tokens[token] = request.safety_fingerprint()
        return ReconciliationResult(
            client_order_id=request.client_order_id,
            resolved_status=OrderStatus.UNKNOWN,
            retry_allowed=True,
            reason="ORDER_NOT_FOUND_AND_NO_EXPOSURE",
            retry_token=token,
        )

    def retry_order(
        self,
        request: OrderRequest,
        *,
        reconciliation: ReconciliationResult,
    ) -> OrderResult:
        token = reconciliation.retry_token
        expected_fingerprint = self._retry_tokens.get(token or "")
        if (
            not reconciliation.retry_allowed
            or reconciliation.client_order_id != request.client_order_id
            or expected_fingerprint is None
            or expected_fingerprint != request.safety_fingerprint()
        ):
            raise ReconciliationRequiredError(
                "retry requires matching broker-issued reconciliation evidence"
            )
        if self.query_order(request.client_order_id) is not None:
            raise ReconciliationRequiredError("broker order now exists; retry is no longer safe")
        if self.query_position(request.symbol).net_quantity != 0:
            raise ReconciliationRequiredError("exposure now exists; retry is no longer safe")

        order = self._new_open_order(request)
        self._orders[request.client_order_id] = order
        self._submissions[request.client_order_id] = (request, order.result)
        del self._retry_tokens[token or ""]
        return order.result
