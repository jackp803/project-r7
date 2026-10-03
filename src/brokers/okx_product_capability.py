"""Pinned v0.2 E4 mechanical proofs. These never grant financial or HTTP authority.

Trusted local composition supplies typed account observations and metadata after
readback. Owner-issued proofs bind those exact facts; caller PASS values, profile
labels and copied proof objects cannot substitute for the issuing owner.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re

from brokers.okx_demo import OKXAccountConfigSnapshot, OKXPrerequisiteSnapshot, OKXPositionFact
from decimal import Decimal
from brokers.okx_sizing import validate_okx_submit_metadata, OKXMetadataValidationError, OKXUnsupportedConversionError
from brokers.okx_close_sizing import (
    OKXCloseRoleCapabilityEvidence, OKXCloseSizingError,
    canonical_okx_close_sizing_hash,
    _evaluate_okx_close_residual_sizing_profile,
    _validate_okx_close_residual_sizing_evidence,
)
from brokers.okx_close_sizing_binding import validate_okx_close_metadata_binding

CAPABILITY_PROFILE = 'okx-product-action-role-capability-v0.2'
CLOSE_SIZING_PROFILE = 'okx-product-close-residual-sizing-v0.2'
_ROLES = frozenset({'ENTRY', 'PROTECTION_STOP', 'POSITION_EXIT', 'EMERGENCY_EXIT', 'READ_ONLY_RECONCILIATION'})


class OKXProductCapabilityError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _time(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise OKXProductCapabilityError('PRODUCT_CAPABILITY_UTC_REQUIRED')
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class _ProductMechanicalProof:
    profile: str
    role: str
    account_hash: str
    metadata_hash: str
    observed_at: datetime
    expires_at: datetime
    generation: int


@dataclass(frozen=True)
class _ProductEntryPrerequisiteProof:
    profile: str
    snapshot_hash: str
    account_hash: str
    generation: int
    observed_at: datetime
    expires_at: datetime


class OKXProductCapabilityOwner:
    def __init__(self):
        self._issued = {}
        self._entry_issued = {}
        self._account_hash = None
        self._metadata_hash = None
        self._generation = 0

    def issue(self, role, account, metadata, *, observed_at, now):
        now, observed_at = _time(now), _time(observed_at)
        if not isinstance(role, str) or role not in _ROLES:
            raise OKXProductCapabilityError('PRODUCT_CAPABILITY_ROLE_UNSUPPORTED')
        if (not isinstance(account, OKXAccountConfigSnapshot) or account.account_level != '2' or
            account.position_mode != 'net_mode' or any(not isinstance(x, str) or
            not re.fullmatch('[0-9]{1,64}', x) for x in (account.uid, account.main_uid))):
            raise OKXProductCapabilityError('PRODUCT_CAPABILITY_ACCOUNT_OUTSIDE_PROFILE')
        if observed_at > now or now - observed_at > timedelta(seconds=30):
            raise OKXProductCapabilityError('PRODUCT_CAPABILITY_ACCOUNT_OBSERVATION_STALE')
        try:
            validate_okx_submit_metadata(metadata, now=now)
        except (OKXMetadataValidationError, OKXUnsupportedConversionError, TypeError, AttributeError):
            raise OKXProductCapabilityError('PRODUCT_CAPABILITY_METADATA_NOT_CURRENT') from None
        account_hash, metadata_hash = canonical_okx_close_sizing_hash(account), canonical_okx_close_sizing_hash(metadata)
        if (account_hash, metadata_hash) != (self._account_hash, self._metadata_hash):
            self._issued.clear()
            self._entry_issued.clear()
            self._generation += 1
            self._account_hash, self._metadata_hash = account_hash, metadata_hash
        self._issued = {key: record for key, record in self._issued.items() if record[0].expires_at >= now}
        if len(self._issued) >= 1024:
            raise OKXProductCapabilityError('PRODUCT_CAPABILITY_ISSUANCE_LIMIT')
        proof = _ProductMechanicalProof(CAPABILITY_PROFILE, role, account_hash, metadata_hash,
                                        observed_at, observed_at + timedelta(seconds=30), self._generation)
        self._issued[id(proof)] = (proof, canonical_okx_close_sizing_hash(proof))
        return proof

    def observe_entry_prerequisites(self, prerequisites, *, observed_at, now):
        now, observed_at = _time(now), _time(observed_at)
        if (type(prerequisites) is not OKXPrerequisiteSnapshot or type(prerequisites.positions) is not tuple or
            type(prerequisites.pending_orders) is not tuple or prerequisites.pending_orders or len(prerequisites.positions) > 1000 or
            canonical_okx_close_sizing_hash(prerequisites.account) != self._account_hash or
            any(type(position) is not OKXPositionFact or position.instrument_id != 'BTC-USDT-SWAP' or
                position.margin_mode != 'isolated' or position.position_side != 'net' or
                not isinstance(position.provider_contract_quantity, Decimal) or not position.provider_contract_quantity.is_finite() or
                position.provider_contract_quantity != 0 for position in prerequisites.positions) or
            not observed_at <= now < observed_at + timedelta(seconds=5)):
            raise OKXProductCapabilityError('CURRENT_CONVERGED_ENTRY_PREREQUISITES_REQUIRED')
        self._entry_issued = {key: value for key, value in self._entry_issued.items() if value[0].expires_at > now}
        if len(self._entry_issued) >= 1024:
            raise OKXProductCapabilityError('PRODUCT_ENTRY_OBSERVATION_LIMIT')
        proof = _ProductEntryPrerequisiteProof('okx-product-entry-prerequisites-v0.2',
            canonical_okx_close_sizing_hash(prerequisites), self._account_hash, self._generation,
            observed_at, observed_at + timedelta(seconds=5))
        self._entry_issued[id(proof)] = (proof, canonical_okx_close_sizing_hash(proof))
        return proof

    def require_entry_prerequisites(self, prerequisites, proof, *, now):
        now = _time(now)
        record = self._entry_issued.get(id(proof))
        if (type(proof) is not _ProductEntryPrerequisiteProof or record is None or record[0] is not proof or
            record[1] != canonical_okx_close_sizing_hash(proof) or proof.generation != self._generation or
            proof.account_hash != self._account_hash or not proof.observed_at <= now < proof.expires_at or
            proof.snapshot_hash != canonical_okx_close_sizing_hash(prerequisites)):
            raise OKXProductCapabilityError('CURRENT_OWNER_ENTRY_PREREQUISITES_PROOF_REQUIRED')
        return proof

    def require(self, proof, metadata, *, role, now):
        now = _time(now)
        record = self._issued.get(id(proof))
        if (type(proof) is not _ProductMechanicalProof or record is None or record[0] is not proof or
            record[1] != canonical_okx_close_sizing_hash(proof) or
            proof.profile != CAPABILITY_PROFILE or proof.role != role or not proof.observed_at <= now <= proof.expires_at or
            proof.generation != self._generation or proof.account_hash != self._account_hash or
            proof.metadata_hash != self._metadata_hash or proof.metadata_hash != canonical_okx_close_sizing_hash(metadata)):
            raise OKXProductCapabilityError('PRODUCT_CAPABILITY_CURRENT_OWNER_PROOF_REQUIRED')
        try:
            validate_okx_submit_metadata(metadata, now=now)
        except (OKXMetadataValidationError, OKXUnsupportedConversionError, TypeError, AttributeError):
            raise OKXProductCapabilityError('PRODUCT_CAPABILITY_METADATA_NOT_CURRENT') from None
        return proof

    def close_capability(self, proof, metadata, *, now):
        if type(proof) is not _ProductMechanicalProof or proof.role not in {'POSITION_EXIT', 'EMERGENCY_EXIT'}:
            raise OKXProductCapabilityError('PRODUCT_CLOSE_ROLE_PROOF_REQUIRED')
        self.require(proof, metadata, role=proof.role, now=now)
        return OKXCloseRoleCapabilityEvidence(
            capability_profile_version=CAPABILITY_PROFILE,
            capability_row_ref='e4-product-fieldset:OKX:BTC-USDT-SWAP:' + proof.role + ':net:isolated:v0.2',
            action_role=proof.role, capability_state='REPO_EVIDENCED',
            capability_generation_id='e4-product-generation:' + str(proof.generation) + ':' + proof.account_hash,
            currentness_status='CURRENT', provider='OKX', canonical_symbol='BTC_USDT_PERP',
            provider_instrument_id='BTC-USDT-SWAP', inst_type='SWAP', account_level='2',
            position_mode='net_mode', margin_mode='isolated', provider_position_quantity_unit='CONTRACT',
            provider_position_quantity_proof_ref='e4-product-contract-unit:' + proof.metadata_hash,
            provider_fieldset_status='REPO_EVIDENCED',
        )

    def evaluate_close(self, value, metadata_binding, proof, *, now, supersedes_evidence=None):
        capability = self.close_capability(proof, value.instrument_metadata, now=now)
        if value.capability != capability or value.evaluated_at != now:
            raise OKXProductCapabilityError('PRODUCT_CLOSE_CURRENT_CAPABILITY_MISMATCH')
        validate_okx_close_metadata_binding(value, metadata_binding)
        return _evaluate_okx_close_residual_sizing_profile(
            value, sizing_profile=CLOSE_SIZING_PROFILE, capability_profile=CAPABILITY_PROFILE,
            supersedes_evidence=supersedes_evidence,
        )


def validate_product_close_sizing_evidence(evidence):
    _validate_okx_close_residual_sizing_evidence(evidence, sizing_profile=CLOSE_SIZING_PROFILE)
