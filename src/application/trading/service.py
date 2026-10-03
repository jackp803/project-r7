"""Actual owner admission, durable one-claim dispatch and canonical publication.

Trusted composition only; no mode flag or HTTP body selects a production driver.
An uncertain or recovered claim is always reconciled, never sent again.
"""
from dataclasses import dataclass, replace
from decimal import Decimal
from application.trading.admission import RuntimeAdmission, RuntimeAdmissionError
from application.trading.guards import _TradingEffectGuard
from application.trading.provider import FakeProductProvider, ProductionProductProvider, ProductProviderError
from application.trading.orchestrator import TradingCoordinator
from brokers.okx_product import OKXProductTranslator
from brokers.okx_product_state import restore_product_readback
from brokers.okx_product_readback import (parse_product_ack, parse_product_order, parse_product_fills,
                                         parse_product_algo, parse_product_stop_child)
from brokers.paper_state import encode_fact
from registry import StrategyIdentity
from storage.product_dispatch import ProductDispatchJournal
from storage.runtime import PaperRuntimeJournal


@dataclass(frozen=True)
class TradingOutcome:
    operation_id: str
    status: str
    reason_code: str


class TradingService:
    def __init__(self, *, admission, translator, dispatch, canonical, provider, identity, run_id, clock):
        if (type(admission) is not RuntimeAdmission or type(translator) is not OKXProductTranslator or
            type(dispatch) is not ProductDispatchJournal or type(canonical) is not PaperRuntimeJournal or
            type(identity) is not StrategyIdentity or not callable(clock) or
            type(provider) not in (FakeProductProvider, ProductionProductProvider)):
            raise RuntimeAdmissionError('ACTUAL_TRADING_OWNER_COMPOSITION_REQUIRED')
        if (admission.namespace == 'FIXTURE') != (type(provider) is FakeProductProvider):
            raise RuntimeAdmissionError('FIXTURE_PRODUCTION_COMPOSITION_FORBIDDEN')
        self.admission=admission; self.translator=translator; self.dispatch=dispatch; self.canonical=canonical
        self.provider=provider; self.identity=identity; self.run_id=run_id; self.clock=clock; self.lease=None
        self.execution='FAKE_PROVIDER_VERIFICATION' if type(provider) is FakeProductProvider else 'PRODUCTION'

    def bind_process(self, *, expected_revision, expected_generation):
        decision = self.admission.evaluate(self.identity, expected_revision=expected_revision,
                                          permission='MANAGE_EXISTING', execution=self.execution)
        if not decision.allowed: raise RuntimeAdmissionError(*decision.reason_codes)
        self.dispatch.ensure_run(self.run_id, decision.owner_permission, now=self.clock())
        self.lease=self.dispatch.begin_process(self.run_id, decision.process_binding[0],
                                    expected_generation=expected_generation, now=self.clock())
        return self.lease

    def _guard(self, expected_revision, purpose, **kwargs):
        permit=self.admission.issue(self.identity, expected_revision=expected_revision, permission=purpose, execution=self.execution)
        guard=_TradingEffectGuard(self, permit, purpose, **kwargs)
        guard.require()
        return guard

    def recover_publications(self):
        self._coordinator().recover_publications()

    def _coordinator(self):
        return TradingCoordinator(self.dispatch, self.canonical, self.run_id, self.lease, clock=self.clock)

    def _observe(self, operation_id, status, provider_id, reason, effects, *, child_order_ids=None):
        observation=dict(status=status, provider_id=provider_id, reason_code=reason)
        if child_order_ids is not None: observation['child_order_ids']=list(child_order_ids)
        self._coordinator().observe(operation_id, observation, effects)
        return TradingOutcome(operation_id, status, reason)

    def execute(self, prepared, *, expected_revision):
        self.translator.require(prepared, now=self.clock())
        request=prepared.canonical_request
        snapshot=self.canonical.current_execution_subject(self.identity, request.trade_plan_id,
                            position_id=request.position_id, position_action_id=request.position_action_id)
        purpose='NEW_EXPOSURE' if prepared.role == 'ENTRY' else 'MANAGE_EXISTING'
        guard=self._guard(expected_revision, purpose, snapshot=snapshot, preparation=prepared)
        operation_id=request.order_request_id
        self.recover_publications()
        if not self._coordinator().prepare_and_claim(prepared):
            return self.reconcile(operation_id, expected_revision=expected_revision)
        # No E6 transaction crosses this boundary. The committed claim survives
        # denial, timeout, process loss and publication failure.
        guard.require()
        effects=[dict(kind='ORDER_REQUEST', payload=encode_fact(request))]
        try:
            response=self.provider.request('POST', prepared.path, guard=guard, body=dict(prepared.materialization.body))
            result=parse_product_ack(response, prepared, observed_at=self.clock())
            effects.append(dict(kind='ORDER_RESULT', payload=encode_fact(result)))
            status='ACK_REJECTED' if result.order_status.value == 'REJECTED' else 'ACK_PENDING' if result.order_status.value == 'PENDING' else 'RECONCILIATION_REQUIRED'
            native=result.broker_order_id
            reason='PROVIDER_'+status
        except RuntimeAdmissionError:
            # A final provider guard denial precedes credential/HTTP effects.
            # Retain the committed claim for reconciliation; do not disguise
            # an authority failure as a provider acknowledgement.
            raise
        except (ProductProviderError, ValueError):
            status='RECONCILIATION_REQUIRED'; native=None; reason='PROVIDER_OUTCOME_AMBIGUOUS'
        return self._observe(operation_id, status, native, reason, effects)

    def reconcile(self, operation_id, *, expected_revision):
        guard=self._guard(expected_revision, 'MANAGE_EXISTING')
        self.recover_publications()
        operation=self.dispatch.operation(self.run_id, operation_id)
        if operation is None or operation.recovery_disposition != 'READBACK_REQUIRED':
            raise RuntimeAdmissionError('PRIOR_DURABLE_DISPATCH_CLAIM_REQUIRED')
        prepared=restore_product_readback(operation.request)
        if prepared.role == 'PROTECTION_STOP':
            return self._reconcile_stop(operation, prepared, expected_revision)
        import json
        observation=None if operation.observation_json is None else json.loads(operation.observation_json)
        native=None if observation is None else observation['provider_id']
        query=dict(instId='BTC-USDT-SWAP', **({'ordId': native} if native else {'clOrdId': prepared.materialization.provider_cl_ord_id}))
        try:
            response=self._read('/api/v5/trade/order', query, expected_revision)
            lookup=parse_product_order(response, prepared, observed_at=self.clock(), expected_provider_id=native)
            if not lookup.found or lookup.result is None or lookup.lookup_status != 'FOUND_CONSISTENT':
                return self._observe(operation_id, 'RECONCILIATION_REQUIRED', native, 'PROVIDER_LOOKUP_NOT_ABSENCE_PROOF', [])
            result=lookup.result
            rows=self._read('/api/v5/trade/fills', dict(instId='BTC-USDT-SWAP', instType='SWAP', limit='100'), expected_revision)
            fills=parse_product_fills(rows, prepared, expected_provider_id=result.broker_order_id)
            quantity=sum((fill.quantity for fill in fills), Decimal('0'))
            if quantity != result.filled_quantity or any(fill.filled_at > result.observed_at for fill in fills): raise ValueError()
            if quantity and sum((fill.quantity * fill.price for fill in fills), Decimal('0')) / quantity != result.average_fill_price: raise ValueError()
            effects=[dict(kind='ORDER_REQUEST', payload=encode_fact(prepared.canonical_request)),
                     dict(kind='ORDER_RESULT', payload=encode_fact(result))]
            effects.extend(dict(kind='FILL', payload=encode_fact(fill)) for fill in fills)
        except (ProductProviderError, ValueError):
            return self._observe(operation_id, 'RECONCILIATION_REQUIRED', native, 'PROVIDER_READBACK_NOT_PROVEN', [])
        return self._observe(operation_id, 'ORDER_OBSERVED', result.broker_order_id, 'EXACT_PROVIDER_ORDER_AND_FILL_TRUTH', effects)

    def _read(self, path, query, expected_revision):
        # Each distinct HTTP read obtains a fresh issuer permit. A slow previous
        # read cannot renew its own expired permit or bypass revocation.
        guard=self._guard(expected_revision, 'MANAGE_EXISTING')
        return self.provider.request('GET', path, guard=guard, query=query)

    def _reconcile_stop(self, operation, prepared, expected_revision):
        import json
        from execution.models import OrderResult, OrderStatus, ExecutionHealthStatus, SCHEMA_VERSION
        observation=None if operation.observation_json is None else json.loads(operation.observation_json)
        native=None if observation is None else observation['provider_id']
        query={'algoId': native} if native else {'algoClOrdId': prepared.materialization.provider_cl_ord_id}
        try:
            response=self._read('/api/v5/trade/order-algo', query, expected_revision)
            algo=parse_product_algo(response, prepared, expected_provider_id=native)
            if algo.status == 'RECONCILIATION_REQUIRED':
                return self._observe(operation.operation_id, 'RECONCILIATION_REQUIRED', native, 'PROVIDER_ALGO_NOT_ABSENCE_PROOF', [])
            children=None
            if algo.status == 'TRIGGERED_REQUIRES_CHILD_ORDER':
                child=self._read('/api/v5/trade/order', dict(instId='BTC-USDT-SWAP', ordId=algo.child_order_ids[0]), expected_revision)
                rows=self._read('/api/v5/trade/fills', dict(instId='BTC-USDT-SWAP', instType='SWAP', limit='100'), expected_revision)
                outcome=parse_product_stop_child(response, child, rows, prepared,
                            observed_at=self.clock(), expected_provider_id=algo.provider_algo_id)
                result=outcome.parent_result; fills=outcome.fills; children=algo.child_order_ids
                reason='EXACT_TRIGGERED_STOP_CHILD_AND_FILL_TRUTH'
            else:
                result=OrderResult(SCHEMA_VERSION, prepared.canonical_request.order_request_id,
                    prepared.canonical_request.client_order_id, algo.provider_algo_id,
                    OrderStatus.OPEN if algo.status == 'ACTIVE' else OrderStatus.CANCELED,
                    self.clock(), ExecutionHealthStatus.HEALTHY, prepared.canonical_request.quantity, Decimal('0'))
                fills=(); reason='EXACT_NATIVE_STOP_ACTIVE' if algo.status == 'ACTIVE' else 'EXACT_NATIVE_STOP_CANCELED'
            effects=[dict(kind='ORDER_REQUEST',payload=encode_fact(prepared.canonical_request)),
                     dict(kind='ORDER_RESULT',payload=encode_fact(result))]
            effects.extend(dict(kind='FILL',payload=encode_fact(fill)) for fill in fills)
        except (ProductProviderError, ValueError):
            return self._observe(operation.operation_id, 'RECONCILIATION_REQUIRED', native, 'PROVIDER_STOP_READBACK_NOT_PROVEN', [])
        return self._observe(operation.operation_id, 'ALGO_OBSERVED', algo.provider_algo_id, reason, effects, child_order_ids=children)
