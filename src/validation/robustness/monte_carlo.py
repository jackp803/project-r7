"""Finite deterministic trade-path sensitivity; no profitability warranty."""
from dataclasses import dataclass
from decimal import Decimal,DecimalException,localcontext
import hashlib
import json

from indicators.v02.common import finite_decimal,canonical_decimal,REFERENCE_CONTEXT

class MonteCarloPolicyError(ValueError): pass
def fail(code): raise MonteCarloPolicyError(code)
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(raw): return 'sha256:'+hashlib.sha256(raw).hexdigest()
def text(value): return canonical_decimal(str(value))
def integer(value,minimum,maximum):
    if type(value) is not int or not minimum<=value<=maximum: fail('INVALID_MONTE_CARLO_INTEGER')
    return value

def _policy(value):
    keys={'schema_version','algorithm','algorithm_version','rng_algorithm','resample_count','minimum_samples',
          'minimum_effective_blocks','block_length','sample_source','initial_equity','drawdown_unit',
          'max_path_observations','dependence_model'}
    if not isinstance(value,dict) or set(value)!=keys: fail('INVALID_MONTE_CARLO_POLICY_FIELDS')
    try: value=json.loads(canonical(value))
    except (ValueError,TypeError,RecursionError): fail('INVALID_MONTE_CARLO_POLICY')
    if value['schema_version']!='r7-monte-carlo-policy-v0.2' or value['algorithm_version']!='r7-mc-v1': fail('UNSUPPORTED_MONTE_CARLO_VERSION')
    if value['rng_algorithm']!='SHA256_COUNTER_REJECTION_V1': fail('UNSUPPORTED_RNG')
    if value['algorithm'] not in ('TRADE_PERMUTATION','MOVING_BLOCK_BOOTSTRAP'): fail('UNSUPPORTED_MONTE_CARLO_ALGORITHM')
    expected='ORDER_SENSITIVITY' if value['algorithm']=='TRADE_PERMUTATION' else 'OVERLAPPING_FIXED_BLOCKS'
    if value['dependence_model']!=expected: fail('DEPENDENCE_MODEL_MISMATCH')
    if value['sample_source']!='CLOSED_DEVELOPMENT_TRADE_NET_PNL_USDT': fail('INVALID_MONTE_CARLO_SAMPLE_SOURCE')
    if value['drawdown_unit'] not in ('USDT_AMOUNT','FRACTION_OF_INITIAL_EQUITY'): fail('UNSUPPORTED_DRAWDOWN_UNIT')
    integer(value['resample_count'],1,10000); integer(value['minimum_samples'],2,200000)
    integer(value['minimum_effective_blocks'],2,10000); integer(value['block_length'],1,10000)
    integer(value['max_path_observations'],1,500000)
    try: equity=finite_decimal(value['initial_equity'])
    except ValueError: fail('INVALID_INITIAL_EQUITY')
    if equity<=0: fail('INVALID_INITIAL_EQUITY')
    value['initial_equity']=text(equity)
    return value

class _CounterRNG:
    def __init__(self,seed): self.seed=seed.to_bytes(8,'big'); self.counter=0
    def below(self,size):
        # Rejection removes modulo bias. Protocol bytes and counter width are
        # pinned; no ambient random module/backend/platform state is consulted.
        ceiling=1<<256; limit=ceiling-ceiling%size
        while True:
            raw=hashlib.sha256(b'r7-mc-v02:'+self.seed+self.counter.to_bytes(8,'big')).digest()
            self.counter+=1; number=int.from_bytes(raw,'big')
            if number<limit: return number%size

@dataclass(frozen=True)
class MonteCarloAssessment:
    canonical_json: str
    assessment_hash: str
    def as_dict(self): return json.loads(self.canonical_json)

def _assessment(document):
    raw=canonical(document)
    return MonteCarloAssessment(raw,digest(raw.encode()))

