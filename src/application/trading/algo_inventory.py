"""Issuer-local bounded read scans under actual current E6/E7/E4 owners.

This module grants no protection state, absence, cleanup, retry or financial
authority. A consumer must still compose actual FP04/FP11 and E5 evidence.
"""
from datetime import timedelta

from application.trading.admission import RuntimeAdmissionError
from application.trading.provider import ProductionProductProvider
from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from brokers.okx_product_inventory import (ALGO_TYPES,ProductAlgoInventoryObservation,
                                         parse_product_algo_page)
from brokers.okx_production_transport import _query


def _current(service,metadata,proof,revision):
    service.translator.capabilities.require(proof,metadata,role='READ_ONLY_RECONCILIATION',now=service.clock())
    if type(service.provider) is ProductionProductProvider and proof.account_hash!=service.provider.account_hash:
        raise RuntimeAdmissionError('EXACT_NATIVE_INVENTORY_ACCOUNT_REQUIRED')
    service._guard(revision,'MANAGE_EXISTING')


def read_algo_inventory(service,*,metadata,proof,expected_revision):
    _current(service,metadata,proof,expected_revision)
    start=service.clock();lease=service.lease;provider=service.provider
    request_count=0;scans=[]
    for _ in range(2):
        objects=[];seen=set()
        for kind in ALGO_TYPES:
            cursor=None
            while True:
                if (request_count>=128 or service.lease!=lease or service.provider is not provider or
                    not start<=service.clock()<start+timedelta(seconds=5)):
                    raise RuntimeAdmissionError('BOUNDED_CURRENT_NATIVE_INVENTORY_REQUIRED')
                _current(service,metadata,proof,expected_revision)
                query=dict(instId='BTC-USDT-SWAP',ordType=kind,limit='100')
                if cursor is not None:query['after']=cursor
                _query('/api/v5/trade/orders-algo-pending',query)
                response=service._read('/api/v5/trade/orders-algo-pending',query,expected_revision)
                request_count+=1
                page=parse_product_algo_page(response,algo_type=kind,received_at=service.clock(),after=cursor)
                if any(item.provider_algo_id in seen for item in page):
                    raise RuntimeAdmissionError('NATIVE_INVENTORY_DUPLICATE_OBJECT')
                seen.update(item.provider_algo_id for item in page);objects.extend(page)
                if len(objects)>4096:raise RuntimeAdmissionError('NATIVE_INVENTORY_CAPACITY_LIMIT')
                if len(page)<100:break
                cursor=page[-1].provider_algo_id
        scans.append(tuple(objects))
    if scans[0]!=scans[1]:raise RuntimeAdmissionError('NATIVE_INVENTORY_SCAN_DID_NOT_CONVERGE')
    _current(service,metadata,proof,expected_revision);now=service.clock()
    if service.lease!=lease or service.provider is not provider or not start<=now<start+timedelta(seconds=5):
        raise RuntimeAdmissionError('BOUNDED_CURRENT_NATIVE_INVENTORY_REQUIRED')
    value=ProductAlgoInventoryObservation('okx-product-algo-inventory-v0.2',scans[0],ALGO_TYPES,
        'CONVERGED_BOUNDED_READ_SCAN',start,now,request_count,proof.account_hash,
        canonical_okx_close_sizing_hash(metadata))
    service._algo_inventories={key:record for key,record in service._algo_inventories.items()
        if record[0].request_started_at+timedelta(seconds=5)>now}
    if len(service._algo_inventories)>=1024:raise RuntimeAdmissionError('NATIVE_INVENTORY_ISSUANCE_LIMIT')
    service._algo_inventories[id(value)]=(value,canonical_okx_close_sizing_hash(value),lease,provider)
    return value


def require_algo_inventory(service,value,*,metadata,proof,expected_revision):
    record=service._algo_inventories.get(id(value));now=service.clock()
    if (type(value) is not ProductAlgoInventoryObservation or record is None or record[0] is not value or
        record[1]!=canonical_okx_close_sizing_hash(value) or record[2]!=service.lease or record[3] is not service.provider or
        value.account_hash!=proof.account_hash or value.metadata_hash!=canonical_okx_close_sizing_hash(metadata) or
        not value.request_started_at<=now<value.request_started_at+timedelta(seconds=5)):
        raise RuntimeAdmissionError('CURRENT_ISSUER_NATIVE_INVENTORY_REQUIRED')
    _current(service,metadata,proof,expected_revision)
    if (record[2]!=service.lease or record[3] is not service.provider or
        record[1]!=canonical_okx_close_sizing_hash(value) or
        not value.request_started_at<=service.clock()<value.request_started_at+timedelta(seconds=5)):
        raise RuntimeAdmissionError('CURRENT_ISSUER_NATIVE_INVENTORY_REQUIRED')
    return value
