"""Versioned E4 pure translation, without sockets, credentials or financial authority."""
from dataclasses import dataclass, replace
from datetime import timedelta, datetime
from decimal import Decimal
from types import MappingProxyType

from brokers.okx_demo import OKXOrderMaterialization, OKXPrerequisiteSnapshot, _materialize_market_order, stable_okx_cl_ord_id
from brokers.okx_sizing import size_okx_market_entry
from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from brokers.okx_product_capability import OKXProductCapabilityOwner, CAPABILITY_PROFILE, _time
from execution.gateway import ExecutionGateway
from execution.close import prepare_close_order
from execution.models import Side
from execution.protection_trigger import prepare_trigger_validated_protection_order, _market_payload
from position.protection_registry_policy import interpret_protection_registry_evidence, canonical_protection_registry_hash


class OKXProductError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ProductOrderPreparation:
    role: str
    path: str
    canonical_request: object
    materialization: OKXOrderMaterialization
    metadata: object
    mechanical_proof: object
    capability_profile: str
    authority_hash: str
    prepared_at: datetime
    expires_at: datetime
    source_plan_hash: str | None = None
    source_action_hash: str | None = None
    source_position_hash: str | None = None


class OKXProductTranslator:
    def __init__(self, capabilities):
        if type(capabilities) is not OKXProductCapabilityOwner:
            raise OKXProductError('PRODUCT_CAPABILITY_OWNER_REQUIRED')
        self.capabilities = capabilities
        self._issued = {}

    def _register(self, role, request, materialization, metadata, proof, authority, *, now, expiry, path='/api/v5/trade/order', entry_prerequisites=None):
        # The canonical E4 request records the actual bounded exposure sent.
        # E5's approved plan/action and the original upper bound stay immutable.
        request = replace(request, quantity=materialization.effective_canonical_quantity)
        materialization = replace(materialization, body=MappingProxyType(dict(materialization.body)))
        source = authority.get('input')
        plan = authority.get('plan') if source is None else source.parent_plan
        action = authority.get('action') if source is None else source.action
        position = authority.get('position') if source is None else source.current_position
        prepared = ProductOrderPreparation(role, path, request, materialization,
            metadata, proof, CAPABILITY_PROFILE, canonical_okx_close_sizing_hash(authority), now,
            min(now + timedelta(seconds=1), expiry), canonical_okx_close_sizing_hash(plan),
            None if action is None else canonical_okx_close_sizing_hash(action),
            None if position is None else canonical_okx_close_sizing_hash(position))
        self._issued = {key: record for key, record in self._issued.items() if record[0].expires_at > now}
        if len(self._issued) >= 1024:
            raise OKXProductError('PRODUCT_PREPARATION_ISSUANCE_LIMIT')
        self._issued[id(prepared)] = (prepared, canonical_okx_close_sizing_hash(prepared), entry_prerequisites)
        return prepared

    def require(self, prepared, *, now):
        now = _time(now)
        record = self._issued.get(id(prepared))
        if (type(prepared) is not ProductOrderPreparation or record is None or record[0] is not prepared or
            record[1] != canonical_okx_close_sizing_hash(prepared) or
            not prepared.prepared_at <= now < prepared.expires_at):
            raise OKXProductError('CURRENT_OWNER_ISSUED_PREPARATION_REQUIRED')
        self.capabilities.require(prepared.mechanical_proof, prepared.metadata, role=prepared.role, now=now)
        if record[2] is not None:
            self.capabilities.require_entry_prerequisites(*record[2], now=now)
        return prepared

    def prepare_entry(self, *, plan, metadata, prerequisites, proof, now, prerequisites_proof=None):
        self.capabilities.require(proof, metadata, role='ENTRY', now=now)
        self.capabilities.require_entry_prerequisites(prerequisites, prerequisites_proof, now=now)
        if (not isinstance(prerequisites, OKXPrerequisiteSnapshot) or
            canonical_okx_close_sizing_hash(prerequisites.account) != proof.account_hash or
            prerequisites.pending_orders or any(position.provider_contract_quantity != 0 or
            position.instrument_id != 'BTC-USDT-SWAP' or position.margin_mode != 'isolated' or
            position.position_side != 'net' for position in prerequisites.positions)):
            raise OKXProductError('PRODUCT_ENTRY_PREREQUISITES_NOT_CONVERGED')
        request = ExecutionGateway().prepare_entry_order(plan, now=now)
        sizing = size_okx_market_entry(request, metadata, now=now)
        materialization = _materialize_market_order(request, sizing, metadata, position_mode='net_mode', now=now)
        return self._register('ENTRY', request, materialization, metadata, proof,
                              dict(plan=plan, prerequisites=prerequisites, prerequisites_proof=prerequisites_proof), now=now,
                              expiry=min(datetime.fromisoformat(plan['expires_at'].replace('Z', '+00:00')), prerequisites_proof.expires_at),
                              entry_prerequisites=(prerequisites, prerequisites_proof))

    def prepare_close(self, value, metadata_binding, proof, *, now):
        evidence = self.capabilities.evaluate_close(value, metadata_binding, proof, now=now)
        if value.evaluation_phase != 'PRE_ACTION' or evidence['sizing_state'] not in {'FULLY_REDUCIBLE', 'PARTIALLY_REDUCIBLE'}:
            raise OKXProductError('PRODUCT_CLOSE_FRESH_ACTION_AND_SIZE_REQUIRED')
        request = prepare_close_order(value.action, value.parent_plan, value.current_position, now=now)
        identity = stable_okx_cl_ord_id(request.client_order_id)
        body = dict(instId='BTC-USDT-SWAP', tdMode='isolated', posSide='net',
                    side='buy' if request.side == Side.BUY else 'sell', ordType='market',
                    sz=evidence['quantized_provider_close_size'], clOrdId=identity.provider_cl_ord_id, reduceOnly=True)
        materialization = OKXOrderMaterialization(
            request.order_request_id, request.trade_plan_id, request.client_order_id, identity.provider_cl_ord_id,
            'BTC-USDT-SWAP', body['side'], 'net', Decimal(evidence['quantized_provider_close_size']),
            Decimal(evidence['effective_canonical_close_quantity']), request.quantity,
            value.instrument_metadata.metadata_ref, value.instrument_metadata.observed_at, body,
        )
        return self._register(request.order_role, request, materialization, value.instrument_metadata, proof,
                              dict(input=value, metadata_binding=metadata_binding, sizing=evidence), now=now,
                              expiry=datetime.fromisoformat(value.action['expires_at'].replace('Z', '+00:00')))

    def prepare_protection(self, *, action, plan, position, trigger_evidence, market,
                           market_freshness_classification, registry_evidence, registry_authority,
                           metadata, proof, now):
        self.capabilities.require(proof, metadata, role='PROTECTION_STOP', now=now)
        decision = interpret_protection_registry_evidence(registry_evidence, registry_authority)
        if (not decision.evidence_current or position != registry_authority.position or
            position['lifecycle_state'] != 'OPEN_UNPROTECTED' or
            registry_evidence['multiplicity_state'] != 'NO_ACTIVE_PROTECTION_OBSERVED' or
            registry_evidence['registry_status'] != 'MISSING_PROTECTION_REINTERPRETATION_REQUIRED'):
            raise OKXProductError('PRODUCT_INITIAL_PROTECTION_REGISTRY_NOT_CONVERGED')
        request = prepare_trigger_validated_protection_order(action, plan, position, trigger_evidence, market,
                    market_freshness_classification=market_freshness_classification, now=now)
        lineage = registry_evidence['intended_protection_lineage']
        expected = dict(position_action_id=action['position_action_id'],
                        position_action_hash=canonical_protection_registry_hash(action),
                        approved_trade_plan_hash=canonical_protection_registry_hash(plan),
                        protection_order_request_hash=canonical_protection_registry_hash(request),
                        protection_order_request_ref=request.order_request_id,
                        trigger_validity_ref=trigger_evidence['protection_trigger_validity_id'])
        if any(lineage.get(key) != value for key, value in expected.items()):
            raise OKXProductError('PRODUCT_PROTECTION_EXACT_LINEAGE_REQUIRED')
        market_payload = _market_payload(market)
        for value in (registry_authority.provider_observed_at, registry_authority.provider_received_at,
                      None if market_payload is None else market_payload.get('observed_at'),
                      None if market_payload is None else market_payload.get('received_at')):
            try:
                timestamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
                if timestamp > now or now - timestamp > timedelta(seconds=30):
                    raise ValueError()
            except (ValueError, TypeError, AttributeError):
                raise OKXProductError('PRODUCT_PROTECTION_CURRENT_READBACK_REQUIRED') from None
        native_quantity = request.quantity / (metadata.ct_val * metadata.ct_mult)
        if (native_quantity <= 0 or native_quantity % metadata.lot_sz != 0 or native_quantity < metadata.min_sz or
            (metadata.max_mkt_sz is not None and native_quantity > metadata.max_mkt_sz) or
            request.stop_price % metadata.tick_sz != 0):
            raise OKXProductError('PRODUCT_PROTECTION_EXACT_NATIVE_REPRESENTATION_REQUIRED')
        identity = stable_okx_cl_ord_id(request.client_order_id)
        body = dict(instId='BTC-USDT-SWAP', tdMode='isolated', posSide='net',
                    side='buy' if request.side == Side.BUY else 'sell', ordType='conditional',
                    sz=format(native_quantity, 'f'), algoClOrdId=identity.provider_cl_ord_id,
                    slTriggerPx=format(request.stop_price, 'f'), slOrdPx='-1', slTriggerPxType='last', reduceOnly=True)
        materialization = OKXOrderMaterialization(
            request.order_request_id, request.trade_plan_id, request.client_order_id, identity.provider_cl_ord_id,
            'BTC-USDT-SWAP', body['side'], 'net', native_quantity, request.quantity, request.quantity,
            metadata.metadata_ref, metadata.observed_at, body,
        )
        return self._register('PROTECTION_STOP', request, materialization, metadata, proof,
                              dict(action=action, plan=plan, position=position, trigger=trigger_evidence,
                                   market=market_payload, registry=registry_evidence, registry_authority=registry_authority),
                              now=now, expiry=datetime.fromisoformat(action['expires_at'].replace('Z', '+00:00')),
                              path='/api/v5/trade/order-algo')
