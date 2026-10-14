"""Actual intake/selection/backup, with test-only clean source provenance.

These source regressions never issue native qualification or Paper results.
"""
from datetime import datetime,timezone
import json,unittest
from unittest.mock import patch

from application.config import load_config
from application.fixtures.recipe import prepare_fixture
from application.local_owners import LocalOwners
from application.platform import product_backup
from application.research.evidence import capture_provenance
from tests.application import test_fixture_recipe_flow as recipe


class FixtureSealedInputBackupTests(unittest.TestCase):
    setUp=recipe.FixtureRecipeFlowTests.setUp
    call=recipe.FixtureRecipeFlowTests.call
    initialize=recipe.FixtureRecipeFlowTests.initialize
    configure=recipe.FixtureRecipeFlowTests.configure

    def selected(self,**kwargs):
        config=self.initialize()
        generated=prepare_fixture(self.config_path,'positive',**kwargs)
        self.profile=self.data/generated['selection_profile_ref'];self.configure()
        owners=LocalOwners(config,namespace='FIXTURE')
        with owners.inbox_factory() as inbox:
            self.assertEqual(inbox.scan_once(datetime.now(timezone.utc)).accepted,1)
        facts=capture_provenance();facts['worktree']='CLEAN'
        with patch('application.paper.setup.capture_provenance',return_value=facts):
            self.call(['configure-paper','--config',str(self.config_path),
                '--selection-profile',str(self.data/'fixture-inputs/paper-selection.json')])
        return load_config(self.config_path)

    def backup_restore(self,config,reference):
        backup=self.root/'sealed-input-backup';target=self.root/'sealed-input-restore'
        original=(self.data/reference).read_bytes()
        result=product_backup.create_product_backup(config,backup)
        self.assertEqual(result['status'],'PRODUCT_DATA_BACKUP_VERIFIED')
        manifest=json.loads((backup/'manifest.json').read_bytes())
        self.assertIn(reference,{row['relative_path'] for row in manifest['files']})
        product_backup.verify_product_backup(config,backup)
        product_backup.restore_product_backup(config,backup,target)
        restored=load_config(target/'restored-product.json')
        self.assertEqual((restored.local_data_root/reference).read_bytes(),original)
        self.assertIsNone(restored.cloud_root);self.assertTrue(restored.diagnostic_only)
        self.assertFalse(restored.paper_runtime_enabled)
        for label,raw in (('changed',original+b' '),('missing',None)):
            path=self.data/reference
            if raw is None:path.unlink()
            else:path.write_bytes(raw)
            destination=self.root/(label+'-input-backup')
            with self.subTest(label=label),self.assertRaises(product_backup.ProductBackupError):
                product_backup.create_product_backup(config,destination)
            self.assertFalse(destination.exists());path.write_bytes(original)

    def test_sealed_partial_case_preserved_and_unbound_auxiliary_denied(self):
        config=self.selected(paper_case='partial-fill-hold')
        self.backup_restore(config,'fixture-inputs/paper-case.json')
        (self.data/'fixture-inputs/temporal.json').write_bytes(b'{}')
        destination=self.root/'unsealed-temporal-backup'
        with self.assertRaises(product_backup.ProductBackupError):
            product_backup.create_product_backup(config,destination)
        self.assertFalse(destination.exists())

    def test_sealed_temporal_case_preserved_with_original_validity(self):
        config=self.selected(temporal_case='paper-expire-after-protection')
        self.backup_restore(config,'fixture-inputs/temporal.json')


if __name__=='__main__':unittest.main()
