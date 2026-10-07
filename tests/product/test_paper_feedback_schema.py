import copy,json,unittest
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker,ValidationError
from tests.product import test_paper_runtime_v02 as fixtures

class PaperFeedbackSchemaTests(unittest.TestCase):
    def setUp(self):
        folder=Path(__file__).resolve().parent
        path=(folder if folder.name=='S14-paper-feedback-development' else folder.parent.parent)/'contracts/paper_feedback_v0_2.schema.json'
        self.schema=json.loads(path.read_bytes());Draft202012Validator.check_schema(self.schema)
        self.validator=Draft202012Validator(self.schema,format_checker=FormatChecker())
        self.case=fixtures.PaperRuntimeV02Tests();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.runtime=self.case.start()
        from application.cloud.paper_feedback import build_paper_feedback
        self.builder=build_paper_feedback
    def test_actual_owner_empty_and_closed_opt_out_opt_in_reports_match_versioned_schema(self):
        self.validator.validate(self.builder(self.runtime))
        for event in (self.case.event(0,bars=True),self.case.event(1),self.case.event(2,'60020'),self.case.event(3,'60020')):
            self.case.clock[0]=event.snapshot.observed_at;self.runtime.on_market_event(event)
        self.validator.validate(self.builder(self.runtime));self.validator.validate(self.builder(self.runtime,performance_opt_in=True))
    def test_schema_refuses_private_fields_real_time_forgery_and_opt_out_performance(self):
        from application.cloud.paper_feedback import validate_paper_feedback
        value=self.builder(self.runtime);cases=[]
        private=copy.deepcopy(value);private['strategy']['provider_order_id']='SYNTHETIC_FORBIDDEN';cases.append(private)
        forged=copy.deepcopy(value);forged['observation']['actual_elapsed_seconds']=3600;cases.append(forged)
        optout=copy.deepcopy(value);optout['performance']={key:'1' for key in ('net_pnl_usdt','expectancy_usdt_per_trade','max_drawdown_usdt','profit_factor')};cases.append(optout)
        for tampered in cases:
            with self.subTest(keys=list(tampered)):
                with self.assertRaises(ValidationError):self.validator.validate(tampered)
                with self.assertRaises(ValueError):validate_paper_feedback(tampered)

if __name__=='__main__':unittest.main()
