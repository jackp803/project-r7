"""Reproducible synthetic generation inputs, never results or approval records.

The literal mechanical policies belong only to this named FIXTURE recipe. They
are not ordinary commissioning defaults or real-data performance evidence.
"""
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import io

from application.cloud.authoring import emit_package
from application.config import load_config, product_namespace
from application.datasets.catalog import canonical, digest
from application.platform.private_files import create_private_directory, write_private_new
from application.platform.restoration import require_valid_restoration
from application.platform.scope_lock import ProcessScopeLock, operational_lock_root
from application.platform.supervision import _local_path
from strategy import RUNTIME_FAMILY, compute_content_hash

START = datetime(2026, 10, 2, tzinfo=timezone.utc)
ROOT_ID = 'r7-synthetic-fixture-cloud-v1'
SUBMISSION = 'r7-synthetic-fixture-input'
POLICY_ID = 'r7-synthetic-fixture-policy'
SCENARIOS = ('positive', 'oos-loss', 'insufficient-oos')


def _z(value):
    return value.isoformat().replace('+00:00', 'Z')


def _raw(value):
    return canonical(value).encode('utf-8')


def _window(a, b):
    return dict(start=_z(START+timedelta(hours=a)), end=_z(START+timedelta(hours=b)))


def _definition():
    close = dict(kind='field', timeframe='1h', field='close')
    value = dict(schema_version='contracts-v0.1',strategy_id='r7-synthetic-trend',
        strategy_version='0.2.0',name='SYNTHETIC FIXTURE trend scenario',symbol='BTC_USDT_PERP',
        required_timeframes=['1h'],parameters={'fast_window':2},created_at=_z(START),
        runtime_compatibility=dict(runtime_family=RUNTIME_FAMILY,runtime_version='0.2.0'),
        rules=dict(dsl_version='0.2',behavior_profile='r7-closed-bar-v0.2',evaluation_timeframe='1h',
            features=dict(trend=dict(kind='indicator',name='EMA',semantic_version='r7-ema-v1',source=close,
                parameters={'window':{'kind':'parameter','name':'fast_window'}},output='value')),
            long=dict(kind='operator',name='GT',args=[close,{'kind':'feature','name':'trend'}]),
            short=dict(kind='operator',name='LT',args=[close,{'kind':'feature','name':'trend'}]),
            exit_policy=dict(stop={'kind':'fixed_distance','value':'10'},target={'kind':'reward_risk','multiple':'2'},
                trailing=None,max_hold_seconds=3600)))
    value['content_hash'] = compute_content_hash(value)
    return value


def _risk_policy():
    return dict(schema_version='r7-selected-risk-policy-v0.2',namespace='FIXTURE',generation=1,
        units=dict(margin='USDT_AMOUNT',notional='USDT_AMOUNT',estimated_cost='USDT_AMOUNT',
            drawdown='USDT_AMOUNT',leverage='RATIO',reward_risk='RATIO',time='SECONDS'),
        policy=dict(version='FIXTURE_RISK_V1',max_margin='100',max_notional='100',max_leverage='1',
            min_reward_risk='1',max_estimated_cost='1',max_trades_per_day=10,max_open_positions=1,
            max_drawdown='10',max_consecutive_losses=3,max_intent_age_seconds=60,max_hold_seconds=3600,
            plan_ttl_seconds=30,margin_mode='ISOLATED'))


def _monte_carlo(algorithm):
    return dict(schema_version='r7-monte-carlo-policy-v0.2',algorithm=algorithm,algorithm_version='r7-mc-v1',
        rng_algorithm='SHA256_COUNTER_REJECTION_V1',resample_count=20,minimum_samples=5,
        minimum_effective_blocks=2,block_length=2,sample_source='CLOSED_DEVELOPMENT_TRADE_NET_PNL_USDT',
        initial_equity='1000',drawdown_unit='USDT_AMOUNT',max_path_observations=10000,
        dependence_model='ORDER_SENSITIVITY' if algorithm=='TRADE_PERMUTATION' else 'OVERLAPPING_FIXED_BLOCKS')


