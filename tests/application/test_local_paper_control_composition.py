"""Actual normal owner composition reads/pauses same-store PAPER without attach."""
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from application.config import ProductConfig
from application.local_owners import LocalOwners
from application.control_api.errors import APIError
from application.control_api.paper_ports import PaperReadControlPort
from application.paper.worker import PaperOwnerWorker
from registry import EvidenceGateError
from tests.application.paper_owner_fixtures import PaperOwnerFixture


class LocalPaperControlCompositionTests(unittest.TestCase):
    def fixture_services(self):
        self.f=PaperOwnerFixture(self)
        services=LocalOwners(self.f.config,namespace='FIXTURE',clock=lambda:self.f.h.clock[0]).control_services()
        self.assertIsInstance(services.paper_reader,PaperReadControlPort)
        self.assertIsNone(services.paper_start,'No unqualified release/start factory may be invented')
        return services

    def event_tick(self,worker,run_id,seconds,price='60000',bars=False):
        self.assertTrue(worker.submit_event(run_id,self.f.event(seconds,price,bars)))
        return worker.tick()[run_id][-1]

    def test_unselected_normal_owners_expose_empty_actual_paper_inventory_without_start_authority(self):
        temp=TemporaryDirectory(prefix='R7 normal PAPER reader ');self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        config=ProductConfig('r7-product-config-v0.2','normal-reader',root,None,root/'canonical.sqlite3')
        services=LocalOwners(config,clock=lambda:datetime.now(timezone.utc)).control_services()
        self.assertIsInstance(services.paper_reader,PaperReadControlPort)
        self.assertEqual(services.view('paper_runs')['items'],[])
        self.assertEqual(services.view('paper_runs')['status'],'AVAILABLE')
        self.assertEqual(services.view('health')['runtime'],'NOT_CONFIGURED')
        self.assertFalse((root/'process-supervision.sqlite').exists())
        with self.assertRaises(APIError) as denied:
            services.revision('PAPER_START','strategy:any:1',dict(strategy_id='any',strategy_version='1'))
        self.assertEqual(denied.exception.reason,'OWNER_NOT_CONFIGURED')

    def test_actual_accepted_ack_fill_and_read_inventory_never_attach_a_generation(self):
        services=self.fixture_services();run_id=self.f.start()
        before=self.f.recover(run_id)
        initial=services.view('paper_runs',subject=run_id)
        self.assertEqual(initial['payload']['runtime_status'],'NOT_STARTED')
        self.assertEqual(self.f.recover(run_id),before)
        self.assertEqual([row['run_id'] for row in services.view('paper_runs')['items']],[run_id])
        with PaperOwnerWorker(self.f.config,self.f.factory,namespace='FIXTURE') as worker:
            worker.tick();self.assertEqual(self.event_tick(worker,run_id,0,bars=True).status,'ACKNOWLEDGED')
            ack_state=self.f.recover(run_id)
            ack=services.view('paper_runs',subject=run_id)['payload']
            self.assertIsNone(ack['position'])
            self.assertEqual(ack['orders'][0]['actual_filled_quantity'],'0')
            self.assertEqual(self.f.recover(run_id),ack_state)
            self.event_tick(worker,run_id,1)
            filled_state=self.f.recover(run_id)
            filled=services.view('paper_runs',subject=run_id)['payload']
            self.assertEqual(filled['position']['actual_quantity'],'0.001')
            self.assertEqual(filled['position']['lifecycle_state'],'OPEN_PROTECTED')
            self.assertEqual(filled['reconciliation'],'READY')
            self.assertEqual(filled['runtime_status'],'PROCESS_HEALTH_UNKNOWN')
            self.assertEqual(self.f.recover(run_id),filled_state)

    def test_normal_composed_pause_preserves_protection_and_owner_continues_actual_exit(self):
        services=self.fixture_services();run_id=self.f.start()
        with PaperOwnerWorker(self.f.config,self.f.factory,namespace='FIXTURE') as worker:
            worker.tick();self.event_tick(worker,run_id,0,bars=True);self.event_tick(worker,run_id,1)
            before=self.f.recover(run_id)
            revision=services.revision('PAPER_PAUSE','paper:'+run_id,{})
            receipt=services.execute('PAPER_PAUSE','paper:'+run_id,{},actor='fixture-owner',human=None,
                command_id='normal-composition-pause',expected_revision=revision)
            self.assertEqual(receipt['status'],'PAUSED')
            self.assertEqual(services.view('paper_runs',subject=run_id)['payload']['entry_admission'],'PAUSED')
            self.assertEqual(self.f.recover(run_id),before)
            worker.tick();paused=self.f.recover(run_id)
            self.assertEqual(paused.process_generation,before.process_generation)
            self.assertEqual(paused.state['runtime']['protection_request'],before.state['runtime']['protection_request'])
            self.assertEqual(paused.state['runtime']['position']['actual_quantity'],'0.001')
            self.assertFalse(paused.state['runtime']['paper_entries_allowed'])
            self.event_tick(worker,run_id,2,'60020')
            self.assertTrue(worker.submit_event(run_id,self.f.event(3,'60020')))
            self.assertTrue(any(outcome.status=='CLOSED' for outcome in worker.tick()[run_id]))
            final=services.view('paper_runs',subject=run_id)['payload']
            self.assertEqual(final['position']['lifecycle_state'],'CLOSED')
            self.assertEqual(final['closed_trades_count'],1)
            self.assertIsNotNone(final['metrics'])

    def test_immutable_fixture_store_cannot_be_reopened_as_normal_namespace(self):
        self.f=PaperOwnerFixture(self);run_id=self.f.start();before=self.f.recover(run_id)
        with self.assertRaises(EvidenceGateError):
            LocalOwners(self.f.config,namespace='LOCAL_RESEARCH',clock=lambda:self.f.h.clock[0])
        self.assertEqual(self.f.recover(run_id),before)

if __name__=='__main__':unittest.main()
