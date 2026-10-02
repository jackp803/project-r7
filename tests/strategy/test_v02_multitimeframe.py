from dataclasses import replace
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import importlib.util
import unittest

from strategy import StrategyRuntime,compute_content_hash,parse_strategy_definition
from tests.indicators.v02_fixtures import bars
from tests.strategy.v02_fixtures import definition_v02,field,operator


def utc(hour,minute=0): return datetime(2026,10,2,hour,minute,tzinfo=timezone.utc)


def received(rows): return tuple(replace(row,received_at=row.close_time,symbol='BTC_USDT_PERP') for row in rows)


def multi_definition():
    value=definition_v02()
    value['required_timeframes']=['15m','4h']
    value['rules']['evaluation_timeframe']='15m'
    value['rules']['features']['trend']['parameters']['window']=1
    value['rules']['long']=operator('GT',field('close','15m'),{'kind':'feature','name':'trend'})
    value['rules']['short']=operator('LT',field('close','15m'),{'kind':'feature','name':'trend'})
    value['content_hash']=compute_content_hash(value)
    return parse_strategy_definition(value)


class AsOfTests(unittest.TestCase):
    def test_visible_out_of_profile_financial_input_returns_structured_boundary_error(self):
        api=self.api()
        from strategy.runtime import MarketBoundaryError
        number=Decimal('12345678901234567890123456789012345')
        row=received(bars([1]))[0]
        row=replace(row,open=number,high=number,low=number,close=number)
        with self.assertRaises(MarketBoundaryError) as caught:
            api.build_asof_bundle({'1h':(row,)},utc(1),utc(1))
        self.assertEqual('INVALID_DECIMAL_INPUT',caught.exception.code)

    def test_direct_bundle_cannot_bypass_finality_availability_or_immutability(self):
        api=self.api()
        rows=received(bars([1,2,3]))
        source={'1h':(*rows[:-1],replace(rows[-1],is_closed=False))}
        bundle=api.AsOfBundle(source,utc(3),utc(3),'recorded_received_at')
        self.assertEqual(utc(2),bundle.visible('1h')[-1].close_time)
        source['1h']=rows
        self.assertEqual(utc(2),bundle.visible('1h')[-1].close_time)
        with self.assertRaises(ValueError):
            api.AsOfBundle({'1h':bars([1,2])},utc(2),utc(2),'recorded_received_at')

    def test_real_v02_nested_indicator_warmup_conflict_and_bad_data(self):
        api=self.api()
        value=definition_v02()
        value['rules']['features']['trend']['source']={'kind':'indicator','name':'SMA','semantic_version':'r7-sma-v1',
                          'source':field(),'parameters':{'window':2},'output':'value'}
        value['content_hash']=compute_content_hash(value)
        parsed=parse_strategy_definition(value)
        rows=received(bars([1,3,5],timeframe='4h'))
        warm=StrategyRuntime().evaluate(parsed,api.build_asof_bundle({'4h':rows[:2]},utc(8),utc(8)),utc(8))
        self.assertEqual(['INSUFFICIENT_HISTORY'],warm['reason_codes'])
        final=StrategyRuntime().evaluate(parsed,api.build_asof_bundle({'4h':rows},utc(12),utc(12)),utc(12))
        self.assertEqual('LONG',final['direction'])
        value['rules']['short']=value['rules']['long']
        value['content_hash']=compute_content_hash(value)
        conflict=StrategyRuntime().evaluate(parse_strategy_definition(value),api.build_asof_bundle({'4h':rows},utc(12),utc(12)),utc(12))
        self.assertEqual('NO_TRADE',conflict['direction'])
        self.assertEqual(['CONFLICTING_ENTRY_RULES'],conflict['reason_codes'])

    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('strategy.v02.temporal'),'As-of E2 adapter missing')
        from strategy.v02 import temporal
        return temporal

    def source(self):
        return {'4h':received(bars([80,90,200,300],timeframe='4h')),
                '15m':received(bars([100]*49,timeframe='15m'))}

    def test_1145_uses_0400_0800_bar_not_unfinished_0800_1200(self):
        api=self.api()
        bundle=api.build_asof_bundle(self.source(),utc(11,45),utc(11,45))
        self.assertEqual(utc(8),bundle.candles_by_timeframe['4h'][-1].close_time)
        signal=StrategyRuntime().evaluate(multi_definition(),bundle,utc(11,45))
        self.assertEqual('LONG',signal['direction'])
        self.assertEqual('100',signal['reference_price'])

    def test_1200_requires_finality_and_actual_receipt(self):
        api=self.api()
        source=self.source()
        latest=source['4h'][2]
        source['4h']=(*source['4h'][:2],replace(latest,received_at=utc(12)+timedelta(seconds=5)),source['4h'][3])
        early=api.build_asof_bundle(source,utc(12),utc(12))
        late=api.build_asof_bundle(source,utc(12),utc(12)+timedelta(seconds=5))
        self.assertEqual(utc(8),early.candles_by_timeframe['4h'][-1].close_time)
        self.assertEqual(utc(12),late.candles_by_timeframe['4h'][-1].close_time)
        self.assertEqual('LONG',StrategyRuntime().evaluate(multi_definition(),early,utc(12))['direction'])
        self.assertEqual('SHORT',StrategyRuntime().evaluate(multi_definition(),late,utc(12))['direction'])
        source['4h']=(*source['4h'][:2],replace(latest,is_closed=False),source['4h'][3])
        pending=api.build_asof_bundle(source,utc(12),utc(12))
        self.assertEqual(utc(8),pending.candles_by_timeframe['4h'][-1].close_time)

    def test_all_future_bars_and_receipts_cannot_change_earlier_signal_or_boundary_hash(self):
        api=self.api()
        source=self.source()
        first=StrategyRuntime().evaluate(multi_definition(),api.build_asof_bundle(source,utc(11,45),utc(11,45)),utc(11,45))
        changed={}
        for timeframe,rows in source.items():
            changed[timeframe]=tuple(replace(row,open=Decimal('10000'),high=Decimal('10002'),low=Decimal('9998'),
                                           close=Decimal('10000'),received_at=utc(23)) if row.close_time>utc(11,45) else row for row in rows)
        second=StrategyRuntime().evaluate(multi_definition(),api.build_asof_bundle(changed,utc(11,45),utc(11,45)),utc(11,45))
        self.assertEqual(first,second)

    def test_missing_receipt_requires_explicit_historical_assumption(self):
        api=self.api()
        source={'1h':bars([1,2,3])}
        with self.assertRaises(ValueError): api.build_asof_bundle(source,utc(3),utc(3))
        bundle=api.build_asof_bundle(source,utc(3),utc(3),availability_model='historical_close_assumption')
        self.assertEqual('historical_close_assumption',bundle.availability_model)

    def test_visible_gap_and_duplicate_are_rejected_without_stitching(self):
        api=self.api()
        rows=received(bars([1,2,3]))
        for malformed in ((rows[0],rows[2]),(rows[0],rows[0],rows[1])):
            with self.subTest(rows=malformed):
                with self.assertRaises(ValueError): api.build_asof_bundle({'1h':malformed},utc(3),utc(3))

    def test_aggregation_requires_every_finalized_constituent(self):
        self.assertIsNotNone(importlib.util.find_spec('market_data.aggregation'),'Canonical aggregation missing')
        from market_data.aggregation import aggregate_complete
        rows=received(bars(range(16),timeframe='15m'))
        result=aggregate_complete(rows,'4h')
        self.assertEqual(1,len(result))
        self.assertEqual(utc(4),result[0].close_time)
        self.assertEqual(Decimal('1600'),result[0].volume)
        self.assertEqual(Decimal('0'),result[0].open)
        self.assertEqual(Decimal('15'),result[0].close)
        self.assertEqual(utc(4),result[0].received_at)
        for invalid in (rows[:-1],(rows[0],*rows[2:]),(*rows[:-1],replace(rows[-1],is_closed=False))):
            with self.assertRaises(ValueError): aggregate_complete(invalid,'4h')

