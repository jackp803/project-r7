"""Current-fact projection and source denial; no native executable qualification claim."""
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
import importlib
import json
import unittest

from application.platform.supervision import config_hash
from registry import EvidenceGateError
from registry.product_assessment import canonical,digest
from storage.paper_selection import OperationalSelection
from strategy.v02.capabilities import _revision,build_capability_snapshot
from tests.application.test_paper_release_selection import PaperReleaseSelectionTests


class NativePaperReleaseAdapterTests(PaperReleaseSelectionTests):
    def prepare(self):
        m=importlib.import_module('application.paper.release')
        self.assertTrue(hasattr(m,'_binding_from_current_facts'),
            'Ordinary release must derive runtime generation from actual independent runtime identity')
        record=m.operational_record(self.config,self.owner(),account_ref='explicit-local-unit-account')
        selection=OperationalSelection(3,digest(canonical(record['envelope'])),canonical(record))
        measured=dict(implementation_hash=_revision(),executable_revision='a'*40,
            build_hash='sha256:'+'7'*64,distribution_profile='r7-native-distribution-v0.2')
        identity=dict(measured,role='runtime',generation=7,config_hash=config_hash(self.config),
            product_instance_id=self.config.product_instance_id,pid=1)
        return m,selection,measured,identity

    def test_projection_uses_distinct_durable_config_and_actual_runtime_generation(self):
        m,selection,measured,identity=self.prepare()
        release=m._binding_from_current_facts(self.config,selection,measured,identity)
        self.assertEqual(release.release_kind,'NATIVE_QUALIFIED')
        self.assertEqual(release.namespace,'LOCAL_RESEARCH')
        self.assertEqual(release.config_generation,3)
        self.assertEqual(release.runtime_generation,7)
        self.assertEqual(release.risk_generation,1)
        self.assertEqual(release.account_ref,'explicit-local-unit-account')
        self.assertNotEqual(release.config_hash,identity['config_hash'])
        self.assertEqual(release.capability_hash,build_capability_snapshot().snapshot_hash)

    def test_wrong_source_build_role_config_or_generation_denies_without_defaults(self):
        m,selection,measured,identity=self.prepare()
        for changes in ({'implementation_hash':'sha256:'+'8'*64},{'executable_revision':'b'*40},
                {'build_hash':'sha256:'+'8'*64},{'role':'control'},{'config_hash':'sha256:'+'8'*64},
                {'generation':0},{'generation':True},{'generation':2147483648},
                {'product_instance_id':'foreign-instance'}):
            with self.subTest(changes=changes),self.assertRaises((ValueError,EvidenceGateError)):
                m._binding_from_current_facts(self.config,selection,measured,{**identity,**changes})

    def test_source_currentness_read_never_creates_store_or_bootstraps_runtime(self):
        m=importlib.import_module('application.paper.release')
        self.assertTrue(hasattr(m,'NativePaperReleaseReader'))
        reader=m.NativePaperReleaseReader(self.config,receipt_ref='qualification-'+'a'*64)
        with self.assertRaises(ValueError):reader.current()
        self.assertFalse(self.config.database_path.exists())
        self.assertFalse((self.config.local_data_root/'process-supervision.sqlite').exists())


if __name__=='__main__':unittest.main()
