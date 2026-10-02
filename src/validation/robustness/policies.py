from dataclasses import dataclass
from decimal import localcontext
import json
from indicators.v02.common import REFERENCE_CONTEXT
from validation.oos import ValidationPolicy
from .common import canonical,decimal,dec_text,digest,exact,fail,freeze,hash_value,integer,text
from .monte_carlo import _policy as monte_carlo_policy

@dataclass(frozen=True)
class ResearchPolicy:
    canonical_json: str
    policy_hash: str
    @classmethod
    def parse(cls,value):
        value=freeze(value)
        exact(value,('schema_version','policy_id','generation','namespace','validation_policy_version','minimum_closed_trades',
                     'min_net_pnl_usdt','min_expectancy_usdt_per_trade','drawdown_limit','drawdown_unit','initial_equity_usdt',
                     'max_consecutive_losses','min_profit_factor','profit_factor_null_handling','split_policy_hash','cost_policy_hash'))
        if value['schema_version']!='r7-research-policy-v0.2' or value['namespace'] not in ('FIXTURE','LOCAL_RESEARCH'): fail('UNSUPPORTED_RESEARCH_PROFILE')
        for key in ('policy_id','validation_policy_version'): text(value[key])
        integer(value['generation'],1,2147483647); integer(value['max_consecutive_losses'],0,200000)
        exact(value['minimum_closed_trades'],('development','walk_forward','sealed_oos'))
        for item in value['minimum_closed_trades'].values(): integer(item,1,200000)
        for key in ('split_policy_hash','cost_policy_hash'): hash_value(value[key])
        if value['drawdown_unit'] not in ('USDT_AMOUNT','FRACTION_OF_INITIAL_EQUITY'): fail('UNSUPPORTED_DRAWDOWN_UNIT')
        if value['profit_factor_null_handling'] not in ('BLOCK','ALLOW_NO_LOSSES'): fail('UNSUPPORTED_PROFIT_FACTOR_NULL_HANDLING')
        for key in ('min_net_pnl_usdt','min_expectancy_usdt_per_trade'): value[key]=dec_text(decimal(value[key]))
        for key in ('drawdown_limit','min_profit_factor'): value[key]=dec_text(decimal(value[key],minimum=0))
        equity=decimal(value['initial_equity_usdt'],minimum=0)
        if equity==0: fail('POSITIVE_INITIAL_EQUITY_REQUIRED')
        value['initial_equity_usdt']=dec_text(equity)
        raw=canonical(value); return cls(raw,digest(raw.encode()))
    def as_dict(self): return json.loads(self.canonical_json)
    def validation_policy(self,partition):
        p=self.as_dict()
        if partition not in p['minimum_closed_trades']: fail('UNSUPPORTED_ASSESSMENT_PARTITION')
        with localcontext(REFERENCE_CONTEXT):
            limit=decimal(p['drawdown_limit'])
            if p['drawdown_unit']=='FRACTION_OF_INITIAL_EQUITY': limit*=decimal(p['initial_equity_usdt'])
            return ValidationPolicy(p['validation_policy_version'],p['minimum_closed_trades'][partition],p['min_net_pnl_usdt'],
                dec_text(limit),p['max_consecutive_losses'],None if p['profit_factor_null_handling']=='ALLOW_NO_LOSSES' else p['min_profit_factor'])

def assess_partition(backtest,policy,partition):
    """Add product sample adequacy to the existing E3 threshold authority.

    Development is deliberately not disguised as an OOSValidationContext.
    Final OOS additionally invokes the canonical OOS evaluator in its owner path.
    """
    if not isinstance(policy,ResearchPolicy): fail('SELECTED_RESEARCH_POLICY_REQUIRED')
    p=policy.as_dict(); thresholds=policy.validation_policy(partition); blocked=[]; failed=[]
    if backtest['total_trades']<thresholds.min_total_trades: blocked.append('INSUFFICIENT_EVIDENCE')
    if decimal(backtest['net_pnl'])<thresholds.min_net_pnl: failed.append('MIN_NET_PNL_NOT_MET')
    if decimal(backtest['expectancy'])<decimal(p['min_expectancy_usdt_per_trade']): failed.append('MIN_EXPECTANCY_NOT_MET')
    if decimal(backtest['max_drawdown'])>thresholds.max_drawdown: failed.append('MAX_DRAWDOWN_EXCEEDED')
    if backtest['max_consecutive_losses']>thresholds.max_consecutive_losses: failed.append('MAX_CONSECUTIVE_LOSSES_EXCEEDED')
    if backtest['profit_factor'] is None:
        if p['profit_factor_null_handling']=='BLOCK' or backtest['losses']>0: blocked.append('PROFIT_FACTOR_UNDEFINED')
    elif decimal(backtest['profit_factor'])<decimal(p['min_profit_factor']): failed.append('MIN_PROFIT_FACTOR_NOT_MET')
    return dict(status='BLOCKED' if blocked else 'FAIL' if failed else 'PASS',reason_codes=blocked+failed,
                validation_policy_id=thresholds.identity,thresholds=thresholds.material(),
                drawdown_input_unit=p['drawdown_unit'],initial_equity_usdt=p['initial_equity_usdt'])

