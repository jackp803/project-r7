import importlib,unittest


def policy_fixture(namespace='FIXTURE'):
    return dict(schema_version='r7-paper-promotion-policy-v0.2',policy_id='FIXTURE_FORWARD_POLICY',namespace=namespace,generation=1,
        validation_policy_version='FIXTURE_FORWARD_THRESHOLDS_V1',min_elapsed_seconds=3600,min_closed_trades=2,
        min_net_pnl_usdt='0',min_expectancy_usdt_per_trade='0',max_drawdown_usdt='10',max_consecutive_losses=3,
        min_profit_factor='1',profit_factor_null_handling='ALLOW_NO_LOSSES',required_healthy_seconds=3600,
        maximum_observation_gap_seconds=30,units=dict(time='SECONDS',trade_count='CLOSED_TRADES',pnl='USDT_AMOUNT',
            expectancy='USDT_PER_CLOSED_TRADE',drawdown='USDT_AMOUNT'))


class PaperPromotionPolicyTests(unittest.TestCase):
    def test_public_deployment_risk_and_paper_schemas_are_strict(self):
        import json,jsonschema
        from pathlib import Path
        from tests.application.test_product_assessment_binding import risk_fixture
        contracts=Path(__file__).resolve().parents[2]/'contracts'
        for filename,value in (('paper_promotion_policy_v0_2',policy_fixture()),('selected_risk_policy_v0_2',risk_fixture())):
            path=contracts/(filename+'.schema.json')
            self.assertTrue(path.is_file(),'Missing selected policy schema '+filename)
            schema=json.loads(path.read_text()); jsonschema.Draft202012Validator.check_schema(schema)
            validator=jsonschema.Draft202012Validator(schema); validator.validate(value)
            forged=dict(value,decision='PASS'); self.assertTrue(list(validator.iter_errors(forged)))
        path=contracts/'deployment_envelope_v0_2.schema.json'
        self.assertTrue(path.is_file(),'Missing strict deployment envelope schema')
        jsonschema.Draft202012Validator.check_schema(json.loads(path.read_text()))
    def test_profile_reuses_e3_thresholds_and_rejects_unknown_units_or_defaults(self):
        try: api=importlib.import_module('validation.paper_policy')
        except ModuleNotFoundError: self.fail('Missing strict selected PAPER promotion policy')
        from validation.oos import ValidationPolicy
        selected=api.parse_paper_promotion_policy(policy_fixture(),namespace='FIXTURE')
        self.assertIsInstance(selected.validation_policy,ValidationPolicy)
        self.assertEqual(2,selected.validation_policy.min_total_trades)
        for kind in ('missing','unknown','unit','namespace','boolean','health'):
            value=policy_fixture()
            if kind=='missing': value.pop('min_elapsed_seconds')
            elif kind=='unknown': value['author_pass']=True
            elif kind=='unit': value['units']['drawdown']='PERCENT'
            elif kind=='namespace': value['namespace']='LOCAL_RESEARCH'
            elif kind=='boolean': value['min_closed_trades']=True
            else: value['required_healthy_seconds']=3601
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                api.parse_paper_promotion_policy(value,namespace='FIXTURE')

