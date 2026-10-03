"""Separated scripted and production drivers, each requiring actual current owners."""
import json
from collections import deque
from copy import deepcopy
from application.trading.guards import _TradingEffectGuard
from application.trading.admission import RuntimeAdmissionError
from brokers.okx_production_transport import (OKXProductionHTTPTransport, OKXProductionTransportConfig,
    LocalSecureCredentialProvider, prepare_production_private_request)


class ProductProviderError(ValueError):
    pass


def _guard(value, execution):
    if type(value) is not _TradingEffectGuard or value.execution != execution:
        raise RuntimeAdmissionError('ACTUAL_PROVIDER_EFFECT_GUARD_REQUIRED')
    try:
        return value.require()
    except RuntimeAdmissionError:
        raise
    except ValueError:
        # Mechanical/current canonical gate errors happen before any effect;
        # provider ambiguity parsing must never absorb this denial.
        raise RuntimeAdmissionError('CURRENT_PROVIDER_EFFECT_GATE_DENIED') from None


class FakeProductProvider:
    """In-memory bounded responses only; cannot accept a transport or vault."""
    def __init__(self, responses):
        if not isinstance(responses, list) or len(responses) > 1000: raise ValueError('Bounded fake provider script required')
        raw = json.dumps(responses, allow_nan=False)
        if len(raw.encode()) > 1048576 or any(not isinstance(item, dict) and item != 'LOST_ACK' for item in responses):
            raise ValueError('Pure bounded fake provider data required')
        self._responses = deque(json.loads(raw)); self.calls = []

    def request(self, method, path, *, guard, query=None, body=None):
        owner = _guard(guard, 'FAKE_PROVIDER_VERIFICATION')
        if owner.namespace != 'FIXTURE': raise RuntimeAdmissionError('FAKE_PROVIDER_NAMESPACE_REQUIRED')
        self.calls.append(dict(method=method, path=path, query=deepcopy(query), body=deepcopy(body)))
        if not self._responses: raise ProductProviderError('FAKE_PROVIDER_RESPONSE_UNAVAILABLE')
        value = self._responses.popleft()
        if value == 'LOST_ACK': raise ProductProviderError('PROVIDER_OUTCOME_AMBIGUOUS')
        return value


class ProductionProductProvider:
    """Constructor reads no secrets and opens no socket. No default enrollment."""
    def __init__(self, *, config, vault, credential_handle, account_ref, account_hash, provider_ref):
        if type(config) is not OKXProductionTransportConfig or type(vault) is not LocalSecureCredentialProvider:
            raise ValueError('Explicit production transport and secure reader required')
        import re
        if (not isinstance(credential_handle, str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,63}', credential_handle) or
            not isinstance(account_hash, str) or not re.fullmatch('sha256:[0-9a-f]{64}', account_hash) or
            any(not isinstance(value, str) or not 0 < len(value) <= 256 for value in (account_ref, provider_ref))):
            raise ValueError('Exact local account selection required')
        self.config=config; self.vault=vault; self.handle=credential_handle
        self.account_ref=account_ref; self.account_hash=account_hash; self.provider_ref=provider_ref
        self.transport=OKXProductionHTTPTransport(config)

    def request(self, method, path, *, guard, query=None, body=None):
        owner = _guard(guard, 'PRODUCTION')
        if owner.namespace != 'LOCAL_RESEARCH' or (owner.release.provider_ref, owner.release.account_ref) != (self.provider_ref, self.account_ref):
            raise RuntimeAdmissionError('EXACT_PRODUCTION_PROVIDER_ACCOUNT_REQUIRED')
        prepared = guard.preparation
        if prepared is not None and prepared.mechanical_proof.account_hash != self.account_hash:
            raise RuntimeAdmissionError('CURRENT_SELECTED_PROVIDER_ACCOUNT_REQUIRED')
        credentials = self.vault.load(self.handle)
        timestamp = guard.service.clock().isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        signed = prepare_production_private_request(self.config, credentials, method=method, path=path,
                                                    timestamp=timestamp, query=query, body=body)
        _guard(guard, 'PRODUCTION')
        try: return self.transport.send(signed)
        except Exception: raise ProductProviderError('PROVIDER_OUTCOME_AMBIGUOUS') from None
