"""Actual worker/CLI commitment propagation; no research job or trading start."""
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
import io, unittest
from application.config import ProductConfig
from application.platform.supervision import config_hash
from application.research import worker

class ServiceResearchBindingTests(unittest.TestCase):
    def setUp(self):
        project=Path(__file__).resolve().parents[4]
        self.config=ProductConfig('r7-product-config-v0.2','binding-unit',project/'artifacts/unit-unused-data',None,project/'artifacts/unit-unused-data/canonical.sqlite')
        self.digest=config_hash(self.config);self.path=project/'artifacts/unit-unused-settings/product.json'
    def test_actual_native_child_argv_carries_expected_configuration_commitment(self):
        with patch('sys.frozen',True,create=True):
            argv=worker._job_argv(self.path,'job-1',1,expected_config_hash=self.digest)
        self.assertEqual(argv[-2:],['--expected-config-hash',self.digest])
    def test_changed_child_configuration_is_refused_before_any_local_owner(self):
        with patch.object(worker,'load_config',return_value=self.config),patch.object(worker,'LocalOwners') as owners,self.assertRaises(ValueError):
            worker.run_research_job(self.path,'job-1',1,expected_config_hash='sha256:'+'f'*64)
        owners.assert_not_called()
    def test_internal_cli_preserves_child_commitment_at_actual_worker_boundary(self):
        from application import cli
        with patch.object(worker,'run_research_job',return_value={'status':'BLOCKED'}) as run,redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['_research-job','--config',str(self.path),'--run-id','job-1','--generation','1',
                '--expected-config-hash',self.digest]),0)
        run.assert_called_once_with(self.path,'job-1',1,expected_config_hash=self.digest)

if __name__=='__main__':unittest.main()
