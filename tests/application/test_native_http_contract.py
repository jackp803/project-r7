"""Native smoke denial assertions must match the actual existing API contract."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from application.config import ProductConfig
from application.entrypoints import create_local_app
from tools import verify_native_product


class NativeHTTPContractTests(unittest.TestCase):
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
