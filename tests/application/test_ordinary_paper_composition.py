"""Actual LOCAL owners and ledger; synthetic native boundary is unit evidence.

Fresh LOCAL input generation and actual research create the candidate. Nothing
is copied from FIXTURE result rows. External source/native build measurements
are controlled unit fixtures; actual PID/history/runtime identity is used.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from types import SimpleNamespace
import json
import os
import unittest
from unittest.mock import patch

from application.config import load_config
from application.local_owners import LocalOwners
from application.paper.ordinary_setup import configure_ordinary_paper, load_ordinary_paper_owners
from application.paper.release import NativePaperReleaseReader
from application.paper.service import PaperMarketEvent
from application.paper.worker import PaperOwnerWorker
from application.platform.runtime_identity import read_runtime_identity, RuntimeIdentityUnavailable
from application.research.evidence import capture_provenance
from market_data.candle import Candle
from market_data.current import MarketSnapshot
from registry import EvidenceGateError, StrategyIdentity
from storage.paper_process import open_paper_process_journal
from storage.paper_selection import open_paper_selections, _open_paper_selection_owner
from tests.application import dataset_fixtures
from tests.application import test_research_setup_flow
from tests.product.test_paper_runtime_v02 import simulation_fixture
from tests.validation.test_paper_promotion_policy import policy_fixture
from tests.validation.robustness_fixtures import subject
from strategy.v02.capabilities import build_capability_snapshot


class OrdinaryPaperCompositionTests(unittest.TestCase):
    def prepare(self,*,simulation=None,private_data=False):
        h=test_research_setup_flow.ResearchSetupFlowTests()
        h.setUp();self.addCleanup(h.doCleanups)
        def initialize():
            h.call(['init-profile','--config',str(h.config_path),'--data-root',str(h.data),
                '--cloud-root',str(h.cloud),'--instance-id','ordinary-composition-unit',
                '--enable-paper-runtime'])
            if private_data:
                from application.platform.private_files import create_private_directory
                create_private_directory(h.data)
            return load_config(h.config_path)
        h.initialize=initialize
        config=h.prepare();h.configure()
        clock=[datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)+timedelta(hours=1)]
        local=LocalOwners(config,namespace='LOCAL_RESEARCH',clock=lambda:clock[0])
        with local.inbox_factory() as inbox:inbox.scan_once(clock[0])
        revision=local.queue.selected_submission_revision('public-flow-input','selected-test')
        receipt=local.queue.enqueue('public-flow-input','selected-test','ordinary-unit-enqueue',revision,actor='unit-operator')
        claim=local.queue.claim_next();self.assertEqual(claim.run_id,receipt['run_id'])
        research_measurement={**capture_provenance(),'worktree':'CLEAN'}
        # Explicit unit provenance fixture permits dirty development execution.
        # No installed qualification or exact-clean acceptance credit is issued.
        with patch('application.research.service.capture_provenance',return_value=research_measurement):
            outcome=local.queue.step(claim.run_id,claim.generation)
        self.assertEqual(outcome['state'],'COMPLETE',outcome)
        self.assertEqual(outcome['outcome']['strategy_lifecycle'],'CANDIDATE')
        simulation=simulation_fixture() if simulation is None else dict(simulation)
        simulation.update(namespace='LOCAL_RESEARCH',mode='REAL_TIME')
        (h.data/'paper-sim.json').write_text(json.dumps(simulation),encoding='utf-8')
        (h.data/'paper-promotion.json').write_text(json.dumps(policy_fixture('LOCAL_RESEARCH')),encoding='utf-8')
        operator=h.root/'paper-inputs.json'
        operator.write_text(json.dumps(dict(schema_version='r7-local-paper-inputs-v0.2',
            submission_id='public-flow-input',simulation_policy_ref='paper-sim.json',
            risk_policy_ref='risk.json',promotion_policy_ref='paper-promotion.json',
            paper_policy_ref='ordinary-unit-policy',actor='explicit-unit-operator',workflow_authorized=True,
            account_ref='explicit-isolated-unit-paper-account',qualification_receipt_ref='qualification-'+'a'*64)),encoding='utf-8')
        provenance=capture_provenance()
        provenance.update(worktree='UNAVAILABLE',build_hash='sha256:'+'7'*64,
                          distribution_profile='r7-native-distribution-v0.2')
        facts={key:provenance[key] for key in ('implementation_hash','executable_revision','build_hash','distribution_profile')}
        facts.update(capability_hash=build_capability_snapshot().snapshot_hash,platform_id='windows-11-x86_64',
            worktree='UNAVAILABLE',financial_authority='NONE')
        eligible=[True]
        def measured(reader):
            if not eligible[0]:raise ValueError('Synthetic unit native receipt unavailable')
            return dict(facts)
        self.enterContext(patch.object(NativePaperReleaseReader,'software_eligible',measured))
        # Only the software/installed boundary is controlled; actual durable
        # selection and actual PID/generation reads still execute. No native credit.
        self.enterContext(patch('application.paper.release.sys',SimpleNamespace(frozen=True)))
        def observation(reader,selection):return measured(reader)
        self.enterContext(patch('application.paper.release_observation.ControlReleaseObservation.current',observation))
        self.enterContext(patch('application.paper.release_observation.check_native_once',side_effect=lambda *a,**kw:(dict(facts=dict(facts)),0,0)))
        self.enterContext(patch('application.platform.supervision.capture_provenance',return_value=provenance))
        configured=configure_ordinary_paper(h.config_path,operator)
        self.assertEqual(configured['config_generation'],1)
        self.assertEqual(configure_ordinary_paper(h.config_path,operator)['config_generation'],1)
        selected=load_ordinary_paper_owners(config,resolver=local.resolver,clock=lambda:clock[0])
        return h,config,local,clock,selected,eligible

    @contextmanager
    def no_hot_hashes(self):
        with patch('application.paper.release._revision',side_effect=AssertionError('No hot source hash')), \
                patch('application.paper.service._revision',side_effect=AssertionError('No hot service source hash')), \
                patch('strategy.v02.capabilities._revision',side_effect=AssertionError('No hot capability/source hashing')):
            yield

    def event(self,clock,initial,second,*,bars=False,price='60000'):
        now=initial+timedelta(seconds=second);clock[0]=now
        snapshot=MarketSnapshot('contracts-v0.1','BTC_USDT_PERP',now,now,'HEALTHY',
            'SYNTHETIC_LOCAL_UNIT_ONLY',last_price=Decimal(price),freshness_ms=0)
        candles=tuple(Candle('contracts-v0.1','BTC_USDT_PERP','1h',
            initial-timedelta(hours=2-i),initial-timedelta(hours=1-i),
            Decimal(value),Decimal(value)+1,Decimal(value)-1,Decimal(value),Decimal('1'),
            True,'SYNTHETIC_LOCAL_UNIT_ONLY',received_at=initial)
            for i,value in enumerate(('59000','60000'))) if bars else ()
        return PaperMarketEvent(snapshot,candles,'PUBLIC_MARKET')

    def test_observer_verifies_actual_sealed_inputs_without_writing_store_and_denies_mutation(self):
        h,config,local,clock,selected,_=self.prepare()
        from application.paper.release_observation import validate_selected_inputs
        with open_paper_selections(config.database_path) as reader:selection=reader.current()
        facts=dict(implementation_hash=selected.implementation_hash,capability_hash=build_capability_snapshot().snapshot_hash)
        def hashes():return {p.relative_to(config.local_data_root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in config.local_data_root.rglob('*') if p.is_file()}
        before=hashes();validate_selected_inputs(config,selection,facts);self.assertEqual(before,hashes())
        policy=config.local_data_root/selection.as_dict()['source_subject']['input_refs']['simulation_policy_ref']
        original=policy.read_bytes();policy.write_bytes(original+b' ')
        with self.assertRaises(ValueError):validate_selected_inputs(config,selection,facts)
        policy.write_bytes(original)
        self.assertEqual(before,hashes())

    def test_normal_local_port_idle_bootstrap_real_history_selection_change_protective_successor(self):
        h,config,local,clock,selected,eligible=self.prepare();initial=clock[0]
        identity=StrategyIdentity(subject()['strategy_id'],subject()['strategy_version'])
        services=local.control_services();port=services.paper_start
        self.assertIsNotNone(port)
        with local.registry_factory() as registry:revision=registry.get_strategy(identity).registry_revision
        arguments=dict(strategy_id=identity.strategy_id,strategy_version=identity.strategy_version,policy_id='ordinary-unit-policy')
        with self.assertRaises((EvidenceGateError,RuntimeIdentityUnavailable)):
            port.start(arguments,actor='unit-operator',command_id='ordinary-no-runtime',expected_revision=revision)
        self.assertFalse((config.local_data_root/'process-supervision.sqlite').exists())
        with local.registry_factory() as registry:self.assertEqual(len(registry.list_accepted_paper_starts()),0)
        @contextmanager
        def factory():
            current=load_ordinary_paper_owners(config,resolver=local.resolver,clock=lambda:clock[0])
            with current.owners.service() as service:yield service
        with PaperOwnerWorker(config,factory,namespace='LOCAL_RESEARCH') as worker:
            with self.no_hot_hashes():
                worker.tick();self.assertEqual(worker.snapshot()['active_runs'],())
                observed=read_runtime_identity(config)
                self.assertEqual(observed.identity['pid'],os.getpid())
                self.assertEqual(observed.identity['generation'],1)
                release=selected.current();self.assertEqual(release.config_generation,1);self.assertEqual(release.runtime_generation,1)
                result=port.start(arguments,actor='unit-operator',command_id='ordinary-unit-start',expected_revision=revision)
                run=result['effect_ref'].removeprefix('paper:');worker.tick()
                for second,bars in ((0,True),(1,False)):
                    worker.submit_event(run,self.event(clock,initial,second,bars=bars));worker.tick()
                before=worker.service.process.recover(run)
                self.assertEqual(before.state['runtime']['position']['lifecycle_state'],'OPEN_PROTECTED')
        # Product configuration and selection both change, keeping the same
        # canonical data. Recovery must retain the ORIGINAL commitments.
        from dataclasses import replace
        config=replace(config,control_api_port=config.control_api_port+1)
        with open_paper_selections(config.database_path) as reader:record=reader.current().as_dict()
        from application.paper.owners import PaperOwnerSelection
        from application.paper.release import operational_record
        original=record['owner'];original['simulation_policy']['quantity']='0.002'
        changed=operational_record(config,PaperOwnerSelection(**original),account_ref=record['envelope']['account_ref'])
        changed['source_subject']=record['source_subject']
        with _open_paper_selection_owner(config.database_path) as writer:self.assertEqual(writer.select(changed).generation,2)
        eligible[0]=False  # Unit native currentness loss must not block protection.
        self.assertTrue(hasattr(NativePaperReleaseReader,'management_eligible'),
            'Receipt loss must allow exact native existing-owner recovery without new-entry authority')
        from dataclasses import asdict
        native_facts=asdict(release)
        native_facts['distribution_profile']='r7-native-distribution-v0.2'
        with patch.object(NativePaperReleaseReader,'_installed_facts',return_value=native_facts):
            native=NativePaperReleaseReader(config,receipt_ref=selected.native.receipt_ref)
            admission=native.management_eligible()
        self.assertEqual(admission['status'],'ENTRY_INHIBITED_EXISTING_OWNER_RECOVERY')
        self.assertEqual(admission['financial_authority'],'NONE')
        with self.assertRaises(ValueError):native.current()
        with PaperOwnerWorker(config,factory,namespace='LOCAL_RESEARCH') as worker:
            with self.no_hot_hashes():
                worker.tick();self.assertEqual(read_runtime_identity(config).identity['generation'],2)
                self.assertTrue(worker.service.process.entry_pause_requested(run))
                self.assertEqual(worker.service.runtime(run).service.simulation.as_dict()['quantity'],'0.001')
                for second in (2,3):
                    worker.submit_event(run,self.event(clock,initial,second,price='60020'));worker.tick()
                closed=worker.service.process.recover(run)
            self.assertEqual(closed.binding,before.binding)
            self.assertEqual(closed.state['runtime']['exit_anchor'],before.state['runtime']['exit_anchor'])
            self.assertEqual(closed.state['runtime']['position']['position_id'],before.state['runtime']['position']['position_id'])
            self.assertEqual(closed.state['runtime']['position']['lifecycle_state'],'CLOSED')
            self.assertEqual(Decimal(closed.state['runtime']['position']['actual_quantity']),0)
            self.assertEqual(len(closed.state['runtime']['closed_trades']),1)
            self.assertEqual(closed.state['runtime']['forward']['simulated_elapsed_seconds'],0)
            self.assertGreaterEqual(closed.state['runtime']['forward']['real_elapsed_ns'],0)


if __name__=='__main__':unittest.main()
