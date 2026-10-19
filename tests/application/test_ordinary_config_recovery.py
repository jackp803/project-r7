"""Draft real owner regression; copied into test inventory after native guard."""
from contextlib import contextmanager
from dataclasses import replace
from decimal import Decimal
from contextlib import redirect_stdout
from unittest.mock import patch
import io,json,sys,unittest
from types import SimpleNamespace
from application.local_owners import LocalOwners
from application.paper.ordinary_setup import load_ordinary_paper_owners
from application.paper.worker import PaperOwnerWorker
from registry import EvidenceGateError,StrategyIdentity
from storage.paper_selection import open_paper_selections
from storage.paper_process import open_paper_process_journal
from tests.application import test_ordinary_paper_composition as original
from tests.validation.robustness_fixtures import subject

class OrdinaryConfigRecoveryTests(unittest.TestCase):
    prepare=original.OrdinaryPaperCompositionTests.prepare
    event=original.OrdinaryPaperCompositionTests.event
    no_hot_hashes=original.OrdinaryPaperCompositionTests.no_hot_hashes

    def test_config_only_change_keeps_read_pause_original_protection_and_exit_without_new_entry(self):
        h,config,local,clock,selected,eligible=self.prepare();initial=clock[0]
        identity=StrategyIdentity(subject()['strategy_id'],subject()['strategy_version'])
        with local.registry_factory() as registry:revision=registry.get_strategy(identity).registry_revision
        arguments=dict(strategy_id=identity.strategy_id,strategy_version=identity.strategy_version,policy_id='ordinary-unit-policy')
        @contextmanager
        def factory():
            current=load_ordinary_paper_owners(config,resolver=local.resolver,clock=lambda:clock[0])
            with current.owners.service() as service:yield service
        with PaperOwnerWorker(config,factory,namespace='LOCAL_RESEARCH') as worker:
            worker.tick()
            result=local.control_services().paper_start.start(arguments,actor='unit-operator',
                command_id='config-only-original-start',expected_revision=revision)
            run=result['effect_ref'].removeprefix('paper:');worker.tick()
            for second,bars in ((0,True),(1,False)):
                worker.submit_event(run,self.event(clock,initial,second,bars=bars));worker.tick()
            before=worker.service.process.recover(run)
            self.assertEqual(before.state['runtime']['position']['lifecycle_state'],'OPEN_PROTECTED')
        with open_paper_selections(config.database_path) as reader:original_selection=reader.current()
        config=replace(config,control_api_port=config.control_api_port+1)
        changed=LocalOwners(config,namespace='LOCAL_RESEARCH',clock=lambda:clock[0])
        services=changed.control_services()
        self.assertIsNotNone(services.paper_start)
        self.assertFalse(services.view('health')['live_authorized'])
        self.assertEqual(services.view('paper_runs',subject=run)['status'],'LAST_KNOWN_OWNER_FACTS')
        paused=services.execute('PAPER_PAUSE','paper:'+run,{},actor='unit-operator',human=None,
            command_id='config-only-pause',expected_revision=services.paper_reader.revision(run))
        self.assertEqual(paused['status'],'PAUSED')
        with PaperOwnerWorker(config,factory,namespace='LOCAL_RESEARCH') as worker:
            with self.no_hot_hashes():
                worker.tick()
                self.assertTrue(worker.service.process.entry_pause_requested(run))
                self.assertEqual(worker.service.runtime(run).service.simulation.as_dict()['quantity'],'0.001')
                with self.assertRaises(EvidenceGateError):changed.selected_paper.current()
                protected=worker.service.process.recover(run)
                self.assertEqual(protected.binding,before.binding)
                self.assertEqual(protected.state['runtime']['exit_anchor'],before.state['runtime']['exit_anchor'])
                for second in (2,3):
                    worker.submit_event(run,self.event(clock,initial,second,price='60020'));worker.tick()
                closed=worker.service.process.recover(run)
            self.assertEqual(closed.binding,before.binding)
            self.assertEqual(closed.state['runtime']['position']['position_id'],before.state['runtime']['position']['position_id'])
            self.assertEqual(closed.state['runtime']['position']['lifecycle_state'],'CLOSED')
            self.assertEqual(Decimal(closed.state['runtime']['position']['actual_quantity']),0)
            self.assertEqual(len(closed.state['runtime']['closed_trades']),1)
        with open_paper_selections(config.database_path) as reader:self.assertEqual(reader.current(),original_selection)

    def test_actual_ordinary_worker_bootstrap_recovers_config_only_change_on_receipt_loss(self):
        h,config,local,clock,selected,eligible=self.prepare();initial=clock[0]
        identity=StrategyIdentity(subject()['strategy_id'],subject()['strategy_version'])
        with local.registry_factory() as registry:revision=registry.get_strategy(identity).registry_revision
        arguments=dict(strategy_id=identity.strategy_id,strategy_version=identity.strategy_version,policy_id='ordinary-unit-policy')
        @contextmanager
        def factory():
            current=load_ordinary_paper_owners(config,resolver=local.resolver,clock=lambda:clock[0])
            with current.owners.service() as service:yield service
        with PaperOwnerWorker(config,factory,namespace='LOCAL_RESEARCH') as worker:
            worker.tick()
            run=local.control_services().paper_start.start(arguments,actor='unit-operator',
                command_id='bootstrap-config-start',expected_revision=revision)['effect_ref'].removeprefix('paper:')
            worker.tick()
            for second,bars in ((0,True),(1,False)):
                worker.submit_event(run,self.event(clock,initial,second,bars=bars));worker.tick()
            before=worker.service.process.recover(run)
            self.assertEqual(before.state['runtime']['position']['lifecycle_state'],'OPEN_PROTECTED')
        facts=selected.native.software_eligible();eligible[0]=False
        config=replace(config,control_api_port=config.control_api_port+1)
        raw=json.loads(h.config_path.read_bytes());raw['control_api_port']=config.control_api_port
        h.config_path.write_text(json.dumps(raw),encoding='utf-8')
        from application.paper import ordinary_setup,release_observation
        from application.paper.release import NativePaperReleaseReader
        calls=[]
        def native_check(path,ref,**kwargs):
            calls.append(kwargs.get('mode','software'))
            if kwargs.get('mode')!='management':raise ValueError('UNIT_RECEIPT_UNAVAILABLE_NO_NATIVE_CREDIT')
            with patch.object(NativePaperReleaseReader,'_installed_facts',return_value=facts):
                verified=NativePaperReleaseReader(config,receipt_ref=ref).management_eligible()
            self.assertEqual(verified['new_entry'],'INHIBITED')
            return dict(facts=facts),0,0
        class InhibitedObserver:
            def __init__(self,*args,**kwargs):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def current(self,selection):raise ValueError('UNIT_CURRENT_ENTRY_INHIBITED')
        actual_local=LocalOwners
        with patch.dict(sys.modules,{'sys':SimpleNamespace(**{**vars(sys),'frozen':True})}),\
                patch.object(release_observation,'check_native_once',side_effect=native_check),\
                patch.object(release_observation,'OwnerReleaseObservation',InhibitedObserver),\
                patch('application.local_owners.LocalOwners',side_effect=lambda config,**kw:actual_local(config,clock=lambda:clock[0],**kw)),\
                redirect_stdout(io.StringIO()) as output:
            code=ordinary_setup.ordinary_paper_worker(h.config_path,maximum_ticks=1)
        self.assertEqual(code,0,output.getvalue());self.assertEqual(calls,['software','management'])
        result=json.loads(output.getvalue());self.assertEqual(result['provider_requests'],0)
        self.assertEqual(result['financial_authority'],'NONE')
        with open_paper_process_journal(config.database_path,require_existing=True) as reader:
            recovered=reader.recover(run)
            self.assertTrue(reader.entry_pause_requested(run))
        self.assertEqual(recovered.binding,before.binding)
        self.assertEqual(recovered.state['runtime']['exit_anchor'],before.state['runtime']['exit_anchor'])
        self.assertEqual(recovered.state['runtime']['position']['lifecycle_state'],'OPEN_PROTECTED')
        with open_paper_selections(config.database_path) as reader:self.assertEqual(reader.current().generation,1)

if __name__=='__main__':unittest.main()
