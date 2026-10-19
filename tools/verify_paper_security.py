"""Partial native PQR-06 public security observations, never group qualification.

Fresh synthetic FIXTURE only. Ordinary protected software receipt, runtime and
storage cases remain NOT_RUN. Source mocks earn no native execution credit.
"""
from datetime import datetime, timezone
import json
import secrets
import socket
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler, Request

import verify_paper_product as product


SECURITY_ASSERTIONS = (
    'NATIVE_AUTH_HOST_ORIGIN_CSRF_STALE_IDEMPOTENT_GUARDS',
    'NO_CALLER_PASS_CODE_GENERATION_FINANCIAL_AUTHORITY',
)
REMAINING_ASSERTIONS = (
    'RECEIPT_SUBJECT_ARTIFACT_CURRENT_RUNTIME_NEGATIVE_GATES',
    'IMMUTABLE_RECEIPT_REPLAY_CONFLICT_NAMESPACE',
)


class NativeSecurityFlow(product.NativeExpiryFlow):
    CASES = ('security-guards',)

    def __init__(self, package, output, *, expected_identity=None):
        super().__init__(package, output, 'security-guards', expected_identity=expected_identity)
        self.anonymous_opener = build_opener(ProxyHandler({}), product.NoRedirect())
        self.observation.update(coverage='PQR06_PARTIAL_SECURITY_ONLY', scoped_native_security_passed=False,
                                remaining_native_observations=list(REMAINING_ASSERTIONS))

    def setup(self):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        self.command('init', ['init-profile', '--config', self.config, '--data-root', self.data,
                             '--cloud-root', self.cloud, '--instance-id', 'pqr-06-security',
                             '--port', port, '--execution-mode', 'FIXTURE'])
        self.generated = self.command('prepare', ['prepare-fixture', '--config', self.config,
                                                 '--scenario', 'positive', '--temporal-case', 'none'])
        if self.generated['execution_evidence'] != 'NOT_RUN':
            raise ValueError('Fresh native unexecuted security inputs required')
        self.command('research-selection', ['configure-research', '--config', self.config,
                                            '--selection-profile', self.data / 'fixture-inputs/selection.json'])
        self.observation['enrollment'] = product.enroll(self.executable, self.config, self.password, env=self.env)
        self.start_control('control-security')

    def request(self, method, path, body=None, *, expected=200, reason=None,
                anonymous=False, headers_override=None):
        origin = urlsplit(self.origin)
        overrides = {} if headers_override is None else headers_override
        if (origin.scheme != 'http' or origin.hostname not in ('127.0.0.1', 'localhost', '::1')
                or origin.username is not None or origin.password is not None or origin.path
                or origin.query or origin.fragment or origin.port is None
                or not path.startswith('/api/v1/') or any(c in path for c in ('?', '#', '\\'))
                or any(part in ('.', '..') for part in path.split('/'))
                or method not in ('GET', 'POST') or type(anonymous) is not bool
                or not isinstance(overrides, dict)
                or set(overrides) - {'Host', 'Origin', 'x-r7-csrf', 'Sec-Fetch-Site'}
                or any(v is not None and (type(v) is not str or '\r' in v or '\n' in v)
                       for v in overrides.values())):
            raise ValueError('Fixed local native security request required')
        self.require_api_control()
        headers = {'Origin': self.origin}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        if not anonymous and self.csrf is not None:
            headers['x-r7-csrf'] = self.csrf
        for key, value in overrides.items():
            if value is None:
                headers.pop(key, None)
            else:
                headers[key] = value
        request = Request(self.origin + path, data=None if body is None else product.canonical(body).encode(),
                          headers=headers, method=method)
        opener = self.anonymous_opener if anonymous else self.opener
        try:
            response = opener.open(request, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read(1024 * 1024 + 1)
            status = response.code
            if response.geturl() != self.origin + path or len(raw) > 1024 * 1024:
                raise ValueError('Bounded native security response required')
        self.require_api_control()
        payload = json.loads(raw)
        error = payload.get('error', {}) if isinstance(payload, dict) else {}
        observed_reason = error.get('reason_codes', []) if isinstance(error, dict) else []
        category = {400: 'INVALID_INPUT', 401: 'AUTHORIZATION_REQUIRED', 403: 'AUTHORIZATION_REQUIRED',
                    409: 'CONFLICT', 422: 'INVALID_INPUT'}.get(expected)
        # Never retain request/response bodies, authentication proofs or headers.
        retained_reason = [reason] if reason is not None and observed_reason == [reason] else []
        self.requests.append(dict(method=method, path=path, status=status,
                                  reason_codes=retained_reason,
                                  actual_at=datetime.now(timezone.utc).isoformat()))
        self.persist()
        if (status != expected or reason is not None and observed_reason != [reason]
                or category is not None and (not isinstance(error, dict) or error.get('category') != category)):
            raise ValueError('Actual native security status/reason mismatch')
        return payload

    def owner_effects(self):
        overview = self.view('overview')
        return dict(scan_revision=overview['scan_revision'], lifecycle_counts=overview['lifecycle_counts'],
                    live_authorized=overview['live_authorized'],
                    pages={name: product.sha(product.canonical(self.view(name)['items']).encode())
                           for name in ('submissions', 'strategies', 'research/runs', 'paper/runs')})

    def unchanged(self, before):
        if self.owner_effects() != before:
            raise ValueError('Denied or replayed command changed actual owner effects')

    def authentication_guards(self):
        status = self.request('GET', '/api/v1/auth/status', anonymous=True)
        if status != dict(configured=True, namespace='FIXTURE', enrollment='LOCAL_CLI_ONLY'):
            raise ValueError('Actual native fixture authentication status required')
        self.request('GET', '/api/v1/overview', anonymous=True, expected=401, reason='AUTHORIZATION_REQUIRED')
        self.login()
        before = self.owner_effects()
        if before['live_authorized'] is not False:
            raise ValueError('Fixture login cannot grant live authority')
        self.request('GET', '/api/v1/overview', anonymous=True, expected=401, reason='AUTHORIZATION_REQUIRED')
        self.unchanged(before)

    def security_guards(self):
        before = self.owner_effects()
        body = dict(command_id='guard-' + secrets.token_hex(12), expected_revision=before['scan_revision'])
        cases = (({'Host': 'forbidden.invalid'}, 400, 'HOST_NOT_ALLOWED'),
                 ({'Origin': 'https://forbidden.invalid'}, 403, 'ORIGIN_NOT_ALLOWED'),
                 ({'Origin': None}, 403, 'SAME_ORIGIN_REQUIRED'),
                 ({'x-r7-csrf': None}, 403, 'CSRF_REQUIRED'),
                 ({'x-r7-csrf': 'x' * 43}, 403, 'CSRF_REQUIRED'))
        for headers, status, reason in cases:
            self.request('POST', '/api/v1/research/scan', body, expected=status, reason=reason,
                         headers_override=headers)
            self.unchanged(before)

    def scan_replay_guards(self):
        before = self.owner_effects()
        body = dict(command_id='scan-' + secrets.token_hex(12), expected_revision=before['scan_revision'])
        _, receipt, summary = self.scan(body=body)
        after = self.owner_effects()
        if (after['scan_revision'] != before['scan_revision'] + 1
                or receipt.get('status') != 'COMPLETE' or summary.get('accepted') != 1
                or after['pages']['research/runs'] != before['pages']['research/runs']
                or after['pages']['paper/runs'] != before['pages']['paper/runs']
                or after['live_authorized'] is not False):
            raise ValueError('Actual single scan without research or Paper execution required')
        if self.request('POST', '/api/v1/research/scan', body) != receipt:
            raise ValueError('Completed exact native scan receipt changed')
        self.unchanged(after)
        self.request('POST', '/api/v1/research/scan', {**body, 'command_id': 'stale-' + secrets.token_hex(12)},
                     expected=409, reason='RESOURCE_REVISION_CONFLICT')
        self.unchanged(after)
        self.request('POST', '/api/v1/research/scan', {**body, 'expected_revision': after['scan_revision']},
                     expected=409, reason='CONFLICT')
        self.unchanged(after)

    def dto_guards(self):
        before = self.owner_effects()
        fields = dict(passed=True, status='PASS', code='untrusted-code', runtime_generation=1,
                      config_generation=1, risk_generation=1, namespace='LOCAL_RESEARCH',
                      financial_authority='APPROVED', risk_policy={}, execution_inventory=[],
                      release_kind='NATIVE_QUALIFIED')
        for key, value in fields.items():
            body = dict(command_id='extra-' + secrets.token_hex(12), expected_revision=before['scan_revision'])
            self.request('POST', '/api/v1/research/scan', {**body, key: value}, expected=422,
                         reason='DTO_VALIDATION_FAILED')
            self.unchanged(before)

    def financial_guard(self):
        before = self.owner_effects()
        self.request('POST', '/api/v1/deployments/native-security-subject/activate',
                     dict(command_id='financial-' + secrets.token_hex(12), expected_revision=0,
                          strategy_id='native-security-subject', strategy_version='1',
                          evidence_ref='native-security-evidence'), expected=403,
                     reason='FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN')
        self.unchanged(before)

    def run(self):
        self.observation.update(passed=False, scoped_native_security_passed=False,
                                coverage='PQR06_PARTIAL_SECURITY_ONLY',
                                remaining_native_observations=list(REMAINING_ASSERTIONS),
                                assertions={name: 'NOT_RUN' for name in (*SECURITY_ASSERTIONS, *REMAINING_ASSERTIONS)})
        try:
            self.setup()
            self.authentication_guards()
            self.security_guards()
            self.scan_replay_guards()
            self.dto_guards()
            self.financial_guard()
        except Exception as error:
            self.observation['error_type'] = type(error).__name__
            raise
        finally:
            try:
                self.stop_control()
                self.guard()
            finally:
                self.persist()
        self.observation.update(scoped_native_security_passed=True,
                                assertions={**{name: 'PASS' for name in SECURITY_ASSERTIONS},
                                            **{name: 'NOT_RUN' for name in REMAINING_ASSERTIONS}})
        self.persist()
        return self.observation


def verify_slice(package, output, identity):
    """Retain one actual native partial attempt; never return group PASS."""
    flow = NativeSecurityFlow(package, output / 'security-guards', expected_identity=identity)
    try:
        return [flow.run()]
    except Exception as error:
        flow.observation.update(passed=False, scoped_native_security_passed=False,
                                error_type=type(error).__name__)
        flow.persist()
        return [flow.observation]
