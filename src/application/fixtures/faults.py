"""Closed sealed E1 recovery inputs, never execution or authority records."""
from application.config import product_namespace
from application.cloud.manifest import validate_package
from application.cloud.safe_files import read_bounded
from application.datasets.catalog import canonical,decode,read_local

CASES=('normal','hold-for-recovery','fill-at-target','partial-fill-hold',
    'duplicate-market-hold','missing-market-hold','stale-market-hold')
SCHEMA='r7-synthetic-fixture-paper-case-v1'
REFERENCE='fixture-inputs/paper-case.json'
SUBMISSION='r7-synthetic-fixture-input'
HOLD_SECONDS=30


def validate(value):
    if (not isinstance(value,dict) or set(value)!={'schema_version','case','submission_id'}
            or value['schema_version']!=SCHEMA or value['case'] not in CASES[1:]
            or value['submission_id']!=SUBMISSION):
        raise ValueError('Closed sealed FIXTURE Paper case required')
    return decode(canonical(value).encode('utf-8'))


def generate(case):
    if case not in CASES:raise ValueError('Closed FIXTURE Paper case required')
    if case=='normal':return None
    return validate(dict(schema_version=SCHEMA,case=case,submission_id=SUBMISSION))


def policy_ref(document):return 'r7-synthetic-paper-policy-'+validate(document)['case']


def require_selection(document,selected):
    if document is None:return
    document=validate(document)
    fraction='0.5' if document['case']=='partial-fill-hold' else '1'
    if (selected['paper_policy_ref']!=policy_ref(document)
            or selected['simulation_policy']['initial_fill_fraction']!=fraction):
        raise ValueError('Sealed fixture case requires its exact policy/fill semantics')


def read_case(config,package):
    if product_namespace(config)!='FIXTURE':raise ValueError('Synthetic Paper cases cannot select ordinary Paper')
    verified=validate_package(package.snapshot)
    payloads=[spec for spec in verified.manifest.payloads if spec.role=='research_notes']
    auxiliary=config.local_data_root/REFERENCE
    if not payloads:
        if auxiliary.exists():raise ValueError('Fixture Paper case missing from sealed author payload')
        return None
    raw=read_bounded(verified.snapshot.root,payloads[0].relative_path,65536)
    try:value=decode(raw)
    except ValueError:
        if auxiliary.exists():raise ValueError('Sealed fixture Paper case invalid') from None
        return None
    if not isinstance(value,dict) or value.get('schema_version')!=SCHEMA:
        if auxiliary.exists():raise ValueError('Sealed fixture Paper case schema missing')
        return None
    document=validate(value);manifest=verified.manifest.raw
    if (manifest['submission_id']!=SUBMISSION or manifest['intent_class']!='EVERGREEN_STRATEGY'
            or manifest['validity']!={'from':None,'until':None}
            or read_local(config.local_data_root,REFERENCE,65536)!=raw):
        raise ValueError('Fixture Paper case differs from original sealed payload/subject')
    return document
