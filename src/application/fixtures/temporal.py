"""Closed FIXTURE expiry inputs, bound to the actual sealed author payload.

These cases select finite synthetic timing only. They neither issue results nor
change the original validity, risk, supervisor clock or financial authority.
"""
from datetime import datetime,timedelta,timezone
import time,uuid

from application.cloud.manifest import safe_component,validate_package
from application.cloud.safe_files import read_bounded
from application.config import product_namespace
from application.datasets.catalog import canonical,decode,read_local
from application.platform.private_files import create_private_directory,write_private_new,require_private
from execution.models import require_utc
from strategy.v02.temporal import assess_submission_validity

CASES=('none','research-expire-before-robustness','paper-expire-before-entry','paper-expire-after-protection')
SCHEMA='r7-synthetic-fixture-temporal-v1'
REFERENCE='fixture-inputs/temporal.json'
SUBMISSION='r7-synthetic-fixture-input'


def utc(value):
    if not isinstance(value,str):raise ValueError('Original bounded UTC fixture validity required')
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    require_utc(parsed,'fixture temporal validity')
    return parsed


def validate(value):
    if (not isinstance(value,dict) or set(value)!={'schema_version','case','submission_id','validity'}
            or value['schema_version']!=SCHEMA or value['case'] not in CASES[1:]
            or value['submission_id']!=SUBMISSION):
        raise ValueError('Closed sealed FIXTURE temporal input required')
    interval=value['validity']
    if not isinstance(interval,dict) or set(interval)!={'from','until'}:
        raise ValueError('Exact original fixture validity required')
    lower,upper=utc(interval['from']),utc(interval['until'])
    if upper-lower!=timedelta(seconds=125):raise ValueError('Fixed bounded fixture interval required')
    assess_submission_validity(dict(intent_class='TACTICAL_STRATEGY',validity=interval),lower)
    return decode(canonical(value).encode('utf-8'))


def generate(case):
    if case not in CASES:raise ValueError('Closed FIXTURE temporal case required')
    if case=='none':return None
    actual=datetime.now(timezone.utc)
    z=lambda value:value.isoformat().replace('+00:00','Z')
    return validate(dict(schema_version=SCHEMA,case=case,submission_id=SUBMISSION,
        validity={'from':z(actual-timedelta(seconds=5)),'until':z(actual+timedelta(seconds=120))}))


def policy_ref(document):
    return 'r7-synthetic-paper-policy-'+validate(document)['case']


def read_temporal(config,package):
    if product_namespace(config)!='FIXTURE':raise ValueError('Temporal inputs cannot select ordinary Paper')
    verified=validate_package(package.snapshot)
    payloads=[spec for spec in verified.manifest.payloads if spec.role=='research_notes']
    auxiliary=config.local_data_root/REFERENCE
    if not payloads:
        if auxiliary.exists():raise ValueError('Fixture temporal payload missing from sealed submission')
        return None
    raw=read_bounded(verified.snapshot.root,payloads[0].relative_path,65536)
    try:value=decode(raw)
    except ValueError:
        if auxiliary.exists():raise ValueError('Sealed fixture temporal input invalid') from None
        return None
    if not isinstance(value,dict) or value.get('schema_version')!=SCHEMA:
        if auxiliary.exists():raise ValueError('Sealed fixture temporal schema missing')
        return None
    value=validate(value);manifest=verified.manifest.raw
    if (manifest['submission_id']!=SUBMISSION or manifest['intent_class']!='TACTICAL_STRATEGY'
            or manifest['validity']!=value['validity'] or read_local(config.local_data_root,REFERENCE,65536)!=raw):
        raise ValueError('Fixture temporal input differs from original sealed validity/payload')
    return value


def research_checkpoint(config,resolver,queue,run_id,generation,owner_run_id,stage,input_hash):
    if stage!='robustness':return
    claim=lambda:queue.checkpoint_claim(run_id,generation,owner_run_id,input_hash=input_hash)
    subject=claim()
    if subject['submission_id']!=SUBMISSION:return
    _,package=resolver.package(subject['submission_id'])
    document=read_temporal(config,package)
    if document is None or document['case']!='research-expire-before-robustness':return
    safe_component(owner_run_id)
    upper=utc(document['validity']['until']);started=datetime.now(timezone.utc)
    if (upper-started).total_seconds()>120:raise ValueError('Fixture actual wait exceeds fixed deadline')
    target=config.local_data_root/'fixture-observations'
    if not target.exists():create_private_directory(target)
    require_private(target,directory=True)
    # Full native owner IDs stay in the sealed observation body. A bounded
    # random filename remains inside the existing safe artifact component limit.
    observation='checkpoint-'+uuid.uuid4().hex
    safe_component(observation+'-start.json');safe_component(observation+'-finish.json')
    evidence=dict(schema_version=SCHEMA,case=document['case'],owner_run_id=owner_run_id,
        stage=stage,manifest_hash=package.manifest.manifest_hash,original_validity=document['validity'],
        actual_started_at=started.isoformat(),clock='ACTUAL_UTC',execution_evidence='OBSERVATION_ONLY')
    write_private_new(target/(observation+'-start.json'),(canonical(evidence)+'\n').encode('utf-8'))
    deadline=time.monotonic()+125
    while datetime.now(timezone.utc)<upper:
        claim()
        if time.monotonic()>=deadline:raise ValueError('Fixture expiry wait reached bounded deadline')
        time.sleep(min(.1,max(0,(upper-datetime.now(timezone.utc)).total_seconds())))
    # This records actual elapsed observation only. The unchanged queue resolver
    # performs the normal EXPIRED rejection after this observer returns.
    claim();read_temporal(config,package)
    evidence.update(actual_finished_at=datetime.now(timezone.utc).isoformat())
    write_private_new(target/(observation+'-finish.json'),(canonical(evidence)+'\n').encode('utf-8'))
