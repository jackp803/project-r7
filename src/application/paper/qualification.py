"""Fixed PQR receipt verification, separate from strategy/workflow authority.

The expected profile is installed trusted product inventory, never a request
body. This verifier neither imports PASS nor starts/migrates an owner.
"""
from dataclasses import asdict
import hashlib
from pathlib import Path

from application.datasets.catalog import read_local
from application.cloud.manifest import safe_relative
from registry.product_assessment import canonical, digest
from storage.qualification import QualificationReceipt

PROFILE_ID = 'r7-qualified-paper-release-v0.2'
GROUPS = tuple(f'PQR-{number:02d}' for number in range(1,8))


def validate_qualified_receipt(receipt, profile, *, artifact_root, measured):
    """Trusted composition only; exact installed profile plus measured target."""
    try:
        _validate(receipt, profile, Path(artifact_root), measured)
    except (ValueError, TypeError, KeyError, OSError, AttributeError, RecursionError):
        raise ValueError('QUALIFIED_PAPER_FIXED_INVENTORY_OR_SUBJECT_INVALID') from None


def _validate(receipt, profile, root, measured):
    if (not isinstance(receipt, QualificationReceipt) or receipt.scope != 'SOFTWARE_CHECK_EXECUTION_ONLY'
            or receipt.subject.namespace != 'LOCAL_RESEARCH' or receipt.profile_id != PROFILE_ID
            or not receipt.passed or not isinstance(profile, dict)
            or profile['schema_version'] != 'r7-qualified-paper-inventory-v0.2'
            or profile['profile_id'] != PROFILE_ID
            or profile['decision_ref'] != 'PM_PAPER_RELEASE_MAPPING_DECISION_20261013'
            or receipt.profile_hash != digest(canonical(profile)) or receipt.profile_manifest != profile):
        raise ValueError()
    if (asdict(receipt.subject) != dict(namespace='LOCAL_RESEARCH',
            **{key:measured[key] for key in ('executable_revision','implementation_hash','build_hash','platform_id')})
            or profile['platform_id'] != measured['platform_id'] or profile['capability_hash'] != measured['capability_hash']):
        raise ValueError()
    groups = profile['groups']
    if not isinstance(groups,list) or tuple(group['check_id'] for group in groups) != GROUPS:
        raise ValueError()
    members=[]
    for group in groups:
        if not isinstance(group['members'],list) or not group['members']:
            raise ValueError()
        members.extend((group['check_id'],member) for member in group['members'])
    if tuple(member['member_id'] for _,member in members) != tuple(check.check_id for check in receipt.checks):
        raise ValueError()
    evidence=receipt.execution_evidence
    if (not isinstance(evidence,dict) or set(evidence) != {'schema_version','provenance','members'}
            or evidence['schema_version'] != 'r7-qualified-paper-execution-evidence-v0.2'
            or evidence['provenance'] != 'FIXTURE_SOFTWARE_CHECKS_ONLY'
            or not isinstance(evidence['members'],list) or len(evidence['members']) != len(members)):
        raise ValueError()
    for (group_id,member),check,result in zip(members,receipt.checks,evidence['members']):
        if (not isinstance(result,dict) or set(result) != {'member_id','group_id','test_cases','artifacts','assertions'}
                or result['member_id'] != check.check_id or result['group_id'] != group_id
                or check.command_ref != member['command_ref'] or not check.passed
                or not isinstance(member['test_cases'],list) or result['test_cases'] != member['test_cases']):
            raise ValueError()
        if member['kind'] == 'UNITTEST':
            if not member['test_cases'] or check.tests_run != len(member['test_cases']) or member['assertions']:
                raise ValueError()
        elif member['kind'] == 'NATIVE_ASSERTIONS':
            if member['test_cases'] or check.tests_run != 0 or not member['assertions']:
                raise ValueError()
        else:
            raise ValueError()
        artifacts=result['artifacts']
        if not isinstance(artifacts,list) or not 1 <= len(artifacts) <= 128:
            raise ValueError()
        bindings={}
        for artifact in artifacts:
            if not isinstance(artifact,dict) or set(artifact) != {'ref','hash'}:
                raise ValueError()
            ref=safe_relative(artifact['ref'])
            if ref in bindings or 'sha256:'+hashlib.sha256(read_local(root,ref,8*1024*1024)).hexdigest() != artifact['hash']:
                raise ValueError()
            bindings[ref]=artifact['hash']
        if bindings.get(check.log_ref) != check.log_hash:
            raise ValueError()
        assertions=result['assertions']
        if not isinstance(assertions,list) or tuple(row['assertion_id'] for row in assertions) != tuple(member['assertions']):
            raise ValueError()
        for assertion in assertions:
            if (not isinstance(assertion,dict) or set(assertion) != {'assertion_id','status','evidence_ref','evidence_hash'}
                    or assertion['status'] != 'PASS' or bindings.get(assertion['evidence_ref']) != assertion['evidence_hash']):
                raise ValueError()