def _quantiles(values):
    values=sorted(values); n=len(values)
    return {label:text(values[max(0,(n*numerator+denominator-1)//denominator-1)])
            for label,numerator,denominator in (('0.05',5,100),('0.50',50,100),('0.95',95,100))}

def _path(values,indices,equity,unit):
    running=peak=drawdown=Decimal(0)
    for index in indices:
        running+=values[index]; peak=max(peak,running); drawdown=max(drawdown,peak-running)
    return running,running/Decimal(len(indices)),drawdown if unit=='USDT_AMOUNT' else drawdown/equity

def evaluate_monte_carlo(net_pnl_samples,policy,*,seed):
    """Execute a declared algorithm; PASS means computed adequate sensitivity.

    Quantitative product thresholds are evaluated separately against these raw
    results. Trade permutation cannot supply expectancy inference. Block output
    is conditional on the selected sequence/dependence model, not a profit claim.
    """
    policy=_policy(policy); integer(seed,0,(1<<64)-1)
    if not isinstance(net_pnl_samples,(tuple,list)) or len(net_pnl_samples)>200000: fail('INVALID_SAMPLE_SEQUENCE')
    values=[]
    for value in net_pnl_samples:
        if not isinstance(value,(str,Decimal)) or isinstance(value,bool): fail('FINITE_DECIMAL_SAMPLES_REQUIRED')
        try: values.append(finite_decimal(str(value)))
        except ValueError: fail('FINITE_DECIMAL_SAMPLES_REQUIRED')
    size=len(values); permutations=policy['algorithm']=='TRADE_PERMUTATION'
    if size*policy['resample_count']>policy['max_path_observations']: fail('MONTE_CARLO_COMPUTATION_BUDGET_EXCEEDED')
    limitations=['Finite resampling sensitivity is not a profitability guarantee',
                 'Selection bias and unobserved market regimes are not removed by resampling']
    if not permutations: limitations.append('Dependence beyond selected block length is not modeled')
    with localcontext(REFERENCE_CONTEXT): rank_resolution=text(Decimal(1)/Decimal(policy['resample_count']))
    document=dict(schema_version='r7-monte-carlo-assessment-v0.2',status='BLOCKED',reason_codes=['INSUFFICIENT_EVIDENCE'],
                  algorithm=policy['algorithm'],algorithm_version=policy['algorithm_version'],rng_algorithm=policy['rng_algorithm'],
                  seed=seed,sample_count=size,resample_count=policy['resample_count'],policy_hash=digest(canonical(policy).encode()),
                  policy=policy,source_hash=digest(canonical([text(value) for value in values]).encode()),
                  sample_source=policy['sample_source'],drawdown_unit=policy['drawdown_unit'],initial_equity=policy['initial_equity'],
                  interpretation='DRAWDOWN_ORDER_SENSITIVITY_ONLY' if permutations else 'CONDITIONAL_BLOCK_RESAMPLING_SENSITIVITY',
                  dependence_model=policy['dependence_model'],block_length=None if permutations else policy['block_length'],
                  effective_blocks=None if permutations else size//policy['block_length'],
                  quantile_method='EMPIRICAL_NEAREST_RANK_V1',statistical_precision={'resamples':policy['resample_count'],
                        'quantile_rank_resolution':rank_resolution},
                  samples=[],drawdown_quantiles=None,expectancy_quantiles=None,limitations=limitations)
    if size<policy['minimum_samples'] or (not permutations and size//policy['block_length']<policy['minimum_effective_blocks']):
        return _assessment(document)
    rng=_CounterRNG(seed); equity=finite_decimal(policy['initial_equity']); drawdowns=[]; means=[]
    with localcontext(REFERENCE_CONTEXT):
        # Precision metadata is itself calculated under the declared context.
        document['statistical_precision']['quantile_rank_resolution']=text(Decimal(1)/Decimal(policy['resample_count']))
        for number in range(policy['resample_count']):
            if permutations:
                indices=list(range(size))
                for i in range(size-1,0,-1):
                    j=rng.below(i+1); indices[i],indices[j]=indices[j],indices[i]
            else:
                indices=[]; block=policy['block_length']
                while len(indices)<size:
                    start=rng.below(size-block+1)
                    indices.extend(range(start,start+min(block,size-len(indices))))
            try: net,mean,drawdown=_path(values,indices,equity,policy['drawdown_unit'])
            except DecimalException:
                document.update(status='BLOCKED',reason_codes=['ARITHMETIC_PROFILE_EXCEEDED'],samples=[],
                                drawdown_quantiles=None,expectancy_quantiles=None)
                return _assessment(document)
            document['samples'].append(dict(sample=number,source_indices=indices,net_pnl=text(net),
                                             expectancy=None if permutations else text(mean),max_drawdown=text(drawdown)))
            drawdowns.append(drawdown); means.append(mean)
        document.update(status='PASS',reason_codes=['SENSITIVITY_COMPUTED'],drawdown_quantiles=_quantiles(drawdowns),
                        expectancy_quantiles=None if permutations else _quantiles(means))
    return _assessment(document)
