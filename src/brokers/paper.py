from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Mapping

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


class PaperBroker(Broker):
    """Deterministic in-memory broker for E4 contract and failure-path tests.

    ambiguous_outcomes maps client_order_id -> whether the broker actually accepted
    the order while the caller received an ambiguous acknowledgement. This lets
    tests model both lost-ack-after-accept and no-accept cases without blind retry.
    """

    def __init__(self, *, ambiguous_outcomes: Mapping[str, bool] | None = None) -> None:
        self._ambiguous_outcomes = dict(ambiguous_outcomes or {})
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
        order.result = replace(
            order.result,
            order_status=status,
            observed_at=filled_at,
            requested_quantity=order.request.quantity,
            filled_quantity=new_filled,
            average_fill_price=average,
        )
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
            return ReconciliationResult(
                client_order_id=request.client_order_id,
                resolved_status=previous_result.order_status,
                retry_allowed=False,
                reason="ORDER_NOT_AMBIGUOUS",
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
