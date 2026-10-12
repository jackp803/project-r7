"""Read-only observation of actual source public worker failure; no qualification."""
from pathlib import Path
import json,sys,unittest
repo=Path(__file__).resolve().parent.parent/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(repo),str(repo/'src')]
from tests.application.test_normal_fixture_worker import NormalFixtureWorkerTests
from application.config import load_config
from storage.paper_process import open_paper_process_journal
original=NormalFixtureWorkerTests.worker
def observed(self,ticks,label):
    result=original(self,ticks,label)
    config=load_config(self.config_path)
    with open_paper_process_journal(config.database_path,require_existing=True) as process:
        for run in process._db.execute('SELECT run_id FROM paper_process_runs').fetchall():
            state=process.recover(run['run_id']).state['runtime']
            print('ACTUAL_SYNTHETIC_RUNTIME_OBSERVATION',json.dumps({key:state[key] for key in
                ('market_status','last_signal','last_intent','risk_decision','entry_request','position','candles')}),flush=True)
    return result
NormalFixtureWorkerTests.worker=observed
suite=unittest.TestSuite([NormalFixtureWorkerTests('test_public_worker_stop_pause_restart_protects_and_closes_actual_trade')])
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
