import tempfile
import unittest
from pathlib import Path
from datetime import timedelta

import tests.storage.test_product_dispatch_v02 as dispatch_fixtures
import tests.brokers.test_okx_product_translation_v02 as order_fixtures
import tests.storage.test_paper_runtime_durability as canonical_fixtures
import tests.execution.test_gateway as gateway_fixtures
from brokers.paper_state import encode_fact
from brokers.okx_product_readback import parse_product_ack
from storage.runtime import open_paper_runtime_journal


class ProductPublicationV02Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = dispatch_fixtures.ProductDispatchV02Tests(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.journal, self.lease = self.fixture.initialized()
        self.now = self.fixture.now
        helper = order_fixtures.OKXProductTranslationV02Tests(methodName='runTest')
        helper.setUp()
        self.prepared = helper.entry()
        request = self.fixture.request(self.prepared.materialization.provider_cl_ord_id)
        request['body'] = dict(self.prepared.materialization.body)
        self.journal.prepare('run', 'op', request, lease=self.lease, now=self.now)
        self.journal.claim_dispatch('run', 'op', lease=self.lease, now=self.now)
        self.ack = dict(status='ACK_PENDING', provider_id='1234', reason_code='PROVIDER_ACK_PENDING')
        result = parse_product_ack(dict(code='0', data=[dict(ordId='1234', sCode='0', clOrdId=request['native_client_id'])]),
                                   self.prepared, observed_at=helper.now)
        self.effects = [dict(kind='ORDER_RESULT', payload=encode_fact(result))]

    def observe(self, **changes):
        arguments = dict(lease=self.lease, now=self.now, canonical_effects=self.effects)
        arguments.update(changes)
        self.journal.observe('run', 'op', self.ack, **arguments)

    def test_observation_and_exact_pending_canonical_bundle_survive_reopen(self):
        self.observe()
        pending = self.journal.pending_publications('run')
        self.assertEqual(1, len(pending))
        self.assertEqual(self.effects, pending[0].effects)
        self.journal.close()
        with self.fixture.open(self.fixture.path) as recovered:
            retained = recovered.pending_publications('run')
            self.assertEqual(pending, retained)
            lease = recovered.begin_process('run', 'pid:2', expected_generation=1, now=self.now)
            recovered.mark_publication(retained[0], lease=lease, now=self.now)
            self.assertEqual((), recovered.pending_publications('run'))
            self.assertFalse(recovered.claim_dispatch('run', 'op', lease=lease, now=self.now))

    def test_partial_canonical_publication_can_replay_exact_facts_without_new_effect(self):
        self.observe()
        batch = self.journal.pending_publications('run')[0]
        plan = gateway_fixtures._approved_plan(self.prepared.prepared_at)
        risk = canonical_fixtures.risk_decision()
        risk.update(risk_decision_id=plan['risk_decision_id'], intent_id=plan['intent_id'],
                    strategy_id=plan['strategy_id'], strategy_version=plan['strategy_version'],
                    risk_policy_version=plan['risk_policy_version'], approved_quantity=plan['quantity'])
        with open_paper_runtime_journal(self.fixture.path.parent / 'canonical.sqlite') as canonical:
            canonical.persist_risk_decision(risk)
            canonical.persist_approved_trade_plan(plan)
            canonical.persist_order_request(encode_fact(self.prepared.canonical_request))
            first = canonical.publish_canonical_effects(batch.effects)
            replay = canonical.publish_canonical_effects(batch.effects)
            self.assertEqual(first, replay)
            self.journal.mark_publication(batch, lease=self.lease, now=self.now)
            self.journal.mark_publication(batch, lease=self.lease, now=self.now)
            self.assertEqual((), self.journal.pending_publications('run'))

    def test_bundle_mutation_private_payload_and_old_process_receipt_are_rejected(self):
        from dataclasses import replace
        for effects in ([dict(kind='__dict__', payload={})],
                        [dict(kind='ORDER_RESULT', payload=dict(self.effects[0]['payload'], secret='private'))],
                        [dict(kind='ORDER_RESULT', payload=dict(self.effects[0]['payload'], reject_reason='private message'))]):
            with self.subTest(effects=effects), self.assertRaises(ValueError):
                self.observe(canonical_effects=effects)
        self.assertEqual('DISPATCHING', self.journal.operation('run', 'op').status)
        self.observe()
        batch = self.journal.pending_publications('run')[0]
        with self.assertRaises(ValueError):
            self.journal.mark_publication(replace(batch, effects_json='[]'), lease=self.lease, now=self.now)
        with self.assertRaises(ValueError):
            self.observe(canonical_effects=[])
        self.journal.begin_process('run', 'pid:2', expected_generation=1, now=self.now)
        with self.assertRaises(ValueError):
            self.journal.mark_publication(batch, lease=self.lease, now=self.now)

    def test_modern_outbox_cannot_publish_another_request_or_provider_identity(self):
        from brokers.okx_product_state import durable_product_intent, restore_product_readback
        helper=order_fixtures.OKXProductTranslationV02Tests(methodName='runTest'); helper.setUp()
        prepared=helper.entry(); intent=durable_product_intent(prepared)
        restored=restore_product_readback(intent)
        with self.assertRaises(ValueError): helper.translator.require(restored, now=helper.now)
        op=prepared.canonical_request.order_request_id
        with self.fixture.open(self.fixture.path.parent/'modern.sqlite') as writer:
            writer.ensure_run('modern', self.fixture.owner, now=self.now)
            lease=writer.begin_process('modern','pid:modern',expected_generation=0,now=self.now)
            writer.prepare('modern',op,intent,lease=lease,now=self.now)
            writer.claim_dispatch('modern',op,lease=lease,now=self.now)
            for effects in ([dict(kind='ORDER_REQUEST',payload=dict(intent['canonical_request'],quantity='0.020'))],
                            [dict(kind='ORDER_RESULT',payload=dict(self.effects[0]['payload'],broker_order_id='999'))],
                            [dict(kind='ORDER_RESULT',payload=dict(self.effects[0]['payload'],client_order_id='other'))]):
                with self.subTest(effects=effects),self.assertRaises(ValueError):
                    writer.observe('modern',op,self.ack,lease=lease,now=self.now,canonical_effects=effects)
            self.assertEqual('DISPATCHING',writer.operation('modern',op).status)
            writer.observe('modern',op,self.ack,lease=lease,now=self.now,canonical_effects=self.effects)
            self.assertEqual(1,len(writer.pending_publications('modern')))


if __name__ == '__main__':
    unittest.main()
