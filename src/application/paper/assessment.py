"""Forward assessment from exact E6-published E5 results and observed clocks."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json

from backtest.metrics import calculate_metrics
from registry import EvidenceGateError
from registry.product_assessment import canonical, digest
from validation.paper_policy import PaperPromotionPolicy


@dataclass(frozen=True)
class ForwardAssessment:
    canonical_json: str
    assessment_hash: str
    def as_dict(self): return json.loads(self.canonical_json)


def assess_forward(run, policy):
    from .service import PaperRuntime
    if not isinstance(run,PaperRuntime) or not isinstance(policy,PaperPromotionPolicy):
        raise ValueError('Actual recovered Paper runtime and selected policy required')
    service=run.service; recovered=service.process.recover(run.run_id)
    strategy=service.registry.get_strategy(run.engine.identity)
    if (recovered.binding!=service._binding(strategy) or policy.policy_hash!=service.promotion.policy_hash or
        recovered.binding['paper_policy_hash']!=policy.policy_hash):
        raise EvidenceGateError('Exact current run/source/selected PAPER policy required')
    runtime=recovered.state['runtime']; observed=runtime['forward']; selected=policy.as_dict()
    trades=[]; seen=set()
    for trade in runtime['closed_trades']:
        if trade['trade_result_id'] in seen: raise EvidenceGateError('Duplicate canonical forward trade')
        seen.add(trade['trade_result_id'])
        graph=service.canonical.recover(trade_plan_id=trade['trade_plan_id'])
        if graph.status!='READY' or graph.trade_result is None or graph.trade_result.payload!=trade:
            raise EvidenceGateError('Actual published E5 forward financial graph required')
        funding=next((fact.payload for fact in graph.funding_evidence if fact.canonical_id==trade['funding_evidence_id']),None)
        if funding is None: raise EvidenceGateError('Affirmative forward funding evidence required')
        if trade['funding_evidence_status']=='ZERO_CONFIRMED' and funding['status']=='ZERO_CONFIRMED':
            funding_cost='0'
        elif trade['funding_evidence_status']=='INCLUDED' and funding['status']=='INCLUDED':
            funding_cost=trade['funding_cost']
        else: raise EvidenceGateError('Forward funding truth cannot be inferred')
        # E5 fill prices already include configured slippage. Metrics receives
        # zero additional deduction, explicitly, to avoid subtracting twice.
        trades.append(dict(trade,slippage_cost='0',funding_cost=funding_cost))
    metrics=calculate_metrics(trades)
    fixture=runtime['mode']=='ACCELERATED_FIXTURE'
    elapsed=observed['simulated_elapsed_seconds'] if fixture else observed['real_elapsed_ns']//1_000_000_000
    healthy=observed['simulated_healthy_seconds'] if fixture else observed['real_healthy_ns']//1_000_000_000
    blocked=[]; failed=[]
    if recovered.pending_operations: blocked.append('PUBLICATION_OR_OPERATION_PENDING')
    if elapsed<selected['min_elapsed_seconds']: blocked.append('INSUFFICIENT_OBSERVATION_DURATION')
    if metrics.total_trades<selected['min_closed_trades']: blocked.append('INSUFFICIENT_CLOSED_TRADES')
    if healthy<selected['required_healthy_seconds']: blocked.append('INSUFFICIENT_HEALTHY_OBSERVATION')
    if observed['clock_status']!='CONSISTENT': blocked.append('OBSERVATION_CLOCK_UNVERIFIED')
    if observed['max_observed_gap_seconds']>selected['maximum_observation_gap_seconds']: blocked.append('OBSERVATION_GAP_EXCEEDED')
    if not observed['last_healthy'] or not run.engine.reconciled: blocked.append('CURRENT_RUNTIME_NOT_HEALTHY')
    age=None if observed['observed_at'] is None else (service.clock()-datetime.fromisoformat(observed['observed_at'].replace('Z','+00:00'))).total_seconds()
    if age is None or age<0 or age>selected['maximum_observation_gap_seconds']:
        blocked.append('CURRENT_FORWARD_OBSERVATION_STALE')
    thresholds=policy.validation_policy
    if metrics.net_pnl<thresholds.min_net_pnl: failed.append('MIN_NET_PNL_NOT_MET')
    if metrics.expectancy<Decimal(selected['min_expectancy_usdt_per_trade']): failed.append('MIN_EXPECTANCY_NOT_MET')
    if metrics.max_drawdown>thresholds.max_drawdown: failed.append('MAX_DRAWDOWN_EXCEEDED')
    if metrics.max_consecutive_losses>thresholds.max_consecutive_losses: failed.append('MAX_CONSECUTIVE_LOSSES_EXCEEDED')
    if metrics.profit_factor is None:
        if selected['profit_factor_null_handling']=='BLOCK' or metrics.losses>0: blocked.append('PROFIT_FACTOR_UNDEFINED')
    elif metrics.profit_factor<Decimal(selected['min_profit_factor']): failed.append('MIN_PROFIT_FACTOR_NOT_MET')
    status='BLOCKED' if blocked else 'FAIL' if failed else 'PASS'
    body=dict(schema_version='r7-paper-forward-assessment-v0.2',run_id=run.run_id,namespace=service.namespace,
        run_revision=recovered.revision,binding=recovered.binding,policy_hash=policy.policy_hash,
        paper_policy_ref=service.policy_ref,forward_mode=runtime['mode'],
        execution='SIMULATED_MECHANICS' if fixture else 'ACTUAL_OWNER',entries_enabled=False,broker_kind='PAPER_ONLY',
        started_at=observed['started_at'],observed_at=observed['observed_at'],
        actual_elapsed_seconds=0 if fixture else elapsed,actual_healthy_seconds=0 if fixture else healthy,
        simulated_elapsed_seconds=elapsed if fixture else 0,simulated_healthy_seconds=healthy if fixture else 0,
        max_observed_gap_seconds=observed['max_observed_gap_seconds'],closed_trades=metrics.total_trades,
        losses=metrics.losses,net_pnl_usdt=str(metrics.net_pnl),expectancy_usdt_per_trade=str(metrics.expectancy),
        max_drawdown_usdt=str(metrics.max_drawdown),max_consecutive_losses=metrics.max_consecutive_losses,
        profit_factor=None if metrics.profit_factor is None else str(metrics.profit_factor),
        slippage_convention='IN_FILL_PRICE_NO_ADDITIONAL_DEDUCTION',funding_model=service.simulation.as_dict()['funding_model'],
        account_scope=service.simulation.as_dict()['account_scope'],
        status=status,reason_codes=blocked+failed)
    raw=canonical(body)
    return ForwardAssessment(raw,digest(raw))
