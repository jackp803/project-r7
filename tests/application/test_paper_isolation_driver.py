"""Source-only boundary tests; no native concurrency or capacity credit."""
import importlib
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch


class PaperIsolationDriverTests(unittest.TestCase):
    def module(self):
        root = Path(__file__).resolve().parents[2]
        with patch.object(sys, 'path', [str(root / 'tools'), *sys.path]):
            return importlib.import_module('tools.verify_paper_isolation')

    def result(self):
        return dict(status='JOB_TERMINATED', run_id='job-source', job_state='FAILED',
                    reason_codes=['OWNED_WORKER_TIMEOUT'], tree_reaped=True, parent_pid=20,
                    child_pid=30, exit_code=124, memory_enforcement='SOFT_LIMIT_ONLY')

    def metric(self, pid, parent):
        return dict(pid=pid, parent_pid=parent, created_100ns=1, rss_bytes=100, private_bytes=50,
                    kernel_cpu_100ns=0, user_cpu_100ns=0, priority_class=0x4000)

    def test_only_exact_actual_owned_timeout_counts(self):
        module = self.module()
        module.require_timeout(self.result(), run_id='job-source', process_exit_code=2)
        for changes in ({'status': 'JOB_FINISHED'}, {'job_state': 'COMPLETE'}, {'tree_reaped': False},
                        {'reason_codes': ['RESEARCH_MEMORY_PRESSURE']}, {'run_id': 'wrong'},
                        {'parent_pid': 30}, {'exit_code': 0}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                module.require_timeout({**self.result(), **changes}, run_id='job-source', process_exit_code=2)

    def test_sample_inventory_never_reads_outside_the_owned_job(self):
        module = self.module()
        sampler = object.__new__(module.WindowsOwnedProcessSampler)
        owned = object()
        sampler._job_pids = Mock(return_value=(11, 12))
        sampler._read_process = Mock(side_effect=[self.metric(11, 1), self.metric(12, 11)])
        rows = sampler.sample_owned(owned)
        self.assertEqual([row['pid'] for row in rows], [11, 12])
        self.assertEqual([call.args for call in sampler._read_process.call_args_list], [(owned, 11), (owned, 12)])

    def test_missing_process_metric_is_failure_not_an_invented_zero(self):
        module = self.module()
        sampler = object.__new__(module.WindowsOwnedProcessSampler)
        sampler._job_pids = Mock(return_value=(11,))
        sampler._read_process = Mock(return_value={'pid': 11})
        with self.assertRaises(ValueError):
            sampler.sample_owned(object())

    def test_kernel_metrics_use_one_stable_owned_handle_and_close_it(self):
        module = self.module()
        sampler = object.__new__(module.WindowsOwnedProcessSampler)
        sampler.kernel = Mock(); sampler.ntdll = Mock(); owned = Mock()
        sampler.kernel.OpenProcess.return_value = 7
        sampler.kernel.WaitForSingleObject.return_value = 258
        def membership(handle, job, output):
            output._obj.value = True
            return True
        def basic(handle, information, output, size, returned):
            output._obj.UniqueProcessId = 40
            output._obj.InheritedFromUniqueProcessId = 30
            return 0
        def memory(handle, output, size):
            output._obj.WorkingSetSize = 100
            output._obj.PrivateUsage = 50
            return True
        def counters(handle, created, exited, kernel, user):
            created._obj.dwLowDateTime = 1
            kernel._obj.dwLowDateTime = 2
            user._obj.dwLowDateTime = 3
            return True
        sampler.kernel.IsProcessInJob.side_effect = membership
        sampler.ntdll.NtQueryInformationProcess.side_effect = basic
        sampler.kernel.K32GetProcessMemoryInfo.side_effect = memory
        sampler.kernel.GetProcessTimes.side_effect = counters
        sampler.kernel.GetPriorityClass.return_value = 0x4000
        row = sampler._read_process(owned, 40)
        self.assertEqual((row['rss_bytes'], row['private_bytes'], row['parent_pid']), (100, 50, 30))
        self.assertEqual((row['kernel_cpu_100ns'], row['user_cpu_100ns']), (2, 3))
        sampler.kernel.CloseHandle.assert_called_once_with(7)

    def test_membership_failure_never_reads_process_memory_or_cpu(self):
        module = self.module()
        sampler = object.__new__(module.WindowsOwnedProcessSampler)
        sampler.kernel = Mock(); sampler.ntdll = Mock(); owned = Mock()
        sampler.kernel.OpenProcess.return_value = 7
        sampler.kernel.IsProcessInJob.return_value = False
        with self.assertRaises(ValueError):
            sampler._read_process(owned, 40)
        sampler.kernel.K32GetProcessMemoryInfo.assert_not_called()
        sampler.kernel.GetProcessTimes.assert_not_called()
        sampler.kernel.CloseHandle.assert_called_once_with(7)

    def test_actual_exited_owned_process_is_a_distinct_terminal_nonmeasurement(self):
        module = self.module()
        sampler = object.__new__(module.WindowsOwnedProcessSampler)
        sampler.kernel = Mock(); sampler.ntdll = Mock(); owned = Mock()
        sampler.kernel.OpenProcess.return_value = 7
        def membership(handle, job, output):
            output._obj.value = True
            return True
        sampler.kernel.IsProcessInJob.side_effect = membership
        sampler.kernel.WaitForSingleObject.return_value = 0
        with self.assertRaises(module.MeasurementProcessExited):
            sampler._read_process(owned, 40)
        sampler.kernel.K32GetProcessMemoryInfo.assert_not_called()
        sampler.kernel.CloseHandle.assert_called_once_with(7)

    def test_only_same_actual_stopped_research_identity_is_terminal(self):
        module = self.module()
        identity = dict(pid=20, generation=1, process_generation_id='exact', config_hash='same')
        self.assertTrue(module.is_expected_research_stop({**identity, 'state': 'STOPPED'}, identity))
        for changes in ({'state': 'FAILED'}, {'state': 'RUNNING'}, {'generation': 2}, {'pid': 21}):
            self.assertFalse(module.is_expected_research_stop({**identity, 'state': 'STOPPED', **changes}, identity))

    def test_terminal_wait_keeps_paper_observation_but_invents_no_process_sample(self):
        module = self.module()
        flow = object.__new__(module.NativeResearchIsolationFlow)
        flow.observe_paper = Mock(return_value={'observed': 'actual-source-mock'})
        flow.persist = Mock(); flow.observation = {}
        owned = Mock(); owned.process.poll.side_effect = [None, None, 2]
        samples = []
        with patch.object(module.time, 'monotonic', return_value=0), patch.object(module.time, 'sleep'):
            flow.wait_terminal_research(owned, object(), object(), samples, end=10)
        self.assertEqual(len(samples), 2)
        self.assertNotIn('process_samples', flow.observation)

    def test_research_target_must_be_observed_beyond_both_bootstraps(self):
        module = self.module()
        samples = [dict(processes={'research': [self.metric(10, 1), self.metric(20, 10), self.metric(30, 20)]})]
        with self.assertRaises(ValueError):
            module.require_research_target(samples, self.result())
        samples[0]['processes']['research'].append(self.metric(40, 30))
        self.assertEqual(module.require_research_target(samples, self.result()), [40])

    def test_target_ancestry_without_measured_actual_research_parent_is_incomplete(self):
        module = self.module()
        samples = [dict(processes={'research': [self.metric(30, 20), self.metric(40, 30)]})]
        with self.assertRaises(ValueError):
            module.require_research_target(samples, self.result())

    def test_progress_reports_actual_gap_without_inventing_deadline_slack(self):
        module = self.module()
        samples = [dict(monotonic_ns=n, checkpoint_revision=r, broker_observed_at=f'2026-10-19T00:00:0{r}Z')
                   for n, r in ((0, 1), (1_200_000_000, 2), (2_600_000_000, 3))]
        result = module.progress_report(samples, selected_deadline_seconds=1)
        self.assertEqual(result['selected_protection_poll_seconds'], 1)
        self.assertAlmostEqual(result['max_observed_checkpoint_gap_seconds'], 1.4)
        self.assertTrue(result['observed_gap_exceeds_selected_interval'])
        self.assertEqual(result['deadline_conformance'], 'NOT_ESTABLISHED_BY_SAMPLED_FIXTURE')

    def test_two_advancing_broker_observations_are_required(self):
        module = self.module()
        samples = [dict(monotonic_ns=n, checkpoint_revision=r, broker_observed_at='2026-10-19T00:00:01Z')
                   for n, r in ((0, 1), (1, 2), (2, 3))]
        with self.assertRaises(ValueError):
            module.progress_report(samples, selected_deadline_seconds=1)

    def test_original_definition_is_only_authored_as_fresh_input(self):
        module = self.module()
        flow = object.__new__(module.NativeResearchIsolationFlow)
        flow.generated = dict(submission_id='original', policy_id='selected-policy')
        flow.cloud = Path('SOURCE_CLOUD')
        flow.output = Path('SOURCE_OUTPUT')
        flow.config = Path('SOURCE_CONFIG')
        flow.observation = {}
        flow.input_commitments = Mock(return_value={'source': 'same'})
        flow.submission = Mock(return_value={'receipt': {'original': True}})
        flow.view = Mock(side_effect=[dict(payload={'revision': 2})])
        flow.scan = Mock(return_value=({}, {}, {'accepted': 1}))
        flow.command = Mock(return_value={'execution_evidence': 'NOT_RUN', 'status': 'AUTHORING_PACKAGE_CREATED'})
        flow.request = Mock(return_value={'effect_ref': 'research-job:job-source', 'status': 'QUEUED'})
        definition = dict(strategy_id='original-strategy', content_hash='old', name='Original')
        with patch.object(module.product, 'read_local', return_value=module.product.canonical(definition).encode()), \
                patch.object(module.product, 'write_private_new') as writer:
            self.assertEqual(flow.prepare_research_submission(), 'job-source')
        argv = flow.command.call_args.args[1]
        self.assertEqual(argv[0], 'author-package')
        self.assertNotIn('--notes', argv)
        self.assertTrue(all(argv[argv.index(flag) + 1] == 'synthetic-fixture'
                            for flag in ('--dataset-profile', '--validation-profile', '--robustness-profile')))
        self.assertNotEqual(writer.call_args.args[1], module.product.canonical(definition).encode())

    def test_failed_reap_retains_owned_research_handle_and_closes_capture(self):
        module = self.module()
        flow = object.__new__(module.NativeResearchIsolationFlow)
        flow.research_child = Mock()
        handle = flow.research_child
        flow.research_stream = Mock()
        capture = flow.research_stream
        flow.commands = []
        flow.persist = Mock()
        with patch.object(module, 'terminate_owned', return_value=Mock(reaped=False)):
            with self.assertRaises(module.NativeIsolationCleanupError):
                flow.cleanup_research()
        self.assertIs(flow.research_child, handle)
        capture.close.assert_called_once()
        self.assertIsNone(flow.research_stream)

    def test_failed_control_reap_also_retains_exact_handle(self):
        module = self.module()
        flow = object.__new__(module.NativeResearchIsolationFlow)
        flow.control = Mock(); handle = flow.control
        handle.wait.return_value = 2
        flow.control_stream = Mock(); capture = flow.control_stream
        flow.config = Path('SOURCE_CONFIG'); flow.commands = []; flow.persist = Mock(); flow.command = Mock()
        flow.control_log = Path('SOURCE_CONTROL.log')
        with patch.object(module, 'terminate_owned', return_value=Mock(reaped=False)):
            with self.assertRaises(module.NativeIsolationCleanupError):
                flow.cleanup_control()
        self.assertIs(flow.control, handle)
        capture.close.assert_called_once()

    def test_setup_control_stop_uses_same_handle_retaining_cleanup(self):
        module = self.module()
        flow = object.__new__(module.NativeResearchIsolationFlow)
        flow.cleanup_control = Mock()
        flow.stop_control()
        flow.cleanup_control.assert_called_once()

    def test_scope_flags_only_follow_complete_actual_checks_and_cleanup(self):
        module = self.module()
        flow = object.__new__(module.NativeResearchIsolationFlow)
        flow.observation = {}
        flow.run_checks = Mock()
        flow.cleanup_all = Mock(side_effect=module.NativeIsolationCleanupError('source-only'))
        flow.persist = Mock()
        with self.assertRaises(module.NativeIsolationCleanupError):
            flow.run()
        self.assertFalse(flow.observation['passed'])
        self.assertFalse(flow.observation['research_fault_protection_isolation'])
        self.assertFalse(flow.observation['host_bounded_capacity_measured'])


if __name__ == '__main__':
    unittest.main()