def _policies(scenario):
    split = dict(schema_version='r7-split-policy-v0.2',policy_id='FIXTURE_SPLIT',generation=1,namespace='FIXTURE',
        training=_window(0,16),development=_window(16,32),sealed_oos=_window(32,48),warmup_bars=2,
        max_holding_seconds=3600,label_horizon_seconds=3600,embargo_seconds=3600,
        embargo_rationale='Synthetic fixture one-hour boundary exclusion')
    cost = dict(schema_version='r7-replay-cost-policy-v0.2',policy_id='FIXTURE_COST',generation=1,namespace='FIXTURE',
        cost_model_version='FIXTURE_COST_V1',fixed_quantity='1',quantity_unit='BASE',fee_unit='BPS_OF_NOTIONAL',
        maker_bps='2',taker_bps='4',slippage_unit='BPS_OF_REFERENCE_PRICE',entry_bps='1',exit_bps='1',max_evaluations=100)
    split_hash, cost_hash = digest(_raw(split)), digest(_raw(cost))
    research = dict(schema_version='r7-research-policy-v0.2',policy_id='FIXTURE_RESEARCH',generation=1,namespace='FIXTURE',
        validation_policy_version='FIXTURE_VALIDATION_V1',
        minimum_closed_trades={'development':5,'walk_forward':1,'sealed_oos':100 if scenario=='insufficient-oos' else 5},
        min_net_pnl_usdt='0',min_expectancy_usdt_per_trade='0',drawdown_limit='100',drawdown_unit='USDT_AMOUNT',
        initial_equity_usdt='1000',max_consecutive_losses=10,min_profit_factor='0',profit_factor_null_handling='ALLOW_NO_LOSSES',
        split_policy_hash=split_hash,cost_policy_hash=cost_hash)
    robustness = dict(schema_version='r7-robustness-policy-v0.2',policy_id='FIXTURE_ROBUSTNESS',generation=1,namespace='FIXTURE',
        algorithm_version='r7-robustness-v1',split_policy_hash=split_hash,cost_policy_hash=cost_hash,
        neighborhood=[{'parameter':'fast_window','type':'INTEGER','minimum':0,'maximum':3,'values':[1,2,3,0]}],
        maximum_trials=4,maximum_replays=40,maximum_evaluations=2000,selection_procedure='TRAIN_NET_PNL_THEN_VARIANT_HASH_V1',
        minimum_neighborhood_pass_fraction='0.5',minimum_walk_forward_pass_fraction='1',minimum_stress_net_pnl_usdt='0',
        walk_forward_windows=[dict(training=_window(a,b),evaluation=_window(c,d)) for a,b,c,d in ((0,8,8,12),(4,12,12,16))],
        stress_scenarios=[dict(name='EXPLICIT_ADVERSE_10BPS',fee_add_bps='10',entry_slippage_add_bps='10',
            exit_slippage_add_bps='10',funding_adverse_multiplier='2')],
        monte_carlo=[_monte_carlo('TRADE_PERMUTATION'),_monte_carlo('MOVING_BLOCK_BOOTSTRAP')],
        max_monte_carlo_drawdown_q95='100',minimum_block_expectancy_q05_usdt_per_trade='0')
    simulation = dict(schema_version='r7-paper-simulation-policy-v0.2',namespace='FIXTURE',mode='ACCELERATED_FIXTURE',
        policy_id='FIXTURE_SIMULATION',generation=1,initial_balance_usdt='1000',quantity='0.001',leverage='1',
        fee_rate='0.00005',slippage_bps='0',estimated_roundtrip_cost_usdt='0.006',initial_fill_fraction='1',
        partial_remainder_behavior='CANCEL_AFTER_FIRST_FILL',market_max_age_seconds=5,action_ttl_seconds=30,
        protection_poll_seconds=1,maximum_cached_candles_per_timeframe=2000,
        funding_model='EXPLICIT_REGISTERED_PAPER_ZERO',account_scope='ISOLATED_PER_STRATEGY_RUN')
    promotion = dict(schema_version='r7-paper-promotion-policy-v0.2',policy_id='FIXTURE_FORWARD_POLICY',namespace='FIXTURE',generation=1,
        validation_policy_version='FIXTURE_FORWARD_THRESHOLDS_V1',min_elapsed_seconds=3600,min_closed_trades=2,
        min_net_pnl_usdt='0',min_expectancy_usdt_per_trade='0',max_drawdown_usdt='10',max_consecutive_losses=3,
        min_profit_factor='1',profit_factor_null_handling='ALLOW_NO_LOSSES',required_healthy_seconds=3600,
        maximum_observation_gap_seconds=30,units=dict(time='SECONDS',trade_count='CLOSED_TRADES',pnl='USDT_AMOUNT',
            expectancy='USDT_PER_CLOSED_TRADE',drawdown='USDT_AMOUNT'))
    return dict(split=split,cost=cost,research=research,robustness=robustness,risk=_risk_policy(),
        simulation=simulation,promotion=promotion)


