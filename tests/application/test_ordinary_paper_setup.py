"""Normal entrypoints require explicit local selection and qualified native bytes."""
from contextlib import redirect_stdout
import importlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

from application import cli
from application.config import load_config
from application.entrypoints import initialize_profile


class OrdinaryPaperSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='r7-ordinary-setup-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.config_path=self.root/'product.json';self.data=self.root/'data'

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.ordinary_setup'))
        return importlib.import_module('application.paper.ordinary_setup')

    def test_normal_profile_explicit_runtime_flag_configures_no_workflow_and_starts_nothing(self):
        import inspect
        self.assertIn('paper_runtime_enabled',inspect.signature(initialize_profile).parameters)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['init-profile','--config',str(self.config_path),'--data-root',str(self.data),
                '--instance-id','ordinary-setup-test','--enable-paper-runtime']),0)
        config=load_config(self.config_path)
        self.assertTrue(config.paper_runtime_enabled);self.assertFalse(config.diagnostic_only)
        self.assertFalse(self.data.exists())

    def test_source_configure_paper_denies_without_creating_store_or_inventing_mapping_wait(self):
        m=self.module()
        initialize_profile(self.config_path,self.data,instance_id='ordinary-no-grant-test')
        config=load_config(self.config_path)
        profile=dict(schema_version='r7-local-paper-inputs-v0.2',submission_id='explicit-submission',
            simulation_policy_ref='inputs/simulation.json',risk_policy_ref='inputs/risk.json',
            promotion_policy_ref='inputs/promotion.json',paper_policy_ref='explicit-paper-policy',
            actor='explicit-local-operator',workflow_authorized=False,account_ref='explicit-local-account',
            qualification_receipt_ref='qualification-'+'a'*64)
        selected=self.root/'paper-input.json';selected.write_text(json.dumps(profile),encoding='utf-8')
        self.assertEqual(m.read_operator_profile(config,selected),profile)
        from application.paper.setup import configure_paper
        with self.assertRaises(ValueError):configure_paper(self.config_path,selected)
        self.assertFalse(self.data.exists())
        for key in ('passed','release_generation','runtime_generation','qualified_release'):
            selected.write_text(json.dumps({**profile,key:True}),encoding='utf-8')
            with self.subTest(key=key),self.assertRaises(ValueError):m.read_operator_profile(config,selected)


if __name__=='__main__':unittest.main()
