import importlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from application.cloud.manifest import canonical_bytes
from application.research.service import ResearchService
from tests.application.test_research_robustness import selected
from tests.application.test_research_pipeline import configured
from tests.validation.robustness_fixtures import subject


class FeedbackTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.cloud.feedback'))
        return importlib.import_module('application.cloud.feedback')

    def execute(self,root,service,*,full):
        options=dict(research_policy_ref='research.json',robustness_policy_ref='robustness.json',family_id='fixture-family',seed=42) if full else {}
        return service.run(submission_id='fixture-submission',definition=subject(),dataset_ref='dataset.json',split_policy_ref='split.json',cost_policy_ref='cost.json',**options)

    def service(self,root):
        return ResearchService(local_root=root,database_path=Path(root)/'research.sqlite',registry_path=Path(root)/'registry.sqlite',namespace='FIXTURE',owner_id='owner-feedback')

    def test_actual_owner_feedback_defaults_to_no_financial_metrics_and_missing_stages_not_run(self):
        module=self.module()
        with TemporaryDirectory() as root:
            configured(root)
            with self.service(root) as service:
                run=self.execute(root,service,full=False)
                feedback=module.build_research_feedback(service,run.run_id)
                raw=canonical_bytes(feedback).decode()
                self.assertEqual(feedback['schema_version'],'r7-chat-feedback-v0.2')
                self.assertEqual(feedback['performance_policy'],'OPT_OUT')
                self.assertIsNone(feedback['development']['performance'])
                self.assertEqual(feedback['sealed_oos']['status'],'NOT_RUN')
                self.assertEqual(feedback['paper']['status'],'NOT_RUN');self.assertIsNone(feedback['paper']['observation_seconds'])
                self.assertEqual(feedback['live']['status'],'NOT_RUN');self.assertIsNone(feedback['live']['performance'])
                self.assertNotIn('net_pnl',raw);self.assertNotIn(str(root),raw)
                from html.parser import HTMLParser
                class Summary(HTMLParser):
                    def __init__(self):super().__init__();self.rows=[];self.cells=None;self.cell=None
                    def handle_starttag(self,tag,attrs):
                        if tag=='tr':self.cells=[]
                        if tag in ('td','th'):self.cell=[]
                    def handle_data(self,data):
                        if self.cell is not None:self.cell.append(data)
                    def handle_endtag(self,tag):
                        if tag in ('td','th') and self.cell is not None:self.cells.append(''.join(self.cell));self.cell=None
                        if tag=='tr':self.rows.append(self.cells);self.cells=None
                summary=Summary();summary.feed(module.render_feedback(feedback).decode())
                self.assertEqual(len(summary.rows),7,'A compact stage table precedes the full JSON detail')
                self.assertEqual(summary.rows[-2],['PAPER','NOT_RUN','—','—'])
                self.assertEqual(summary.rows[-1],['LIVE','NOT_RUN','—','—'])
                self.assertEqual(summary.rows[2][1],feedback['development']['status'])
                self.assertEqual(summary.rows[2][2],str(feedback['development']['sample_count']))
                self.assertEqual(service.ledger.holdout_observations(),[])
                from jsonschema import Draft202012Validator,ValidationError
                schema=json.loads((Path(__file__).resolve().parents[2]/'contracts/chat_feedback_v0_2.schema.json').read_bytes())
                validator=Draft202012Validator(schema);validator.validate(feedback)
                with self.assertRaises(ValidationError):validator.validate({**feedback,'provider_account_id':'SYNTHETIC_FORBIDDEN'})

    def test_actual_oos_feedback_marks_chat_observation_idempotently_and_opt_in_metrics_are_exact_strings(self):
        module=self.module()
        with TemporaryDirectory() as root:
            selected(root)
            with self.service(root) as service:
                run=self.execute(root,service,full=True)
                default=module.build_research_feedback(service,run.run_id)
                self.assertEqual(default['sealed_oos']['status'],'PASS')
                self.assertIsNone(default['sealed_oos']['performance'])
                self.assertTrue(default['holdout_observed'])
                self.assertEqual(len([v for v in service.ledger.holdout_observations() if v['kind']=='CHAT_OBSERVATION']),1)
                again=module.build_research_feedback(service,run.run_id);self.assertEqual(again,default)
                self.assertEqual(len([v for v in service.ledger.holdout_observations() if v['kind']=='CHAT_OBSERVATION']),1)
                opt_in=module.build_research_feedback(service,run.run_id,performance_opt_in=True)
                actual=service.report(run.run_id)['product_assessment']['sealed_backtest']
                self.assertEqual(opt_in['sealed_oos']['performance']['net_pnl'],actual['net_pnl'])
                self.assertIsInstance(opt_in['sealed_oos']['performance']['net_pnl'],str)
                bundle=module.feedback_bundle(opt_in)
                self.assertEqual(set(bundle.payloads),{'feedback.json','report.html'})
                html=bundle.payloads['report.html'].decode()
                self.assertNotIn('<script',html.lower());self.assertNotIn('https://',html);self.assertNotIn(str(root),html)

    def test_adversarial_private_owner_fields_are_omitted_and_freeform_report_input_is_rejected(self):
        module=self.module()
        with TemporaryDirectory() as root:
            configured(root)
            with self.service(root) as service:
                run=self.execute(root,service,full=False)
                original=service.report
                def contaminated(run_id):
                    report=original(run_id)
                    report.update(provider_account_id='SYNTHETIC_PROVIDER_PRIVATE',local_path=str(root),
                        raw_response={'api_secret':'SYNTHETIC_SECRET'},account_balance='999999.123')
                    report['backtest']['provider_order_id']='SYNTHETIC_ORDER_PRIVATE'
                    return report
                from unittest.mock import patch
                with patch.object(service,'report',contaminated):feedback=module.build_research_feedback(service,run.run_id,performance_opt_in=True)
                raw=canonical_bytes(feedback).decode()
                for forbidden in ('SYNTHETIC_PROVIDER_PRIVATE','SYNTHETIC_SECRET','SYNTHETIC_ORDER_PRIVATE',str(root),'999999.123'):
                    self.assertNotIn(forbidden,raw)
                with self.assertRaises(module.FeedbackError):module.build_research_feedback({'status':'PASS'},run.run_id)
                with self.assertRaises(module.FeedbackError):module.build_research_feedback(service,run.run_id,performance_opt_in='yes')

    def test_queue_cli_records_owner_result_without_cloud_connection_or_performance_opt_in(self):
        from application.cli import main
        from contextlib import redirect_stdout
        from io import StringIO
        with TemporaryDirectory() as temporary:
            root=Path(temporary);configured(root)
            with self.service(root) as service:
                run=self.execute(root,service,full=False)
            config=root/'product.json';config.write_bytes(canonical_bytes(dict(schema_version='r7-product-config-v0.2',product_instance_id='feedback-fixture',
                local_data_root=str(root),cloud_root=None,database_path=str(root/'registry.sqlite'))))
            output=StringIO()
            with redirect_stdout(output):
                code=main(['queue-research-feedback','--config',str(config),'--run-id',run.run_id,'--namespace','FIXTURE'])
            self.assertEqual(code,0);self.assertEqual(json.loads(output.getvalue())['status'],'FEEDBACK_QUEUED')
            with self.service(root) as service:
                pending=service.journal.pending_feedback_publications(10)
                self.assertEqual(len(pending),1)
                self.assertEqual(json.loads(pending[0][1].payloads['feedback.json'])['performance_policy'],'OPT_OUT')


if __name__=='__main__':unittest.main()