def _dataset(scenario):
    import pyarrow as pa
    import pyarrow.parquet as pq
    rows = []
    for index in range(48):
        lower, upper = START+timedelta(hours=index), START+timedelta(hours=index+1)
        prices = dict(open=str(100+index),high=str(102+index),low=str(99+index),close=str(101+index))
        if scenario=='oos-loss' and index>=32:
            offset = index-32
            prices = dict(open=str(1000000+offset),high=str(1000002+offset),low=str(999999+offset),close=str(1000001+offset))
        rows.append(dict(schema_version='contracts-v0.1',symbol='BTC_USDT_PERP',timeframe='1h',open_time=lower,
            close_time=upper,**prices,volume='10',is_closed=True,source='SYNTHETIC_FIXTURE',received_at=upper,
            source_record_id='r7-synthetic-'+str(index)))
    schema = pa.schema([pa.field(name,kind,nullable=nullable) for name,kind,nullable in [
        ('schema_version',pa.string(),False),('symbol',pa.string(),False),('timeframe',pa.string(),False),
        ('open_time',pa.timestamp('ms',tz='UTC'),False),('close_time',pa.timestamp('ms',tz='UTC'),False),
        *[(key,pa.string(),False) for key in ('open','high','low','close','volume')],
        ('is_closed',pa.bool_(),False),('source',pa.string(),False),('received_at',pa.timestamp('ms',tz='UTC'),True),
        ('source_record_id',pa.string(),True)]])
    candles = io.BytesIO()
    pq.write_table(pa.Table.from_pylist(rows,schema=schema),candles,compression='NONE',row_group_size=4)
    logical = [dict(row,open_time=_z(row['open_time']),close_time=_z(row['close_time']),received_at=_z(row['received_at'])) for row in rows]
    funding_rows = [dict(event_at=START+timedelta(hours=i),rate='0.0001',source='SYNTHETIC_FIXTURE') for i in range(0,48,8)]
    funding_schema = pa.schema([pa.field('event_at',pa.timestamp('ms',tz='UTC'),False),
        pa.field('rate',pa.string(),False),pa.field('source',pa.string(),False)])
    funding = io.BytesIO()
    pq.write_table(pa.Table.from_pylist(funding_rows,schema=funding_schema),funding,compression='NONE')
    funding_logical = [dict(row,event_at=_z(row['event_at'])) for row in funding_rows]
    manifest = dict(schema_version='r7-dataset-v0.2',dataset_id='r7-synthetic-fixture-dataset',dataset_version='1',
        namespace='FIXTURE',symbol='BTC_USDT_PERP',source_instrument='SYNTHETIC:BTC-USDT',normalization_version='r7-canonical-e1-v0.2',
        alignment='UTC',availability_model='recorded_received_at',information_cutoff=_z(START+timedelta(hours=48)),
        units=dict(price='USDT_PER_BASE',volume='BASE',quantity='BASE',settlement='USDT',instrument_type='LINEAR_PERPETUAL'),
        candles=[dict(path='candles.parquet',timeframe='1h',**_window(0,48),rows=48,finalized_rows=48,
            missing_ranges=[],duplicate_ranges=[],logical_hash=digest(_raw(logical)),byte_hash=digest(candles.getvalue()))],
        funding=dict(mode='RECORDED',path='funding.parquet',**_window(0,48),rows=6,interval_seconds=28800,
            logical_hash=digest(_raw(funding_logical)),byte_hash=digest(funding.getvalue()),rate_unit='FRACTION_PER_EVENT',
            notional_basis='ENTRY_FILL_PRICE_X_BASE_QUANTITY'),created_at=_z(START+timedelta(hours=48)))
    return manifest, candles.getvalue(), funding.getvalue()


