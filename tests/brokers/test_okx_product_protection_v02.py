import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import tests.position.test_protection_registry_policy as registry_fixtures
import tests.execution.test_protection_trigger_consumer as trigger_fixtures
import tests.brokers.test_okx_demo_adapter as metadata_fixtures
from brokers.okx_demo import OKXAccountConfigSnapshot
from brokers.okx_product_capability import OKXProductCapabilityOwner
from brokers.okx_product import OKXProductTranslator
from execution.protection_trigger import prepare_trigger_validated_protection_order, require_provider_trigger_basis_compatibility
from execution.protection_registry_evidence_boundary import build_protection_registry_multiplicity_evidence
from position.protection_registry_policy import canonical_protection_registry_hash


class OKXProductProtectionV02Tests(unittest.TestCase):
    def setUp(self):
        self.registry = registry_fixtures.ProtectionRegistryPolicyTests(methodName='runTest')
        self.registry.setUp()
        self.trigger = trigger_fixtures.ProtectionTriggerConsumerTests(methodName='runTest')
        self.trigger.setUp()
        self.owner = OKXProductCapabilityOwner()
        self.translator = OKXProductTranslator(self.owner)

    def context(self, kind='missing', *, coverage='COMPLETE', currentness='CURRENT', lifecycle='OPEN_UNPROTECTED', stop='59400.00'):
        _, authority, registry_input = self.registry._build(kind, lifecycle=lifecycle, coverage=coverage, currentness=currentness)
        now = self.registry.fixture.evaluated_at
        self.trigger.action_created_at = now - timedelta(seconds=5)
        self.trigger.action_expires_at = now + timedelta(seconds=30)
        self.trigger.evaluated_at = now - timedelta(seconds=1)
        plan = self.trigger._plan(created_at=(now - timedelta(minutes=30)).isoformat().replace('+00:00', 'Z'),
                                  expires_at=(now + timedelta(minutes=5)).isoformat().replace('+00:00', 'Z'),
                                  protection_instruction={'stop_level': stop, 'target_level': '61200', 'max_hold_seconds': 1800})
        position = authority.position
        action = self.trigger._action(position=position, plan=plan)
        market = self.trigger._market(observed_at=(now - timedelta(seconds=2)).isoformat().replace('+00:00', 'Z'),
                                      received_at=(now - timedelta(seconds=1)).isoformat().replace('+00:00', 'Z'))
        evidence = self.trigger._evidence(position=position, plan=plan, action=action, market=market)
        request = prepare_trigger_validated_protection_order(action, plan, position, evidence, market,
                    market_freshness_classification='FRESH', now=now)
        lineage = dict(registry_input.intended_protection_lineage)
        lineage.update(position_action_id=action['position_action_id'], position_action_hash=canonical_protection_registry_hash(action),
                       approved_trade_plan_hash=canonical_protection_registry_hash(plan),
                       protection_order_request_hash=canonical_protection_registry_hash(request),
                       protection_order_request_ref=request.order_request_id, trigger_validity_ref=evidence['protection_trigger_validity_id'])
        registry_evidence = build_protection_registry_multiplicity_evidence(replace(registry_input, intended_protection_lineage=lineage))
        metadata = replace(metadata_fixtures._metadata(now), ct_val=Decimal('0.0001'))
        proof = self.owner.issue('PROTECTION_STOP', OKXAccountConfigSnapshot('2', 'net_mode', '123', '123'), metadata,
                                 observed_at=now, now=now)
        return dict(action=action, plan=plan, position=position, trigger_evidence=evidence, market=market,
                    market_freshness_classification='FRESH', registry_evidence=registry_evidence,
                    registry_authority=authority, metadata=metadata, proof=proof, now=now)

    def test_initial_stop_requires_actual_e5_fp03_current_empty_fp11_and_native_last_mapping(self):
        context = self.context()
        prepared = self.translator.prepare_protection(**context)
        body = prepared.materialization.body
        self.assertEqual('/api/v5/trade/order-algo', prepared.path)
        self.assertEqual('PROTECTION_STOP', prepared.role)
        self.assertEqual('conditional', body['ordType'])
        self.assertEqual('last', body['slTriggerPxType'])
        self.assertEqual('-1', body['slOrdPx'])
        self.assertEqual('59400.00', body['slTriggerPx'])
        self.assertEqual('12', body['sz'])
        self.assertIs(body['reduceOnly'], True)
        self.translator.require(prepared, now=context['now'])
        with self.assertRaises(ValueError):
            require_provider_trigger_basis_compatibility(context['trigger_evidence'], context['proof'])

    def test_multiple_orphan_stale_incomplete_unknown_registry_cannot_create_or_cancel(self):
        for options in ({'kind': 'multiple'}, {'kind': 'intended-plus-external'}, {'kind': 'unknown'},
                        {'currentness': 'STALE'}, {'coverage': 'INCOMPLETE'}, {'coverage': 'UNKNOWN'}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.translator.prepare_protection(**self.context(**options))

    def test_wrong_action_lineage_or_newer_position_cannot_reuse_proof(self):
        context = self.context()
        context['action'] = dict(context['action'], position_action_id='other-action')
        with self.assertRaises(ValueError):
            self.translator.prepare_protection(**context)
        context = self.context()
        context['position'] = dict(context['position'], actual_quantity='0.0011')
        with self.assertRaises(ValueError):
            self.translator.prepare_protection(**context)

    def test_trigger_price_or_quantity_is_not_silently_rounded(self):
        with self.assertRaises(ValueError):
            self.translator.prepare_protection(**self.context(stop='59400.05'))
        context = self.context()
        context['metadata'] = replace(context['metadata'], lot_sz=Decimal('5'), min_sz=Decimal('5'))
        context['proof'] = self.owner.issue('PROTECTION_STOP', OKXAccountConfigSnapshot('2', 'net_mode', '123', '123'),
                            context['metadata'], observed_at=context['now'], now=context['now'])
        with self.assertRaises(ValueError):
            self.translator.prepare_protection(**context)


if __name__ == '__main__':
    unittest.main()
