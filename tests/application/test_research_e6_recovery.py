from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from application.research.service import ResearchService
from application.research.evidence import now_utc
from tests.application.test_research_pipeline import configured
from tests.backtest.test_v02_owner_binding import strategy

class ResearchE6RecoveryTests(unittest.TestCase):
    def test_crash_after_e6_evidence_save_before_job_receipt_recovers_same_upstream_record(self):
        with TemporaryDirectory() as root:
            configured(root)
            with ResearchService(local_root=root,database_path=Path(root)/'jobs.sqlite',registry_path=Path(root)/'registry.sqlite',namespace='FIXTURE',owner_id='fixture-owner') as service:
                def execute(): return service.run(submission_id='fixture-crash',definition=strategy(),dataset_ref='dataset.json',split_policy_ref='split.json',cost_policy_ref='cost.json')
                import sqlite3
                from contextlib import closing
                before=[]
                def actual_evidence_rows():
                    uri=(Path(root)/'registry.sqlite').resolve().as_uri()+'?mode=ro'
                    with closing(sqlite3.connect(uri,uri=True)) as db:
                        db.execute('PRAGMA query_only=ON')
                        definition=strategy()
                        return db.execute('SELECT * FROM validation_evidence WHERE evidence_type=? AND strategy_id=? AND strategy_version=? ORDER BY evidence_id',
                            ('BACKTEST_RESULT',definition['strategy_id'],definition['strategy_version'])).fetchall()
                original=service.journal.finish
                def crash(claim,*args,**kwargs):
                    if claim.stage=='e6_backtest_persistence':
                        before.extend(actual_evidence_rows())
                        self.assertEqual(len(before),1)
                        raise RuntimeError('fixture crash after E6 save')
                    return original(claim,*args,**kwargs)
                with patch.object(service.journal,'finish',crash):
                    with self.assertRaises(RuntimeError): execute()
                run_id=service.journal.runs()[0]['run_id']
                self.assertEqual('RUNNING',service.journal.attempts(run_id)[-1]['status'])
                future=now_utc()+timedelta(minutes=6)
                # Fixture job clock expiry; does not supply forward-trading evidence.
                with patch('application.research.orchestrator.now_utc',return_value=future):
                    result=execute()
                report=service.report(result.run_id)
                attempts=[a for a in report['attempts'] if a['stage']=='e6_backtest_persistence']
                self.assertEqual(['ABORTED','COMPLETE'],[a['status'] for a in attempts])
                self.assertEqual(report['backtest_e6_evidence_id'],before[0][0])
                self.assertEqual(actual_evidence_rows(),before)
                self.assertEqual('BACKTESTING',result.strategy_lifecycle)
