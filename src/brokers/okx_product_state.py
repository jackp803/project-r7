"""Exact durable readback context. Restoring never issues submit authority."""
from datetime import datetime
from decimal import Decimal
from types import MappingProxyType
import re
from brokers.paper_state import encode_fact, decode_fact
from brokers.okx_demo import OKXOrderMaterialization, stable_okx_cl_ord_id
from brokers.okx_product import ProductOrderPreparation, OKXProductError
from brokers.okx_product_capability import CAPABILITY_PROFILE
from brokers.okx_production_transport import _body
from execution.models import OrderRequest
from registry.product_assessment import canonical, digest

PROFILE = 'okx-product-durable-readback-v0.2'
_BASE = {'role', 'path', 'native_client_id', 'body', 'canonical_request_hash', 'authority_hash'}
_FIELDS = _BASE | {'preparation_profile', 'canonical_request', 'normalization'}


def durable_product_intent(prepared):
    material = prepared.materialization
    value = dict(role=prepared.role, path=prepared.path, native_client_id=material.provider_cl_ord_id,
        body=dict(material.body), canonical_request=encode_fact(prepared.canonical_request),
        preparation_profile=PROFILE, authority_hash=prepared.authority_hash,
        normalization=dict(approved_quantity=str(material.canonical_approved_quantity),
            metadata_ref=material.instrument_metadata_ref,
            metadata_observed_at=material.instrument_metadata_observed_at.isoformat().replace('+00:00', 'Z'),
            source_plan_hash=prepared.source_plan_hash, source_action_hash=prepared.source_action_hash,
            source_position_hash=prepared.source_position_hash))
    value['canonical_request_hash'] = digest(canonical(value['canonical_request']))
    restore_product_readback(value)
    return value


def restore_product_readback(value):
    try:
        if not isinstance(value, dict) or set(value) != _FIELDS or value['preparation_profile'] != PROFILE:
            raise ValueError()
        request = decode_fact(OrderRequest, value['canonical_request'])
        role = value['role']; body = value['body']; normalization = value['normalization']
        path = '/api/v5/trade/order-algo' if role == 'PROTECTION_STOP' else '/api/v5/trade/order'
        client_key = 'algoClOrdId' if role == 'PROTECTION_STOP' else 'clOrdId'
        _body(path, body)
        if (role not in {'ENTRY', 'PROTECTION_STOP', 'POSITION_EXIT', 'EMERGENCY_EXIT'} or
            (request.order_role not in (None, 'ENTRY') if role == 'ENTRY' else request.order_role != role) or
            request.symbol != 'BTC_USDT_PERP' or value['path'] != path or
            value['native_client_id'] != stable_okx_cl_ord_id(request.client_order_id).provider_cl_ord_id or
            body[client_key] != value['native_client_id'] or body['side'] != request.side.value.lower() or
            digest(canonical(value['canonical_request'])) != value['canonical_request_hash'] or
            (role != 'ENTRY' and (request.reduce_only is not True or body.get('reduceOnly') is not True))):
            raise ValueError()
        if not isinstance(normalization, dict) or set(normalization) != {'approved_quantity','metadata_ref','metadata_observed_at',
                'source_plan_hash','source_action_hash','source_position_hash'}:
            raise ValueError()
        for key in ('authority_hash', 'canonical_request_hash'):
            if not isinstance(value[key], str) or not re.fullmatch('sha256:[0-9a-f]{64}', value[key]): raise ValueError()
        for key in ('source_plan_hash','source_action_hash','source_position_hash'):
            hashed = normalization[key]
            if hashed is None and role == 'ENTRY' and key != 'source_plan_hash': continue
            if not isinstance(hashed, str) or not re.fullmatch('sha256:[0-9a-f]{64}', hashed): raise ValueError()
        approved = Decimal(normalization['approved_quantity'])
        if not approved.is_finite() or approved < request.quantity: raise ValueError()
        at = datetime.fromisoformat(normalization['metadata_observed_at'].replace('Z', '+00:00'))
        from execution.models import require_utc
        require_utc(at, 'metadata_observed_at')
        reference = normalization['metadata_ref']
        if not isinstance(reference, str) or not 0 < len(reference) <= 256 or any(c in reference for c in '\x00\r\n'): raise ValueError()
        material = OKXOrderMaterialization(request.order_request_id, request.trade_plan_id, request.client_order_id,
            value['native_client_id'], 'BTC-USDT-SWAP', body['side'], 'net', Decimal(body['sz']), request.quantity,
            approved, reference, at, MappingProxyType(dict(body)))
        return ProductOrderPreparation(role, path, request, material, None, None, CAPABILITY_PROFILE,
            value['authority_hash'], request.created_at, request.created_at,
            normalization['source_plan_hash'], normalization['source_action_hash'], normalization['source_position_hash'])
    except (ValueError, TypeError, KeyError, AttributeError):
        raise OKXProductError('EXACT_DURABLE_PRODUCT_READBACK_CONTEXT_REQUIRED') from None
