from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import unittest
from tests.product.test_api_authority import APIFixture


class ControlAssetTests(APIFixture,unittest.TestCase):
    def mount(self):
        self.assertIsNotNone(importlib.util.find_spec('application.control_api.assets'),'Local production UI serving is missing')
        from application.control_api.assets import mount_control_center
        self.assets=self.root/'ui'; (self.assets/'assets').mkdir(parents=True)
        (self.assets/'index.html').write_text('<!doctype html><html lang="zh-Hant"><title>R7 本機控制中心</title></html>',encoding='utf-8')
        (self.assets/'assets/app.js').write_text('const r7=true;',encoding='utf-8')
        mount_control_center(self.app,self.assets)

    def test_local_login_shell_and_self_assets_are_public_but_api_stays_authenticated(self):
        self.mount()
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertIn('zh-Hant',response.text)
        self.assertIn("script-src 'self'",response.headers['content-security-policy'])
        self.assertEqual(self.client.get('/assets/app.js').status_code,200)
        self.assertEqual(self.client.get('/api/v1/overview').status_code,401)
        self.assertEqual(self.client.get('/api/v1/missing').status_code,404)

    def test_static_traversal_cannot_read_auth_or_other_project_files(self):
        self.mount()
        (self.root/'outside.txt').write_text('fixture-private-content',encoding='utf-8')
        for path in ('/assets/%2e%2e/%2e%2e/outside.txt','/assets/%2e%2e/index.html','/auth.sqlite'):
            with self.subTest(path=path):
                response=self.client.get(path)
                self.assertEqual(response.status_code,404,response.text)
                self.assertNotIn('fixture-private-content',response.text)

    def test_ui_mount_does_not_drift_openapi_or_accept_missing_asset_root(self):
        before=self.app.openapi(); self.mount()
        self.assertEqual(self.app.openapi(),before)
        from application.control_api.assets import mount_control_center
        with self.assertRaises(ValueError): mount_control_center(self.app,self.root/'missing')


if __name__=='__main__': unittest.main()
