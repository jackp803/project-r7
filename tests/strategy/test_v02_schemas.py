import copy
import json
from pathlib import Path
import unittest
from jsonschema import Draft202012Validator
from tests.strategy.v02_fixtures import definition_v02
from application.cloud.manifest import canonical_bytes,parse_manifest


class SchemaTests(unittest.TestCase):
    def validator(self,name):
        path=Path(__file__).resolve().parents[2]/'contracts'/name
        self.assertTrue(path.is_file(),'Authoring schema missing')
        value=json.loads(path.read_text(encoding='utf-8'))
        Draft202012Validator.check_schema(value)
        return Draft202012Validator(value)

    def test_strategy_schema_accepts_example_and_rejects_mixed_forms(self):
        validator=self.validator('strategy_dsl_v0_2.schema.json')
        value=definition_v02()
        self.assertEqual([],list(validator.iter_errors(value)))
        invalid=copy.deepcopy(value)
        invalid['rules']['features']['trend']['timeframe']='4h'
        self.assertTrue(list(validator.iter_errors(invalid)))
        invalid=copy.deepcopy(value)
        invalid['rules']['exit_policy']['stop']['value']=10.5
        self.assertTrue(list(validator.iter_errors(invalid)))

    def test_package_schema_matches_strict_manifest_shape_without_conferring_authority(self):
        validator=self.validator('strategy_package_v0_2.schema.json')
        value={'package_schema_version':'r7-strategy-package-v0.2',
               'submission_id':'example-1','strategy_id':'fixture-v02-trend','strategy_version':'0.2.0',
               'strategy_content_hash':'sha256:'+'1'*64,'created_at':'2026-10-02T00:00:00Z',
               'created_by':'offline authoring fixture','research_hypothesis':'test schema only',
               'requested_dataset_profile':'fixture','requested_validation_profile':'fixture',
               'requested_robustness_profile':'fixture',
               'required_runtime_profile':{'runtime_family':'project-r7-e2-strategy-runtime','runtime_version':'0.2.0'},
               'capability_snapshot_hash':'sha256:'+'2'*64,
               'payloads':[{'role':'strategy_definition','relative_path':'strategy.json','media_type':'application/json',
                            'byte_length':100,'sha256':'sha256:'+'3'*64}],
               'intent_class':'EVERGREEN_STRATEGY','validity':{'from':None,'until':None}}
        self.assertEqual([],list(validator.iter_errors(value)))
        self.assertEqual('example-1',parse_manifest(canonical_bytes(value)).submission_id)
        value['activate']=True
        self.assertTrue(list(validator.iter_errors(value)))
        del value['activate']
        value['intent_class']='TACTICAL_STRATEGY'
        self.assertTrue(list(validator.iter_errors(value)))

