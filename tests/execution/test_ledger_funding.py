"""E4 source units only. Scripted local pages are not native owner proof."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from decimal import localcontext, ROUND_DOWN
import importlib
import unittest


class AllocatedLedgerFundingTests(unittest.TestCase):
    def setUp(self):
        self.api=importlib.import_module('execution.ledger_funding')
        self.plan=dict(schema_version='contracts-v0.1',trade_plan_id='plan-ledger',symbol='BTC_USDT_PERP')
        self.position=dict(schema_version='contracts-v0.1',position_id='position-ledger',symbol='BTC_USDT_PERP',
            actual_quantity='0',reconciliation_status='CONSISTENT',opened_at='2026-08-24T05:05:00Z',
            broker_state_observed_at='2026-08-24T05:15:00Z')
        self.subject=self.api.FundingLedgerSubject('plan-ledger','position-ledger','BTC_USDT_PERP',
            'sha256:'+'a'*64,'fixture-provider','native-fixture-5678',self.position['opened_at'],
            self.position['broker_state_observed_at'])
        self.started=datetime(2026,8,24,5,15,1,tzinfo=timezone.utc)
        self.received=datetime(2026,8,24,5,15,2,tzinfo=timezone.utc)

    def row(self,record_id='row-1',cost='0.125',when='2026-08-24T05:10:00Z',**changes):
        from dataclasses import asdict
        value=dict(record_id=record_id,event_time=when,funding_cost=cost,cost_currency='USDT',
            allocation={k:v for k,v in asdict(self.subject).items() if k not in ('interval_start','interval_end')})
        value.update(changes);return value

    def page(self,rows=None,**changes):
        from dataclasses import asdict
        value=dict(profile=self.api.FIXTURE_WIRE_PROFILE,snapshot_id='fixture-snapshot-1',
            snapshot_at='2026-08-24T05:15:00Z',subject=asdict(self.subject),
            coverage_start=self.subject.interval_start,complete_through=self.subject.interval_end,
            page_index=0,cursor=None,next_cursor=None,records=[] if rows is None else rows)
        value.update(changes);return value

    def read(self,pages,*,source=None,subject=None):
        self.calls=[];pending=iter(deepcopy(pages))
        def read_page(query):
            self.calls.append(query);return next(pending)
        if source is None:source=self.api.FixtureFundingLedgerSource(read_page)
        observation=source.read_interval(self.subject if subject is None else subject,request_started_at=self.started,received_at=self.received)
        return source,observation

    def produce(self,pages,**changes):
        source,observed=self.read(pages)
        kwargs=dict(calculated_at=self.received,source=source);kwargs.update(changes)
        return self.api.produce_broker_ledger_funding_evidence(self.plan,self.position,observed,**kwargs)

    def test_signed_costs_zero_records_and_complete_empty_have_distinct_meaning(self):
        for rows,cost,count,status in (([self.row(),self.row('credit','-0.025')],'0.1',2,'INCLUDED'),
                ([self.row(cost='-0.025')],'-0.025',1,'INCLUDED'),([self.row(cost='0')],'0',1,'INCLUDED'),
                ([self.row(cost='0.125'),self.row('credit','-0.125')],'0',2,'INCLUDED'),([], '0',0,'ZERO_CONFIRMED')):
            with self.subTest(cost=cost,count=count,status=status):
                evidence=self.produce([self.page(rows)])
                self.assertEqual((evidence['funding_cost'],evidence['source_record_count'],evidence['status']),(cost,count,status))
                self.assertEqual(evidence['source_kind'],'BROKER_LEDGER')
                self.assertEqual(evidence['source'],self.api.FIXTURE_SOURCE)
                self.assertEqual(evidence['source_version'],self.api.FIXTURE_SOURCE_VERSION)
                self.assertNotIn('account_hash',evidence);self.assertNotIn('native_position_id',evidence)
                self.assertRegex(evidence['source_material_hash'],r'^[0-9a-f]{64}$')

    def test_half_open_boundaries_and_stable_identity_ignore_calculation_clock(self):
        rows=[self.row('end','900',self.subject.interval_end),self.row('start','0.125',self.subject.interval_start)]
        source,observation=self.read([self.page(rows)])
        first=self.api.produce_broker_ledger_funding_evidence(self.plan,self.position,observation,source=source,calculated_at=self.received)
        later=self.api.produce_broker_ledger_funding_evidence(self.plan,self.position,observation,source=source,calculated_at='2026-08-24T06:00:00Z')
        self.assertEqual((first['funding_cost'],first['source_record_count']),('0.125',1))
        self.assertEqual(first['funding_evidence_id'],later['funding_evidence_id'])
        changed=self.produce([self.page([self.row(cost='0.126')])])
        self.assertNotEqual(first['funding_evidence_id'],changed['funding_evidence_id'])

    def test_actual_page_chain_is_read_and_every_page_is_bound(self):
        pages=[self.page([self.row()],next_cursor='page-two'),
            self.page([self.row('credit','-0.025')],page_index=1,cursor='page-two')]
        source,observation=self.read(pages)
        self.assertEqual([c['cursor'] for c in self.calls],[None,'page-two'])
        self.assertTrue(all(c['subject']['account_hash']==self.subject.account_hash for c in self.calls))
        evidence=self.api.produce_broker_ledger_funding_evidence(self.plan,self.position,observation,source=source,calculated_at=self.received)
        self.assertEqual(evidence['funding_cost'],'0.1')
        pages[1]['snapshot_id']='another-snapshot'
        with self.assertRaises(ValueError):self.read(pages)

    def test_missing_page_gap_unresolved_cursor_and_stale_watermark_never_emit_zero(self):
        invalid=([
            self.page(next_cursor='absent')], [self.page(coverage_start='2026-08-24T05:06:00Z')],
            [self.page(complete_through='2026-08-24T05:14:59Z')],
            [self.page(page_index=1)], [self.page(cursor='unsolicited')],
            [self.page(snapshot_at='2026-08-24T05:14:59Z')],
            [self.page(snapshot_at='2026-08-24T05:15:03Z')],
            [self.page(next_cursor='loop'),self.page(page_index=1,cursor='loop',next_cursor='loop')])
        for pages in invalid:
            with self.subTest(pages=pages),self.assertRaises(ValueError):self.read(pages)

    def test_malformed_duplicate_foreign_scope_currency_and_event_coverage_refuse(self):
        foreign=deepcopy(self.row());foreign['allocation']['native_position_id']='other-position'
        invalid=([self.row(),self.row()], [self.row(),self.row(cost='9')], [foreign],
            [self.row(cost_currency='BTC')], [self.row(when='2026-08-24T05:04:59Z')],
            [self.row(when='2026-08-24T05:15:01Z')], [dict(self.row(),unknown=True)],
            [self.row(cost=True)],[self.row(cost='NaN')],[self.row(cost='1e-2')],
            [self.row(cost='9'*129)],[self.row(cost=' 1')],[self.row(record_id='')])
        for rows in invalid:
            with self.subTest(rows=rows),self.assertRaises(ValueError):self.read([self.page(rows)])

    def test_typed_source_issuance_cannot_be_copied_or_used_by_another_source(self):
        source,observed=self.read([self.page([self.row()])])
        other=self.api.FixtureFundingLedgerSource(lambda query:self.page())
        for issuer,value in ((source,replace(observed)),(other,observed),(source,{})):
            with self.subTest(issuer=issuer,value=type(value)),self.assertRaises(ValueError):
                self.api.produce_broker_ledger_funding_evidence(self.plan,self.position,value,source=issuer,calculated_at=self.received)

    def test_exact_plan_position_interval_and_calculation_time_are_required(self):
        source,observed=self.read([self.page()])
        for plan,position,clock in ((dict(self.plan,trade_plan_id='other'),self.position,self.received),
                (self.plan,dict(self.position,position_id='other'),self.received),
                (self.plan,dict(self.position,actual_quantity='1'),self.received),
                (self.plan,dict(self.position,broker_state_observed_at='2026-08-24T05:14:00Z'),self.received),
                (self.plan,self.position,'2026-08-24T05:14:59Z')):
            with self.subTest(plan=plan,position=position,clock=clock),self.assertRaises(ValueError):
                self.api.produce_broker_ledger_funding_evidence(plan,position,observed,source=source,calculated_at=clock)

    def test_aggregation_is_exact_under_hostile_ambient_context_and_input_is_detached(self):
        a='9'*60+'.'+'9'*60;b='0.'+'0'*59+'1'
        pages=[self.page([self.row(cost=a),self.row('tiny',b)])]
        source,observed=self.read(pages)
        pages[0]['records'][0]['funding_cost']='0'
        with localcontext() as ctx:
            ctx.prec=2;ctx.rounding=ROUND_DOWN
            evidence=self.api.produce_broker_ledger_funding_evidence(self.plan,self.position,observed,source=source,calculated_at=self.received)
        self.assertEqual(evidence['funding_cost'],'1'+'0'*60)

    def test_record_page_and_wire_budgets_refuse_instead_of_truncating(self):
        with self.assertRaises(ValueError):self.read([self.page([self.row(str(i)) for i in range(1001)])])
        pages=[self.page(page_index=i,cursor=None if i==0 else f'p{i}',next_cursor=f'p{i+1}') for i in range(16)]
        with self.assertRaises(ValueError):self.read(pages)
        with self.assertRaises(ValueError):self.read([self.page(snapshot_id='x'*1048577)])
        self.subject=replace(self.subject,provider_ref='p'*256,native_position_id='n'*256,symbol='S'*256)
        with self.assertRaisesRegex(ValueError,'FUNDING_LEDGER_WIRE_LIMIT'):
            self.read([self.page([self.row(str(i)) for i in range(1000)])])

    def test_unknown_page_shapes_invalid_subject_and_clock_order_fail_closed(self):
        for page in (None,[],{},dict(self.page(),unknown=True),dict(self.page(),records={}),dict(self.page(),page_index=True)):
            with self.subTest(page=type(page)),self.assertRaises(ValueError):self.read([page])
        for subject in ({},replace(self.subject,account_hash='not-hash'),replace(self.subject,interval_end=self.subject.interval_start)):
            with self.subTest(subject=type(subject)),self.assertRaises(ValueError):self.read([self.page()],subject=subject)
        source=self.api.FixtureFundingLedgerSource(lambda query:self.page())
        with self.assertRaises(ValueError):source.read_interval(self.subject,request_started_at=self.received,received_at=self.started)

    def test_receive_clock_is_sampled_once_after_pages_and_failure_issues_nothing(self):
        sequence=[]
        def reader(query):sequence.append('page');return self.page()
        def clock():sequence.append('received');return self.received
        source=self.api.FixtureFundingLedgerSource(reader)
        observed=source.read_interval(self.subject,request_started_at=self.started,received_at=clock)
        self.assertEqual(sequence,['page','received']);self.assertIs(source.require(observed),observed)
        for failing in (lambda:'2026-08-24T05:14:59Z',lambda:None):
            before=len(source._issued)
            with self.assertRaises(ValueError):source.read_interval(self.subject,request_started_at=self.started,received_at=failing)
            self.assertEqual(len(source._issued),before)
