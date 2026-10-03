import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from tempfile import TemporaryDirectory
from pathlib import Path

import tests.brokers.test_okx_demo_adapter as entry_fixtures
import tests.execution.test_gateway as gateway_fixtures
import tests.brokers.test_okx_product_close_v02 as close_fixtures
import tests.storage.test_paper_runtime_durability as storage_fixtures
from brokers.okx_demo import OKXAccountConfigSnapshot, OKXPrerequisiteSnapshot
from brokers.okx_product_capability import OKXProductCapabilityOwner
from brokers.paper_state import encode_fact
from storage.runtime import open_paper_runtime_journal


class OKXProductTranslationV02Tests(unittest.TestCase):
    def setUp(self):
        from brokers.okx_product import OKXProductTranslator
        self.capabilities = OKXProductCapabilityOwner()
        self.translator = OKXProductTranslator(self.capabilities)
        self.now = entry_fixtures.NOW
        self.metadata = entry_fixtures._metadata(self.now)
        self.account = OKXAccountConfigSnapshot('2', 'net_mode', '123', '123')
        self.prerequisites = OKXPrerequisiteSnapshot(self.account, (), ())

    def entry(self, **changes):
        proof = self.capabilities.issue('ENTRY', self.account, self.metadata,
                                        observed_at=self.now, now=self.now)
        prerequisites_proof = self.capabilities.observe_entry_prerequisites(self.prerequisites, observed_at=self.now, now=self.now)
        arguments = dict(plan=gateway_fixtures._approved_plan(self.now), metadata=self.metadata,
                         prerequisites=self.prerequisites, prerequisites_proof=prerequisites_proof, proof=proof, now=self.now)
        arguments.update(changes)
        return self.translator.prepare_entry(**arguments)

    def test_entry_uses_actual_e5_gateway_and_existing_contract_sizing(self):
        prepared = self.entry()
        self.assertEqual('ENTRY', prepared.role)
        self.assertEqual('/api/v5/trade/order', prepared.path)
        self.assertEqual('10', prepared.materialization.body['sz'])
        self.assertEqual('net', prepared.materialization.body['posSide'])
        self.assertNotIn('reduceOnly', prepared.materialization.body)
        self.assertEqual(Decimal('0.010'), prepared.materialization.effective_canonical_quantity)
        self.assertIs(self.translator.require(prepared, now=self.now), prepared)

    def test_entry_requires_current_issuer_bound_position_and_pending_order_observations(self):
        proof = self.capabilities.issue('ENTRY', self.account, self.metadata, observed_at=self.now, now=self.now)
        arguments = dict(plan=gateway_fixtures._approved_plan(self.now), metadata=self.metadata,
                         prerequisites=self.prerequisites, proof=proof, now=self.now)
        with self.assertRaises(ValueError): self.translator.prepare_entry(**arguments)
        issue=getattr(self.capabilities,'observe_entry_prerequisites',None)
        self.assertTrue(callable(issue),'Missing E4 current prerequisite observation binding')
        old=issue(self.prerequisites,observed_at=self.now-timedelta(seconds=4),now=self.now)
        with self.assertRaises(ValueError):
            self.translator.prepare_entry(**dict(arguments,prerequisites_proof=old,now=self.now+timedelta(seconds=2)))
        current=issue(self.prerequisites,observed_at=self.now,now=self.now)
        for copied in (replace(current),dict(status='PASS'),True):
            with self.subTest(copied=copied),self.assertRaises(ValueError):
                self.translator.prepare_entry(**dict(arguments,prerequisites_proof=copied))

    def test_existing_exposure_pending_orders_and_non_e5_plan_block_entry(self):
        for prerequisite in (
            replace(self.prerequisites, positions=(entry_fixtures.OKXPositionFact('BTC-USDT-SWAP', 'isolated', 'net', Decimal('1')),)),
            replace(self.prerequisites, pending_orders=(entry_fixtures.OKXPendingOrderFact('BTC-USDT-SWAP', '1', 'a', 'live'),)),
        ):
            with self.assertRaises(ValueError):
                self.entry(prerequisites=prerequisite)
        with self.assertRaises(ValueError):
            self.entry(plan={'intent_id': 'strategy-intent', 'quantity': '99'})

    def test_copy_mutation_expiry_and_cross_translator_cannot_reuse_preparation(self):
        from brokers.okx_product import OKXProductTranslator, OKXProductError
        prepared = self.entry()
        for bad in (replace(prepared), True, {'state': 'PASS'}):
            with self.assertRaises(OKXProductError):
                self.translator.require(bad, now=self.now)
        with self.assertRaises(OKXProductError):
            OKXProductTranslator(self.capabilities).require(prepared, now=self.now)
        with self.assertRaises(OKXProductError):
            self.translator.require(prepared, now=self.now + timedelta(seconds=2))
        with self.assertRaises(ValueError):
            self.translator.require(prepared, now=self.now.replace(tzinfo=None))
        with self.assertRaises(TypeError):
            prepared.materialization.body['sz'] = '1000'
        object.__setattr__(prepared.materialization, 'provider_contract_quantity', Decimal('1000'))
        with self.assertRaises(OKXProductError):
            self.translator.require(prepared, now=self.now)

    def test_close_uses_current_e5_authority_and_shared_v02_cap_without_enlargement(self):
        fixture = close_fixtures.OKXProductCloseV02Tests(methodName='runTest')
        fixture.setUp()
        self.translator.capabilities = fixture.owner
        for emergency in (False, True):
            position = fixture.fixture.position(lifecycle='EMERGENCY' if emergency else 'OPEN_PROTECTED')
            value = fixture.fixture.sizing_input(source_position=position, action=fixture.fixture.action(emergency=emergency),
                                                 applicability=fixture.fixture.applicability(role='EMERGENCY_EXIT' if emergency else 'POSITION_EXIT', close_max='10'))
            value, proof = fixture.prepared(value, 'EMERGENCY_EXIT' if emergency else 'POSITION_EXIT')
            prepared = self.translator.prepare_close(value, fixture.binding_fixture.binding(value), proof,
                                                      now=value.evaluated_at)
            self.assertIs(prepared.materialization.body['reduceOnly'], True)
            self.assertEqual('10', prepared.materialization.body['sz'])
            self.assertEqual(Decimal('0.0010'), prepared.materialization.effective_canonical_quantity)
            self.assertEqual('sell', prepared.materialization.body['side'])
            self.translator.require(prepared, now=value.evaluated_at)

    def publish_canonical_ack(self, prepared, plan, action=None):
        from brokers.okx_product_readback import parse_product_ack
        risk = storage_fixtures.risk_decision()
        risk.update(risk_decision_id=plan['risk_decision_id'], intent_id=plan['intent_id'],
                    strategy_id=plan['strategy_id'], strategy_version=plan['strategy_version'],
                    risk_policy_version=plan['risk_policy_version'], approved_quantity=plan['quantity'])
        response = dict(code='0', data=[dict(clOrdId=prepared.materialization.provider_cl_ord_id, ordId='1234', sCode='0')])
        result = parse_product_ack(response, prepared, observed_at=prepared.prepared_at)
        with TemporaryDirectory() as root, open_paper_runtime_journal(Path(root) / 'canonical.sqlite') as journal:
            journal.persist_risk_decision(risk)
            journal.persist_approved_trade_plan(plan)
            if action is not None:
                journal.persist_position_action(action)
            journal.persist_order_request(encode_fact(prepared.canonical_request))
            stored = journal.persist_order_result(encode_fact(result))
            self.assertEqual(prepared.materialization.effective_canonical_quantity, Decimal(stored.payload['requested_quantity']))

    def test_entry_quantization_and_close_cap_publish_exact_effective_quantity_to_actual_e6(self):
        plan = gateway_fixtures._approved_plan(self.now)
        plan['quantity'] = '0.0105'
        prepared = self.entry(plan=plan)
        self.publish_canonical_ack(prepared, plan)
        self.assertEqual(Decimal('0.010'), prepared.canonical_request.quantity)
        self.assertEqual(Decimal('0.0105'), prepared.materialization.canonical_approved_quantity)
        self.assertEqual('0.0105', plan['quantity'])
        fixture = close_fixtures.OKXProductCloseV02Tests(methodName='runTest')
        fixture.setUp()
        from brokers.okx_product import OKXProductTranslator
        translator = OKXProductTranslator(fixture.owner)
        value, proof = fixture.prepared(fixture.fixture.sizing_input(applicability=fixture.fixture.applicability(close_max='10')))
        prepared = translator.prepare_close(value, fixture.binding_fixture.binding(value), proof, now=value.evaluated_at)
        self.publish_canonical_ack(prepared, value.parent_plan, value.action)
        self.assertEqual(Decimal('0.0010'), prepared.canonical_request.quantity)
        self.assertEqual(Decimal('0.0012'), prepared.materialization.canonical_approved_quantity)


if __name__ == '__main__':
    unittest.main()
