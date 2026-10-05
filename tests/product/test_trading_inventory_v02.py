"""Actual E6/E7-fenced native scans with controlled fake provider only."""
import unittest
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

import tests.product.test_trading_position_v02 as fixtures
import tests.brokers.test_okx_product_inventory_v02 as rows


class TradingInventoryV02Tests(unittest.TestCase):
    def setUp(self):
        self.helper=fixtures.TradingPositionV02Tests(methodName='runTest')
        self.addCleanup(self.helper.doCleanups)
        self.helper.setUp()
        self.fixture=self.helper.fixture
        self.rows=rows.ProductInventoryV02Tests(methodName='runTest');self.rows.setUp()
        self.rows.now=self.fixture.clock[0]

    def scans(self, first=(), second=None):
        # Eight distinct documented types, each explicitly exhausted; two scans
        # compare original native material, never manufacture an atomic snapshot.
        second=first if second is None else second
        return [dict(code='0',data=list(values) if i==0 else [])
                for values in (first,second) for i in range(8)]

    def read(self, script):
        service,provider=self.helper.helper.service(script)
        metadata,proof=self.helper.current_metadata()
        value=service.read_algo_inventory(metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        return service,provider,metadata,proof,value

    def test_two_bounded_complete_scans_return_issuer_bound_truth_without_post(self):
        service,provider,metadata,proof,value=self.read(self.scans([self.rows.row()]))
        self.assertEqual(1,len(value.objects))
        self.assertEqual('CONVERGED_BOUNDED_READ_SCAN',value.coverage)
        self.assertEqual(16,value.request_count)
        self.assertTrue(all(call['method']=='GET' for call in provider.calls))
        self.assertIs(value,service.require_algo_inventory(value,metadata=metadata,proof=proof,
            expected_revision=self.fixture.revision))
        self.assertIsNone(self.helper.canonical.recover(trade_plan_id=self.helper.helper.plan['trade_plan_id']).current_position_projection)

    def test_a_changed_second_scan_is_not_protection_or_absence_proof(self):
        service,provider=self.helper.helper.service(self.scans([self.rows.row()],[self.rows.row(sz='5')]))
        metadata,proof=self.helper.current_metadata()
        with self.assertRaises(ValueError):
            service.read_algo_inventory(metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        self.assertTrue(all(call['method']=='GET' for call in provider.calls))

    def test_full_page_requires_next_cursor_and_does_not_silently_truncate(self):
        first=[self.rows.row(str(1000-i)) for i in range(100)]
        script=[]
        for scan in range(2):
            script.extend([dict(code='0',data=first),dict(code='0',data=[])])
            script.extend(dict(code='0',data=[]) for _ in range(7))
        service,provider,metadata,proof,value=self.read(script)
        self.assertEqual(100,len(value.objects));self.assertEqual(18,value.request_count)
        self.assertEqual('901',provider.calls[1]['query']['after'])
        self.assertEqual('901',provider.calls[10]['query']['after'])

    def test_copies_mutation_stale_generation_and_provider_replacement_cannot_refresh_scan(self):
        service,provider,metadata,proof,value=self.read(self.scans())
        for changed in (replace(value),replace(value,request_count=1)):
            with self.assertRaises(ValueError):
                service.require_algo_inventory(changed,metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        lease=service.lease
        service.lease=replace(lease,generation=lease.generation+1)
        with self.assertRaises(ValueError):
            service.require_algo_inventory(value,metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        service.lease=lease
        service.provider=self.helper.helper.api().FakeProductProvider([])
        with self.assertRaises(ValueError):
            service.require_algo_inventory(value,metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        service.provider=provider;self.fixture.clock[0]+=timedelta(seconds=6)
        with self.assertRaises(ValueError):
            service.require_algo_inventory(value,metadata=metadata,proof=proof,expected_revision=self.fixture.revision)

    def test_revoked_owner_revision_and_page_error_do_not_retry_or_issue_incomplete_scan(self):
        service,provider=self.helper.helper.service([dict(code='50000',data=[])])
        metadata,proof=self.helper.current_metadata()
        with self.assertRaises(ValueError):
            service.read_algo_inventory(metadata=metadata,proof=proof,expected_revision=self.fixture.revision+1)
        self.assertEqual([],provider.calls)
        with self.assertRaises(ValueError):
            service.read_algo_inventory(metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        self.assertEqual(1,len(provider.calls))

    def test_provider_changed_during_owner_validation_cannot_receive_current_scan(self):
        service,provider,metadata,proof,value=self.read(self.scans())
        original=service._guard
        def changing(*args,**kwargs):
            result=original(*args,**kwargs)
            service.provider=self.helper.helper.api().FakeProductProvider([])
            return result
        with patch.object(service,'_guard',side_effect=changing),self.assertRaises(ValueError):
            service.require_algo_inventory(value,metadata=metadata,proof=proof,expected_revision=self.fixture.revision)


if __name__=='__main__':unittest.main()
