"""Trusted actual owner factory; FIXTURE mechanics never qualify production."""
from contextlib import closing
from dataclasses import replace
from datetime import datetime,timezone
import importlib,importlib.util,json,sqlite3,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch

from application.config import ProductConfig
from application.control_api.paper_ports import PaperStartControlPort
from application.paper.worker import PaperOwnerWorker
from registry import EvidenceGateError
from registry.operational_authority import HumanAuthenticator
from storage import open_sqlite_platform
from storage.runtime import open_paper_runtime_journal
from tests.application.paper_owner_fixtures import PaperOwnerFixture
from tests.product.test_paper_runtime_v02 import simulation_fixture
from tests.application.test_product_assessment_binding import risk_fixture
from tests.validation.test_paper_promotion_policy import policy_fixture

NOW=datetime(2026,10,8,tzinfo=timezone.utc)

class PaperOwnerCompositionTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.owners'),'Trusted same-store PAPER composition is missing')
        return importlib.import_module('application.paper.owners')

    def values(self,**changes):
        values=dict(namespace='FIXTURE',simulation_policy=simulation_fixture(),risk_policy=risk_fixture(),
            promotion_policy=policy_fixture(),paper_policy_ref='owner-fixture-policy',actor='fixture-paper-owner',
            workflow_authorized=True,submission_validity={'intent_class':'EVERGREEN_STRATEGY','validity':{'from':None,'until':None}})
        values.update(changes);return values

    def selection(self,m,**changes):return m.PaperOwnerSelection(**self.values(**changes))

    def composition(self,m,f,**changes):
        args=dict(selection=self.selection(m),current_release=lambda:f.release,
            authenticator=HumanAuthenticator(namespace='FIXTURE',reauth_seconds=300,verifier=lambda _:None,clock=lambda:f.h.clock[0]),
            clock=lambda:f.h.clock[0]);args.update(changes)
        return m.PaperOwnerComposition(f.config,**args)

    def fixture(self):return PaperOwnerFixture(self)

    def test_selection_is_a_deep_immutable_observation_of_explicit_policies(self):
        m=self.module();values=self.values();selection=m.PaperOwnerSelection(**values)
        values['simulation_policy']['quantity']='99';values['risk_policy']['policy']['max_margin']='99'
        view=selection.as_dict();view['simulation_policy']['quantity']='88'
        self.assertEqual(selection.as_dict()['simulation_policy']['quantity'],'0.001')
        self.assertEqual(selection.as_dict()['risk_policy']['policy']['max_margin'],'100')
        with self.assertRaises((AttributeError,TypeError)):selection.namespace='LOCAL_RESEARCH'

    def test_selection_rejects_truthy_workflow_and_unknown_fields(self):
        m=self.module()
        for value in (1,'yes',None):
            with self.subTest(value=value),self.assertRaises(ValueError):self.selection(m,workflow_authorized=value)
        with self.assertRaises(TypeError):self.selection(m,passed=True)

    def test_selection_uses_existing_same_namespace_policy_validators(self):
        m=self.module()
        for field in ('simulation_policy','risk_policy','promotion_policy'):
            values=self.values();values[field]['namespace']='LOCAL_RESEARCH'
            with self.subTest(field=field),self.assertRaises(ValueError):m.PaperOwnerSelection(**values)
        with self.assertRaises(ValueError):self.selection(m,submission_validity={'intent_class':'EVERGREEN_STRATEGY'})

    def test_unbounded_actor_policy_reference_and_namespace_are_rejected(self):
        m=self.module()
        for changes in ({'actor':''},{'actor':'x'*257},{'paper_policy_ref':''},{'paper_policy_ref':'x'*257},{'namespace':'LIVE'}):
            with self.subTest(changes=list(changes)),self.assertRaises(ValueError):self.selection(m,**changes)

    def test_actual_start_port_prepares_e6_run_without_attaching_runtime_generation(self):
        m=self.module();f=self.fixture();owners=self.composition(m,f)
        with f.h.registry_factory() as registry:revision=registry.get_strategy(f.identity).registry_revision
        port=PaperStartControlPort(namespace='FIXTURE',service_factory=owners.service)
        result=port.start(dict(strategy_id=f.identity.strategy_id,strategy_version=f.identity.strategy_version,policy_id='owner-fixture-policy'),
            actor='fixture-owner',command_id='composed-start',expected_revision=revision)
        run_id=result['effect_ref'].removeprefix('paper:')
        self.assertEqual(result['status'],'COMPLETE');self.assertEqual(f.recover(run_id).process_generation,0)
        with f.h.registry_factory() as registry:self.assertEqual(registry.get_strategy(f.identity).current_lifecycle_state,'PAPER')

    def test_independent_worker_uses_composition_for_actual_protection_and_flat_close(self):
        m=self.module();f=self.fixture();owners=self.composition(m,f);run_id=f.start()
        with PaperOwnerWorker(f.config,owners.service,namespace='FIXTURE') as worker:
            worker.tick()
            for second,price,bars,expected in [(0,'60000',True,'ACKNOWLEDGED'),(1,'60000',False,'PROTECTED'),(2,'60020',False,'EXIT_REQUESTED'),(3,'60020',False,'CLOSED')]:
                self.assertTrue(worker.submit_event(run_id,f.event(second,price,bars)))
                self.assertIn(expected,[row.status for row in worker.tick()[run_id]])
            recovered=f.recover(run_id);position=recovered.state['runtime']['position']
            self.assertEqual(position['lifecycle_state'],'CLOSED');self.assertEqual(len(recovered.state['runtime']['closed_trades']),1)
            self.assertEqual(worker.service.canonical.recover(position_id=position['position_id']).status,'READY')

    def test_factory_can_be_created_on_control_thread_and_opened_on_owner_thread(self):
        m=self.module();f=self.fixture();owners=self.composition(m,f);outcomes=[]
        def own():
            try:
                with owners.service() as service:
                    outcomes.append(service.registry.lifecycle_counts())
                    outcomes.append(service.process._db.execute('SELECT 1').fetchone()[0])
            except BaseException as error:outcomes.append(error)
        thread=threading.Thread(target=own);thread.start();thread.join(20)
        self.assertFalse(thread.is_alive());self.assertEqual(outcomes[-1],1);self.assertFalse(any(isinstance(row,BaseException) for row in outcomes))

    def test_all_actual_owner_connections_close_on_context_failure(self):
        m=self.module();f=self.fixture();owners=self.composition(m,f);connections=[]
        with self.assertRaisesRegex(RuntimeError,'controlled consumer failure'):
            with owners.service() as service:
                connections=[service.registry._store._connection,service.process._db,service.canonical._store._connection]
                raise RuntimeError('controlled consumer failure')
        for connection in connections:
            with self.assertRaises(sqlite3.ProgrammingError):connection.execute('SELECT 1')
        with owners.service() as service:self.assertTrue(service.registry.lifecycle_counts())

    def test_denied_workflow_cannot_create_or_accept_a_paper_run(self):
        m=self.module();f=self.fixture();owners=self.composition(m,f,selection=self.selection(m,workflow_authorized=False))
        with f.h.registry_factory() as registry:revision=registry.get_strategy(f.identity).registry_revision
        with owners.service() as service:
            with self.assertRaises(EvidenceGateError):service.start(f.identity,'owner-fixture-policy',revision,'denied-start')
        with f.h.registry_factory() as registry:self.assertEqual(registry.get_strategy(f.identity).current_lifecycle_state,'CANDIDATE')
        with closing(sqlite3.connect(f.config.database_path)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM paper_process_runs').fetchone()[0],0)

    def test_restore_inhibition_prevents_new_start_even_with_selected_workflow(self):
        m=self.module();f=self.fixture();f.restore_inhibited(self);owners=self.composition(m,f)
        with owners.service() as service:self.assertFalse(service.authorized)
        self.assertTrue(owners.selection.as_dict()['workflow_authorized'])

    def test_unavailable_release_reader_is_not_replaced_by_current_source_or_pass_json(self):
        m=self.module();f=self.fixture()
        def missing():raise EvidenceGateError('PM_PROFILE_NOT_ACCEPTED')
        owners=self.composition(m,f,current_release=missing)
        with f.h.registry_factory() as registry:revision=registry.get_strategy(f.identity).registry_revision
        with owners.service() as service:
            with self.assertRaisesRegex(EvidenceGateError,'PM_PROFILE_NOT_ACCEPTED'):service.start(f.identity,'owner-fixture-policy',revision,'blocked-profile')
        with f.h.registry_factory() as registry:self.assertEqual(registry.get_strategy(f.identity).current_lifecycle_state,'CANDIDATE')
        with closing(sqlite3.connect(f.config.database_path)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM paper_process_runs').fetchone()[0],0)

    def test_same_namespace_authenticator_and_bounded_local_store_are_required(self):
        m=self.module();f=self.fixture()
        auth=HumanAuthenticator(namespace='LOCAL_RESEARCH',reauth_seconds=300,verifier=lambda _:None,clock=lambda:NOW)
        with self.assertRaises(ValueError):self.composition(m,f,authenticator=auth)
        bad=replace(f.config,database_path=f.config.local_data_root.parent/'outside-paper.sqlite3')
        with self.assertRaises(ValueError):m.PaperOwnerComposition(bad,selection=self.selection(m),current_release=lambda:f.release,
            authenticator=HumanAuthenticator(namespace='FIXTURE',reauth_seconds=300,verifier=lambda _:None,clock=lambda:NOW),clock=lambda:NOW)
        self.assertFalse(bad.database_path.exists())

    def test_missing_canonical_database_is_not_initialized_by_factory(self):
        m=self.module();f=self.fixture();config=replace(f.config,database_path=f.config.local_data_root/'missing-composition.sqlite3')
        owners=m.PaperOwnerComposition(config,selection=self.selection(m),current_release=lambda:f.release,
            authenticator=HumanAuthenticator(namespace='FIXTURE',reauth_seconds=300,verifier=lambda _:None,clock=lambda:NOW),clock=lambda:NOW)
        with self.assertRaises((ValueError,sqlite3.Error)):
            with owners.service():self.fail('Missing canonical store was created')
        self.assertFalse(config.database_path.exists())

    def test_parent_path_cannot_open_or_mutate_an_existing_outside_store(self):
        m=self.module()
        with tempfile.TemporaryDirectory(prefix='R7 paper outside store ') as directory:
            parent=Path(directory).resolve();root=parent/'inside';root.mkdir()
            outside=parent/'outside-paper.sqlite3'
            with open_sqlite_platform(outside,research_namespace='FIXTURE'):pass
            before=outside.read_bytes()
            for selected_root,path in ((root,root/'..'/'outside-paper.sqlite3'),
                                       (root/'..',root/'..'/'outside-paper.sqlite3')):
                config=ProductConfig('r7-product-config-v0.2','outside-store-fixture',selected_root,None,path)
                with self.subTest(root_parts=selected_root.parts),patch.object(m,'open_sqlite_platform',wraps=m.open_sqlite_platform) as opened:
                    with self.assertRaises(ValueError):
                        owners=m.PaperOwnerComposition(config,selection=self.selection(m),current_release=lambda:None,
                            authenticator=HumanAuthenticator(namespace='FIXTURE',reauth_seconds=300,verifier=lambda _:None,clock=lambda:NOW),clock=lambda:NOW)
                        with owners.service():pass
                    opened.assert_not_called()
                    self.assertEqual(outside.read_bytes(),before)


    def test_local_research_diagnostic_defaults_do_not_enable_selected_workflow(self):
        m=self.module()
        with tempfile.TemporaryDirectory(prefix='R7 local selected paper ') as directory:
            root=Path(directory).resolve();path=root/'canonical.sqlite3'
            with open_sqlite_platform(path,research_namespace='LOCAL_RESEARCH'):pass
            config=ProductConfig('r7-product-config-v0.2','local-selected-fixture',root,None,path)
            values=self.values(namespace='LOCAL_RESEARCH',promotion_policy=policy_fixture('LOCAL_RESEARCH'))
            values['simulation_policy'].update(namespace='LOCAL_RESEARCH',mode='REAL_TIME')
            values['risk_policy']['namespace']='LOCAL_RESEARCH';selection=m.PaperOwnerSelection(**values)
            def unavailable():raise EvidenceGateError('PM_PROFILE_NOT_ACCEPTED')
            owners=m.PaperOwnerComposition(config,selection=selection,current_release=unavailable,
                authenticator=HumanAuthenticator(namespace='LOCAL_RESEARCH',reauth_seconds=300,verifier=lambda _:None,clock=lambda:NOW),clock=lambda:NOW)
            with owners.service() as service:
                self.assertFalse(service.authorized);self.assertEqual(service.simulation.as_dict()['mode'],'REAL_TIME')
            with closing(sqlite3.connect(path)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM paper_process_runs').fetchone()[0],0)

    def test_existing_other_namespace_is_not_rebound_by_paper_factory(self):
        m=self.module()
        with tempfile.TemporaryDirectory(prefix='R7 paper namespace ') as directory:
            root=Path(directory).resolve();path=root/'canonical.sqlite3'
            with open_sqlite_platform(path,research_namespace='LOCAL_RESEARCH'):pass
            config=ProductConfig('r7-product-config-v0.2','paper-namespace-fixture',root,None,path)
            owners=m.PaperOwnerComposition(config,selection=self.selection(m),current_release=lambda:None,
                authenticator=HumanAuthenticator(namespace='FIXTURE',reauth_seconds=300,verifier=lambda _:None,clock=lambda:NOW),clock=lambda:NOW)
            with self.assertRaises(EvidenceGateError):
                with owners.service():self.fail('Another canonical namespace was rebound')
            with closing(sqlite3.connect(path)) as db:self.assertEqual(db.execute('SELECT namespace FROM registry_research_namespace').fetchone()[0],'LOCAL_RESEARCH')


class PaperOwnerExistingStoreTests(unittest.TestCase):
    def test_platform_existing_mode_rejects_missing_database_without_creation(self):
        with tempfile.TemporaryDirectory(prefix='R7 owner missing store ') as directory:
            path=Path(directory)/'canonical.sqlite3'
            try:
                with open_sqlite_platform(path,research_namespace='FIXTURE',require_existing=True):self.fail('Missing store created')
            except TypeError:self.fail('Supported existing-store E6 factory policy is missing')
            except sqlite3.Error:pass
            self.assertFalse(path.exists())

    def test_canonical_runtime_existing_mode_rejects_missing_database_without_creation(self):
        with tempfile.TemporaryDirectory(prefix='R7 owner missing runtime ') as directory:
            path=Path(directory)/'canonical.sqlite3'
            try:
                with open_paper_runtime_journal(path,require_existing=True):self.fail('Missing runtime store created')
            except TypeError:self.fail('Supported existing-store runtime factory policy is missing')
            except sqlite3.Error:pass
            self.assertFalse(path.exists())

    def test_runtime_migration_failure_closes_actual_open_connection(self):
        import storage._paper_runtime as storage
        with tempfile.TemporaryDirectory(prefix='R7 owner migration failure ') as directory:
            path=Path(directory)/'canonical.sqlite3';captured=[];original=storage._connect
            def connect(*args,**kwargs):
                db=original(*args,**kwargs);captured.append(db);return db
            with patch.object(storage,'_connect',side_effect=connect),patch.object(storage,'_apply_migrations',side_effect=RuntimeError('controlled migration failure')):
                with self.assertRaisesRegex(RuntimeError,'controlled migration failure'):open_paper_runtime_journal(path)
            try:
                self.assertEqual(len(captured),1)
                with self.assertRaises(sqlite3.ProgrammingError):captured[0].execute('SELECT 1')
            finally:
                for db in captured:db.close()


if __name__=='__main__':unittest.main()