def parse_robustness_policy(value):
    p=freeze(value)
    exact(p,('schema_version','policy_id','generation','namespace','algorithm_version','split_policy_hash','cost_policy_hash',
             'neighborhood','maximum_trials','maximum_replays','maximum_evaluations','selection_procedure',
             'minimum_neighborhood_pass_fraction','minimum_walk_forward_pass_fraction','minimum_stress_net_pnl_usdt',
             'walk_forward_windows','stress_scenarios','monte_carlo','max_monte_carlo_drawdown_q95',
             'minimum_block_expectancy_q05_usdt_per_trade'))
    if p['schema_version']!='r7-robustness-policy-v0.2' or p['algorithm_version']!='r7-robustness-v1': fail('UNSUPPORTED_ROBUSTNESS_VERSION')
    if p['namespace'] not in ('FIXTURE','LOCAL_RESEARCH'): fail('INVALID_ROBUSTNESS_NAMESPACE')
    text(p['policy_id']); integer(p['generation'],1,2147483647)
    for key in ('split_policy_hash','cost_policy_hash'): hash_value(p[key])
    integer(p['maximum_trials'],1,256); integer(p['maximum_replays'],1,256); integer(p['maximum_evaluations'],1,200000)
    if p['selection_procedure']!='TRAIN_NET_PNL_THEN_VARIANT_HASH_V1': fail('UNSUPPORTED_SELECTION_PROCEDURE')
    for key in ('minimum_neighborhood_pass_fraction','minimum_walk_forward_pass_fraction'): decimal(p[key],minimum=0,maximum=1)
    decimal(p['max_monte_carlo_drawdown_q95'],minimum=0)
    for key in ('minimum_stress_net_pnl_usdt','minimum_block_expectancy_q05_usdt_per_trade'): decimal(p[key])
    for key,maximum in (('neighborhood',8),('walk_forward_windows',32),('stress_scenarios',32),('monte_carlo',2)):
        if not isinstance(p[key],list) or not 1<=len(p[key])<=maximum: fail('INVALID_ROBUSTNESS_STAGE_LIST')
    names=set(); trials=1
    for dimension in p['neighborhood']:
        exact(dimension,('parameter','type','minimum','maximum','values')); name=text(dimension['parameter'])
        if name in names: fail('DUPLICATE_NEIGHBORHOOD_PARAMETER')
        names.add(name)
        if dimension['type'] not in ('INTEGER','DECIMAL'): fail('UNSUPPORTED_PARAMETER_TYPE')
        if not isinstance(dimension['values'],list) or not 1<=len(dimension['values'])<=32: fail('INVALID_NEIGHBORHOOD_VALUES')
        if dimension['type']=='INTEGER':
            lower=integer(dimension['minimum'],-1000000,1000000); upper=integer(dimension['maximum'],lower,1000000)
            for val in dimension['values']: integer(val,lower,upper)
        else:
            lower=decimal(dimension['minimum']); upper=decimal(dimension['maximum'],minimum=lower)
            for val in dimension['values']: decimal(val,minimum=lower,maximum=upper)
        if len({canonical(v) for v in dimension['values']})!=len(dimension['values']): fail('DUPLICATE_NEIGHBORHOOD_VALUE')
        trials*=len(dimension['values'])
    if trials>p['maximum_trials']: fail('NEIGHBORHOOD_TRIAL_BUDGET_EXCEEDED')
    names=set()
    for scenario in p['stress_scenarios']:
        exact(scenario,('name','fee_add_bps','entry_slippage_add_bps','exit_slippage_add_bps','funding_adverse_multiplier'))
        name=text(scenario['name'])
        if name in names: fail('DUPLICATE_STRESS_SCENARIO')
        names.add(name)
        for key in ('fee_add_bps','entry_slippage_add_bps','exit_slippage_add_bps'): decimal(scenario[key],minimum=0,maximum=9999)
        decimal(scenario['funding_adverse_multiplier'],minimum=1,maximum=1000)
    p['monte_carlo']=[monte_carlo_policy(item) for item in p['monte_carlo']]
    if {item['algorithm'] for item in p['monte_carlo']}!={'TRADE_PERMUTATION','MOVING_BLOCK_BOOTSTRAP'}: fail('MANDATORY_MONTE_CARLO_ALGORITHMS_REQUIRED')
    return p
