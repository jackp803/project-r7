"""Actual owned child lifecycle only; no native product or financial credit."""
from pathlib import Path
import subprocess,sys,tempfile,unittest
import verify_plat08_crossversion_native as subject

class HelperLifecycleTests(unittest.TestCase):
    def flow(self):
        temporary=tempfile.TemporaryDirectory(prefix='r7-plat08-helper-')
        self.addCleanup(temporary.cleanup)
        flow=object.__new__(subject.LocalDiagnosticControl)
        flow.output=Path(temporary.name)/'private';subject.create_private_directory(flow.output)
        flow.executable=Path(sys.executable)
        flow.password='UNUSED_SYNTHETIC_INPUT';flow.env=None;flow.owned=[]
        flow.commands=[];flow.observation=dict(commands=flow.commands,result_scope='HELPER_LIFECYCLE_ONLY')
        flow.guard=lambda:None
        def cleanup():
            for owned in flow.owned:
                self.assertTrue(subject.terminate_owned(owned,deadline_seconds=5).reaped)
        self.addCleanup(cleanup)
        return flow

    def test_real_child_is_registered_reaped_and_json_command_observed(self):
        flow=self.flow()
        result=flow.command('actual-json',[],argv=[sys.executable,'-c','print("{\\\"actual\\\":true}")'])
        self.assertEqual({'actual':True},result)
        self.assertEqual(1,len(flow.owned))
        self.assertTrue(flow.owned[0].termination_report.reaped)
        self.assertTrue(flow.commands[0]['tree_reaped'])
        self.assertNotIn('passed',flow.observation)

    def test_actual_started_child_wait_exception_retains_handle_and_reaps_before_propagation(self):
        flow=self.flow();spawn=flow._spawn
        def spawn_then_interrupt(*args,**kwargs):
            owned=spawn(*args,**kwargs)
            def interrupted_wait(*args,**kwargs):raise subprocess.TimeoutExpired('actual-owned-wait',0)
            owned.wait=interrupted_wait
            return owned
        flow._spawn=spawn_then_interrupt
        with self.assertRaises(subprocess.TimeoutExpired):
            flow.command('actual-wait-failure',[],argv=[sys.executable,'-c','import time;time.sleep(30)'],timeout=60)
        self.assertEqual(1,len(flow.owned))
        self.assertIsNotNone(flow.owned[0].process.poll())
        self.assertTrue(flow.owned[0].termination_report.reaped)
        self.assertTrue(flow.commands[0]['tree_reaped'])
        self.assertIsNone(flow.commands[0]['exit_code'])
        self.assertNotIn('passed',flow.observation)

if __name__=='__main__':unittest.main(verbosity=2)
