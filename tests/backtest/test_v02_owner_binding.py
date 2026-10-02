from datetime import timedelta
from decimal import Decimal
from tempfile import TemporaryDirectory
import unittest

from backtest.e2_runtime import project_e2_runtime_binding
from backtest.replay import DatasetDescriptor,HistoricalReplayEngine,ReplayConfig
from backtest.costs import FeeModel,SlippageModel
from strategy import compute_content_hash,parse_strategy_definition
from tests.application.dataset_fixtures import dataset,START
from tests.strategy.v02_fixtures import definition_v02,field,operator

def strategy():
    value=definition_v02(); value['required_timeframes']=['1h']; value['rules']['evaluation_timeframe']='1h'
    value['rules']['features']['trend']['source']=field('close','1h')
    value['rules']['long']=operator('GT',field('close','1h'),{'kind':'feature','name':'trend'})
    value['rules']['short']=operator('LT',field('close','1h'),{'kind':'feature','name':'trend'})
    value['rules']['exit_policy']['max_hold_seconds']=3600
    value['content_hash']=compute_content_hash(value)
    return value

class OwnerBindingTests(unittest.TestCase):
    def test_new_bar_high_cannot_retroactively_activate_a_trailing_stop_in_that_bar(self):
        from application.datasets.catalog import DatasetCatalog
        from application.datasets.resolver import DatasetResolver
        with TemporaryDirectory() as root:
            dataset(root,mutate=lambda rows:rows[3].update(open='104',high='200',low='103.5',close='190'))
            bound=DatasetResolver(DatasetCatalog(root)).resolve('dataset.json')
            value=strategy(); value['rules']['exit_policy'].update(target=None,trailing={'kind':'fixed_distance','value':'1'},max_hold_seconds=36000)
            value['content_hash']=compute_content_hash(value)
            binding=project_e2_runtime_binding(runtime_profile='0.2.0',candles_by_timeframe=bound.candles_by_timeframe)
            config=ReplayConfig(Decimal(1),'FIXTURE_COST',FeeModel('FIXTURE_FEE',Decimal(0),Decimal(0)),
                                SlippageModel('FIXTURE_SLIP',Decimal(0),Decimal(0)),bound.funding_model)
            result=HistoricalReplayEngine(binding,config).run(parse_strategy_definition(value),bound.candles_by_timeframe['1h'],
                DatasetDescriptor(bound.dataset_id,bound.logical_hash,bound.start,bound.end))
            self.assertEqual(START+timedelta(hours=5),result.trades[0].closed_at)
            self.assertEqual(Decimal(104),result.trades[0].exit_fill_price)

    def test_v02_protective_and_trailing_exits_use_e5_geometry_and_prior_bar_only(self):
        from application.datasets.catalog import DatasetCatalog
        from application.datasets.resolver import DatasetResolver
        with TemporaryDirectory() as root:
            dataset(root); bound=DatasetResolver(DatasetCatalog(root)).resolve('dataset.json')
            def replay(value):
                value['content_hash']=compute_content_hash(value)
                binding=project_e2_runtime_binding(runtime_profile='0.2.0',candles_by_timeframe=bound.candles_by_timeframe)
                config=ReplayConfig(Decimal(1),'FIXTURE_COST',FeeModel('FIXTURE_FEE',Decimal(0),Decimal(0)),
                                    SlippageModel('FIXTURE_SLIP',Decimal(0),Decimal(0)),bound.funding_model)
                return HistoricalReplayEngine(binding,config).run(parse_strategy_definition(value),bound.candles_by_timeframe['1h'],
                    DatasetDescriptor(bound.dataset_id,bound.logical_hash,bound.start,bound.end))
            narrow=strategy(); narrow['rules']['exit_policy'].update(stop={'kind':'fixed_distance','value':'1'},target={'kind':'reward_risk','multiple':'1'},max_hold_seconds=36000)
            result=replay(narrow)
            self.assertEqual('STOP_LOSS',result.trades[0].exit_reason)
            self.assertEqual(Decimal(101),result.trades[0].exit_fill_price)
            trailing=strategy(); trailing['rules']['exit_policy'].update(target=None,trailing={'kind':'fixed_distance','value':'1'},max_hold_seconds=36000)
            result=replay(trailing)
            # Entry at02:00, bar high104 proposes103 only after03:00.
            # The next observed03:00 open103 exits; no favorable02:00 intrabar fill.
            self.assertEqual('STOP_LOSS',result.trades[0].exit_reason)
            self.assertEqual(Decimal(103),result.trades[0].exit_fill_price)
            self.assertEqual(START+timedelta(hours=4),result.trades[0].closed_at)

    def test_actual_multi_timeframe_replay_cannot_see_unfinished_or_future_four_hour_data(self):
        from dataclasses import replace
        from application.datasets.catalog import DatasetCatalog
        from application.datasets.resolver import DatasetResolver
        from market_data.aggregation import aggregate_complete
        with TemporaryDirectory() as root:
            dataset(root); bound=DatasetResolver(DatasetCatalog(root)).resolve('dataset.json')
            lower=bound.candles_by_timeframe['1h']; higher=aggregate_complete(lower,'4h')
            value=strategy(); value['required_timeframes']=['1h','4h']
            value['rules']['features']['trend']['source']=field('close','4h')
            value['rules']['features']['trend']['parameters']['window']=1
            value['rules']['long']=operator('GT',field('close','1h'),{'kind':'feature','name':'trend'})
            value['rules']['short']=operator('LT',field('close','1h'),{'kind':'feature','name':'trend'})
            value['content_hash']=compute_content_hash(value); parsed=parse_strategy_definition(value)
            original=project_e2_runtime_binding(runtime_profile='0.2.0',candles_by_timeframe={'1h':lower,'4h':higher})
            changed_higher=(*higher[:-1],replace(higher[-1],close=Decimal(999),high=Decimal(1000)))
            changed=project_e2_runtime_binding(runtime_profile='0.2.0',candles_by_timeframe={'1h':lower,'4h':changed_higher})
            first=original.evaluate(parsed,lower[:3],START+timedelta(hours=3))
            self.assertEqual('NO_TRADE',first['direction'])
            self.assertEqual(['INSUFFICIENT_HISTORY'],first['reason_codes'])
            t5=original.evaluate(parsed,lower[:5],START+timedelta(hours=5))
            self.assertEqual('LONG',t5['direction'])
            self.assertEqual(t5,changed.evaluate(parsed,lower[:5],START+timedelta(hours=5)))
            config=ReplayConfig(Decimal(1),'FIXTURE_COST',FeeModel('FIXTURE_FEE',Decimal(0),Decimal(0)),
                                SlippageModel('FIXTURE_SLIP',Decimal(0),Decimal(0)),bound.funding_model)
            result=HistoricalReplayEngine(original,config).run(parsed,lower,
                DatasetDescriptor(bound.dataset_id,bound.logical_hash,bound.start,bound.end))
            self.assertEqual(START+timedelta(hours=5),result.trades[0].opened_at)
            self.assertEqual(12,result.runtime_invocations)

    def test_actual_v02_replay_uses_e2_e5_next_open_and_first_fill_time_exit(self):
        # Missing profile adaptation must fail; no injected signal/compatibility.
        self.assertIn('runtime_profile',__import__('inspect').signature(project_e2_runtime_binding).parameters)
        from application.datasets.catalog import DatasetCatalog
        from application.datasets.resolver import DatasetResolver
        with TemporaryDirectory() as root:
            dataset(root); bound=DatasetResolver(DatasetCatalog(root)).resolve('dataset.json')
            binding=project_e2_runtime_binding(runtime_profile='0.2.0',candles_by_timeframe=bound.candles_by_timeframe,
                                               availability_model=bound.availability_model)
            config=ReplayConfig(Decimal(1),'FIXTURE_COST',FeeModel('FIXTURE_FEE',Decimal(2),Decimal(4)),
                                SlippageModel('FIXTURE_SLIP',Decimal(1),Decimal(1)),bound.funding_model,run_created_at=START)
            result=HistoricalReplayEngine(binding,config).run(parse_strategy_definition(strategy()),bound.candles_by_timeframe['1h'],
                DatasetDescriptor(bound.dataset_id,bound.logical_hash,bound.start,bound.end))
            self.assertEqual('0.2.0',result.runtime_version)
            self.assertEqual(12,result.runtime_invocations)
            self.assertEqual(START+timedelta(hours=2),result.trades[0].opened_at)
            self.assertEqual(START+timedelta(hours=3),result.trades[0].closed_at)
            self.assertEqual('MAX_HOLD',result.trades[0].exit_reason)
            self.assertEqual(Decimal('102.0102'),result.trades[0].entry_fill_price)
            self.assertGreater(result.trades[0].total_fees,0)
            self.assertGreater(result.trades[0].slippage_cost,0)
            funding_trade=next(t for t in result.trades if t.opened_at==START+timedelta(hours=8))
            self.assertEqual(Decimal('0.01080108'),funding_trade.funding_cost)

    def test_warmup_evaluates_features_without_scoring_trades_or_entry_before_window(self):
        self.assertIn('scored_start',__import__('inspect').signature(ReplayConfig).parameters)
        from application.datasets.catalog import DatasetCatalog
        from application.datasets.resolver import DatasetResolver
        with TemporaryDirectory() as root:
            dataset(root); bound=DatasetResolver(DatasetCatalog(root)).resolve('dataset.json')
            binding=project_e2_runtime_binding(runtime_profile='0.2.0',candles_by_timeframe=bound.candles_by_timeframe,availability_model=bound.availability_model)
            config=ReplayConfig(Decimal(1),'FIXTURE_COST',FeeModel('FIXTURE_FEE',Decimal(0),Decimal(0)),
                                SlippageModel('FIXTURE_SLIP',Decimal(0),Decimal(0)),bound.funding_model,run_created_at=START,
                                scored_start=START+timedelta(hours=4),scored_end=START+timedelta(hours=8),
                                entry_start=START+timedelta(hours=5),entry_end=START+timedelta(hours=7))
            rows=bound.candles_by_timeframe['1h'][2:8]
            result=HistoricalReplayEngine(binding,config).run(parse_strategy_definition(strategy()),rows,
                DatasetDescriptor('fixture-dev',bound.logical_hash,rows[0].open_time,rows[-1].close_time))
            self.assertEqual(START+timedelta(hours=4),result.dataset_start)
            self.assertEqual(START+timedelta(hours=8),result.dataset_end)
            self.assertTrue(result.trades)
            self.assertTrue(all(START+timedelta(hours=5)<=t.opened_at<START+timedelta(hours=7) and t.closed_at<START+timedelta(hours=8) for t in result.trades))
