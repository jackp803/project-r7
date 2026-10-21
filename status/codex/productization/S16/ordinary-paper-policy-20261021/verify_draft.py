"""Offline draft consistency checks, not research/native/workflow acceptance.

From the repository root, CPython3.12 with PYTHONPATH=src;.:
python -X utf8 status/codex/productization/S16/ordinary-paper-policy-20261021/verify_draft.py
No setup/DB/runtime/provider operations are called.
"""
import hashlib
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from application.coordinator import validate_operations
from application.datasets.catalog import canonical
from application.datasets.split_plan import _resolve_split
from application.paper.policy import parse_simulation_policy
from application.paper.public_market import validate_profile
from application.research.service import _cost_policy
from risk.product_policy import parse_product_risk_policy
from strategy import parse_strategy_definition
from validation.paper_policy import parse_paper_promotion_policy
from validation.robustness.evaluator import DevelopmentBinding, _variants
from validation.robustness.policies import ResearchPolicy, parse_robustness_policy

HERE = Path(__file__).resolve().parent


def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def digest(value):
    return 'sha256:' + hashlib.sha256(canonical(value).encode()).hexdigest()


def main():
    draft = read('draft.json')
    checks = []

    def check(name, condition):
        if not condition:
            raise ValueError('DRAFT_CHECK_FAILED:' + name)
        checks.append(name)

    check('explicitly_unselected_and_not_started', draft['status'] == 'DRAFT_NOT_SELECTED'
          and all(draft[k] is False for k in ('applied', 'runtime_started', 'observation_started')))
    selected = draft['proposed_selection_binding']
    check('no_operational_authorization_or_fabricated_receipt', selected['workflow_authorized'] is False
          and all(selected[k] is None for k in ('qualification_receipt_ref', 'submission_id', 'dataset_ref')))
    p = {name: read(name + '.proposed.json') for name in draft['proposed_policy_hashes']}
    check('proposed_hashes_match_actual_material', all(digest(value) == draft['proposed_policy_hashes'][name] for name, value in p.items()))
    ns = 'LOCAL_RESEARCH'
    _cost_policy(p['cost'], ns); checks.append('existing_cost_parser')
    ResearchPolicy.parse(p['research']); checks.append('existing_research_parser')
    robust = parse_robustness_policy(p['robustness']); checks.append('existing_robustness_and_two_mc_parsers')
    parse_product_risk_policy(p['risk'], namespace=ns); checks.append('existing_selected_e5_risk_parser')
    parse_simulation_policy(p['simulation'], namespace=ns); checks.append('existing_ordinary_simulation_parser')
    parse_paper_promotion_policy(p['promotion'], namespace=ns); checks.append('existing_paper_promotion_parser')
    validate_profile(p['market']); checks.append('existing_public_market_parser')
    validate_operations(p['operations']); checks.append('existing_operations_parser')
    for name in ('research', 'robustness'):
        check(name + '_binds_same_split_and_cost', all(p[name][k + '_policy_hash'] == digest(p[k]) for k in ('split', 'cost')))
    dataset = draft['planned_dataset']; start, end = utc(dataset['start']), utc(dataset['end'])
    # Only planned clock bounds are used; this is not a fabricated manifest or dataset.
    split = _resolve_split(ns, 'sha256:' + '0' * 64, start, end, ('4h',), p['split'])
    checks.append('existing_split_parser_on_explicitly_planned_clocks')
    duration = int((end - start).total_seconds())
    check('planned_acquisition_within_89_day_bound', 8*3600 <= duration <= 89*86400 and start.hour % 8 == end.hour % 4 == 0)
    theoretical_bars = duration // 14400
    check('theoretical_rows_only_not_acquired', theoretical_bars == dataset['theoretical_candle_rows']
          and duration // 28800 == dataset['theoretical_funding_rows']
          and dataset['acquired'] is False and dataset['actual_rows'] is None and dataset['actual_hashes'] is None)
    check('conservative_full_span_below_single_replay_cap', theoretical_bars <= p['cost']['max_evaluations'])
    binding = DevelopmentBinding({'4h': ()}, None, ns, 'PLANNED_CLOCK_CHECK_ONLY', 'NOT_ACQUIRED',
        'sha256:' + '0'*64, split.policy_hash, canonical(p['cost']), canonical(p['split']),
        start, split.development.end, split.development)
    previous = None
    windows = []
    for item in robust['walk_forward_windows']:
        train = binding.window(item['training'], embargo=False)
        evaluation = binding.window(item['evaluation'], embargo=True)
        check('wf_window_' + str(len(windows)+1) + '_ordered_and_development_only',
              split.development.start <= train.start < train.end <= evaluation.start
              and evaluation.end <= split.development.end
              and (previous is None or previous <= evaluation.start))
        previous = evaluation.end; windows.append((train, evaluation))
    strategy = read('engineering-strategy-0.2.2.proposed.json')
    parsed = parse_strategy_definition(strategy); checks.append('existing_e2_proposed_strategy_parser')
    _, variants = _variants(strategy, robust)
    check('five_distinct_referenced_valid_variants', len(variants) == 5
          and len({v['variant_hash'] for _, v in variants}) == 5
          and all(v['status'] != 'INVALID' for _, v in variants))
    check('baseline_parameter_and_original_exit_scope', parsed.strategy_version == '0.2.2'
          and strategy['parameters'] == {'adx_threshold': 20} and strategy['rules']['exit_policy']['max_hold_seconds'] == 14400)
    planned = [split.development] * (1 + len(variants) + len(robust['stress_scenarios']))
    for train, evaluation in windows:
        planned.extend([train] * len(variants) + [evaluation])
    theoretical_evaluations = sum(int((w.end - w.warmup_start).total_seconds()) // 14400 for w in planned)
    check('planned_robustness_budget', len(planned) == 20 <= robust['maximum_replays']
          and theoretical_evaluations <= robust['maximum_evaluations'])
    sim, risk, cost, research, forward = p['simulation'], p['risk']['policy'], p['cost'], p['research'], p['promotion']
    check('cross_policy_quantity_equity_and_fee_units', sim['quantity'] == cost['fixed_quantity']
          and sim['initial_balance_usdt'] == research['initial_equity_usdt']
          and Decimal(sim['fee_rate'])*10000 == Decimal(cost['maker_bps']) == Decimal(cost['taker_bps'])
          and Decimal(sim['slippage_bps']) == Decimal(cost['entry_bps']) == Decimal(cost['exit_bps']))
    check('risk_simulation_limits_agree', Decimal(sim['leverage']) <= Decimal(risk['max_leverage'])
          and Decimal(sim['estimated_roundtrip_cost_usdt']) <= Decimal(risk['max_estimated_cost'])
          and risk['max_hold_seconds'] == strategy['rules']['exit_policy']['max_hold_seconds'] == p['split']['max_holding_seconds'])
    check('mc_sample_equity_unit_and_capacity_agree', all(
        mc['initial_equity'] == research['initial_equity_usdt'] and mc['drawdown_unit'] == research['drawdown_unit']
        and mc['minimum_samples'] == research['minimum_closed_trades']['development']
        and theoretical_bars * mc['resample_count'] <= mc['max_path_observations']
        for mc in robust['monte_carlo']))
    check('forward_duration_health_and_samples', forward['min_elapsed_seconds'] == 30*86400
          and forward['required_healthy_seconds'] == 2566080 and forward['min_closed_trades'] == 30)
    check('unsupported_loss_controls_not_invented', 'max_loss_per_trade' not in risk and 'max_daily_loss' not in risk)
    check('zero_funding_and_long_run_capacity_disclosed', sim['funding_model'] == 'EXPLICIT_REGISTERED_PAPER_ZERO'
          and draft['observation_plan']['start_allowed'] is False
          and draft['observation_plan']['capacity'] == 'NOT_ESTABLISHED_FOR_30_DAYS')
    check('no_provider_or_private_execution_claim', draft['local_api_calls_this_preparation'] == draft['private_requests'] == draft['provider_mutation'] == 0)
    inputs = sorted(HERE.glob('*.proposed.json')) + [HERE / 'draft.json']
    report = dict(kind='OFFLINE_DRAFT_CONSISTENCY_ONLY', status='PASS', checks_passed=len(checks), checks=checks,
        source_execution='EXISTING_PARSERS_AND_CLOCK_ARITHMETIC_ONLY',
        product_qualification='NOT_RUN', candidate='NOT_ASSESSED', policies_selected=False, runtime_started=False,
        provider_requests=0, planned_robustness_replays=len(planned), theoretical_robustness_bar_evaluations=theoretical_evaluations,
        input_byte_hashes={f.name: 'sha256:' + hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs})
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
