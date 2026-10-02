"""Pinned additive product role, using actual E7's current-authority interpreter.

Pure evidence, never provider/process/capital authorization. Legacy entry points
remain pinned to v0.1. A production application additionally needs actual current
E6 consent/release and provider capability; no such permission is defaulted here.
"""
from types import MappingProxyType
from integration.runtime_preflight import (
    RuntimePreflightInput,RuntimePreflightValidationError,_evaluate_runtime_preflight_profile,
    _validate_runtime_preflight_profile,
)

PRODUCT_RUNTIME_PREFLIGHT_PROFILE_VERSION='product-runtime-preflight-v0.2'
_ROLES=frozenset({'LIVE_RUNTIME'})
_CLASSES=MappingProxyType({'LIVE_RUNTIME':'PERSISTENT_LIVE_RUNTIME'})


def evaluate_product_runtime_preflight(value,authority):
    if not isinstance(value,RuntimePreflightInput) or value.runtime_preflight_profile_version!=PRODUCT_RUNTIME_PREFLIGHT_PROFILE_VERSION or value.runtime_role not in _ROLES:
        raise RuntimePreflightValidationError('PREFLIGHT_EVIDENCE_IDENTITY_INVALID','Pinned product profile/role required')
    return _evaluate_runtime_preflight_profile(value,authority,
        profile_version=PRODUCT_RUNTIME_PREFLIGHT_PROFILE_VERSION,runtime_roles=_ROLES,
        authorization_classes=_CLASSES,reconciliation_roles=_ROLES,external_roles=_ROLES,product_live=True)


def validate_product_runtime_preflight_evidence(evidence):
    _validate_runtime_preflight_profile(evidence,profile_version=PRODUCT_RUNTIME_PREFLIGHT_PROFILE_VERSION,runtime_roles=_ROLES)


def product_runtime_preflight_evidence_is_current(evidence,current_input,current_authority):
    try:
        validate_product_runtime_preflight_evidence(evidence)
        current=evaluate_product_runtime_preflight(current_input,current_authority)
    except (RuntimePreflightValidationError,AttributeError,TypeError):return False
    return dict(evidence)==current
