"""Read-only retained public-input and decision check; no research/model PASS."""
import hashlib
import json
from pathlib import Path

from application.cloud.manifest import parse_manifest, verify_payload
from application.datasets.catalog import DatasetCatalog

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def read(name):
    return json.loads((HERE / name).read_bytes())


def digest(raw):
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


def main():
    checks = []
    def check(name, predicate):
        if not predicate:
            raise ValueError('CHECKPOINT_CHECK_FAILED:' + name)
        checks.append(name)
    byte_manifest = read('public-input-byte-manifest.json')
    for row in byte_manifest['files']:
        path = HERE / row['path']
        check('public_input_bytes:' + row['path'], path.stat().st_size == row['bytes'] and digest(path.read_bytes()) == row['sha256'])
    check('exact_31_capture_3_author_files', byte_manifest['file_count'] == len(byte_manifest['files']) == 34
          and len(list((HERE / 'public-capture').rglob('*'))) >= 31)
    a = read('public-capture/acquisition.json')
    dataset = DatasetCatalog(HERE).load('public-capture/dataset.json')
    check('existing_dataset_manifest_validator', dataset.manifest_hash == a['manifest_hash'])
    check('actual_528_candles_264_funding_no_reported_gaps', a['status'] == 'DATASET_ACQUIRED'
          and a['candle_rows'] == 528 and a['funding_rows'] == 264
          and a['missing_ranges'] == a['duplicate_ranges'] == [])
    check('actual_9_public_requests_responses', a['provider_requests'] == a['provider_responses'] == 9
          and a['private_requests'] == a['provider_mutation'] == 0 and a['credentials'] == 'NONE')
    requests = list((HERE / 'public-capture/requests').glob('*-attempt.json'))
    responses = list((HERE / 'public-capture/requests').glob('*-result.json'))
    check('retained_actual_request_response_counts', len(requests) == len(responses) == 9)
    pkg = HERE / 'engineering-input'
    manifest = parse_manifest((pkg / 'manifest.json').read_bytes())
    for spec in manifest.payloads:
        verify_payload(spec, (pkg / spec.relative_path).read_bytes())
    check('actual_engineering_package_payloads', len(manifest.payloads) == 2
          and manifest.manifest_hash == 'sha256:d13d93b5c6823b925db12572dee5f1ddfcf5feb7e37db26e5a86d6abd874bf1c')
    d = read('operator-decision.json')
    check('numeric_selected_zero_rejected', d['selected_numeric_and_engineering_protocol'] is True and d['zero_funding_model_selected'] is False)
    check('approved_model_design_exact_bytes', d['model_design'] == 'HUMAN_APPROVED_20261021'
          and d['approved_design_sha256'] == digest((ROOT / d['approved_design_ref']).read_bytes()))
    check('plan_exact_bytes', d['implementation_plan_sha256'] == digest((ROOT / d['implementation_plan_ref']).read_bytes()))
    check('nothing_installed_or_started_or_receipt_copied', all(d[k] is False for k in
          ('product_policies_installed','owner_enrolled','qualification_receipt_issued','paper_started','real_time_observation_started')))
    r = read('funding-design-review-final.json')
    check('revised_design_static_review_no_execution', r['critical'] == r['important'] == 0 and r['execution'] == 'NONE')
    for row in r['reviewed_doc_hashes']:
        expected = row['sha256'] if row['sha256'].startswith('sha256:') else 'sha256:' + row['sha256']
        check('reviewed_document_current:' + row['path'], digest((ROOT / row['path']).read_bytes()) == expected)
    execution = read('execution.json')
    accounting = execution['request_accounting']
    check('cumulative_public17_not_zero', accounting['cumulative_public_requests'] == accounting['cumulative_public_responses'] == 17
          and accounting['previous_public_requests'] + accounting['new_public_requests'] == 17)
    check('no_research_or_product_acceptance', execution['research'] == execution['qualification'] == 'NOT_RUN'
          and execution['paper'] == execution['real_time_observation'] == 'NOT_STARTED')
    if (HERE / 'retention-manifest.json').exists():
        retained = read('retention-manifest.json')
        for row in retained['files']:
            check('retained_bytes:' + row['path'], digest((HERE / row['path']).read_bytes()) == row['sha256'])
    print(json.dumps(dict(kind='PUBLIC_INPUT_DECISION_BYTE_CHECK_ONLY', status='PASS', checks_passed=len(checks),
        checks=checks, market_api_calls=0, model_tests='NOT_RUN', backtest='NOT_RUN', native_qualification='NOT_RUN',
        ordinary_paper='NOT_STARTED', independent_oos='UNRESOLVED', sealed_financial_rows_decoded=False), sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
