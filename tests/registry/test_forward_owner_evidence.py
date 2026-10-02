"""Pure guard fixtures do not accumulate or claim real elapsed PAPER evidence."""
from datetime import datetime,timedelta,timezone
import copy,unittest
from registry import EvidenceGateError
from registry.operational_authority import ProductLifecycleComposition,HumanAuthenticator
from validation.paper_policy import parse_paper_promotion_policy
from tests.validation.test_paper_promotion_policy import policy_fixture


class ForwardOwnerGuardTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,3,tzinfo=timezone.utc)
        auth=HumanAuthenticator(namespace='LOCAL_RESEARCH',verifier=lambda _:None,reauth_seconds=300,clock=lambda:self.now)
        self.boundary=ProductLifecycleComposition(namespace='LOCAL_RESEARCH',current_release=lambda:None,
            resolve_evidence=lambda *_:None,authenticator=auth,clock=lambda:self.now)
        self.policy=parse_paper_promotion_policy(policy_fixture('LOCAL_RESEARCH'),namespace='LOCAL_RESEARCH')
        self.body=dict(forward_mode='REAL_TIME',execution='ACTUAL_OWNER',status='PASS',
            actual_elapsed_seconds=3600,actual_healthy_seconds=3600,closed_trades=7,losses=0,
            max_consecutive_losses=0,max_observed_gap_seconds=0,observed_at=self.now.isoformat(),
            started_at=(self.now-timedelta(hours=1)).isoformat(),net_pnl_usdt='7',
            expectancy_usdt_per_trade='1',max_drawdown_usdt='0',profit_factor=None)

    def test_impossible_financial_metrics_cannot_be_forward_evidence(self):
        for change in ({'max_drawdown_usdt':'-1'},{'max_consecutive_losses':1,'losses':0}):
            with self.subTest(change=change),self.assertRaises(EvidenceGateError):
                self.boundary.validate_real_forward(dict(self.body,**change),self.policy)

    def test_accelerated_insufficient_unhealthy_stale_and_quantitative_failure_are_denied(self):
        self.boundary.validate_real_forward(self.body,self.policy) # numeric fixture, no publication/state transition
        for change in ({'forward_mode':'ACCELERATED_FIXTURE'},{'execution':'SIMULATED_MECHANICS'},
            {'actual_elapsed_seconds':3599},{'actual_healthy_seconds':3599},{'closed_trades':1},
            {'max_observed_gap_seconds':31},{'observed_at':(self.now-timedelta(seconds=31)).isoformat()},
            {'started_at':(self.now+timedelta(seconds=1)).isoformat()},
            {'net_pnl_usdt':'-1'},{'max_drawdown_usdt':'11'},{'losses':1,'profit_factor':None},
            {'closed_trades':True},{'net_pnl_usdt':'NaN'}):
            with self.subTest(change=change),self.assertRaises(EvidenceGateError):
                self.boundary.validate_real_forward(dict(self.body,**change),self.policy)
