"""E6 product evidence identity and persistence-side gates.

The private writer capability separates trusted owner composition from ordinary
store calls. It does not sandbox hostile Python or a raw SQLite writer.
"""
from dataclasses import dataclass
import hashlib
import json

from .models import EvidenceGateError,StrategyIdentity

_PRODUCT_EVIDENCE_CAPABILITY=object()


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


def digest(raw):
    return 'sha256:'+hashlib.sha256(raw.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class ProductAssessmentRecord:
    assessment_id: str
    run_id: str
    identity: StrategyIdentity
    strategy_content_hash: str
    namespace: str
    implementation_hash: str
    status: str
    payload_json: str
    payload_hash: str
    risk_policy_json: str | None
    risk_policy_hash: str | None
    validation_evidence_id: str | None
    recorded_at: str
    result_ref: str


def product_managed(store,strategy):
    return store.get_research_namespace() is not None or strategy.declared_runtime_version=='0.2.0'


def require_product_record(store,strategy,record,*,status):
    from strategy.v02.capabilities import _revision
    if record is None or record.status!=status:
        raise EvidenceGateError('Complete actual E3 product assessment required')
    if record.identity!=strategy.identity or record.strategy_content_hash!=strategy.content_hash:
        raise EvidenceGateError('Product assessment subject mismatch')
    if record.namespace!=store.get_research_namespace() or record.implementation_hash!=_revision():
        raise EvidenceGateError('Product assessment namespace or current source mismatch')
    if digest(record.payload_json)!=record.payload_hash:
        raise EvidenceGateError('Product assessment content commitment mismatch')
    payload=json.loads(record.payload_json)
    if payload['status']!=status or payload['run_id']!=record.run_id:
        raise EvidenceGateError('Product assessment outcome mismatch')
    return payload


def require_product_candidate(store,strategy,decision_id):
    record=store.product_assessment_for_decision(decision_id)
    payload=require_product_record(store,strategy,record,status='PASS')
    if payload.get('independent_oos') is not True or payload.get('sealed_dataset_verification',{}).get('scope')!='FULL_LOGICAL_VERIFIED':
        raise EvidenceGateError('Complete independent final OOS required')
    if record.risk_policy_json is None or digest(record.risk_policy_json)!=record.risk_policy_hash:
        raise EvidenceGateError('Selected exact E5 risk policy required; diagnostic mode cannot promote')
    from risk.product_policy import parse_product_risk_policy
    parse_product_risk_policy(json.loads(record.risk_policy_json),namespace=record.namespace)
    if record.validation_evidence_id!=decision_id:
        raise EvidenceGateError('Canonical decision and product assessment mismatch')
    return record
