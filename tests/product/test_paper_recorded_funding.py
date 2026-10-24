"""Real LOCAL E4/E5/E6 owners on a controlled clock/source; no native/elapsed credit."""
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import importlib
import json
import unittest
from unittest.mock import patch

from application.paper.ordinary_setup import load_ordinary_paper_owners
from application.platform.supervision import ProcessSupervisor
from execution.funding import public_recorded_funding_model
from registry import StrategyIdentity
from tests.application import test_ordinary_paper_composition as composition
from tests.application.test_recorded_paper_policy import recorded_policy
from tests.validation.robustness_fixtures import subject


def floor(value):return value.replace(hour=value.hour//8*8,minute=0,second=0,microsecond=0)
def stamp(value):return value.isoformat().replace('+00:00','Z')


class PaperRecordedFundingTests(unittest.TestCase):
    def prepare(self,*,four_hour=False,instance_id='ordinary-composition-unit'):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.funding_source'),
            'No trusted source-owned observation port for durable funding pending')
        from application.paper.funding_source import PaperFundingSource
        helper=composition.OrdinaryPaperCompositionTests();self.addCleanup(helper.doCleanups)
        self.four_hour=four_hour
        self.h,self.config,self.local,self.clock,_,_=helper.prepare(simulation=recorded_policy(),private_data=True,
            input_transform=self.four_hour_inputs if four_hour else None,instance_id=instance_id)
        from application.paper.public_market import configure_market_data
        from tests.application.test_public_paper_market import profile
        from application.datasets.catalog import canonical
        public=self.h.root/'public-market-profile.json';public.write_text(canonical(profile()),encoding='utf-8')
        configure_market_data(self.h.config_path,public)
        # These scenarios begin between settlements. Exact-boundary/late
        # publication behavior is tested separately, never inventing a row
        # published before its actual request cursor.
        if four_hour:
            self.clock[0]=self.clock[0].replace(hour=self.clock[0].hour//4*4)+timedelta(hours=4)
            if self.clock[0].hour%8==0:self.clock[0]+=timedelta(hours=4)
        elif self.clock[0].hour%8==0:self.clock[0]+=timedelta(hours=1)
        self.helper=helper;self.initial=self.clock[0];self.model=public_recorded_funding_model();self.latest=[None]
        self.source=PaperFundingSource(self.model,lambda:self.latest[0])
        self.observe(self.initial)
        self.supervisor=self.enterContext(ProcessSupervisor(self.config,'runtime'))
        self.selected=load_ordinary_paper_owners(self.config,resolver=self.local.resolver,
            clock=lambda:self.clock[0],funding_source=self.source)
        self.identity=self.selected.identity
        self.service=self.enterContext(self.selected.owners.service())
        self.ref=self.service.start(self.identity,self.service.policy_ref,
            self.service.registry.get_strategy(self.identity).registry_revision,'recorded-unit-start')
        self.runtime=self.service.runtime(self.ref.run_id)

    def four_hour_inputs(self,helper):
        """Generate new, unexecuted4h inputs through existing source fixtures."""
        from tests.application import dataset_fixtures,cloud_fixtures
        from tests.strategy.v02_fixtures import definition_v02
        from strategy import compute_content_hash
        from strategy.v02.capabilities import build_capability_snapshot
        from application.datasets.catalog import canonical,digest
        dataset=dataset_fixtures.dataset(helper.data,count=48,timeframe='4h');dataset['namespace']='LOCAL_RESEARCH'
        dataset_fixtures.save_manifest(helper.data,dataset)
        base=dataset_fixtures.START
        def scale(value):return stamp(base+(datetime.fromisoformat(value.replace('Z','+00:00'))-base)*4)
        split=json.loads((helper.data/'split.json').read_bytes())
        for key in ('training','development','sealed_oos'):
            split[key]={name:scale(value) for name,value in split[key].items()}
        for key in ('max_holding_seconds','label_horizon_seconds','embargo_seconds'):split[key]*=4
        (helper.data/'split.json').write_text(canonical(split),encoding='utf-8')
        split_hash=digest(canonical(split).encode())
        for name in ('research','robustness'):
            path=helper.data/(name+'.json');value=json.loads(path.read_bytes());value['split_policy_hash']=split_hash
            if name=='robustness':
                for window in value['walk_forward_windows']:
                    for region in ('training','evaluation'):
                        window[region]={key:scale(at) for key,at in window[region].items()}
            path.write_text(canonical(value),encoding='utf-8')
        strategy=definition_v02();strategy['rules']['features']['trend']['parameters']['window']={'kind':'parameter','name':'fast_window'}
        strategy['content_hash']=compute_content_hash(strategy)
        folder,manifest,_=cloud_fixtures.package(helper.cloud,submission='public-flow-input',version='0.2',definition=strategy)
        manifest['capability_snapshot_hash']=build_capability_snapshot().snapshot_hash
        (folder/'manifest.json').write_text(canonical(manifest),encoding='utf-8')

    def observe(self,now,*,missing_latest=False):
        end=floor(now)-(timedelta(hours=8) if missing_latest else timedelta())
        start=floor(self.initial)-timedelta(hours=8)
        times=[start+timedelta(hours=8*i) for i in range(int((end-start).total_seconds()/28800)+1)]
        began=now-timedelta(milliseconds=100)
        rows=[dict(instId='BTC-USDT-SWAP',fundingTime=str(int(t.timestamp()*1000)),
            realizedRate='0.0001',fundingRate='0.9') for t in reversed(times)]
        page=dict(url='https://www.okx.com/api/v5/public/funding-rate-history?after='+str(int(began.timestamp()*1000))+'&instId=BTC-USDT-SWAP&limit=100',
            request_started_at=stamp(began),received_at=stamp(now),http_status=200,
            response_body=json.dumps(dict(code='0',msg='',data=rows),separators=(',',':')).encode())
        self.latest[0]=self.model.observe((page,),coverage_start=start,observed_at=now)

    def event(self,second,*,bars=False,price='60000'):
        event=self.helper.event(self.clock,self.initial,second,bars=bars and not self.four_hour,price=price)
        if bars and self.four_hour:
            from dataclasses import replace
            from market_data.candle import Candle
            candles=tuple(Candle('contracts-v0.1','BTC_USDT_PERP','4h',
                self.initial-timedelta(hours=(2-i)*4),self.initial-timedelta(hours=(1-i)*4),
                Decimal(value),Decimal(value)+1,Decimal(value)-1,Decimal(value),Decimal('1'),
                True,'CONTROLLED_4H_SOURCE_ONLY',received_at=self.initial)
                for i,value in enumerate(('59000','60000')))
            event=replace(event,candles=candles)
        return event

    def close_pending(self,*,instance_id='ordinary-composition-unit'):
        self.prepare(instance_id=instance_id)
        self.assertEqual(self.selected.selection.as_dict()['simulator_profile']['funding_model'],
            'OKX_PUBLIC_RECORDED_ENTRY_NOTIONAL_V1')
        first=self.runtime.on_market_event(self.event(0,bars=True))
        self.assertEqual(first.status,'ACKNOWLEDGED',first.reason_codes)
        self.assertEqual(self.runtime.on_market_event(self.event(1)).status,'PROTECTED')
        self.latest[0]=None  # Source fails after exposure; close must continue.
        self.assertEqual(self.runtime.on_market_event(self.event(2,price='60020')).status,'EXIT_REQUESTED')
        outcome=self.runtime.on_market_event(self.event(3,price='60020'))
        self.assertEqual(outcome.status,'FUNDING_PENDING')
        return self.service.process.recover(self.ref.run_id)

    def test_flat_pending_is_durable_without_final_sample_and_repeated_close(self):
        pending=self.close_pending();state=pending.state
        from brokers.paper import PaperBroker
        self.assertEqual(PaperBroker.from_state(state['broker']).query_position('BTC_USDT_PERP').net_quantity,0)
        self.assertEqual(state['runtime']['closed_trades'],[])
        self.assertEqual(Decimal(state['runtime']['pending_funding']['flat']['actual_quantity']),0)
        graph=self.service.canonical.recover(position_id=state['runtime']['position']['position_id'])
        self.assertIsNone(graph.trade_result)
        self.assertEqual(len(graph.fills),2)
        for second in (4,5,6):
            self.assertEqual(self.runtime.on_market_event(self.event(second)).status,'FUNDING_PENDING')
        after=self.service.process.recover(self.ref.run_id)
        self.assertEqual(after.state['broker']['payload']['submissions'],state['broker']['payload']['submissions'])
        self.assertFalse(self.service.is_quiescent(self.ref.run_id))
        from application.paper.assessment import assess_forward
        self.assertIn('FUNDING_FINALIZATION_PENDING',assess_forward(self.runtime,self.service.promotion).as_dict()['reason_codes'])

    def test_successor_recovers_flat_pending_and_finalizes_once_at_original_flat_clock(self):
        pending=self.close_pending();flat=pending.state['runtime']['pending_funding']['flat']
        # A new service/process journal generation recovers actual E4 broker and E6 facts.
        successor=self.enterContext(self.selected.owners.service());self.service=successor
        runtime=successor.runtime(self.ref.run_id)
        self.assertTrue(runtime.engine.reconciled,runtime.engine.recovery_reason)
        self.clock[0]=floor(self.initial)+timedelta(hours=8,seconds=2)
        self.observe(self.clock[0])
        outcome=runtime.on_deadline(self.clock[0]);self.assertEqual(outcome.status,'CLOSED')
        state=successor.process.recover(self.ref.run_id).state
        self.assertIsNone(state['runtime']['pending_funding'])
        self.assertEqual(len(state['runtime']['closed_trades']),1)
        graph=successor.canonical.recover(position_id=state['runtime']['position']['position_id'])
        self.assertEqual(len(graph.fills),2)
        self.assertEqual(graph.current_position_projection.payload['broker_state_observed_at'],flat['broker_state_observed_at'])
        self.assertEqual(graph.trade_result.payload,state['runtime']['closed_trades'][0])
        self.assertEqual(runtime.on_deadline(self.clock[0]),outcome)
        receipt=state['runtime']['funding_finalizations'][0]
        self.assertEqual(receipt['flat_observed_at'],flat['broker_state_observed_at'])
        self.assertGreater(receipt['wall_wait_seconds'],0)
        self.assertEqual(receipt['source_snapshot_hash'],self.latest[0].snapshot_hash)

    def test_late_publication_and_stale_observation_never_finalize_or_create_zero(self):
        pending=self.close_pending()
        self.clock[0]=floor(self.initial)+timedelta(hours=8,seconds=2)
        self.observe(self.clock[0],missing_latest=True)
        self.assertEqual(self.runtime.on_deadline(self.clock[0]).status,'FUNDING_PENDING')
        self.observe(self.clock[0]);self.clock[0]+=timedelta(seconds=61)
        self.assertEqual(self.runtime.on_deadline(self.clock[0]).status,'FUNDING_PENDING')
        self.assertEqual(self.service.process.recover(self.ref.run_id).state['runtime']['closed_trades'],[])

    def test_crash_after_flat_checkpoint_replays_original_fills_before_pending_reconcile(self):
        self.prepare()
        for second,bars,price in ((0,True,'60000'),(1,False,'60000'),(2,False,'60020')):
            self.runtime.on_market_event(self.event(second,bars=bars,price=price))
        self.latest[0]=None
        with patch.object(type(self.service.canonical),'persist_fill',side_effect=RuntimeError('controlled fill publication crash')):
            with self.assertRaises(RuntimeError):self.runtime.on_market_event(self.event(3,price='60020'))
        crashed=self.service.process.recover(self.ref.run_id)
        self.assertIsNotNone(crashed.state['runtime']['pending_funding'])
        self.assertEqual(len(crashed.pending_operations),1)
        successor=self.enterContext(self.selected.owners.service())
        runtime=successor.runtime(self.ref.run_id)
        self.assertTrue(runtime.engine.reconciled,runtime.engine.recovery_reason)
        after=successor.process.recover(self.ref.run_id)
        self.assertEqual(after.pending_operations,())
        self.assertEqual(after.state['broker'],crashed.state['broker'])
        graph=successor.canonical.recover(position_id=after.state['runtime']['position']['position_id'])
        self.assertEqual(len(graph.fills),2)
        self.assertIsNone(graph.trade_result)

    def test_crash_between_final_funding_and_trade_result_republishes_same_effect(self):
        pending=self.close_pending()
        self.clock[0]=floor(self.initial)+timedelta(hours=8,seconds=2);self.observe(self.clock[0])
        with patch.object(type(self.service.canonical),'persist_trade_result',side_effect=RuntimeError('controlled financial publication crash')):
            with self.assertRaises(RuntimeError):self.runtime.on_deadline(self.clock[0])
        crashed=self.service.process.recover(self.ref.run_id)
        self.assertIsNone(crashed.state['runtime']['pending_funding'])
        self.assertEqual(len(crashed.state['runtime']['closed_trades']),1)
        operation=self.service.process.operation(self.ref.run_id,crashed.pending_operations[0])
        self.latest[0]=None  # Applied effects must not borrow a later source.
        successor=self.enterContext(self.selected.owners.service());runtime=successor.runtime(self.ref.run_id)
        self.assertTrue(runtime.engine.reconciled,runtime.engine.recovery_reason)
        recovered=successor.process.recover(self.ref.run_id)
        self.assertEqual(recovered.state,crashed.state)
        self.assertEqual(recovered.pending_operations,())
        self.assertEqual(successor.process.operation(self.ref.run_id,operation.operation_id).effect_hash,operation.effect_hash)

    def test_missing_source_blocks_entry_without_impairing_ordinary_owner(self):
        self.prepare();self.latest[0]=None
        outcome=self.runtime.on_market_event(self.event(0,bars=True))
        self.assertEqual(outcome.status,'BLOCKED')
        self.assertIn('PUBLIC_FUNDING_SOURCE_UNAVAILABLE',outcome.reason_codes)
        self.assertEqual(self.service.process.recover(self.ref.run_id).state['broker']['payload']['submissions'],[])

    def test_source_loss_does_not_credit_healthy_forward_time_while_protection_continues(self):
        self.prepare()
        self.service.monotonic_clock=lambda:int((self.clock[0]-self.initial).total_seconds()*1_000_000_000)
        self.runtime.on_market_event(self.event(0,bars=True));self.runtime.on_market_event(self.event(1))
        before=self.service.process.recover(self.ref.run_id).state['runtime']['forward']['real_healthy_ns']
        self.latest[0]=None
        self.runtime.on_market_event(self.event(2));self.runtime.on_market_event(self.event(3))
        state=self.service.process.recover(self.ref.run_id).state['runtime']
        self.assertEqual(state['position']['lifecycle_state'],'OPEN_PROTECTED')
        self.assertEqual(state['forward']['real_healthy_ns'],before)
        self.assertFalse(state['forward']['last_healthy'])

    def test_normal_control_port_requires_current_actual_owner_projection_without_source_attachment(self):
        self.prepare()
        from application.paper.funding_feed import funding_request,publish_health
        from application.paper.capture_archive import PublicCaptureArchive,ROOT
        from storage.paper_selection import open_paper_selections
        with open_paper_selections(self.config.database_path) as reader:selection=reader.current()
        request=funding_request(self.config,selection,self.supervisor.identity['process_generation_id'],now=self.clock[0])
        archive=PublicCaptureArchive(self.config.local_data_root/ROOT)
        import uuid
        token=str(uuid.uuid4());archive.reserve(token,kind='funding',maximum_requests=16,maximum_bytes=1024*1024)
        pointer=archive.commit(token,{'public-source.json':self.latest[0].canonical_json.encode()},requests=1,responses=1,complete=True)
        result=dict(provider_requests=1,provider_responses=1)
        publish_health(self.h.config_path,request,result,self.latest[0],pointer,state='PUBLIC_FUNDING_ACQUIRED',reason=None)
        # No E4 reader is installed in the control process. It must use its
        # separately verified native owner's bounded health projection.
        local_selected=load_ordinary_paper_owners(self.config,resolver=self.local.resolver,clock=lambda:self.clock[0])
        with local_selected.owners.service() as control:
            self.assertTrue(control.funding_start_ready())
            self.clock[0]+=timedelta(seconds=61)
            self.assertFalse(control.funding_start_ready())

    def test_pending_feedback_and_control_view_show_model_without_a_financial_sample(self):
        self.close_pending()
        from application.cloud.paper_feedback import build_paper_feedback,validate_paper_feedback
        from application.control_api.paper_ports import PaperReadControlPort
        from storage.paper_process import open_paper_process_journal
        from storage.runtime import open_paper_runtime_journal
        report=build_paper_feedback(self.runtime,performance_opt_in=True)
        self.assertEqual(report['schema_version'],'r7-paper-feedback-v0.3')
        self.assertEqual(report['funding']['status'],'FUNDING_PENDING')
        self.assertEqual(report['funding']['cost_basis'],'ACTUAL_ENTRY_FILL_NOTIONAL')
        self.assertEqual(report['funding']['pending_allocations'],1)
        self.assertIsNone(report['performance'])
        self.assertNotEqual(report['assessment']['status'],'PASS')
        validate_paper_feedback(report)
        from jsonschema import Draft202012Validator,FormatChecker
        from pathlib import Path
        schema=json.loads((Path(__file__).parents[2]/'contracts/paper_feedback_v0_3.schema.json').read_bytes())
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema,format_checker=FormatChecker()).validate(report)
        from copy import deepcopy
        from jsonschema import ValidationError
        tampered=[]
        value=deepcopy(report);value['funding']['cost_basis']='SETTLEMENT_MARK_PRICE';tampered.append(value)
        value=deepcopy(report);value['schema_version']='r7-paper-feedback-v0.2';tampered.append(value)
        value=deepcopy(report);value['funding']['pending_allocations']=0;tampered.append(value)
        value=deepcopy(report);value['assessment']['status']='PASS';tampered.append(value)
        for value in tampered:
            with self.assertRaises(ValueError):validate_paper_feedback(value)
            with self.assertRaises(ValidationError):Draft202012Validator(schema,format_checker=FormatChecker()).validate(value)
        from application.cloud.paper_feedback import paper_feedback_bundle
        from application.cloud.public_feedback import validate_public_feedback_publication
        bundle=paper_feedback_bundle(report)
        validate_public_feedback_publication(bundle.logical_path,dict(bundle.payloads))
        reader=PaperReadControlPort(namespace='LOCAL_RESEARCH',
            process_factory=lambda:open_paper_process_journal(self.config.database_path),
            canonical_factory=lambda:open_paper_runtime_journal(self.config.database_path),clock=lambda:self.clock[0])
        view=reader.view(self.ref.run_id)['payload']
        self.assertEqual(view['funding']['status'],'FUNDING_PENDING')
        self.assertEqual(Decimal(view['funding']['flat_observation']['actual_quantity']),0)
        self.assertEqual(view['closed_trades_count'],0)

    def test_actual_four_hour_valid_signal_blocked_by_source_is_counted_once_without_order(self):
        self.prepare(four_hour=True);self.assertEqual(self.runtime.engine.strategy.required_timeframe,'4h')
        self.latest[0]=None
        outcome=self.runtime.on_market_event(self.event(0,bars=True))
        self.assertEqual(outcome.status,'BLOCKED')
        self.runtime.on_market_event(self.event(1));self.runtime.on_market_event(self.event(2))
        state=self.service.process.recover(self.ref.run_id).state
        self.assertEqual(state['broker']['payload']['submissions'],[])
        impact=state['runtime']['funding_opportunities']
        self.assertEqual(impact['valid_blocked'],1)
        self.assertEqual(impact['evaluated_boundaries'],1)
        self.assertEqual(impact['records'][0]['risk_decision']['decision'],'APPROVE')
        from application.cloud.paper_feedback import build_paper_feedback
        report=build_paper_feedback(self.runtime)
        self.assertEqual(report['funding']['opportunities']['valid_blocked'],1)
        self.assertEqual(report['funding']['opportunities']['unresolved_financial'],0)

    def test_funding_pending_reason_changes_and_wait_survive_successor(self):
        self.close_pending()
        self.clock[0]=self.initial+timedelta(seconds=4);self.observe(self.clock[0])
        self.runtime.on_deadline(self.clock[0])
        self.latest[0]=None;self.clock[0]+=timedelta(seconds=1);self.runtime.on_deadline(self.clock[0])
        pending=self.service.process.recover(self.ref.run_id).state['runtime']['pending_funding']
        self.assertEqual([item['reason'] for item in pending['reason_history']],
            ['PUBLIC_FUNDING_SOURCE_UNAVAILABLE','FUNDING_SOURCE_INCOMPLETE','PUBLIC_FUNDING_SOURCE_UNAVAILABLE'])
        successor=self.enterContext(self.selected.owners.service());runtime=successor.runtime(self.ref.run_id)
        self.assertEqual(successor.process.recover(self.ref.run_id).state['runtime']['pending_funding'],pending)
        self.clock[0]=floor(self.initial)+timedelta(hours=8,seconds=2);self.observe(self.clock[0])
        runtime.on_deadline(self.clock[0])
        receipt=successor.process.recover(self.ref.run_id).state['runtime']['funding_finalizations'][0]
        self.assertEqual(receipt['reason_history'],pending['reason_history'])

    def test_actual_four_hour_pending_financial_risk_is_unknown_not_a_valid_missed_trade(self):
        self.prepare(four_hour=True)
        for second,bars,price in ((0,True,'60000'),(1,False,'60000'),(2,False,'60020'),(3,False,'60020')):
            self.runtime.on_market_event(self.event(second,bars=bars,price=price))
        self.assertIsNotNone(self.service.process.recover(self.ref.run_id).state['runtime']['pending_funding'])
        self.latest[0]=None
        from dataclasses import replace
        from market_data.candle import Candle
        event=self.event(14400,price='61000')
        candle=Candle('contracts-v0.1','BTC_USDT_PERP','4h',self.initial,self.initial+timedelta(hours=4),
            Decimal('60000'),Decimal('61001'),Decimal('59999'),Decimal('61000'),Decimal('1'),
            True,'CONTROLLED_NEXT4H_ONLY',received_at=self.clock[0])
        self.runtime.on_market_event(replace(event,candles=(candle,)))
        impact=self.service.process.recover(self.ref.run_id).state['runtime']['funding_opportunities']
        self.assertEqual(impact['valid_blocked'],0)
        self.assertEqual(impact['unresolved_financial'],1)
        self.assertEqual(impact['evaluated_boundaries'],1)
        self.assertEqual(impact['records'][0]['risk_decision']['account_state_status'],'UNKNOWN')


if __name__=='__main__':unittest.main()
