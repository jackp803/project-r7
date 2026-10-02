import unittest
from tests.product.test_api_authority import APIFixture


class APICSRFTests(APIFixture, unittest.TestCase):
    def test_dns_rebinding_and_wrong_origin_cannot_login(self):
        body = dict(username='local-owner', password=self.password, command_id='login-one', expected_revision=0)
        for headers in ({'Host': 'evil.invalid:8765', **self.origin}, {'Origin': 'http://evil.invalid'}, {}):
            with self.subTest(headers=list(headers)):
                response = self.client.post('/api/v1/auth/login', json=body, headers=headers)
                self.assertIn(response.status_code, (400, 403))

    def test_cross_site_get_and_forwarded_headers_cannot_bypass_loopback_rules(self):
        self.login()
        response = self.client.get('/api/v1/health', headers={'Sec-Fetch-Site': 'cross-site'})
        self.assertEqual(response.status_code, 403)
        response = self.client.get('/api/v1/health', headers={'Host': 'evil.invalid', 'X-Forwarded-Host': '127.0.0.1:8765'})
        self.assertEqual(response.status_code, 400)

    def test_product_write_requires_matching_csrf_even_with_valid_session(self):
        self.login()
        body = dict(command_id='settings-one', expected_revision=0, display_timezone='UTC', scan_interval=45)
        for csrf in (None, 'wrong'):
            headers = dict(self.origin)
            if csrf: headers['X-R7-CSRF'] = csrf
            response = self.client.put('/api/v1/settings/non-secret', json=body, headers=headers)
            self.assertEqual(response.status_code, 403)

    def test_form_and_missing_content_type_cannot_bypass_strict_json(self):
        for content_type in (None, 'text/plain', 'application/x-www-form-urlencoded'):
            headers = dict(self.origin)
            if content_type: headers['Content-Type'] = content_type
            response = self.client.post('/api/v1/auth/login', content='{}', headers=headers)
            self.assertEqual(response.status_code, 415)

    def test_duplicate_json_keys_nonfinite_and_oversize_body_are_rejected(self):
        cases = ('{"username":"one","username":"two"}', '{"value":NaN}', '{"value":"' + 'x'*65536 + '"}')
        for content in cases:
            with self.subTest(size=len(content)):
                response = self.client.post('/api/v1/auth/login', content=content,
                    headers=dict(self.origin, **{'Content-Type': 'application/json'}))
                self.assertIn(response.status_code, (413, 422))

    def test_no_wildcard_cors_and_security_headers_on_authenticated_response(self):
        self.login()
        response = self.client.get('/api/v1/health')
        self.assertNotIn('access-control-allow-origin', response.headers)
        self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
        self.assertEqual(response.headers['x-frame-options'], 'DENY')
        self.assertIn('no-store', response.headers['cache-control'])
        self.assertIn("frame-ancestors 'none'", response.headers['content-security-policy'])