def prepare_fixture(config_path, scenario):
    """Fresh stopped-owner synthetic inputs; actual research must run separately."""
    config = load_config(config_path)
    if product_namespace(config)!='FIXTURE' or scenario not in SCENARIOS or config.cloud_root is None:
        raise ValueError('Explicit FIXTURE mode, scenario and fresh fake cloud staging required')
    from application.entrypoints import _outside_installation
    _outside_installation(config.local_data_root)
    _outside_installation(config.cloud_root)
    with ExitStack() as stack:
        for role in ('control','research','runtime','cloud'):
            stack.enter_context(ProcessScopeLock(role+':'+config.product_instance_id,lock_root=operational_lock_root(config)))
        if load_config(config_path)!=config or require_valid_restoration(config)['status']!='NOT_RESTORED':
            raise ValueError('Unchanged non-restored fixture configuration required')
        target = config.local_data_root/'fixture-inputs'
        for path in (config.local_data_root,config.cloud_root,target):
            _local_path(path)
        if target.exists() or config.cloud_root.exists() or (config.local_data_root/'owner-selections.json').exists():
            raise ValueError('Fresh fixture inputs and fake staging required; preserve existing data')
        if not config.local_data_root.exists():
            create_private_directory(config.local_data_root)
        create_private_directory(target)
        create_private_directory(config.cloud_root)
        create_private_directory(config.cloud_root/'inbox')
        create_private_directory(config.cloud_root/'inbox'/'strategies')
        manifest, candles, funding = _dataset(scenario)
        write_private_new(target/'candles.parquet',candles)
        write_private_new(target/'funding.parquet',funding)
        write_private_new(target/'dataset.json',_raw(manifest))
        for name,value in _policies(scenario).items():
            write_private_new(target/(name+'.json'),_raw(value))
        package = emit_package(_definition(),config.cloud_root/'inbox'/'strategies'/SUBMISSION,
            submission_id=SUBMISSION,created_at=_z(START),created_by='SYNTHETIC FIXTURE product recipe',
            research_hypothesis='Accelerated mechanical demonstration; no real strategy evidence',
            requested_dataset_profile='synthetic-fixture',requested_validation_profile='synthetic-fixture',
            requested_robustness_profile='synthetic-fixture')
        write_private_new(config.cloud_root/'.r7-root.json',_raw({'root_id':ROOT_ID}))
        policy = {('dataset_ref' if key=='dataset' else key+'_policy_ref'):
            'fixture-inputs/'+key+'.json' for key in ('dataset','split','cost','research','robustness','risk')}
        policy.update(family_id='r7-synthetic-fixture-family',seed=42,requested_dataset_profile='synthetic-fixture',
            requested_validation_profile='synthetic-fixture',requested_robustness_profile='synthetic-fixture')
        selection = dict(schema_version='r7-owner-selections-v0.2',cloud_root_id=ROOT_ID,research_policies={POLICY_ID:policy})
        paper = dict(schema_version='r7-fixture-paper-inputs-v0.2',submission_id=SUBMISSION,
            simulation_policy_ref='fixture-inputs/simulation.json',risk_policy_ref='fixture-inputs/risk.json',
            promotion_policy_ref='fixture-inputs/promotion.json',paper_policy_ref='r7-synthetic-paper-policy')
        write_private_new(target/'paper-selection.json',_raw(paper))
        if load_config(config_path)!=config:
            raise ValueError('Fixture configuration changed during input generation')
        write_private_new(target/'selection.json',_raw(selection))
    return dict(status='SYNTHETIC_FIXTURE_INPUTS_CREATED',namespace='FIXTURE',scenario=scenario,
        recipe_version='r7-synthetic-fixture-v1',selection_profile_ref='fixture-inputs/selection.json',
        submission_id=SUBMISSION,policy_id=POLICY_ID,manifest_hash=package['manifest_hash'],
        cloud='FAKE_LOCAL_STAGING',market='SYNTHETIC_FIXTURE',execution_evidence='NOT_RUN',
        financial_authority='NONE',provider_requests=0,credentials='NONE',capital='NONE')
