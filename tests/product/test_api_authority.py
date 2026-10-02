"""Real ASGI/session/SQLite controls; explicit fixture namespace only."""
from datetime import datetime, timezone, timedelta
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient
from application.config import ProductConfig
from application.control_api.auth import LocalAuth
from application.control_api.commands import CommandLedger


class APIFixture:
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('application.control_api.app'),
                             'Authenticated versioned FastAPI is missing')
        from application.control_api.app import create_app
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.clock = [datetime(2026, 10, 3, tzinfo=timezone.utc)]
        self.auth = LocalAuth(self.root/'auth.sqlite', namespace='FIXTURE', clock=lambda: self.clock[0], session_seconds=60)
        self.password = 'explicit-test-only-password-123'
        self.auth.create_owner('local-owner', self.password)
        self.config = ProductConfig('r7-product-config-v0.2', 'fixture-control', self.root, None, self.root/'canonical.sqlite')
        self.ledger = CommandLedger(self.root/'commands.sqlite', namespace='FIXTURE', clock=lambda: self.clock[0])
        self.app = create_app(self.config, auth=self.auth, commands=self.ledger)
        self.client = TestClient(self.app, base_url='http://127.0.0.1:8765', client=('127.0.0.1', 42000), raise_server_exceptions=False)
        self.addCleanup(self.client.close)
        self.origin = {'Origin': 'http://127.0.0.1:8765'}

    def login(self, **extra):
        body = dict(username='local-owner', password=self.password, command_id='login-one', expected_revision=0)
        body.update(extra)
        response = self.client.post('/api/v1/auth/login', json=body, headers=self.origin)
        self.assertEqual(response.status_code, 200, response.text)
        self.csrf = response.json()['csrf_token']
        return response

    def post(self, path, body):
        return self.client.post(path, json=body, headers=dict(self.origin, **{'X-R7-CSRF': self.csrf}))


