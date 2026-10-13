"""Changing selected policies preserves original actual E5/Paper owner management."""
from contextlib import contextmanager
import inspect
import unittest

from application.paper.owners import PaperOwnerSelection
from application.paper.service import PaperService
from application.paper.worker import PaperOwnerWorker
from tests.application.paper_owner_fixtures import PaperOwnerFixture
from tests.application.test_product_assessment_binding import risk_fixture
from tests.product.test_paper_runtime_v02 import simulation_fixture
from tests.validation.test_paper_promotion_policy import policy_fixture


class PaperSelectionRecoveryTests(unittest.TestCase):
    def release_guard_factory(self,f,current):
        self.assertIn('entry_current',inspect.signature(PaperService).parameters)
        @contextmanager
        def factory():
            with f.factory() as original:
                original.entry_current=lambda _:current[0]
                yield original
        return factory

    def test_release_loss_after_prepared_start_denies_new_ack_without_selection_change(self):
        f=PaperOwnerFixture(self);run=f.start();current=[False];before=f.recover(run)
        with PaperOwnerWorker(f.config,self.release_guard_factory(f,current),namespace='FIXTURE') as worker:
            worker.tick();worker.submit_event(run,f.event(0,'60000',True));worker.tick()
            after=f.recover(run)
            self.assertIsNone(after.state['runtime']['entry_request'])
            self.assertEqual(after.state['broker'],before.state['broker'])

    def test_release_loss_cancels_unfilled_ack_and_preserves_open_protective_exit(self):
        for already_filled in (False,True):
            with self.subTest(already_filled=already_filled):
                f=PaperOwnerFixture(self);run=f.start();current=[True]
                with PaperOwnerWorker(f.config,self.release_guard_factory(f,current),namespace='FIXTURE') as worker:
                    worker.tick();worker.submit_event(run,f.event(0,'60000',True));worker.tick()
                    if already_filled:
                        worker.submit_event(run,f.event(1,'60000'));worker.tick()
                        position=f.recover(run).state['runtime']['position']
                        self.assertEqual(position['lifecycle_state'],'OPEN_PROTECTED')
                    current[0]=False
                    for second in (2,3):worker.submit_event(run,f.event(second,'60020'));worker.tick()
                    state=f.recover(run).state['runtime']
                    if already_filled:
                        self.assertEqual(state['position']['position_id'],position['position_id'])
                        self.assertEqual(state['position']['lifecycle_state'],'CLOSED')
                        self.assertEqual(len(state['closed_trades']),1)
                    else:
                        self.assertIsNone(state['position']);self.assertEqual(state['closed_trades'],[])

    def owner(self):
        return PaperOwnerSelection(namespace='FIXTURE',simulation_policy=simulation_fixture(),risk_policy=risk_fixture(),
            promotion_policy=policy_fixture(),paper_policy_ref='owner-fixture-policy',actor='fixture-paper-owner',
            workflow_authorized=True,submission_validity={'intent_class':'EVERGREEN_STRATEGY','validity':{'from':None,'until':None}})

    def changed_factory(self,f):
        self.assertIn('management_selection',inspect.signature(PaperService).parameters,
            'A replacement policy must not deny original open-position recovery')
        @contextmanager
        def factory():
            with f.factory() as original:
                selected=simulation_fixture();selected['quantity']='0.002'
                yield PaperService(registry=original.registry,process_journal=original.process,
                    canonical_journal=original.canonical,namespace='FIXTURE',simulation_policy=selected,
                    risk_policy=risk_fixture(),promotion_policy=policy_fixture(),paper_policy_ref='owner-fixture-policy',
                    submission_validity={'intent_class':'EVERGREEN_STRATEGY','validity':{'from':None,'until':None}},
                    actor='replacement-test-owner',workflow_authorized=True,current_release=lambda:f.release,
                    clock=lambda:f.h.clock[0],management_selection=lambda _:self.owner(),selection_current=lambda _:False)
        return factory

    def test_protected_successor_keeps_original_quantity_anchor_binding_and_closes(self):
        f=PaperOwnerFixture(self);run=f.start()
        with PaperOwnerWorker(f.config,f.factory,namespace='FIXTURE') as worker:
            worker.tick()
            for second,bars in ((0,True),(1,False)):
                worker.submit_event(run,f.event(second,'60000',bars));worker.tick()
        before=f.recover(run);position=before.state['runtime']['position']
        self.assertEqual(position['lifecycle_state'],'OPEN_PROTECTED')
        with PaperOwnerWorker(f.config,self.changed_factory(f),namespace='FIXTURE') as worker:
            worker.tick()
            self.assertTrue(worker.service.process.entry_pause_requested(run))
            runtime=worker.service.runtime(run)
            self.assertEqual(runtime.service.simulation.as_dict()['quantity'],'0.001')
            current=f.recover(run)
            self.assertEqual(current.binding,before.binding)
            self.assertEqual(current.state['runtime']['exit_anchor'],before.state['runtime']['exit_anchor'])
            self.assertEqual(current.state['runtime']['position']['position_id'],position['position_id'])
            for second in (2,3):
                worker.submit_event(run,f.event(second,'60020'));worker.tick()
            closed=f.recover(run)
            self.assertEqual(closed.state['runtime']['position']['lifecycle_state'],'CLOSED')
            self.assertEqual(len(closed.state['runtime']['closed_trades']),1)

    def test_pending_original_start_is_paused_without_attaching_or_creating_simulated_effects(self):
        f=PaperOwnerFixture(self);run=f.start();before=f.recover(run)
        with PaperOwnerWorker(f.config,self.changed_factory(f),namespace='FIXTURE') as worker:
            worker.tick()
            self.assertEqual(worker.snapshot()['active_runs'],())
            self.assertTrue(worker.service.process.entry_pause_requested(run))
        after=f.recover(run)
        self.assertEqual(after.process_generation,0)
        self.assertEqual(after.state,before.state)
        self.assertEqual(after.binding,before.binding)


if __name__=='__main__':unittest.main()
