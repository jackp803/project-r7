from __future__ import annotations

from abc import ABC, abstractmethod

from src.execution.models import (
    Fill,
    OrderRequest,
    OrderResult,
    PositionExposureSnapshot,
    ReconciliationResult,
)


class Broker(ABC):
    """Minimum E4 broker contract for paper integration.

    Ambiguous submit responses must be queried/reconciled before retry.
    Implementations must not infer risk approval or change requested exposure.
    """

    @abstractmethod
    def submit_order(self, request: OrderRequest) -> OrderResult:
        raise NotImplementedError

    @abstractmethod
    def query_order(self, client_order_id: str) -> OrderResult | None:
        raise NotImplementedError

    @abstractmethod
    def query_position(self, symbol: str) -> PositionExposureSnapshot:
        raise NotImplementedError

    @abstractmethod
    def query_fills(self, client_order_id: str) -> tuple[Fill, ...]:
        raise NotImplementedError

    @abstractmethod
    def reconcile(
        self,
        request: OrderRequest,
        *,
        order_snapshot: OrderResult | None,
        position_snapshot: PositionExposureSnapshot,
    ) -> ReconciliationResult:
        raise NotImplementedError

    @abstractmethod
    def retry_order(
        self,
        request: OrderRequest,
        *,
        reconciliation: ReconciliationResult,
    ) -> OrderResult:
        """Retry only with broker-issued reconciliation evidence proving safety."""
        raise NotImplementedError
