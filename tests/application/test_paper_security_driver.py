"""Source-only security driver checks; mocks establish no native qualification."""
import importlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch


class PaperSecurityDriverTests(unittest.TestCase):
    def module(self):
        root = Path(__file__).resolve().parents[2]
        with patch.object(sys, 'path', [str(root / 'tools'), *sys.path]):
            return importlib.import_module('tools.verify_paper_security')

    def flow(self):
        flow = object.__new__(self.module().NativeSecurityFlow)
        flow.origin = 'http://127.0.0.1:8765'
        flow.csrf = 'SOURCE_ONLY_CSRF'
        flow.requests = []
        flow.require_api_control = Mock()
        flow.persist = Mock()
        flow.opener = Mock()
        flow.anonymous_opener = Mock()
        return flow

    def response(self, status, payload):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps(payload).encode()
        response.code = status
        response.geturl.return_value = 'http://127.0.0.1:8765/api/v1/research/scan'
        return response

    def test_request_overrides_are_local_bounded_and_do_not_record_proofs(self):
        flow = self.flow()
        error = dict(error=dict(category='AUTHORIZATION_REQUIRED', reason_codes=['SAME_ORIGIN_REQUIRED']))
        flow.anonymous_opener.open.return_value = self.response(403, error)
        flow.request('POST', '/api/v1/research/scan', dict(command_id='safe', expected_revision=0),
                     expected=403, reason='SAME_ORIGIN_REQUIRED', anonymous=True,
                     headers_override={'Origin': None})
        request = flow.anonymous_opener.open.call_args.args[0]
        self.assertFalse(request.has_header('Origin'))
        self.assertFalse(request.has_header('X-r7-csrf'))
        self.assertEqual(flow.require_api_control.call_count, 2)
        self.assertNotIn('SOURCE_ONLY_CSRF', json.dumps(flow.requests))
        self.assertNotIn('body', flow.requests[0])
        flow.opener.open.assert_not_called()

    def test_changed_control_cannot_contribute_response_evidence(self):
        flow = self.flow()
        flow.require_api_control.side_effect = [None, ValueError('SOURCE_ONLY_PRIVATE_TEXT')]
        flow.opener.open.return_value = self.response(200, {})
        with self.assertRaises(ValueError):
            flow.request('POST', '/api/v1/research/scan', {})
        self.assertEqual(flow.requests, [])

    def test_wrong_reason_or_oversized_response_fails_closed(self):
        flow = self.flow()
        flow.opener.open.return_value = self.response(403, dict(error=dict(reason_codes=['OTHER'])))
        with self.assertRaises(ValueError):
            flow.request('POST', '/api/v1/research/scan', {}, expected=403, reason='CSRF_REQUIRED')
        response = self.response(200, {})
        response.read.return_value = b'x' * (1024 * 1024 + 1)
        flow.opener.open.return_value = response
        with self.assertRaises(ValueError):
            flow.request('POST', '/api/v1/research/scan', {})

    def test_nonlocal_paths_and_arbitrary_header_inputs_never_send(self):
        flow = self.flow()
        for path, headers in [('https://example.invalid/api/v1/health', {}),
                              ('/api/v1/research/scan', {'Authorization': 'forbidden'})]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                flow.request('GET', path, headers_override=headers)
        flow.opener.open.assert_not_called()

    def test_correct_status_and_reason_with_wrong_error_category_is_rejected(self):
        flow = self.flow()
        flow.opener.open.return_value = self.response(403, dict(error=dict(
            category='INVALID_INPUT', reason_codes=['CSRF_REQUIRED'])))
        with self.assertRaises(ValueError):
            flow.request('POST', '/api/v1/research/scan', {}, expected=403, reason='CSRF_REQUIRED')

    def test_security_matrix_checks_every_fixed_header_guard_without_effects(self):
        flow = self.flow()
        flow.owner_effects = Mock(return_value={'scan_revision': 0})
        flow.request = Mock(return_value={})
        flow.security_guards()
        calls = flow.request.call_args_list
        self.assertEqual([call.kwargs['reason'] for call in calls],
                         ['HOST_NOT_ALLOWED', 'ORIGIN_NOT_ALLOWED', 'SAME_ORIGIN_REQUIRED',
                          'CSRF_REQUIRED', 'CSRF_REQUIRED'])
        self.assertEqual(calls[2].kwargs['headers_override'], {'Origin': None})
        self.assertEqual(calls[3].kwargs['headers_override'], {'x-r7-csrf': None})
        self.assertEqual(flow.owner_effects.call_count, 6)

    def test_scan_replay_requires_exact_receipt_and_stale_conflict_without_execution(self):
        flow = self.flow()
        before = dict(scan_revision=0, pages={'research/runs': 'empty', 'paper/runs': 'empty'},
                      live_authorized=False)
        after = {**before, 'scan_revision': 1}
        receipt = dict(status='COMPLETE', effect_ref='inbox-scan:source-only')
        flow.owner_effects = Mock(side_effect=[before, after, after, after, after])
        flow.scan = Mock(return_value=({}, receipt, {'accepted': 1}))
        flow.request = Mock(side_effect=[receipt, {}, {}])
        flow.scan_replay_guards()
        self.assertEqual(flow.request.call_args_list[1].kwargs['reason'], 'RESOURCE_REVISION_CONFLICT')
        self.assertEqual(flow.request.call_args_list[2].kwargs['reason'], 'CONFLICT')
        flow.owner_effects = Mock(side_effect=[before, after])
        flow.request = Mock(return_value={**receipt, 'effect_ref': 'different'})
        with self.assertRaises(ValueError):
            flow.scan_replay_guards()

    def test_setup_uses_positive_fixture_without_temporal_expiry_or_early_login(self):
        m = self.module()
        flow = self.flow()
        flow.config = Path('SOURCE_ONLY_CONFIG.json')
        flow.data = Path('SOURCE_ONLY_DATA')
        flow.cloud = Path('SOURCE_ONLY_CLOUD')
        flow.executable = Path('SOURCE_ONLY.exe')
        flow.password = 'SOURCE_ONLY_PASSWORD'
        flow.env = {}
        flow.observation = {}
        flow.command = Mock(side_effect=[{}, dict(execution_evidence='NOT_RUN'), {}])
        flow.start_control = Mock()
        flow.login = Mock()
        probe = Mock()
        probe.__enter__ = Mock(return_value=probe)
        probe.__exit__ = Mock(return_value=False)
        probe.getsockname.return_value = ('127.0.0.1', 8765)
        with patch.object(m.socket, 'socket', return_value=probe), patch.object(m.product, 'enroll', return_value={}):
            flow.setup()
        args = flow.command.call_args_list[1].args[1]
        self.assertEqual(args[args.index('--scenario') + 1], 'positive')
        self.assertEqual(args[args.index('--temporal-case') + 1], 'none')
        flow.login.assert_not_called()

    def test_extra_authority_fields_require_422_without_owner_effect(self):
        flow = self.flow()
        flow.owner_effects = Mock(return_value={'scan_revision': 0})
        flow.request = Mock(return_value={})
        flow.dto_guards()
        names = {next(key for key in call.args[2] if key not in ('command_id', 'expected_revision'))
                 for call in flow.request.call_args_list}
        self.assertTrue({'passed', 'code', 'runtime_generation', 'namespace', 'financial_authority'} <= names)
        for call in flow.request.call_args_list:
            self.assertEqual(call.kwargs['expected'], 422)
            self.assertEqual(call.kwargs['reason'], 'DTO_VALIDATION_FAILED')

    def test_effect_change_is_not_security_success(self):
        flow = self.flow()
        flow.owner_effects = Mock(side_effect=[{'scan_revision': 0}, {'scan_revision': 1}])
        flow.request = Mock(return_value={})
        with self.assertRaises(ValueError):
            flow.financial_guard()

    def test_scoped_success_never_qualifies_whole_group(self):
        flow = self.flow()
        flow.observation = dict(passed=False)
        for name in ('setup', 'authentication_guards', 'security_guards', 'scan_replay_guards',
                     'dto_guards', 'financial_guard', 'stop_control', 'guard'):
            setattr(flow, name, Mock())
        result = flow.run()
        self.assertFalse(result['passed'])
        self.assertTrue(result['scoped_native_security_passed'])
        self.assertEqual(result['assertions']['RECEIPT_SUBJECT_ARTIFACT_CURRENT_RUNTIME_NEGATIVE_GATES'], 'NOT_RUN')
        self.assertEqual(result['assertions']['IMMUTABLE_RECEIPT_REPLAY_CONFLICT_NAMESPACE'], 'NOT_RUN')
        flow.stop_control.assert_called_once()

    def test_failed_attempt_stays_partial_and_cleanup_always_runs(self):
        flow = self.flow()
        flow.observation = dict(passed=False)
        flow.setup = Mock(side_effect=ValueError('SOURCE_ONLY_PRIVATE_TEXT'))
        flow.stop_control = Mock()
        flow.guard = Mock()
        with self.assertRaises(ValueError):
            flow.run()
        self.assertFalse(flow.observation['passed'])
        self.assertFalse(flow.observation['scoped_native_security_passed'])
        self.assertNotIn('SOURCE_ONLY_PRIVATE_TEXT', json.dumps(flow.observation))
        flow.stop_control.assert_called_once()


if __name__ == '__main__':
    unittest.main()
