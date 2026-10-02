"""Real observation credit cannot be minted by synthetic wall-clock advances."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from application.paper.observation import initial_forward_observation,record_forward_observation
from validation.paper_policy import parse_paper_promotion_policy
from tests.validation.test_paper_promotion_policy import policy_fixture


class ForwardObservationTests(unittest.TestCase):
    def service(self,mono,instance='process-1'):
        return SimpleNamespace(monotonic_clock=lambda:mono[0],_instance_id=instance,
            promotion=parse_paper_promotion_policy(policy_fixture(),namespace='FIXTURE'))

    def test_fast_forward_wall_clock_yields_zero_real_credit_and_unverified_clock(self):
        row=dict(mode='REAL_TIME',forward=initial_forward_observation()); mono=[100]
        service=self.service(mono); now=datetime(2026,10,3,tzinfo=timezone.utc)
        record_forward_observation(row,service,now,True); mono[0]+=1_000_000
        record_forward_observation(row,service,now+timedelta(hours=2),True)
        self.assertEqual(row['forward']['real_elapsed_ns'],0)
        self.assertEqual(row['forward']['real_healthy_ns'],0)
        self.assertEqual(row['forward']['clock_status'],'WALL_MONOTONIC_DIVERGED')

    def test_matching_actual_monotonic_intervals_count_but_restart_gap_is_not_healthy_credit(self):
        row=dict(mode='REAL_TIME',forward=initial_forward_observation()); mono=[100]
        service=self.service(mono); now=datetime(2026,10,3,tzinfo=timezone.utc)
        record_forward_observation(row,service,now,True); mono[0]+=2_000_000_000
        record_forward_observation(row,service,now+timedelta(seconds=2),True)
        self.assertEqual(row['forward']['real_elapsed_ns'],2_000_000_000)
        self.assertEqual(row['forward']['real_healthy_ns'],2_000_000_000)
        restarted=self.service([10],'process-2')
        record_forward_observation(row,restarted,now+timedelta(hours=1),True)
        self.assertEqual(row['forward']['real_healthy_ns'],2_000_000_000)
        self.assertEqual(row['forward']['real_elapsed_ns'],2_000_000_000)
        self.assertEqual(row['forward']['max_observed_gap_seconds'],3598)

    def test_fixture_never_counts_matching_clock_intervals_as_actual_forward(self):
        row=dict(mode='ACCELERATED_FIXTURE',forward=initial_forward_observation()); mono=[100]
        service=self.service(mono); now=datetime(2026,10,3,tzinfo=timezone.utc)
        record_forward_observation(row,service,now,True); mono[0]+=2_000_000_000
        record_forward_observation(row,service,now+timedelta(seconds=2),True)
        self.assertEqual(row['forward']['real_healthy_ns'],0)
        self.assertEqual(row['forward']['real_elapsed_ns'],0)
        self.assertEqual(row['forward']['simulated_elapsed_seconds'],2)
