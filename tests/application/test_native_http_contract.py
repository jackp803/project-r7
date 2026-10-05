"""Native smoke denial assertions must match the actual existing API contract."""
from pathlib import Path
import json
from tempfile import TemporaryDirectory
import unittest

from application.config import ProductConfig, load_config
from application.entrypoints import create_local_app, initialize_profile
from tools import verify_native_product


class NativeHTTPContractTests(unittest.TestCase):
    def test_native_config_fault_uses_validated_defaults_from_actual_first_run_profile(self):
        with TemporaryDirectory(prefix='R7 原生 設定 預設 ') as temporary:
            root = Path(temporary)
            path = root / 'profile.json'
            initialize_profile(path, root / 'data', instance_id='native-config-fault-fixture')
            original = path.read_bytes()
            previous = load_config(path)
            changed = verify_native_product.changed_scan_profile(path)
            self.assertEqual(path.read_bytes(), original)
            path.write_text(json.dumps(changed), encoding='utf-8')
            current = load_config(path)
            self.assertEqual(current.scan_interval, previous.scan_interval + 1)
            self.assertEqual(current.product_instance_id, previous.product_instance_id)
            self.assertEqual(current.control_api_host, '127.0.0.1')

    def test_native_expected_denials_match_actual_local_security_adapter(self):
        from fastapi.testclient import TestClient
        with TemporaryDirectory(prefix='R7 原生 HTTP 契約 ') as temporary:
            root = Path(temporary)
            assets = root / 'ui'
            (assets / 'assets').mkdir(parents=True)
            (assets / 'index.html').write_text('<html>FIXTURE</html>', encoding='utf-8')
            config = ProductConfig('r7-product-config-v0.2', 'native-http-fixture', root / 'data',
                                   None, root / 'data' / 'canonical.sqlite3')
            app = create_local_app(config, asset_root=assets)
            with TestClient(app, base_url='http://127.0.0.1:8765', client=('127.0.0.1', 42000)) as client:
                host = client.get('/api/v1/auth/status', headers={'Host': 'external.invalid'})
                self.assertEqual(host.json()['error']['reason_codes'], ['HOST_NOT_ALLOWED'])
                self.assertEqual(host.status_code, verify_native_product.DENIAL_STATUSES['HOST'])
                origin = client.get('/api/v1/auth/status', headers={'Origin': 'http://external.invalid'})
                self.assertEqual(origin.status_code, verify_native_product.DENIAL_STATUSES['ORIGIN'])
                anonymous = client.get('/api/v1/health')
                self.assertEqual(anonymous.status_code, verify_native_product.DENIAL_STATUSES['ANONYMOUS'])
