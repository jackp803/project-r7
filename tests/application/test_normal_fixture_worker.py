"""Public independent FIXTURE worker with labeled clocks and actual journals."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from application.config import load_config
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.supervision import process_health
from storage.paper_process import open_paper_process_journal
from storage.runtime import open_paper_runtime_journal
from tests.application import test_normal_fixture_paper as normal
from tests.application import test_research_setup_flow as research_normal


class NormalFixtureWorkerTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='R7 public fixture worker 中文 ')
        self.root=Path(temporary.name)
        self.config_path=self.root/'config.json'
        self.data,self.cloud=self.root/'local data',self.root/'cloud simulation'
        self.profile=self.root/'operator selection.json'
        def cleanup():
            # Windows publication paths exceed MAX_PATH. Keep logical product
            # paths canonical and extend only the owned recursive cleanup path.
            target=self.root.resolve()
            base=Path(tempfile.gettempdir()).resolve()
            self.assertTrue(target!=base and target.is_relative_to(base))
            from application.platform.private_files import _filesystem_path
            temporary.name=str(_filesystem_path(target))
            temporary.cleanup()
        self.addCleanup(cleanup)
    call=normal.NormalFixturePaperTests.call
    initialize=normal.NormalFixturePaperTests.initialize
    generate=normal.NormalFixturePaperTests.generate
    prepare=normal.NormalFixturePaperTests.prepare
    configure=normal.NormalFixturePaperTests.configure
    app=normal.NormalFixturePaperTests.app
    flow=normal.NormalFixturePaperTests.flow
    configure_paper=normal.NormalFixturePaperTests.configure_paper

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
        self.assertEqual(result['observation_clock'],'SYNTHETIC_UTC_SECONDS')
        self.assertEqual(result['process_health_clock'],'ACTUAL_UTC')
        self.assertEqual(result['financial_authority'],'NONE')
        self.assertEqual(result['ticks'],ticks)
        self.assertEqual(result['status'],'STOPPED')
        self.assertEqual(result['run_failures'],{})
        self.assertEqual(result['provider_requests'],0)
        return result

    def test_ordinary_worker_rejected_before_owner_store_initialization(self):
        research_normal.ResearchSetupFlowTests.initialize(self)
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
            self.assertIsNotNone(position)
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
            self.assertEqual(after.state['runtime']['forward']['real_elapsed_ns'],0)
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

    def test_normal_completed_trade_stages_actual_reports_and_receipts(self):
        actual,lifecycle=self.flow('positive')
        self.assertEqual(lifecycle,'CANDIDATE')
        self.configure_paper()
        config=load_config(self.config_path)
        with self.authenticated(config) as (client,headers):
            run=self.start(client,headers)
            self.worker(5,'publication')
            view=client.get('/api/v1/paper/runs/'+run).json()['data']['payload']
            self.assertEqual(view['closed_trades_count'],1)
        self.call(['queue-research-feedback','--config',str(self.config_path),
            '--run-id',actual['owner_run_id'],'--namespace','FIXTURE'])
        from storage.paper_feedback import PaperFeedbackOutbox
        with open_paper_process_journal(config.database_path,require_existing=True) as process:
            generation=process.recover(run).process_generation
            pending=PaperFeedbackOutbox(process).pending(10)
        self.assertEqual(len(pending),1)
        operation,bundle,artifact=pending[0]
        report=json.loads(bundle.payloads['feedback.json'])
        self.assertEqual(report['observation']['closed_trades'],1)
        self.assertEqual(report['observation']['actual_elapsed_seconds'],0)
        self.assertEqual(report['assessment']['status'],'BLOCKED')
        self.assertEqual(report['live']['status'],'NOT_RUN')
        self.assertIsNone(report['performance'])
        self.assertEqual(report['financial_authority'],'NONE')
        result=self.call(['publish-fixture-outbox','--config',str(self.config_path),'--limit','10'])
        self.assertEqual(result['status'],'LOCAL_STAGED')
        self.assertGreaterEqual(result['local_staged'],3)
        self.assertEqual(result['cloud_acknowledged'],0)
        folder=self.cloud/bundle.logical_path
        self.assertEqual((folder/'feedback.json').read_bytes(),bundle.payloads['feedback.json'])
        self.assertEqual((folder/'report.html').read_bytes(),bundle.payloads['report.html'])
        receipt=json.loads((folder/'manifest.json').read_bytes())
        self.assertEqual(receipt['operation_id'],operation)
        self.assertEqual(receipt['artifact_hash'],artifact)
        manifests=list((self.cloud/'receipts').rglob('manifest.json'))
        self.assertGreaterEqual(len(manifests),1)
        self.call(['publish-fixture-outbox','--config',str(self.config_path),'--limit','10'])
        with open_paper_process_journal(config.database_path,require_existing=True) as process:
            self.assertEqual(process.recover(run).process_generation,generation)
            self.assertEqual(PaperFeedbackOutbox(process).publications()[0]['state'],'LOCAL_STAGED')
        self.assertEqual((folder/'manifest.json').read_bytes(),json.dumps(receipt,sort_keys=True,separators=(',',':')).encode())
