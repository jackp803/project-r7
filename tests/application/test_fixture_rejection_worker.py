"""Public independent source owner must recover actual E5 failed protection."""
from decimal import Decimal
import json,unittest
from application.config import load_config
from brokers.paper import PaperBroker
from brokers.paper_state import decode_fact
from execution.models import OrderRequest,OrderStatus
from storage.paper_process import open_paper_process_journal
from storage.runtime import open_paper_runtime_journal
from tests.application import test_normal_fixture_worker as normal


class FixtureRejectionWorkerTests(unittest.TestCase):
    setUp=normal.NormalFixtureWorkerTests.setUp
    call=normal.NormalFixtureWorkerTests.call
    initialize=normal.NormalFixtureWorkerTests.initialize
    prepare=normal.NormalFixtureWorkerTests.prepare
    configure=normal.NormalFixtureWorkerTests.configure
    app=normal.NormalFixtureWorkerTests.app
    flow=normal.NormalFixtureWorkerTests.flow
    configure_paper=normal.NormalFixtureWorkerTests.configure_paper
    authenticated=normal.NormalFixtureWorkerTests.authenticated
    start=normal.NormalFixtureWorkerTests.start
    worker=normal.NormalFixtureWorkerTests.worker

    def generate(self,scenario='positive'):
        return self.call(['prepare-fixture','--config',str(self.config_path),'--scenario',scenario,
            '--paper-case','protection-rejected-hold'])

    def test_actual_rejected_protection_has_nonzero_emergency_and_successor_exits_original_position(self):
        self.assertEqual(self.flow('positive')[1],'CANDIDATE');self.configure_paper();config=load_config(self.config_path)
        with self.authenticated(config) as (client,headers):
            run=self.start(client,headers);first=self.worker(2,'rejected-protection')
            with open_paper_process_journal(config.database_path,require_existing=True) as journal:before=journal.recover(run)
            runtime=before.state['runtime'];position=runtime['position']
            self.assertEqual(position['lifecycle_state'],'EMERGENCY');self.assertGreater(Decimal(position['actual_quantity']),0)
            broker=PaperBroker.from_state(before.state['broker']);request=decode_fact(OrderRequest,runtime['protection_request'])
            self.assertEqual(broker.query_order(request.client_order_id).order_status,OrderStatus.REJECTED)
            second=self.worker(4,'rejected-successor')
            with open_paper_process_journal(config.database_path,require_existing=True) as journal:after=journal.recover(run)
            self.assertEqual(second['process_generation'],first['process_generation']+1)
            self.assertEqual(after.binding,before.binding);self.assertEqual(after.state['runtime']['exit_anchor'],runtime['exit_anchor'])
            closed=after.state['runtime']['position'];self.assertEqual(closed['position_id'],position['position_id'])
            self.assertEqual(closed['lifecycle_state'],'CLOSED');self.assertEqual(Decimal(closed['actual_quantity']),0)
            with open_paper_runtime_journal(config.database_path,require_existing=True) as journal:graph=journal.recover(position_id=position['position_id'])
            self.assertEqual(graph.status,'READY');self.assertEqual(len(graph.fills),2)
            self.assertEqual(len(after.state['runtime']['closed_trades']),1)


if __name__=='__main__':unittest.main()
