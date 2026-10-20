"""Supplemental genuine 4h source-owner proof; accelerated FIXTURE only."""
from contextlib import ExitStack
from datetime import timedelta
from decimal import Decimal
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import pyarrow as pa
import pyarrow.parquet as pq
from application.datasets.catalog import DatasetCatalog,utc
from application.datasets.resolver import DatasetResolver
from application.datasets.split_plan import resolve_split
from application.paper.assessment import assess_forward
from application.paper.scheduler import PaperScheduler
from application.paper.service import PaperMarketEvent,PaperService
from application.research.service import ResearchService
from market_data.aggregation import aggregate_complete
from market_data.candle import Candle
from market_data.current import MarketSnapshot
from registry.operational_authority import HumanAuthenticator,ProductLifecycleComposition,ReleaseBinding
from risk.product_policy import parse_product_risk_policy
from storage.paper_process import open_paper_process_journal
from storage.platform import open_sqlite_platform
from storage.runtime import open_paper_runtime_journal
from strategy import compute_content_hash,parse_strategy_definition
from strategy.v02.capabilities import _revision,build_capability_snapshot
from tests.application.dataset_fixtures import START,candle_schema,dataset,encoded,hashed,logical_rows,save_manifest,split_policy,z
from tests.application.test_product_assessment_binding import risk_fixture
from tests.application.test_research_pipeline import configured
from tests.product.test_paper_runtime_v02 import simulation_fixture
from tests.strategy.v02_fixtures import field,operator
from tests.validation.robustness_fixtures import research_policy,robustness_policy,subject
from tests.validation.test_paper_promotion_policy import policy_fixture


def four_hour_inputs(root):
    configured(root)
    def repeated_path(rows):
        for index,row in enumerate(rows):
            price=100+index//4
            row.update(open=str(price),high=str(price+2),low=str(price-1),close=str(price+1))
    manifest=dataset(root,count=192,mutate=repeated_path)
    hourly=DatasetResolver(DatasetCatalog(root)).resolve('dataset.json')
    bars=aggregate_complete(hourly.candles_by_timeframe['1h'],'4h')
    if len(bars)!=48:raise AssertionError('48 actual complete E1 aggregates required')
    rows=[]
    for bar in bars:
        row=bar.to_interchange_dict()
        for key in ('open_time','close_time','received_at'):row[key]=getattr(bar,key)
        rows.append(row)
    target=root/'candles.parquet'
    pq.write_table(pa.Table.from_pylist(rows,schema=candle_schema()),target,compression='NONE',row_group_size=4)
    manifest['dataset_id']='fixture-str12-four-hour'
    manifest['candles'][0].update(timeframe='4h',rows=48,finalized_rows=48,
        logical_hash=logical_rows(rows),byte_hash=hashed(target.read_bytes()))
    save_manifest(root,manifest)  # Full 192h funding grid/commitments retained.
    bound=DatasetResolver(DatasetCatalog(root)).resolve('dataset.json')
    if set(bound.candles_by_timeframe)!={'4h'}:raise AssertionError('Only genuine4h execution inputs required')
    split_input=split_policy()
    for name,lower,upper in (('training',0,64),('development',64,128),('sealed_oos',128,192)):
        split_input[name]=dict(start=z(START+timedelta(hours=lower)),end=z(START+timedelta(hours=upper)))
    split=resolve_split(bound,split_input)
    cost=json.loads((root/'cost.json').read_bytes())
    research=research_policy(split,cost);robustness=robustness_policy(split,cost)
    for window in robustness['walk_forward_windows']:
        for partition in window.values():
            for key in ('start','end'):partition[key]=z(START+(utc(partition[key])-START)*4)
    for name,value in (('split',split_input),('research',research),('robustness',robustness),('risk',risk_fixture())):
        (root/(name+'.json')).write_bytes(encoded(value))
    definition=subject();definition['required_timeframes']=['4h'];rules=definition['rules']
    rules['evaluation_timeframe']='4h';rules['features']['trend']['source']=field('close','4h')
    rules['long']=operator('GT',field('close','4h'),dict(kind='feature',name='trend'))
    rules['short']=operator('LT',field('close','4h'),dict(kind='feature',name='trend'))
    definition['content_hash']=compute_content_hash(definition)
    return definition


