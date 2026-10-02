"""Explicit mechanical test policies; never installed financial commissioning values."""
from datetime import timedelta
from pathlib import Path
from application.datasets.catalog import DatasetCatalog,canonical,digest
from application.datasets.resolver import DatasetResolver
from application.datasets.split_plan import resolve_split
from strategy import compute_content_hash
from tests.application.dataset_fixtures import dataset,split_policy,START,z
from tests.application.test_research_pipeline import configured
from tests.backtest.test_v02_owner_binding import strategy
from tests.validation.test_monte_carlo import fixture_policy

def subject():
    value=strategy()
    value['rules']['features']['trend']['parameters']['window']={'kind':'parameter','name':'fast_window'}
    value['content_hash']=compute_content_hash(value)
    return value

def inputs(root,mutate=None):
    import json
    configured(root); dataset(root,count=48,mutate=mutate)
    policy=split_policy()
    for name,a,b in (('training',0,16),('development',16,32),('sealed_oos',32,48)):
        policy[name]={'start':z(START+timedelta(hours=a)),'end':z(START+timedelta(hours=b))}
    resolved=DatasetResolver(DatasetCatalog(root)).resolve('dataset.json')
    return resolved,resolve_split(resolved,policy),json.loads((Path(root)/'cost.json').read_text())

def research_policy(split,cost):
    return dict(schema_version='r7-research-policy-v0.2',policy_id='FIXTURE_RESEARCH',generation=1,namespace='FIXTURE',
                validation_policy_version='FIXTURE_VALIDATION_V1',minimum_closed_trades={'development':5,'walk_forward':1,'sealed_oos':5},
                min_net_pnl_usdt='0',min_expectancy_usdt_per_trade='0',drawdown_limit='100',drawdown_unit='USDT_AMOUNT',
                initial_equity_usdt='1000',max_consecutive_losses=10,min_profit_factor='0',profit_factor_null_handling='ALLOW_NO_LOSSES',
                split_policy_hash=split.policy_hash,cost_policy_hash=digest(canonical(cost).encode()))

def robustness_policy(split,cost):
    windows=[]
    for a,b,c,d in ((0,8,8,12),(4,12,12,16)):
        windows.append({'training':{'start':z(START+timedelta(hours=a)),'end':z(START+timedelta(hours=b))},
                        'evaluation':{'start':z(START+timedelta(hours=c)),'end':z(START+timedelta(hours=d))}})
    return dict(schema_version='r7-robustness-policy-v0.2',policy_id='FIXTURE_ROBUSTNESS',generation=1,namespace='FIXTURE',
                algorithm_version='r7-robustness-v1',split_policy_hash=split.policy_hash,cost_policy_hash=digest(canonical(cost).encode()),
                neighborhood=[{'parameter':'fast_window','type':'INTEGER','minimum':0,'maximum':3,'values':[1,2,3,0]}],
                maximum_trials=4,maximum_replays=40,maximum_evaluations=2000,
                selection_procedure='TRAIN_NET_PNL_THEN_VARIANT_HASH_V1',minimum_neighborhood_pass_fraction='0.5',
                minimum_walk_forward_pass_fraction='1',minimum_stress_net_pnl_usdt='0',
                walk_forward_windows=windows,stress_scenarios=[{'name':'EXPLICIT_ADVERSE_10BPS','fee_add_bps':'10',
                    'entry_slippage_add_bps':'10','exit_slippage_add_bps':'10','funding_adverse_multiplier':'2'}],
                monte_carlo=[fixture_policy(),fixture_policy('MOVING_BLOCK_BOOTSTRAP')],
                max_monte_carlo_drawdown_q95='100',minimum_block_expectancy_q05_usdt_per_trade='0')
