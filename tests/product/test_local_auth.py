"""Local fixture passwords only; no operator/provider credential access."""
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from registry.operational_authority import HumanAuthenticator
from registry.models import EvidenceGateError


class LocalAuthTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('application.control_api.auth'),
                             'Actual local session authentication is missing')
        from application.control_api.auth import LocalAuth, AuthenticationError
        self.error = AuthenticationError
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'auth.sqlite'
        self.clock = [datetime(2026, 10, 3, tzinfo=timezone.utc)]
        self.password = 'explicit-test-only-password-123'
        self.auth = LocalAuth(self.path, namespace='FIXTURE', clock=lambda: self.clock[0], session_seconds=60)
        self.auth.create_owner('local-owner', self.password)

    def login(self, command='login-one'):
        return self.auth.login('local-owner', self.password, command_id=command, expected_revision=0)

    def test_password_hashed_and_opaque_token_never_stored_as_plaintext(self):
        grant = self.login()
        identity = self.auth.authenticate(grant.token)
        self.assertEqual(identity.actor, 'local-owner')
        self.assertEqual(identity.roles, ('ProductOwner',))
        db = sqlite3.connect(self.path)
        try:
            rows = repr(db.execute('SELECT * FROM local_users').fetchall()) + repr(db.execute('SELECT * FROM local_sessions').fetchall())
        finally: db.close()
        self.assertIn('$argon2id$', rows)
        self.assertNotIn(self.password, rows)
        self.assertNotIn(grant.token, rows)
        self.assertNotIn(grant.csrf_token, rows)
        self.assertNotIn(grant.token, repr(grant))

    def test_unknown_user_and_wrong_password_have_same_safe_reason(self):
        for username, password in (('unknown-owner', self.password), ('local-owner', 'wrong')):
            with self.subTest(username=username):
                with self.assertRaises(self.error) as error:
                    self.auth.login(username, password, command_id='login-' + username, expected_revision=0)
                self.assertEqual(error.exception.code, 'AUTHORIZATION_REQUIRED')
                self.assertNotIn(password, str(error.exception))

    def test_expiry_and_revocation_remove_authority_without_deleting_evidence(self):
        grant = self.login()
        self.clock[0] += timedelta(seconds=60)
        with self.assertRaises(self.error): self.auth.authenticate(grant.token)
        grant2 = self.login('login-two')
        self.auth.logout(grant2.token, expected_revision=1)
        with self.assertRaises(self.error): self.auth.authenticate(grant2.token)

    def test_clock_regression_fails_closed(self):
        grant = self.login()
        self.clock[0] += timedelta(seconds=5)
        self.auth.authenticate(grant.token)
        self.clock[0] -= timedelta(seconds=1)
        with self.assertRaises(self.error): self.auth.authenticate(grant.token)

    def test_csrf_is_bound_to_session_and_constant_time_verified(self):
        one = self.login()
        two = self.login('login-two')
        self.auth.require_csrf(one.token, one.csrf_token)
        for csrf in (None, '', 'wrong', two.csrf_token):
            with self.subTest(csrf='invalid'):
                with self.assertRaises(self.error): self.auth.require_csrf(one.token, csrf)

    def test_reauth_issues_actual_e6_capability_and_logout_revokes_it(self):
        grant = self.login()
        issuer = HumanAuthenticator(namespace='FIXTURE', verifier=self.auth.verify_reauthentication,
            reauth_seconds=30, clock=lambda: self.clock[0], current_verifier=self.auth.verify_reauthentication)
        proof = self.auth.reauthenticate(grant.token, self.password, expected_revision=1)
        human = issuer.authenticate(proof)
        self.assertEqual(issuer.authorize(human), 'local-owner')
        with self.assertRaises(EvidenceGateError): issuer.authenticate({'actor': 'ProductOwner', 'roles': ['ProductOwner']})
        self.auth.logout(grant.token, expected_revision=2)
        # Issuer tickets are explicitly tracked/revoked by the session service.
        with self.assertRaises(EvidenceGateError): issuer.authorize(human)

    def test_reauth_wrong_password_or_stale_revision_does_not_advance_session(self):
        grant = self.login()
        for password, revision in (('wrong', 1), (self.password, 0)):
            with self.subTest(revision=revision):
                with self.assertRaises(self.error): self.auth.reauthenticate(grant.token, password, expected_revision=revision)
        self.assertEqual(self.auth.session_view(grant.token)['revision'], 1)

    def test_first_run_owner_cannot_be_overwritten_or_created_twice(self):
        with self.assertRaises(self.error): self.auth.create_owner('another', self.password)
        self.assertEqual(self.auth.authenticate(self.login().token).actor, 'local-owner')

    def test_replayed_login_identity_cannot_issue_another_session(self):
        self.login()
        with self.assertRaises(self.error): self.login()

    def test_failed_login_rate_limit_is_durable_and_bounded(self):
        for index in range(5):
            with self.assertRaises(self.error):
                self.auth.login('local-owner', 'wrong', command_id='failed-' + str(index), expected_revision=0)
        with self.assertRaises(self.error) as error: self.login()
        self.assertEqual(error.exception.code, 'AUTHENTICATION_THROTTLED')
        from application.control_api.auth import LocalAuth
        other = LocalAuth(self.path, namespace='FIXTURE', clock=lambda: self.clock[0], session_seconds=60)
        with self.assertRaises(self.error): other.login('local-owner', self.password, command_id='other', expected_revision=0)
        self.clock[0] += timedelta(seconds=301)
        self.assertEqual(other.authenticate(other.login('local-owner', self.password, command_id='later', expected_revision=0).token).actor, 'local-owner')

    def test_namespace_binding_cannot_be_reopened_as_real(self):
        from application.control_api.auth import LocalAuth
        with self.assertRaises(self.error): LocalAuth(self.path, namespace='LOCAL_RESEARCH', clock=lambda: self.clock[0])

    def test_ambiguous_persisted_namespace_is_not_silently_accepted(self):
        from application.control_api.auth import LocalAuth
        db = sqlite3.connect(self.path)
        try:
            with db: db.execute('INSERT INTO local_auth_meta VALUES(?)', ('LOCAL_RESEARCH',))
        finally: db.close()
        with self.assertRaises(self.error) as error:
            LocalAuth(self.path, namespace='FIXTURE', clock=lambda: self.clock[0])
        self.assertEqual(error.exception.code, 'AUTH_NAMESPACE_CONFLICT')

    def test_unconfigured_store_has_no_default_password_or_authority(self):
        from application.control_api.auth import LocalAuth
        empty = LocalAuth(self.path.with_name('empty.sqlite'), namespace='FIXTURE', clock=lambda: self.clock[0])
        with self.assertRaises(self.error): empty.login('admin', 'admin', command_id='default-login', expected_revision=0)


if __name__ == '__main__': unittest.main()
