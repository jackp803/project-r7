"""Controlled genuine protected-close fixture; execution is recorded separately.

Test/helper only. One actual FakeProductProvider instance throughout.
No cleanup, finalization, funding, DB terminal injection or PaperBroker bypass.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import unittest
import json

import tests.product.test_trading_close_v02 as close_fixtures
import tests.product.test_trading_inventory_v02 as inventory_fixtures
import tests.brokers.test_okx_demo_adapter as metadata_fixtures
import tests.execution.test_protection_registry_evidence as registry_fixtures
from brokers.okx_demo import OKXAccountConfigSnapshot
from brokers.paper_state import decode_fact
from execution.models import OrderRequest, OrderResult, Fill
from execution.protection_trigger import prepare_trigger_validated_protection_order
from execution.protection_registry_evidence_boundary import build_protection_registry_multiplicity_evidence
from position import CurrentProtectionRegistryAuthority
from position.protection import build_protect_position_action
from position.protection_registry_policy import canonical_protection_registry_hash
from position.protection_trigger_validity import build_protection_trigger_validity_evidence
from position.lifecycle_execution_binding import (validate_position_lifecycle_execution_evidence_binding,
    build_position_lifecycle_execution_evidence_binding)


def stamp(value):
    return value.isoformat().replace('+00:00', 'Z')


class GenuineProtectedCloseContext:
    def __init__(self, testcase):
        self.test = testcase
        self.owner = close_fixtures.TradingCloseV02Tests(methodName='runTest')
        self.owner.setUp()
        testcase.addCleanup(self.owner.doCleanups)
        self.fixture = self.owner.fixture
        self.position = self.owner.position
        self.helper = self.owner.helper
        # Existing genuine helper: actual FULL FILLED entry, real canonical
        # fills plus issued native position read and normal E5 entry publication.
        context = self.owner.entered()
        self.service, self.provider = context[:2]
        self.provider_identity = id(self.provider)
        self.contracts = format(self.helper.prepared.materialization.provider_contract_quantity, 'f')
        testcase.assertEqual('10', self.contracts, 'Existing bounded fixture quantity; fail on changed recipe')
        self.entry_operation = self.helper.prepared.canonical_request.order_request_id
        self.stop = None
        self.close = None
        self.first_close_fill = None
        self.assert_binding()
        entry = next(item.payload for item in self.recover().current_order_results
                     if item.payload['order_request_id'] == self.entry_operation)
        testcase.assertEqual('FILLED', entry['order_status'])
        testcase.assertEqual(Decimal(entry['requested_quantity']), Decimal(entry['filled_quantity']))

    def recover(self):
        return self.position.recover()

    def append(self, *responses):
        # Script input only, consumed by the same actual provider and parsers.
        self.test.assertEqual(self.provider_identity, id(self.service.provider))
        from application.trading.provider import FakeProductProvider
        self.provider._responses.extend(FakeProductProvider(list(responses))._responses)

    def assert_binding(self):
        recovered = self.recover()
        self.test.assertTrue(recovered.restart_authoritative, recovered.reason_codes)
        validate_position_lifecycle_execution_evidence_binding(
            recovered.current_lifecycle_execution_binding.payload,
            recovered.current_position_projection.payload)
        rebuilt = build_position_lifecycle_execution_evidence_binding(
            recovered.current_position_projection.payload,
            order_requests=tuple(decode_fact(OrderRequest, row.payload) for row in recovered.order_requests),
            order_results=tuple(decode_fact(OrderResult, row.payload) for row in recovered.order_result_observations),
            fills=tuple(decode_fact(Fill, row.payload) for row in recovered.fills))
        self.test.assertEqual(rebuilt, recovered.current_lifecycle_execution_binding.payload,
                              'Binding must cover the complete actual recovered execution graph')
        return recovered

    def fresh(self, role='READ_ONLY_RECONCILIATION'):
        now = self.fixture.clock[0]
        metadata = replace(metadata_fixtures._metadata(now), ct_val=Decimal('0.0001'))
        proof = self.helper.capabilities.issue(role, OKXAccountConfigSnapshot('2', 'net_mode', '123', '123'),
            metadata, observed_at=now, now=now)
        return metadata, proof

    def protect(self):
        now = self.fixture.clock[0]
        recovered = self.assert_binding()
        position = recovered.current_position_projection.payload
        binding = recovered.current_lifecycle_execution_binding.payload
        action = build_protect_position_action(position, self.helper.plan,
            created_at=now, expires_at=now+timedelta(seconds=30))
        self.helper.canonical.persist_position_action(action)
        market = dict(schema_version='contracts-v0.1', symbol='BTC_USDT_PERP', source='FIXTURE_MARKET',
            observed_at=stamp(now), received_at=stamp(now), health_status='HEALTHY', last_price='60000', freshness_ms=0)
        trigger = build_protection_trigger_validity_evidence(position, action, self.helper.plan, market,
            market_freshness_classification='FRESH', evaluated_at=now)
        request = prepare_trigger_validated_protection_order(action, self.helper.plan, position, trigger, market,
            market_freshness_classification='FRESH', now=now)
        # Same E4 pre-protection registry evidence builder recipe as existing
        # TradingDispatchV02Tests.stop(), using actual full-entry position/binding.
        registry = registry_fixtures.ProtectionRegistryMultiplicityEvidenceTests(methodName='runTest')
        registry.setUp(); self.test.addCleanup(registry.doCleanups)
        registry.provider_observed_at = now
        registry.provider_received_at = now
        registry.evaluated_at = now
        lineage = registry.intended_lineage(position,
            position_action_id=action['position_action_id'],
            position_action_hash=canonical_protection_registry_hash(action),
            approved_trade_plan_hash=canonical_protection_registry_hash(self.helper.plan),
            protection_order_request_hash=canonical_protection_registry_hash(request),
            protection_order_request_ref=request.order_request_id,
            trigger_validity_ref=trigger['protection_trigger_validity_id'],
            lifecycle_projection_ref=position['lifecycle_projection_id'],
            lifecycle_execution_binding_ref=binding['lifecycle_execution_binding_id'])
        evidence = build_protection_registry_multiplicity_evidence(registry.input_for(
            position=position, lineage=lineage, observed_set=registry.observed_set([]),
            lifecycle_projection_ref=position['lifecycle_projection_id'],
            lifecycle_execution_binding_ref=binding['lifecycle_execution_binding_id']))
        authority = CurrentProtectionRegistryAuthority(evidence['position_ref'], evidence['position_hash'],
            position, position, binding, evidence['provider_identity_ref'], evidence['provider_instrument_ref'],
            evidence['provider_observation_generation_id'], evidence['provider_observed_at'],
            evidence['provider_received_at'], evidence['observed_active_protection_set_hash'])
        metadata, proof = self.fresh('PROTECTION_STOP')
        self.stop = self.helper.translator.prepare_protection(action=action, plan=self.helper.plan,
            position=position, trigger_evidence=trigger, market=market, market_freshness_classification='FRESH',
            registry_evidence=evidence, registry_authority=authority, metadata=metadata, proof=proof, now=now)
        algo = dict(self.stop.materialization.body, instType='SWAP', algoId='2345', state='live',
            ordIdList=[], actualSz='0', failCode='', cTime=str(int(now.timestamp()*1000)),
            uTime=str(int(now.timestamp()*1000)))
        self.append(dict(code='0', data=[dict(algoId='2345', algoClOrdId=algo['algoClOrdId'], sCode='0')]))
        self.service.execute(self.stop, expected_revision=self.fixture.revision)
        self.fixture.clock[0] += timedelta(seconds=1)
        # Real target readback and complete convergent native inventory.
        self.append(dict(code='0', data=[algo]), self.position.response(pos=self.contracts))
        scans = inventory_fixtures.TradingInventoryV02Tests(methodName='runTest').scans([algo])
        self.append(*scans)
        self.service.reconcile(self.stop.canonical_request.order_request_id, expected_revision=self.fixture.revision)
        metadata, proof = self.fresh()
        native = self.service.read_position(metadata=metadata, proof=proof, expected_revision=self.fixture.revision,
                                            expected_provider_position_id='5678')
        self.position.project(self.service, native, metadata, proof)
        inventory = self.service.read_algo_inventory(metadata=metadata, proof=proof, expected_revision=self.fixture.revision)
        self.service.project_protection(self.stop.canonical_request.order_request_id, native, inventory,
            metadata=metadata, proof=proof, expected_revision=self.fixture.revision)
        recovered = self.assert_binding()
        self.test.assertEqual('OPEN_PROTECTED', recovered.current_position_projection.payload['lifecycle_state'])
        self.positive_source = deepcopy(recovered.current_position_projection.payload)
        # Preserve latest original ENTRY publication, not protection inventory receipt.
        self.original_positive = self.service.dispatch.latest_position_publication('fixture-run', self.entry_operation)
        self.test.assertEqual('5678', json.loads(self.original_positive.observation_json)['provider_position_id'])
        # Metadata and issuer read still current at this unchanged fixture clock.
        close_metadata, close_proof = self.fresh('POSITION_EXIT')
        self.test.assertEqual(metadata, close_metadata)
        self.close = self.service.prepare_fixture_close(self.helper.plan['trade_plan_id'], native,
            metadata=metadata, read_proof=proof, close_proof=close_proof, expected_revision=self.fixture.revision)
        self.test.assertEqual(self.positive_source, self.recover().current_position_projection.payload)
        self.append(dict(code='0', data=[dict(ordId='3456', clOrdId=self.close.materialization.provider_cl_ord_id, sCode='0')]))
        self.service.execute(self.close, expected_revision=self.fixture.revision)
        self.assert_binding()
        return self

    def close_readback(self, *, flat):
        self.fixture.clock[0] += timedelta(seconds=2)
        now = self.fixture.clock[0]
        prepared = self.close
        if self.first_close_fill is None:
            self.first_close_fill = dict(instId='BTC-USDT-SWAP', clOrdId=prepared.materialization.provider_cl_ord_id,
                ordId='3456', tradeId='2', side='sell', posSide='net', fillSz='4', fillPx='61000',
                fillTime=str(int((now-timedelta(seconds=1)).timestamp()*1000)), fee='-0.01', feeCcy='USDT')
        rows = [deepcopy(self.first_close_fill)]
        if flat:
            rows.append(dict(self.first_close_fill, tradeId='3', fillSz='6',
                             fillTime=str(int(now.timestamp()*1000))))
        filled, net = ('10', '0') if flat else ('4', '6')
        order = dict(prepared.materialization.body, instType='SWAP', ordId='3456',
                     state='filled' if flat else 'partially_filled', accFillSz=filled, avgPx='61000')
        self.append(dict(code='0', data=[order]), dict(code='0', data=rows),
                    self.position.response(pos=net, posId='5678', avgPx='0' if flat else '60000'))
        result = self.service.reconcile(prepared.canonical_request.order_request_id, expected_revision=self.fixture.revision)
        self.test.assertEqual('ORDER_OBSERVED', result.status)
        metadata, proof = self.fresh()
        native = self.service.read_position(metadata=metadata, proof=proof, expected_revision=self.fixture.revision,
                                            expected_provider_position_id='5678')
        self.service.project_close_position(prepared.canonical_request.order_request_id, native,
            metadata=metadata, proof=proof, expected_revision=self.fixture.revision)
        return self.assert_binding()


class TradingProtectedCloseV02Tests(unittest.TestCase):
    def test_full_entry_actual_protection_partial_and_same_position_flat_keep_complete_original_graph(self):
        context = GenuineProtectedCloseContext(self).protect()
        partial = context.close_readback(flat=False)
        self.assertEqual('0.0006', partial.current_position_projection.payload['actual_quantity'])
        self.assertEqual('EXIT_REQUESTED', partial.current_position_projection.payload['lifecycle_state'])
        flat = context.close_readback(flat=True)
        self.assertEqual(Decimal(0), Decimal(flat.current_position_projection.payload['actual_quantity']))
        self.assertEqual('EXIT_REQUESTED', flat.current_position_projection.payload['lifecycle_state'])
        self.assertEqual(context.positive_source['opened_at'], flat.current_position_projection.payload['opened_at'])
        self.assertIn(context.positive_source, [item.payload for item in flat.lifecycle_history])
        self.assertEqual(context.original_positive,
            context.service.dispatch.latest_position_publication('fixture-run', context.entry_operation))
        results = {row.payload['order_request_id']: row.payload for row in flat.current_order_results}
        self.assertEqual('FILLED', results[context.entry_operation]['order_status'])
        self.assertEqual('FILLED', results[context.close.canonical_request.order_request_id]['order_status'])
        self.assertEqual('OPEN', results[context.stop.canonical_request.order_request_id]['order_status'],
                         'Explicit zero does not cancel the unused stop')
        self.assertEqual(3, len(flat.order_requests))
        self.assertEqual(3, len(flat.fills))
        self.assertIsNone(flat.trade_result)
        self.assertEqual((), flat.funding_evidence)
        self.assertEqual(context.provider_identity, id(context.service.provider))
        posts = [row for row in context.provider.calls if row['method'] == 'POST']
        self.assertEqual(3, len(posts))
        self.assertEqual(['/api/v5/trade/order', '/api/v5/trade/order-algo', '/api/v5/trade/order'],
                         [row['path'] for row in posts])
        self.assertTrue(posts[-1]['body']['reduceOnly'])
        self.assertFalse(context.provider._responses, 'Every scripted observation must be consumed by actual owners')
