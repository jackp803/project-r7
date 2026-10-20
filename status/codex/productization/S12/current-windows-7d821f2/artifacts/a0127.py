"""Actual external helper subprocess/denial parsing, not native product evidence."""
import json,sys,tempfile,unittest
from pathlib import Path
import verify_ordinary_idle_coordinator as helper
from application.platform.private_files import create_private_directory

class OrdinaryIdleHelperTests(unittest.TestCase):
    def test_runtime_idle_summary_rejects_requests_wrong_generation_or_missing_counters(self):
        value=dict(status='STOPPED',namespace='LOCAL_RESEARCH',mode='REAL_TIME',market_source='NOT_CONNECTED',
            provider_requests=0,provider_responses=0,request_accounting='COMPLETE',run_failures={},
            process_generation=3,financial_authority='NONE',capital='NONE')
        self.assertEqual(helper.require_idle_runtime_summary(json.dumps(value).encode(),3),value)
        for key,bad in (('provider_requests',1),('process_generation',2),('market_source','CONNECTED'),('provider_responses',None)):
            changed=dict(value);changed[key]=bad
            with self.subTest(field=key),self.assertRaises(ValueError):helper.require_idle_runtime_summary(json.dumps(changed).encode(),3)

    def view(self,root):
        report=dict(commands=[],sessions=[],scope='SOURCE_HELPER_ONLY_NOT_NATIVE_QUALIFICATION')
        return helper.make_idle_view(root,root/'unused-data',root/'unused-config.json',root/'unused-operations.json',
            root/'unused-installation',{},report,lambda:None)

    def test_actual_command_json_survives_redaction_without_enrolling_any_credential(self):
        with tempfile.TemporaryDirectory(dir=helper.BASE,prefix='idle-helper-unit-') as directory:
            root=Path(directory)/'case';create_private_directory(root);view=self.view(root)
            value=view.command('actual-owned-helper-json',[],argv=[sys.executable,'-X','utf8','-c',
                'import json; print(json.dumps({"status":"SOURCE_HELPER_ONLY"}))'])
            self.assertEqual(value,{'status':'SOURCE_HELPER_ONLY'})
            self.assertTrue(view.observation['commands'][0]['tree_reaped'])
            self.assertFalse((root/'unused-config.json').exists())

    def test_exit_two_from_another_startup_failure_is_not_a_duplicate_scope_pass(self):
        with tempfile.TemporaryDirectory(dir=helper.BASE,prefix='idle-helper-unit-') as directory:
            root=Path(directory)/'case';create_private_directory(root);view=self.view(root)
            for index,kind in enumerate(('INVALID_CONFIGURATION','OWNER_SCOPE_BUSY')):
                value=dict(schema_version='r7-startup-diagnostic-v0.2',error_kind=kind)
                view.command('denial-'+str(index),[],expected=2,argv=[sys.executable,'-X','utf8','-c',
                    'import json; print('+repr(json.dumps(value))+'); raise SystemExit(2)'])
                raw=(root/('denial-'+str(index)+'.log')).read_bytes()
                if kind=='OWNER_SCOPE_BUSY':self.assertEqual(helper.require_duplicate_denial(raw),value)
                else:
                    with self.assertRaises(ValueError):helper.require_duplicate_denial(raw)
                self.assertTrue(view.observation['commands'][-1]['tree_reaped'])

if __name__=='__main__':unittest.main(verbosity=2)
