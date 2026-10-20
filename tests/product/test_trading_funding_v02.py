"""Actual guarded fake ledger joined to original native partial/flat ownership."""
from copy import deepcopy
from dataclasses import asdict,replace
from datetime import timedelta
from unittest.mock import patch
import unittest

import tests.product.test_trading_close_projection_v02 as fixtures


class TradingFundingV02Tests(unittest.TestCase):
    def setUp(self):
        self.flow=fixtures.TradingCloseProjectionV02Tests(methodName='runTest');self.flow.setUp()
        self.addCleanup(self.flow.doCleanups);self.fixture=self.flow.fixture

    def flat(self):
        context,prepared=self.flow.closing()
        partial=self.flow.readback(context,prepared);self.flow.project(context,prepared,partial)
        flat=self.flow.readback(context,prepared,filled='10',net='0');self.flow.project(context,prepared,flat)
        self.fixture.clock[0]+=timedelta(seconds=1)
        return context,prepared

    def script(self,context,*,empty=False,changes=None,paginated=False):
        from application.trading.provider import FakeProductProvider
        from execution.ledger_funding import FIXTURE_WIRE_PROFILE
        from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
        service,provider,*_=context;recovered=self.flow.position.recover()
        position=recovered.current_position_projection.payload
        subject=dict(trade_plan_id=recovered.trade_plan_id,position_id=recovered.position_id,
            symbol=position['symbol'],account_hash=canonical_okx_close_sizing_hash(dict(
                provider_ref=self.fixture.release[0].provider_ref,account_ref=self.fixture.release[0].account_ref)),
            provider_ref=self.fixture.release[0].provider_ref,native_position_id='5678',
            interval_start=position['opened_at'],interval_end=position['broker_state_observed_at'])
        allocation={k:v for k,v in subject.items() if k not in ('interval_start','interval_end')}
        rows=[] if empty else [dict(record_id='cost-1',event_time=subject['interval_start'],funding_cost='0.125',cost_currency='USDT',allocation=allocation),
            dict(record_id='credit-1',event_time=subject['interval_start'],funding_cost='-0.025',cost_currency='USDT',allocation=allocation)]
        page=dict(profile=FIXTURE_WIRE_PROFILE,snapshot_id='actual-fake-ledger-snapshot',
            snapshot_at=self.fixture.clock[0].isoformat().replace('+00:00','Z'),subject=subject,
            coverage_start=subject['interval_start'],complete_through=subject['interval_end'],
            page_index=0,cursor=None,next_cursor=None,records=rows)
        if changes:page.update(changes)
        pages=[page]
        if paginated:
            page['records']=rows[:1];page['next_cursor']='page-two'
            pages.append(dict(deepcopy(page),records=rows[1:],page_index=1,cursor='page-two',next_cursor=None))
        provider._responses.extend(FakeProductProvider(pages)._responses)
        return subject

    def read(self,context):
        recovered=self.flow.position.recover()
        return context[0].read_fixture_funding_ledger(recovered.trade_plan_id,recovered.position_id,
            expected_revision=self.fixture.revision)

    def publish(self,context,value):
        return context[0].publish_fixture_funding_ledger(value,expected_revision=self.fixture.revision)

    def test_actual_partial_is_refused_then_flat_paginated_ledger_publishes_without_closing(self):
        context,prepared=self.flow.closing();service,provider,*_=context
        self.flow.project(context,prepared,self.flow.readback(context,prepared))
        before=list(provider.calls)
        with self.assertRaises(ValueError):self.read(context)
        self.assertEqual(provider.calls,before)
        self.flow.project(context,prepared,self.flow.readback(context,prepared,filled='10',net='0'))
        self.fixture.clock[0]+=timedelta(seconds=1);subject=self.script(context,paginated=True)
        value=self.read(context);published=self.publish(context,value)
        recovered=self.flow.position.recover()
        self.assertEqual(len(recovered.funding_evidence),1)
        evidence=recovered.funding_evidence[0]
        self.assertEqual(published,evidence)
        self.assertEqual((evidence.payload['funding_cost'],evidence.payload['source_record_count']),('0.1',2))
        self.assertEqual(evidence.payload['interval_end'],subject['interval_end'])
        self.assertEqual(recovered.current_position_projection.payload['lifecycle_state'],'EXIT_REQUESTED')
        self.assertIsNone(recovered.trade_result)
        calls=list(provider.calls);self.assertEqual(self.publish(context,value),published);self.assertEqual(provider.calls,calls)
        ledger=[c for c in calls if c['path']=='/r7-fixture/v1/allocated-funding']
        self.assertEqual([c['query']['cursor'] for c in ledger],[None,'page-two'])
        self.assertTrue(all(c['method']=='GET' and c['body'] is None and c['query']['subject']==subject for c in ledger))
        self.assertEqual(len([c for c in calls if c['method']=='POST']),2)

    def test_incomplete_empty_ledger_never_becomes_zero_or_closed(self):
        context,prepared=self.flat();service,provider,*_=context
        self.script(context,empty=True,changes=dict(next_cursor='missing'))
        with self.assertRaises(ValueError):self.read(context)
        recovered=self.flow.position.recover()
        self.assertEqual(recovered.funding_evidence,());self.assertIsNone(recovered.trade_result)
        self.assertEqual(recovered.current_position_projection.payload['lifecycle_state'],'EXIT_REQUESTED')

    def test_copied_replaced_provider_or_stale_observation_cannot_publish(self):
        from application.trading.provider import FakeProductProvider
        context,prepared=self.flat();service,provider,*_=context;self.script(context)
        value=self.read(context)
        with self.assertRaises(ValueError):self.publish(context,replace(value))
        service.provider=FakeProductProvider([])
        with self.assertRaises(ValueError):self.publish(context,value)
        service.provider=provider;self.fixture.clock[0]+=timedelta(seconds=6)
        with self.assertRaises(ValueError):self.publish(context,value)
        self.assertEqual(self.flow.position.recover().funding_evidence,())

    def test_canonical_write_failure_replays_after_successor_without_ledger_or_order_request(self):
        context,prepared=self.flat();service,provider,*_=context;self.script(context)
        value=self.read(context);canonical=service.canonical
        with patch.object(type(canonical),'persist_funding_evidence',side_effect=OSError('fixture write failure')):
            with self.assertRaises(OSError):self.publish(context,value)
        self.assertEqual(len(service.dispatch.pending_funding_publications(service.run_id)),1)
        self.assertEqual(self.flow.position.recover().funding_evidence,())
        calls=list(provider.calls)
        lease=service.dispatch.begin_process(service.run_id,'funding-recovery:2',expected_generation=1,now=self.fixture.clock[0])
        with self.assertRaises(ValueError):self.publish(context,value)
        service.lease=lease;service.recover_publications()
        self.assertEqual(service.dispatch.pending_funding_publications(service.run_id),())
        self.assertEqual(len(self.flow.position.recover().funding_evidence),1)
        self.assertEqual(provider.calls,calls)
        self.assertIsNone(self.flow.position.recover().trade_result)

    def test_claim_appended_at_actual_outbox_writer_fence_blocks_publication(self):
        from storage.product_dispatch import open_product_dispatch_journal
        context,prepared=self.flat();service,provider,*_=context;self.script(context)
        value=self.read(context)
        decision=service.admission.evaluate(service.identity,expected_revision=self.fixture.revision,
            permission='MANAGE_EXISTING',execution=service.execution)
        original=service.dispatch.observe_funding
        def append_then_write(*args,**kwargs):
            with open_product_dispatch_journal(self.fixture.root/'dispatch.sqlite') as writer:
                writer.ensure_run('other-ledger',decision.owner_permission,now=self.fixture.clock[0])
                lease=writer.begin_process('other-ledger','other-ledger:1',expected_generation=0,now=self.fixture.clock[0])
                unknown=dict(role='ENTRY',path='/api/v5/trade/order',native_client_id='OTHERLEDGER',
                    body=dict(instId='BTC-USDT-SWAP',tdMode='isolated',posSide='net',side='buy',ordType='market',sz='10',clOrdId='OTHERLEDGER'),
                    canonical_request_hash='sha256:'+'1'*64,authority_hash='sha256:'+'2'*64)
                writer.prepare('other-ledger','other-ledger-op',unknown,lease=lease,now=self.fixture.clock[0])
                writer.claim_dispatch('other-ledger','other-ledger-op',lease=lease,now=self.fixture.clock[0])
            return original(*args,**kwargs)
        with patch.object(service.dispatch,'observe_funding',side_effect=append_then_write):
            with self.assertRaises(ValueError):self.publish(context,value)
        self.assertEqual(self.flow.position.recover().funding_evidence,())
        self.assertEqual(service.dispatch.pending_funding_publications(service.run_id),())

    def test_actual_foreign_scope_and_production_composition_refuse(self):
        context,prepared=self.flat();service,provider,*_=context
        subject=self.script(context);provider._responses[0]['subject']['native_position_id']='other-position'
        with self.assertRaises(ValueError):self.read(context)
        self.assertEqual(self.flow.position.recover().funding_evidence,())
        service.execution='PRODUCTION';before=list(provider.calls)
        with self.assertRaises(ValueError):self.read(context)
        self.assertEqual(provider.calls,before)

    def test_insert_or_replace_cannot_rewrite_original_funding_outbox_or_receipt(self):
        import sqlite3
        context,prepared=self.flat();service,*_=context;self.script(context)
        self.publish(context,self.read(context));connection=service.dispatch._db
        connection.execute('PRAGMA recursive_triggers=OFF')
        for table in ('product_dispatch_funding_outbox','product_dispatch_funding_publications'):
            original=connection.execute(f'SELECT * FROM {table}').fetchone()
            with self.subTest(table=table),self.assertRaises(sqlite3.IntegrityError):
                connection.execute(f'INSERT OR REPLACE INTO {table} VALUES('+','.join('?' for _ in original)+')',tuple(original))
            connection.rollback()
            self.assertEqual(tuple(connection.execute(f'SELECT * FROM {table}').fetchone()),tuple(original))

    def test_damaged_pending_source_hash_or_original_link_blocks_recovery_before_canonical_write(self):
        import json
        from registry.product_assessment import canonical,digest
        context,prepared=self.flat();service,provider,*_=context;self.script(context)
        value=self.read(context)
        with patch.object(type(service.canonical),'persist_funding_evidence',side_effect=OSError('fixture write failure')):
            with self.assertRaises(OSError):self.publish(context,value)
        connection=service.dispatch._db
        row=connection.execute('SELECT * FROM product_dispatch_funding_outbox').fetchone();original=dict(row)
        trigger=connection.execute("SELECT sql FROM sqlite_master WHERE name='product_dispatch_funding_outbox_no_update'").fetchone()[0]
        cases=[]
        source=json.loads(original['observation_json']);source['source_material']['snapshot_id']='damaged-source'
        cases.append((canonical(source),digest(canonical(source))))
        link=json.loads(original['observation_json']);link['entry_operation_id']='wrong-original-entry'
        cases.extend([(canonical(link),digest(canonical(link))),('{}',original['observation_hash'])])
        calls=list(provider.calls)
        for raw,hashed in cases:
            connection.execute('DROP TRIGGER product_dispatch_funding_outbox_no_update')
            connection.execute('UPDATE product_dispatch_funding_outbox SET observation_json=?,observation_hash=?',(raw,hashed))
            connection.execute(trigger);connection.commit()
            try:
                with self.subTest(source_hash=hashed),self.assertRaises(ValueError):service.recover_publications()
                self.assertEqual(self.flow.position.recover().funding_evidence,())
                self.assertEqual(connection.execute('SELECT count(*) FROM product_dispatch_funding_publications').fetchone()[0],0)
            finally:
                connection.execute('DROP TRIGGER product_dispatch_funding_outbox_no_update')
                connection.execute('UPDATE product_dispatch_funding_outbox SET observation_json=?,observation_hash=?',
                    (original['observation_json'],original['observation_hash']))
                connection.execute(trigger);connection.commit()
        service.recover_publications()
        self.assertEqual(len(self.flow.position.recover().funding_evidence),1);self.assertEqual(provider.calls,calls)
