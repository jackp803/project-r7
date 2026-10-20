"""Shared genuine cleanup source fixture; no discoverable TestCase/tests."""
from dataclasses import replace
from datetime import timedelta
import json
import unittest
from unittest.mock import patch

import tests.product.test_trading_protected_close_v02 as fixtures
import tests.product.test_trading_inventory_v02 as inventory_fixtures


class StopCleanupFixture:
    def setUp(self):
        self.flow=fixtures.GenuineProtectedCloseContext(self).protect()
        self.fixture=self.flow.fixture;self.service=self.flow.service;self.provider=self.flow.provider

    def algo(self,**changes):
        now=self.fixture.clock[0]
        row=dict(self.flow.stop.materialization.body,instType='SWAP',algoId='2345',state='live',
            ordIdList=[],actualSz='0',failCode='',cTime=str(int(self.flow.stop.canonical_request.created_at.timestamp()*1000)),
            uTime=str(int(now.timestamp()*1000)))
        row.update(changes);return row

    def flat(self):
        self.flow.close_readback(flat=False);self.flow.close_readback(flat=True)
        self.fixture.clock[0]+=timedelta(seconds=1)

    def reads(self,*,net='0',extra=False,empty=False,stop_changes=None):
        algo=self.algo(**(stop_changes or {}))
        self.flow.append(dict(code='0',data=[algo]),self.flow.position.response(pos=net,posId='5678',avgPx='0' if net=='0' else '60000'))
        stop=self.service.read_fixture_cleanup_stop(self.flow.stop.canonical_request.order_request_id,
            expected_revision=self.fixture.revision)
        metadata,proof=self.flow.fresh()
        native=self.service.read_position(metadata=metadata,proof=proof,expected_revision=self.fixture.revision,
            expected_provider_position_id='5678')
        rows=[] if empty else [algo]
        if extra:rows.append(dict(algo,algoId='9999',algoClOrdId='UNOWNEDSTOP'))
        self.flow.append(*inventory_fixtures.TradingInventoryV02Tests(methodName='runTest').scans(rows))
        inventory=self.service.read_algo_inventory(metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        return stop,native,inventory,metadata,proof

    def prepare(self,reads):
        stop,native,inventory,metadata,proof=reads
        return self.service.prepare_fixture_stop_cleanup(self.flow.stop.canonical_request.order_request_id,
            stop,native,inventory,metadata=metadata,proof=proof,expected_revision=self.fixture.revision)

    def execute(self,prepared):
        return self.service.execute_fixture_stop_cleanup(prepared,expected_revision=self.fixture.revision)

    def cancel_calls(self):return [c for c in self.provider.calls if c['path']=='/api/v5/trade/cancel-algos']

    def append_unknown_entry(self):
        from storage.product_dispatch import open_product_dispatch_journal
        decision=self.service.admission.evaluate(self.service.identity,expected_revision=self.fixture.revision,
            permission='MANAGE_EXISTING',execution=self.service.execution)
        self.assertTrue(decision.allowed)
        with open_product_dispatch_journal(self.fixture.root/'dispatch.sqlite') as writer:
            writer.ensure_run('other-cleanup',decision.owner_permission,now=self.fixture.clock[0])
            lease=writer.begin_process('other-cleanup','other-cleanup:1',expected_generation=0,now=self.fixture.clock[0])
            unknown=dict(role='ENTRY',path='/api/v5/trade/order',native_client_id='OTHERCLEANUP',
                body=dict(instId='BTC-USDT-SWAP',tdMode='isolated',posSide='net',side='buy',ordType='market',sz='10',clOrdId='OTHERCLEANUP'),
                canonical_request_hash='sha256:'+'1'*64,authority_hash='sha256:'+'2'*64)
            writer.prepare('other-cleanup','other-cleanup-op',unknown,lease=lease,now=self.fixture.clock[0])
            writer.claim_dispatch('other-cleanup','other-cleanup-op',lease=lease,now=self.fixture.clock[0])