class APIAuthorityTests(APIFixture, unittest.TestCase):
    def test_every_product_view_requires_actual_session(self):
        for path in ('overview', 'capabilities', 'submissions', 'research/runs', 'strategies', 'datasets', 'policies', 'trading', 'health', 'alerts', 'settings'):
            with self.subTest(path=path):
                response = self.client.get('/api/v1/' + path)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()['error']['category'], 'AUTHORIZATION_REQUIRED')

    def test_login_sets_opaque_http_only_same_site_cookie_without_password_echo(self):
        response = self.login()
        cookie = response.headers['set-cookie']
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=strict', cookie)
        self.assertNotIn(self.password, response.text)
        self.assertNotIn('token', response.json())
        view = self.client.get('/api/v1/auth/session')
        self.assertEqual(view.json()['actor'], 'local-owner')
        self.assertEqual(view.json()['revision'], 1)

    def test_health_is_truthful_and_never_infers_flat_or_authorized_live(self):
        self.login()
        response = self.client.get('/api/v1/overview')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['data']['mode'], 'RESEARCH')
        self.assertEqual(body['data']['live_authorized'], False)
        self.assertIsNone(body['data']['exposure_quantity'])
        self.assertIsNone(body['data']['realized_pnl_usdt'])
        self.assertEqual(body['metadata']['current_or_last_known'], 'CURRENT')
        for field in ('source', 'observed_at', 'as_of', 'freshness', 'implementation_hash', 'config_hash'):
            self.assertIn(field, body['metadata'])
        health = self.client.get('/api/v1/health').json()['data']
        self.assertEqual(health['runtime'], 'NOT_CONFIGURED')
        self.assertEqual(health['cloud'], 'NOT_CONNECTED')
        self.assertEqual(health['provider_requests'], 0)

    def test_settings_are_actual_durable_cas_commands_with_identical_retry(self):
        self.login()
        settings = self.client.get('/api/v1/settings').json()['data']
        body = dict(command_id='settings-one', expected_revision=settings['revision'], display_timezone='UTC', scan_interval=45)
        response = self.client.put('/api/v1/settings/non-secret', json=body,
            headers=dict(self.origin, **{'X-R7-CSRF': self.csrf}))
        self.assertEqual(response.status_code, 200, response.text)
        changed = self.client.get('/api/v1/settings').json()['data']
        self.assertEqual(changed['scan_interval'], 45)
        self.assertEqual(changed['display_timezone'], 'UTC')
        self.assertEqual(changed['revision'], settings['revision'] + 1)
        retry = self.client.put('/api/v1/settings/non-secret', json=body,
            headers=dict(self.origin, **{'X-R7-CSRF': self.csrf}))
        self.assertEqual(retry.json(), response.json())
        different = dict(body, scan_interval=46)
        conflict = self.client.put('/api/v1/settings/non-secret', json=different,
            headers=dict(self.origin, **{'X-R7-CSRF': self.csrf}))
        self.assertEqual(conflict.status_code, 409)
        stale = dict(body, command_id='settings-two')
        self.assertEqual(self.client.put('/api/v1/settings/non-secret', json=stale,
            headers=dict(self.origin, **{'X-R7-CSRF': self.csrf})).status_code, 409)

    def test_actor_and_executable_evidence_cannot_be_injected(self):
        self.login()
        cases = (
            ('/api/v1/paper/runs', dict(strategy_id='one', strategy_version='1', policy_id='selected', actor='ProductOwner')),
            ('/api/v1/research/runs', dict(submission_id='one', policy_id='selected', status='PASS')),
            ('/api/v1/approvals', dict(strategy_id='one', strategy_version='1', envelope_ref='local-envelope', decision='APPROVE',
                reason_code='USER_CONFIRMED', expected_strategy_hash='sha256:'+'a'*64, expected_envelope_hash='sha256:'+'b'*64, actor='ProductOwner')),
        )
        for index, (path, values) in enumerate(cases):
            with self.subTest(path=path):
                response = self.post(path, dict(values, command_id='injection-'+str(index), expected_revision=0))
                self.assertEqual(response.status_code, 422, response.text)
                self.assertNotIn('ProductOwner', response.text)

    def test_fixture_approval_and_activation_are_denied_even_after_reauthentication(self):
        self.login()
        self.assertEqual(self.post('/api/v1/auth/reauthenticate', dict(password=self.password, command_id='reauth-one', expected_revision=1)).status_code, 200)
        body = dict(command_id='approval-one', expected_revision=0, strategy_id='one', strategy_version='1',
            envelope_ref='local-envelope', decision='APPROVE', reason_code='USER_CONFIRMED',
            expected_strategy_hash='sha256:'+'a'*64, expected_envelope_hash='sha256:'+'b'*64)
        response = self.post('/api/v1/approvals', body)
        self.assertEqual(response.status_code, 403)
        self.assertIn('FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN', response.text)
        activation = self.post('/api/v1/deployments/one/activate', dict(command_id='activate-one', expected_revision=0,
            strategy_id='one', strategy_version='1', evidence_ref='local-ref'))
        self.assertEqual(activation.status_code, 403)

    def test_unconfigured_services_report_typed_unavailable_without_fake_queued_jobs(self):
        self.login()
        response = self.post('/api/v1/research/runs', dict(command_id='research-one', expected_revision=0, submission_id='one', policy_id='selected'))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['category'], 'NOT_CONFIGURED')
        self.assertEqual(self.client.get('/api/v1/research/runs').json()['data']['items'], [])

    def test_expired_session_cannot_read_or_write_and_logout_revokes_cookie(self):
        self.login()
        response = self.post('/api/v1/auth/logout', dict(command_id='logout-one', expected_revision=1))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/v1/health').status_code, 401)
        self.login(command_id='login-two')
        self.clock[0] += timedelta(seconds=60)
        self.assertEqual(self.client.get('/api/v1/health').status_code, 401)

    def test_page_bounds_and_unknown_query_fields_are_enforced(self):
        self.login()
        for query in ('limit=0', 'limit=201', 'offset=-1', 'sql=SELECT', 'limit=true'):
            with self.subTest(query=query):
                self.assertEqual(self.client.get('/api/v1/submissions?' + query).status_code, 422)

    def test_errors_never_echo_passwords_paths_or_stack_traces(self):
        response = self.client.post('/api/v1/auth/login', json=dict(username='local-owner', password='wrong-fixture-password',
            command_id='login-one', expected_revision=0, private_key='injected-fixture-key'), headers=self.origin)
        self.assertEqual(response.status_code, 422)
        for value in ('wrong-fixture-password', 'injected-fixture-key', str(self.root), 'Traceback'):
            self.assertNotIn(value, response.text)
        self.assertRegex(response.json()['error']['correlation_id'], '^[0-9a-f]{32}$')

    def test_openapi_has_all_required_routes_and_strict_command_schemas(self):
        snapshot = Path(__file__).resolve().parents[2] / 'contracts' / 'control_api_v0_2.openapi.json'
        self.assertEqual(json.loads(snapshot.read_text(encoding='utf-8')), self.app.openapi(),
                         'Regenerate the committed API contract when routes or DTOs change')
        paths = self.app.openapi()['paths']
        for path in ('/overview', '/capabilities', '/submissions', '/submissions/{submission_id}', '/research/scan',
            '/research/runs', '/research/runs/{run_id}', '/research/runs/{run_id}/cancel', '/strategies',
            '/strategies/{strategy_id}/{strategy_version}', '/datasets', '/policies', '/paper/runs', '/paper/runs/{run_id}',
            '/paper/runs/{run_id}/pause', '/trading', '/health', '/alerts', '/settings', '/settings/non-secret', '/approvals',
            '/deployments/{deployment_id}/activate', '/deployments/{deployment_id}/pause'):
            self.assertIn('/api/v1' + path, paths)
        for schema in self.app.openapi()['components']['schemas'].values():
            if 'command_id' in schema.get('properties', {}):
                self.assertFalse(schema['additionalProperties'])
                self.assertIn('expected_revision', schema['required'])

    def test_unexpected_owner_failure_has_sanitized_correlation_without_exception_text(self):
        self.login()
        def fail(*args,**kwargs): raise RuntimeError('fixture-private-secret '+str(self.root))
        self.app.state.owners.view=fail
        response=self.client.get('/api/v1/health')
        self.assertEqual(response.status_code,500)
        self.assertEqual(response.json()['error']['category'],'INTERNAL_ERROR')
        for value in ('fixture-private-secret',str(self.root),'Traceback'):
            self.assertNotIn(value,response.text)

    def test_openapi_documents_actual_cookie_and_csrf_requirements_and_write_only_password(self):
        spec=self.app.openapi()
        self.assertIn('securitySchemes',spec['components'])
        self.assertEqual(spec['components']['securitySchemes']['r7_session']['in'],'cookie')
        self.assertEqual(spec['paths']['/api/v1/settings/non-secret']['put']['security'],[{'r7_session':[],'r7_csrf':[]}])
        self.assertNotIn('security',spec['paths']['/api/v1/auth/login']['post'])
        self.assertTrue(spec['components']['schemas']['LoginDTO']['properties']['password']['writeOnly'])


if __name__ == '__main__': unittest.main()
