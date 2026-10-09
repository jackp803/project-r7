"""Public independent FIXTURE worker with real UTC and actual owning journals."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from application.config import load_config
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.supervision import process_health
from storage.paper_process import open_paper_process_journal
from storage.runtime import open_paper_runtime_journal
from tests.application.test_normal_fixture_paper import NormalFixturePaperTests as normal
from tests.application.test_research_setup_flow import ResearchSetupFlowTests


class NormalFixtureWorkerTests(unittest.TestCase):
    setUp=normal.setUp
    call=normal.call
    initialize=normal.initialize
    generate=normal.generate
    prepare=normal.prepare
    configure=normal.configure
    app=normal.app
    flow=normal.flow
    configure_paper=normal.configure_paper

    @contextmanager
    def authenticated(self,config):
        from fastapi.testclient import TestClient
        with TestClient(self.app(config),base_url='http://127.0.0.1:8765',client=('127.0.0.1',42000)) as client:
            login=client.post('/api/v1/auth/login',json=dict(username='fixture-owner',
                password='synthetic-source-recipe-password-2026',command_id='worker-login',expected_revision=0),
                headers={'Origin':'http://127.0.0.1:8765'})
            self.assertEqual(login.status_code,200,login.text)
            yield client,{'Origin':'http://127.0.0.1:8765','x-r7-csrf':login.json()['csrf_token']}

    def start(self,client,headers):
        strategy=client.get('/api/v1/strategies').json()['data']['items'][0]
        paper=[row for row in client.get('/api/v1/policies').json()['data']['items'] if row['kind']=='PAPER'][0]
        response=client.post('/api/v1/paper/runs',json=dict(command_id='public-worker-start',
            expected_revision=strategy['registry_revision'],strategy_id=strategy['identity']['strategy_id'],
            strategy_version=strategy['identity']['strategy_version'],policy_id=paper['policy_id']),headers=headers)
        self.assertEqual(response.status_code,200,response.text)
        return response.json()['effect_ref'].removeprefix('paper:')

    def worker(self,ticks,label):
        repo=Path(__file__).resolve().parents[2]
        environment=os.environ.copy()
        environment.update(PYTHONPATH=str(repo/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
        log=self.root/('worker-'+label+'.log')
        handle=None
        with log.open('xb') as output:
            try:
                handle=spawn_owned([sys.executable,'-m','application','paper-worker','--config',
                    str(self.config_path),'--maximum-ticks',str(ticks)],cwd=repo,
                    limits=ResourceLimits(60),env=environment,stdout=output,stderr=subprocess.STDOUT)
                self.assertNotEqual(handle.process.pid,os.getpid())
                code=handle.wait()
            finally:
                self.assertTrue(handle is not None and terminate_owned(handle,deadline_seconds=5).reaped)
        text=log.read_text(encoding='utf-8')
        self.assertEqual(code,0,text)
        result=json.loads(text)
        self.assertEqual(result['namespace'],'FIXTURE')
        self.assertEqual(result['market_source'],'SYNTHETIC_FIXTURE')
        self.assertEqual(result['financial_authority'],'NONE')
        self.assertEqual(result['ticks'],ticks)
        self.assertEqual(result['status'],'STOPPED')
        self.assertEqual(result['run_failures'],{})
        self.assertEqual(result['provider_requests'],0)
        return result

    def test_ordinary_worker_rejected_before_owner_store_initialization(self):
        ResearchSetupFlowTests.initialize(self)
        with self.assertRaises(ValueError):
            self.call(['paper-worker','--config',str(self.config_path),'--maximum-ticks','2'])
        self.assertFalse(self.data.exists())

    def test_invalid_tick_bound_rejected_before_composition(self):
        self.initialize()
        for ticks in ('0','10001'):
            with self.subTest(ticks=ticks),self.assertRaises(ValueError):
                self.call(['paper-worker','--config',str(self.config_path),'--maximum-ticks',ticks])
        self.assertFalse(self.data.exists())

    def test_public_worker_stop_pause_restart_protects_and_closes_actual_trade(self):
        self.assertEqual(self.flow('positive')[1],'CANDIDATE')
        self.configure_paper()
        config=load_config(self.config_path)
        with self.authenticated(config) as (client,headers):
            run=self.start(client,headers)
            first=self.worker(2,'first')
            self.assertEqual(process_health(config,'runtime')['status'],'STOPPED')
            with open_paper_process_journal(config.database_path,require_existing=True) as journal:
                before=journal.recover(run)
            position=before.state['runtime']['position']
            self.assertEqual(position['lifecycle_state'],'OPEN_PROTECTED')
            self.assertEqual(before.process_generation,1)
            view=client.get('/api/v1/paper/runs/'+run).json()['data']
            self.assertEqual(view['payload']['position'],position)
            self.assertEqual(view['payload']['closed_trades_count'],0)
            pause=client.post('/api/v1/paper/runs/'+run+'/pause',json=dict(command_id='public-worker-pause',
                expected_revision=view['revision']),headers=headers)
            self.assertEqual(pause.status_code,200,pause.text)
            second=self.worker(4,'restarted')
            self.assertEqual(second['process_generation'],first['process_generation']+1)
            with open_paper_process_journal(config.database_path,require_existing=True) as journal:
                after=journal.recover(run)
            self.assertEqual(after.process_generation,2)
            closed=after.state['runtime']['position']
            self.assertEqual(closed['position_id'],position['position_id'])
            self.assertEqual(closed['opened_at'],position['opened_at'])
            self.assertEqual(closed['lifecycle_state'],'CLOSED')
            self.assertFalse(after.state['runtime']['paper_entries_allowed'])
            self.assertEqual(len(after.state['runtime']['closed_trades']),1)
            self.assertEqual(after.binding,before.binding)
            with open_paper_runtime_journal(config.database_path,require_existing=True) as canonical:
                graph=canonical.recover(position_id=position['position_id'])
            self.assertEqual(graph.status,'READY')
            self.assertEqual(len(graph.fills),2)
            self.assertEqual(graph.trade_result.payload,after.state['runtime']['closed_trades'][0])
            final=client.get('/api/v1/paper/runs/'+run).json()['data']['payload']
            self.assertEqual(final['closed_trades_count'],1)
            self.assertEqual(final['entry_admission'],'PAUSED')
            self.assertEqual(final['position'],closed)
            self.assertEqual(final['namespace'],'FIXTURE')
            self.assertEqual(final['mode'],'ACCELERATED_FIXTURE')
