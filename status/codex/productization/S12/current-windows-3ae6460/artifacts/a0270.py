"""Synthetic public resource records test retention scope, not product PASS."""
import copy,json,tempfile,unittest
from pathlib import Path
import retain_current_checkpoint as helper
from application.platform.private_files import create_private_directory,write_private_new

class DirectObservationTests(unittest.TestCase):
    def observe(self,change=None):
        revision='2'*40;facts={'executable_revision':revision,'build_hash':'actual-fixture'}
        stage=dict(stage='qualify',revision=revision,attempt='first',passed=True,source_unchanged=True,
            started_at='2026-10-20T00:00:00+00:00',finished_at='2026-10-20T00:00:10+00:00',
            host_samples=[dict(observed_at='2026-10-20T00:00:00+00:00',available_memory_bytes=100,physical_memory_bytes=200),
                dict(error_type='SampleError'),
                dict(observed_at='2026-10-20T00:00:08+00:00',available_memory_bytes=90,physical_memory_bytes=200)])
        isolation=dict(case='research-isolation',passed=True,research_fault_protection_isolation=True,
            host_bounded_capacity_measured=True,capacity_scope='ONE_PAPER_OWNER_ONE_RESEARCH_JOB_AND_CONTROL',
            memory_enforcement='SOFT_LIMIT_ONLY',maximum_load_qualification='NOT_ESTABLISHED',
            target_24gb_qualification='NOT_ESTABLISHED',sampled_peak_total_rss_bytes=30,
            sampled_peak_total_private_bytes=18,
            process_samples=[dict(processes={
                'control':[dict(pid=10,rss_bytes=10,private_bytes=6)],
                'runtime':[dict(pid=11,rss_bytes=12,private_bytes=7)],
                'research':[dict(pid=12,rss_bytes=8,private_bytes=5)]})])
        primary=dict(passed=True,identity=facts,group='PQR-05',observations=[isolation])
        if change:change(stage,primary)
        with tempfile.TemporaryDirectory(dir=helper.BASE,prefix='direct-resource-') as directory:
            root=Path(directory)/'public';create_private_directory(root)
            child=root/'PQR-05-native-artifacts';create_private_directory(child)
            path=child/'native-observations.json';raw=json.dumps(primary).encode();write_private_new(path,raw)
            members=[dict(member_id='PQR-05-native',group_id='PQR-05',artifacts=[
                dict(ref='PQR-05-native-artifacts/native-observations.json',hash=helper.sha(raw))])]
            return helper.host_and_pqr05_observation(helper.CapturedEvidence(root),stage,root,members,facts,revision,'first')[0]

    def test_direct_launch_keeps_whole_run_peaks_unknown_and_actual_slice_separate(self):
        observed=self.observe()
        self.assertIsNone(observed['peak_owned_rss_bytes']);self.assertIsNone(observed['peak_owned_private_bytes'])
        self.assertEqual('UNKNOWN_NOT_OBSERVED_FOR_THIS_ATTEMPT',observed['complete_owning_run']['process_memory_status'])
        self.assertEqual(30,observed['pqr05_isolation']['sampled_peak_total_rss_bytes'])
        self.assertEqual(18,observed['pqr05_isolation']['sampled_peak_total_private_bytes'])
        self.assertEqual(2,observed['valid_samples']);self.assertEqual(90,observed['minimum_host_available_bytes'])
        self.assertEqual(1,observed['host_memory']['error_sample_count'])
        self.assertEqual(8,observed['host_memory']['maximum_observed_gap_seconds'])
        self.assertEqual('NOT_RECORDED',observed['host_memory']['monitor_stopped'])

    def test_stale_identity_missing_actual_samples_or_inconsistent_slice_totals_refuse(self):
        for changed in ('identity','samples','peaks','pid','flag'):
            def alter(stage,primary):
                case=primary['observations'][0]
                if changed=='identity':primary['identity']={}
                elif changed=='samples':case['process_samples']=[]
                elif changed=='peaks':case['sampled_peak_total_rss_bytes']=999
                elif changed=='pid':case['process_samples'][0]['processes']['research'][0]['pid']=10
                else:case['host_bounded_capacity_measured']=False
            with self.subTest(changed=changed),self.assertRaises(ValueError):self.observe(alter)

    def test_missing_host_samples_stay_unknown_without_retrospective_process_attribution(self):
        observed=self.observe(lambda stage,unused:stage.update(host_samples=[dict(error_type='SampleError')]))
        self.assertEqual(0,observed['valid_samples']);self.assertIsNone(observed['minimum_host_available_bytes'])
        self.assertIsNone(observed['peak_owned_private_bytes'])

    def test_wrong_stage_attempt_and_out_of_interval_host_samples_refuse(self):
        for field,value in [('revision','wrong'),('attempt','retry01'),('passed',False),('stage','headless')]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                self.observe(lambda stage,unused:stage.update({field:value}))
        with self.assertRaises(ValueError):
            self.observe(lambda stage,unused:stage['host_samples'][0].update(observed_at='2026-10-21T00:00:00+00:00'))

if __name__=='__main__':unittest.main(verbosity=2)