class FourHourOwnerDeadlineTests(unittest.TestCase):
    def test_actual_four_hour_owner_manages_before_next_entry_boundary(self):
        with TemporaryDirectory(prefix='str12-four-hour-') as temporary:
            root=Path(temporary);definition=four_hour_inputs(root);parsed=parse_strategy_definition(definition)
            self.assertEqual(('4h',),tuple(parsed.required_timeframes))
            self.assertEqual('4h',parsed.evaluation_timeframe)
            self.assertEqual(3600,definition['rules']['exit_policy']['max_hold_seconds'])
            registry_path=root/'registry.sqlite'
            with ResearchService(local_root=root,database_path=root/'research.sqlite',registry_path=registry_path,
                    namespace='FIXTURE',owner_id='fixture-str12-research') as research:
                result=research.run(submission_id='fixture-str12-four-hour',definition=definition,dataset_ref='dataset.json',
                    split_policy_ref='split.json',cost_policy_ref='cost.json',research_policy_ref='research.json',
                    robustness_policy_ref='robustness.json',family_id='fixture-family',seed=42,risk_policy_ref='risk.json')
                report=research.report(result.run_id)
                self.assertEqual('CANDIDATE',result.strategy_lifecycle)
                self.assertEqual('PASS',report['candidate_gate']['status'])
                self.assertEqual('FIXTURE',report['namespace'])
                self.assertEqual(0,report['provenance']['provider_requests'])
                self.assertEqual('0.2.0',report['backtest']['runtime_version'])
                self.assertGreater(report['backtest']['reproducibility']['runtime_invocations'],0)
            t0=START+timedelta(hours=192);clock=[t0];simulation=simulation_fixture()
            self.assertEqual(('FIXTURE','ACCELERATED_FIXTURE'),(simulation['namespace'],simulation['mode']))
            risk=parse_product_risk_policy(risk_fixture(),namespace='FIXTURE');source=_revision()
            self.assertEqual(source,report['provenance']['implementation_hash'])
            release=ReleaseBinding(namespace='FIXTURE',implementation_hash=source,
                executable_revision=report['provenance']['executable_revision'],
                build_hash=hashed(b'STR12_SOURCE_FIXTURE_NO_NATIVE_BUILD'),config_hash=hashed(encoded(simulation)),
                config_generation=1,capability_hash=build_capability_snapshot().snapshot_hash,
                provider_profile_hash=hashed(b'STR12_LOCAL_PAPERBROKER_SOURCE_FIXTURE_ONLY'),
                provider_ref='fixture-paper',account_ref='fixture-str12-account',risk_policy_hash=risk.policy_hash,
                risk_generation=1,runtime_generation=1,release_kind='FIXTURE')
            self.assertEqual('FIXTURE',release.release_kind)
            auth=HumanAuthenticator(namespace='FIXTURE',verifier=lambda proof:None,current_verifier=lambda proof:None,
                reauth_seconds=300,clock=lambda:clock[0])
            active_owner={}
            def resolve_owner(kind,reference,identity):
                return active_owner['service'].resolve_owner_evidence(kind,reference,identity)
            boundary=ProductLifecycleComposition(namespace='FIXTURE',current_release=lambda:release,
                resolve_evidence=resolve_owner,authenticator=auth,clock=lambda:clock[0])
            paper_policy=policy_fixture();policy_ref='fixture-paper-policy'
            boundary.select_paper_policy(policy_ref,paper_policy)
            with ExitStack() as stack:
                registry=stack.enter_context(open_sqlite_platform(registry_path,research_namespace='FIXTURE',
                    lifecycle_boundary=boundary,require_existing=True))
                product=registry.product_assessment(result.run_id);identity=product.identity
                selected=registry.get_strategy(identity)
                self.assertEqual('CANDIDATE',selected.current_lifecycle_state)
                self.assertEqual(definition['content_hash'],selected.content_hash)
                self.assertEqual(risk.policy_hash,product.risk_policy_hash)
                self.assertEqual(('4h',),tuple(parse_strategy_definition(selected.definition_json).required_timeframes))
                process=stack.enter_context(open_paper_process_journal(root/'runtime.sqlite'))
                canonical=stack.enter_context(open_paper_runtime_journal(root/'runtime.sqlite'))
                def make_service():
                    return PaperService(registry=registry,process_journal=process,canonical_journal=canonical,
                        namespace='FIXTURE',simulation_policy=simulation,risk_policy=risk_fixture(),
                        promotion_policy=paper_policy,paper_policy_ref=policy_ref,
                        submission_validity=dict(intent_class='EVERGREEN_STRATEGY',validity=dict(**{'from':None,'until':None})),
                        actor='fixture-str12-paper',workflow_authorized=True,current_release=lambda:release,
                        clock=lambda:clock[0],strategy_identity=identity)
                service=make_service();active_owner['service']=service
                ref=service.start(identity,policy_ref,selected.registry_revision,'fixture-str12-start')
                runtime=service.runtime(ref.run_id)
                self.assertEqual('PAPER',registry.get_strategy(identity).current_lifecycle_state)
                def event(seconds,*,candles=False):
                    clock[0]=t0+timedelta(seconds=seconds);now=clock[0]
                    snapshot=MarketSnapshot('contracts-v0.1','BTC_USDT_PERP',now,now,'HEALTHY','EXPLICIT_FIXTURE',
                        last_price=Decimal('60000'),freshness_ms=0)
                    rows=()
                    if candles:
                        rows=tuple(Candle('contracts-v0.1','BTC_USDT_PERP','4h',
                            t0-timedelta(hours=8-4*index),t0-timedelta(hours=4-4*index),
                            Decimal(value),Decimal(value)+1,Decimal(value)-1,Decimal(value),Decimal('1'),True,
                            'EXPLICIT_FIXTURE',received_at=t0) for index,value in enumerate(('59000','60000')))
                    return PaperMarketEvent(snapshot=snapshot,candles=rows,source_kind='FIXTURE')
                self.assertEqual('ACKNOWLEDGED',runtime.on_market_event(event(0,candles=True)).status)
                self.assertEqual('PROTECTED',runtime.on_market_event(event(1)).status)
                original=process.recover(ref.run_id).state['runtime'];position_id=original['position']['position_id']
                opened_at=original['position']['opened_at'];anchor=original['exit_anchor'];protection=original['protection_request']
                self.assertEqual('OPEN_PROTECTED',original['position']['lifecycle_state'])
                self.assertEqual(z(t0),original['last_entry_boundary'])
                self.assertEqual('APPROVE',original['risk_decision']['decision'])
                runtime.on_market_event(event(2));before=process.recover(ref.run_id)
                self.assertEqual(z(t0+timedelta(seconds=2)),before.state['runtime']['position']['broker_state_observed_at'])
                clock[0]=t0+timedelta(seconds=3);successor=make_service();active_owner['service']=successor
                resumed=successor.runtime(ref.run_id);restarted=process.recover(ref.run_id)
                self.assertEqual(before.process_generation+1,restarted.process_generation)
                self.assertEqual(before.state,restarted.state);self.assertTrue(resumed.engine.reconciled)
                scheduler=PaperScheduler(resumed,maximum_pending_events=2)
                clock[0]=t0+timedelta(seconds=4);scheduler.tick()
                observed=process.recover(ref.run_id).state['runtime']
                self.assertEqual('OPEN_PROTECTED',observed['position']['lifecycle_state'])
                self.assertEqual(z(clock[0]),observed['position']['broker_state_observed_at'])
                self.assertEqual(protection,observed['protection_request']);self.assertEqual(anchor,observed['exit_anchor'])
                self.assertEqual(opened_at,observed['position']['opened_at'])
                deadline=utc(anchor['payload']['hold_deadline'])
                self.assertEqual(utc(opened_at)+timedelta(seconds=3600),deadline)
                self.assertLess(deadline,t0+timedelta(hours=4))
                clock[0]=deadline;outcomes=scheduler.tick()
                self.assertTrue(any(row.status=='EXIT_REQUESTED' for row in outcomes))
                pending=process.recover(ref.run_id).state['runtime']
                self.assertEqual(['E5_MAX_HOLD_REACHED'],pending['exit_action']['reason_codes'])
                self.assertEqual(z(t0),pending['last_entry_boundary']);self.assertEqual(opened_at,pending['position']['opened_at'])
                self.assertEqual('CLOSED',resumed.on_market_event(event(int((deadline-t0).total_seconds())+1)).status)
                final=process.recover(ref.run_id);state=final.state['runtime']
                self.assertLess(clock[0],t0+timedelta(hours=4));self.assertEqual(z(t0),state['last_entry_boundary'])
                self.assertEqual(anchor,state['exit_anchor']);self.assertEqual(1,len(state['closed_trades']))
                # Existing canonical Paper gateway uses role=None/reduce_only=None for entry.
                entries=[row['request'] for row in final.state['broker']['payload']['submissions'] if row['request']['reduce_only'] is not True]
                self.assertEqual([original['entry_request']],entries)
                self.assertEqual(original['entry_request'],state['entry_request'])
                graph=canonical.recover(position_id=position_id)
                self.assertEqual('READY',graph.status);self.assertEqual('CLOSED',graph.current_position_projection.payload['lifecycle_state'])
                self.assertEqual(2,len(graph.fills));self.assertEqual(graph.trade_result.payload,state['closed_trades'][0])
                self.assertEqual(('FIXTURE','ACCELERATED_FIXTURE'),(final.binding['namespace'],final.binding['mode']))
                self.assertEqual(0,state['forward']['real_elapsed_ns'])
                assessment=assess_forward(resumed,successor.promotion).as_dict()
                self.assertEqual('ACCELERATED_FIXTURE',assessment['forward_mode'])
                self.assertEqual(0,assessment['actual_elapsed_seconds']);self.assertEqual(1,assessment['closed_trades'])
                self.assertNotEqual('PASS',assessment['status']);self.assertEqual('PAPER',registry.get_strategy(identity).current_lifecycle_state)


if __name__=='__main__':unittest.main()
