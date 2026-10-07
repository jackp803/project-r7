"""Controlled installer backend mechanics; no actual Linux/systemd execution."""
from dataclasses import asdict
import copy,importlib,json,unittest
from unittest.mock import patch
from application.platform.service_plan import ServiceSettings

class FakeBackend:
    def __init__(self):
        self.files={};self.operations=[];self.fail_write=None;self.reload_ok=True
        self.unit_state={name:dict(LoadState='not-found',ActiveState='inactive',SubState='dead',UnitFileState='',FragmentPath='',DropInPaths='',Job='0')
            for name in ('r7-control.service','r7-research.service')}
        self.parents_generation=1
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def parent_facts(self):return dict(generation=self.parents_generation)
    def snapshot(self,path):
        raw=self.files.get(path)
        return dict(exists=raw is not None,sha256=None if raw is None else 'sha256:'+__import__('hashlib').sha256(raw).hexdigest()),raw
    def manager_state(self,name):return copy.deepcopy(self.unit_state[name])
    def has_dropin(self,name):return False
    def write_new(self,path,raw,mode):
        if path==self.fail_write:raise OSError('controlled write failure')
        if path in self.files:raise FileExistsError('Exclusive target required')
        self.files[path]=raw;self.operations.append(('write',path,mode))
    def remove_exact(self,path,expected):
        state,_=self.snapshot(path)
        if state!=expected:raise ValueError('Target changed')
        del self.files[path];self.operations.append(('remove',path))
    def reload(self):self.operations.append(('reload',));return self.reload_ok

