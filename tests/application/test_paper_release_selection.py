"""Explicit ordinary policies and canonical envelope, development fixtures only."""
from dataclasses import replace
import importlib
import importlib.util
import tempfile
from pathlib import Path
import unittest

from application.config import ProductConfig
from application.paper.owners import PaperOwnerSelection
from tests.application.test_product_assessment_binding import risk_fixture
from tests.product.test_paper_runtime_v02 import simulation_fixture
from tests.validation.test_paper_promotion_policy import policy_fixture


class PaperReleaseSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='r7-release-selection-')
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.config = ProductConfig('r7-product-config-v0.2','ordinary-policy-test',root,None,
            root/'canonical.sqlite3',diagnostic_only=False,paper_runtime_enabled=True)

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.release'),
            'Ordinary release adapter and selection envelope are missing')
        return importlib.import_module('application.paper.release')

    def owner(self, **changes):
        # Explicit test inputs, not installed defaults or ordinary acceptance.
        simulation = simulation_fixture(); simulation.update(namespace='LOCAL_RESEARCH',mode='REAL_TIME')
        risk = risk_fixture(); risk['namespace'] = 'LOCAL_RESEARCH'
        values = dict(namespace='LOCAL_RESEARCH',simulation_policy=simulation,risk_policy=risk,
            promotion_policy=policy_fixture('LOCAL_RESEARCH'),paper_policy_ref='explicit-test-policy',
            submission_validity={'intent_class':'EVERGREEN_STRATEGY','validity':{'from':None,'until':None}},
            actor='explicit-test-operator',workflow_authorized=True)
        values.update(changes)
        return PaperOwnerSelection(**values)

    def test_envelope_binds_complete_selection_simulator_and_account_separately_from_supervisor(self):
        m = self.module(); owner = self.owner()
        record = m.operational_record(self.config,owner,account_ref='explicit-local-test-account')
        envelope = record['envelope']
        from application.platform.supervision import config_hash
        from registry.product_assessment import canonical,digest
        self.assertEqual(envelope['product_config_hash'],config_hash(self.config))
        self.assertEqual(envelope['owner_selection_hash'],owner.selection_hash)
        self.assertNotEqual(digest(canonical(envelope)),config_hash(self.config))
        self.assertEqual(record['simulator_profile']['account_scope'],'ISOLATED_PER_STRATEGY_RUN')
        self.assertEqual(record['owner']['actor'],'explicit-test-operator')
        self.assertTrue(record['owner']['workflow_authorized'])

    def test_actor_workflow_risk_promotion_validity_and_account_changes_invalidate_config(self):
        m = self.module()
        baseline = m.operational_record(self.config,self.owner(),account_ref='account-one')['envelope']
        for changes in ({'actor':'another-test-operator'}, {'workflow_authorized':False},
                        {'paper_policy_ref':'another-policy'}):
            with self.subTest(changes=changes):
                changed = m.operational_record(self.config,self.owner(**changes),account_ref='account-one')
                self.assertNotEqual(changed['envelope'],baseline)
        changed = m.operational_record(self.config,self.owner(),account_ref='account-two')
        self.assertNotEqual(changed['envelope'],baseline)

    def test_fixture_missing_account_and_mutated_record_are_denied(self):
        m = self.module(); owner = self.owner()
        for account in (None,'',' ',1,'x'*257):
            with self.subTest(account_type=type(account).__name__),self.assertRaises(ValueError):
                m.operational_record(self.config,owner,account_ref=account)
        with self.assertRaises(ValueError):
            m.operational_record(replace(self.config,execution_mode='FIXTURE'),owner,account_ref='account')
        record = m.operational_record(self.config,owner,account_ref='account')
        record['owner']['actor'] = 'forged'
        with self.assertRaises(ValueError):
            m.validate_operational_record(self.config,record)

    def test_historical_body_retains_original_config_but_rejects_mutated_commitments(self):
        import copy
        m=self.module();owner=self.owner()
        record=m.operational_record(self.config,owner,account_ref='original-local-account')
        changed=replace(self.config,control_api_port=self.config.control_api_port+1)
        self.assertEqual(m._historical_owner(record).selection_hash,owner.selection_hash)
        with self.assertRaises(ValueError):m.validate_operational_record(changed,record)
        for section,key,value in (('owner','actor','forged'),('simulator_profile','provider_requests',1),
                ('envelope','schema_version','unsupported'),('envelope','product_config_hash','malformed'),
                ('envelope','account_ref','')):
            mutated=copy.deepcopy(record);mutated[section][key]=value
            with self.subTest(section=section,key=key),self.assertRaises(ValueError):m._historical_owner(mutated)


if __name__ == '__main__':
    unittest.main()
