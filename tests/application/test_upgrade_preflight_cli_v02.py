"""Normal CLI uses actual verified bundles and reports bounded schema refusal."""
from contextlib import redirect_stdout,redirect_stderr
import io,json,unittest

from application.cli import main
from tests.application.upgrade_preflight_fixture import make_verified_bundle,source_database_hashes,bundle_hashes


class UpgradePreflightCliV02Tests(unittest.TestCase):
    def test_normal_cli_reports_actual_compatible_and_changed_schema_without_paths_or_effects(self):
        for changed in (False,True):
            with self.subTest(changed=changed):
                c=make_verified_bundle(self,mismatched_queue=changed)
                output=io.StringIO();errors=io.StringIO()
                with redirect_stdout(output),redirect_stderr(errors):
                    code=main(['preflight-product-upgrade','--config',str(c.config_path),
                        '--backup',str(c.backup)])
                self.assertEqual(2 if changed else 0,code)
                result=json.loads(output.getvalue())
                self.assertEqual('BLOCKED' if changed else 'COMPATIBLE_FOR_INHIBITED_CLONE',result['status'])
                self.assertEqual('NONE',result['financial_authority'])
                self.assertEqual(0,result['database_mutations'])
                self.assertEqual(0,result['owner_starts'])
                if changed:self.assertEqual(['UPGRADE_PREFLIGHT_SCHEMA_UNSUPPORTED'],result['reason_codes'])
                self.assertNotIn(str(c.fixture.base),output.getvalue()+errors.getvalue())
                self.assertEqual(c.source_hashes,source_database_hashes(c.config))
                self.assertEqual(c.backup_hashes,bundle_hashes(c.backup))