class ServiceAdminTests(unittest.TestCase):
    def setUp(self):
        self.module=importlib.import_module('application.platform.service_admin')
        self.subject=ServiceSettings('/opt/r7/release','/etc/r7/settings/product.json','/var/lib/r7-data',None,'r7-worker',
            'a'*40,'sha256:'+'b'*64,'sha256:'+'c'*64,24*1024**3)
        self.backend=FakeBackend()
        self.patcher=patch.object(self.module,'verify_service_subject',return_value=self.subject)
        self.verify=self.patcher.start();self.addCleanup(self.patcher.stop)
    def call(self,action='install',**options):
        return self.module.manage_services(self.subject.config_path,action=action,_backend=self.backend,**options)
    def install(self):
        plan=self.call();return self.call(apply=True,operation_hash=plan['operation_hash'])

    def test_default_dry_run_has_no_files_or_manager_mutation(self):
        plan=self.call();self.assertEqual(plan['status'],'DRY_RUN');self.assertEqual(self.backend.operations,[])
        self.assertEqual(self.backend.files,{})
        self.assertEqual(plan['service_start'],'NOT_PERFORMED');self.assertEqual(plan['financial_authority'],'NONE')
        self.verify.assert_called_once()
    def test_missing_default_native_parent_is_structured_prerequisite_without_mutation(self):
        with patch.object(self.module,'LinuxServiceBackend',side_effect=self.module.ServiceAdminPrerequisiteError()):
            result=self.module.manage_services(self.subject.config_path,action='install')
        self.assertEqual(result['status'],'PREREQUISITE_REQUIRED');self.assertFalse(result['applied'])
        self.assertEqual(result['required_directory'],'/var/lib/r7-service-admin')
        self.assertEqual(result['required_mode'],'0700');self.verify.assert_not_called()
    def test_apply_requires_fresh_exact_operation_commitment(self):
        for commitment in (None,'sha256:'+'f'*64):
            with self.subTest(commitment=commitment),self.assertRaises(ValueError):self.call(apply=True,operation_hash=commitment)
        self.assertEqual(self.backend.operations,[])
    def test_subject_and_parent_drift_invalidates_previously_displayed_operation(self):
        plan=self.call();self.backend.parents_generation+=1
        with self.assertRaises(ValueError):self.call(apply=True,operation_hash=plan['operation_hash'])
        self.assertEqual(self.backend.operations,[])
    def test_foreign_unreceipted_unit_is_preserved_even_when_bytes_match_plan(self):
        plan=self.call();name=next(iter(plan['file_hashes']))
        self.backend.files[name]=plan['rendered_files'][name].encode('utf-8')
        original=self.backend.files[name]
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.backend.files[name],original);self.assertEqual(self.backend.operations,[])
    def test_active_pending_job_unknown_or_foreign_manager_state_is_denied(self):
        for changes in (dict(ActiveState='active'),dict(Job='12'),dict(LoadState='unknown'),
                        dict(LoadState='loaded',FragmentPath='/usr/lib/systemd/system/r7-control.service'),dict(DropInPaths='/etc/foreign.conf')):
            with self.subTest(changes=changes):
                original=copy.deepcopy(self.backend.unit_state)
                self.backend.unit_state['r7-control.service'].update(changes)
                with self.assertRaises(ValueError):self.call()
                self.backend.unit_state=original
        self.assertEqual(self.backend.operations,[])
    def test_successful_install_writes_owned_receipt_last_then_only_reloads(self):
        result=self.install();self.assertEqual(result['status'],'FILES_INSTALLED')
        writes=[operation[1] for operation in self.backend.operations if operation[0]=='write']
        self.assertEqual(writes[-1],self.module.RECEIPT)
        self.assertEqual(self.backend.operations[-1],('reload',))
        self.assertEqual(len(writes),4)
    def test_installed_identical_retry_is_truthful_noop(self):
        self.install();self.backend.operations.clear();plan=self.call()
        result=self.call(apply=True,operation_hash=plan['operation_hash'])
        self.assertEqual(result['status'],'ALREADY_INSTALLED');self.assertEqual(self.backend.operations,[])
    def test_partial_write_preserves_partial_files_without_false_ready_receipt(self):
        self.backend.fail_write='/etc/systemd/system/r7-research.service'
        result=self.install();self.assertEqual(result['status'],'INCOMPLETE')
        self.assertNotIn(self.module.RECEIPT,self.backend.files)
        self.assertIn('/etc/systemd/system/r7-control.service',self.backend.files)
        with self.assertRaises(ValueError):self.call()
        self.assertFalse(any(op[0]=='remove' or op[0]=='reload' for op in self.backend.operations))
    def test_reload_failure_preserves_receipt_and_reports_manager_failure_separately(self):
        self.backend.reload_ok=False;result=self.install()
        self.assertEqual(result['status'],'FILES_INSTALLED_RELOAD_FAILED');self.assertIn(self.module.RECEIPT,self.backend.files)
    def test_uninstall_dry_run_and_apply_preserve_binary_config_data_and_scope_inodes(self):
        self.install();self.backend.files.update({'/opt/r7/release/r7':b'binary','/etc/r7/settings/product.json':b'config',
            '/var/lib/r7-data/canonical.sqlite':b'database','/run/r7/scopes/existing.lock':b'lock inode'})
        preserved={name:raw for name,raw in self.backend.files.items() if name not in self.module.TARGETS and name!=self.module.RECEIPT}
        self.backend.operations.clear();plan=self.call('uninstall');self.assertEqual(self.backend.operations,[])
        result=self.call('uninstall',apply=True,operation_hash=plan['operation_hash'])
        self.assertEqual(result['status'],'FILES_REMOVED');self.assertNotIn(self.module.RECEIPT,self.backend.files)
        self.assertTrue(all(self.backend.files[name]==raw for name,raw in preserved.items()))
        removed=[op[1] for op in self.backend.operations if op[0]=='remove']
        self.assertEqual(removed[-1],self.module.RECEIPT)
        self.assertEqual(set(removed),set(self.module.TARGETS)|{self.module.RECEIPT})
    def test_changed_owned_target_or_receipt_blocks_all_removals(self):
        self.install();self.backend.operations.clear();self.backend.files[self.module.TARGETS[0]]+=b'changed'
        with self.assertRaises(ValueError):self.call('uninstall')
        self.assertEqual(self.backend.operations,[])
    def test_uninstall_without_exact_ownership_receipt_is_denied(self):
        with self.assertRaises(ValueError):self.call('uninstall')
        self.assertEqual(self.backend.operations,[])
    def test_dropin_directory_conflict_blocks_install(self):
        self.backend.has_dropin=lambda name:True
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.backend.operations,[])
    def test_installer_does_not_accept_supplied_unit_body_or_alternate_system_root(self):
        with self.assertRaises(TypeError):self.call(system_root='/tmp/alternate')
        with self.assertRaises(TypeError):self.call(unit_body='arbitrary unit')
        self.assertEqual(self.backend.operations,[])

if __name__=='__main__':unittest.main()
