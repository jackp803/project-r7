"""First-run CLI and actual local E6/API composition, without trading startup."""
from contextlib import redirect_stdout
import importlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from application import cli
from application.config import load_config


class NativeEntrypointTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='R7 原生 中文 空格 ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / '設定' / 'product.json'
        self.data = self.root / '本機 資料'
        self.assets = self.root / '介面'
        (self.assets / 'assets').mkdir(parents=True)
        (self.assets / 'index.html').write_text('<html>FIRST_RUN_FIXTURE</html>', encoding='utf-8')

    def initialize(self, **changes):
        argv = ['init-profile', '--config', str(self.config), '--data-root', str(self.data),
                '--instance-id', 'native-fixture']
        if changes.get('data_root') is not None:
            argv[4] = str(changes['data_root'])
        with redirect_stdout(io.StringIO()) as output:
            result = cli.main(argv)
        return result, output.getvalue()

    def entrypoints(self):
        return importlib.import_module('application.entrypoints')

    def test_first_profile_is_explicit_local_diagnostic_and_not_trading_authority(self):
        result, output = self.initialize()
        self.assertEqual(result, 0)
        config = load_config(self.config)
        self.assertEqual(config.local_data_root, self.data)
        self.assertIsNone(config.cloud_root)
        self.assertEqual(config.control_api_host, '127.0.0.1')
        self.assertTrue(config.diagnostic_only)
        self.assertFalse(config.paper_runtime_enabled)
        self.assertFalse(config.database_path.exists())
        self.assertEqual(json.loads(output)['status'], 'PROFILE_CREATED')

    def test_existing_profile_is_preserved_including_identical_retry(self):
        self.initialize()
        original = self.config.read_bytes()
        with self.assertRaises(ValueError):
            self.initialize()
        self.assertEqual(self.config.read_bytes(), original)

    def test_relative_root_and_installed_binary_directory_are_rejected(self):
        with self.assertRaises(ValueError):
            self.initialize(data_root='relative-data')
        entry = self.entrypoints()
        with patch.object(entry, 'installed_root', return_value=self.root / 'installation'):
            with self.assertRaises(ValueError):
                self.initialize(data_root=self.root / 'installation' / 'data')
        self.assertFalse(self.config.exists())

    def test_actual_e6_migrations_and_authenticated_api_are_composed(self):
        self.initialize()
        app = self.entrypoints().create_local_app(load_config(self.config), asset_root=self.assets)
        from fastapi.testclient import TestClient
        from storage import open_sqlite_platform
        with open_sqlite_platform(load_config(self.config).database_path, research_namespace='LOCAL_RESEARCH') as e6:
            self.assertEqual(sum(e6.lifecycle_counts().values()), 0)
        with TestClient(app, base_url='http://127.0.0.1:8765', client=('127.0.0.1', 42000)) as client:
            self.assertIn('FIRST_RUN_FIXTURE', client.get('/').text)
            self.assertEqual(client.get('/api/v1/health').status_code, 401)
            self.assertEqual(client.get('/api/v1/auth/status').json()['configured'], False)
            app.state.local_auth.create_owner('fixture-owner', 'synthetic-native-password-2026')
            login = client.post('/api/v1/auth/login', json=dict(username='fixture-owner',
                password='synthetic-native-password-2026', command_id='native-login', expected_revision=0),
                headers={'Origin': 'http://127.0.0.1:8765'})
            self.assertEqual(login.status_code, 200, login.text)
            health = client.get('/api/v1/health').json()['data']
            self.assertEqual(health['storage'], 'E6_AND_CONTROL_STORES_AVAILABLE')
            self.assertEqual(health['runtime'], 'NOT_CONFIGURED')
            self.assertFalse(health['live_authorized'])
            self.assertEqual(health['provider_requests'], 0)
            strategies = client.get('/api/v1/strategies').json()['data']
            self.assertEqual(strategies['items'], [])
            self.assertEqual(strategies['total'], 0)

    def test_missing_built_ui_fails_before_creating_any_profile_database(self):
        self.initialize()
        with self.assertRaises(ValueError):
            self.entrypoints().create_local_app(load_config(self.config), asset_root=self.root / 'absent')
        self.assertFalse(self.data.exists())

    def test_owner_enrollment_uses_hidden_interactive_input_and_never_prints_password(self):
        self.initialize()
        secret = 'synthetic-native-enrollment-2026'
        with patch('sys.stdin.isatty', return_value=True), patch('getpass.getpass', side_effect=[secret, secret]), \
                redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(['enroll-owner', '--config', str(self.config), '--username', 'fixture-owner']), 0)
        self.assertNotIn(secret, output.getvalue())
        from application.control_api.auth import LocalAuth
        auth = LocalAuth(self.data / 'local-auth.sqlite', namespace='LOCAL_RESEARCH')
        self.assertTrue(auth.configured())
        self.assertNotIn(secret.encode(), auth.path.read_bytes())

    def test_redirected_enrollment_is_refused_without_reading_or_creating_auth(self):
        self.initialize()
        with patch('sys.stdin.isatty', return_value=False), patch('getpass.getpass') as prompt:
            with self.assertRaises(ValueError):
                cli.main(['enroll-owner', '--config', str(self.config), '--username', 'fixture-owner'])
        prompt.assert_not_called()
        self.assertFalse((self.data / 'local-auth.sqlite').exists())

    def test_mismatched_password_confirmation_creates_no_auth_store(self):
        self.initialize()
        with patch('sys.stdin.isatty', return_value=True), patch('getpass.getpass', side_effect=[
                'synthetic-native-enrollment-2026', 'synthetic-wrong-confirmation-2026']):
            with self.assertRaises(ValueError):
                cli.main(['enroll-owner', '--config', str(self.config), '--username', 'fixture-owner'])
        self.assertFalse((self.data / 'local-auth.sqlite').exists())

    def test_frozen_owned_bootstrap_dispatches_argv_without_reserved_marker(self):
        with patch('sys.frozen', True, create=True), \
                patch('application.platform._process_bootstrap.main', return_value=17) as bootstrap:
            self.assertEqual(cli.main(['_owned-process-bootstrap', 'child.exe', 'bounded-argument']), 17)
        bootstrap.assert_called_once_with(['child.exe', 'bounded-argument'])

    def test_source_cli_cannot_borrow_private_frozen_bootstrap_mode(self):
        with self.assertRaises(SystemExit) as rejected:
            cli.main(['_owned-process-bootstrap', 'child.exe'])
        self.assertEqual(rejected.exception.code, 2)
