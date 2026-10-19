"""Source-only actual byte/link and mixed-provenance refusal checks."""
import copy,json,os,tempfile,unittest
from pathlib import Path
import retain_current_checkpoint as helper
from application.platform.private_files import create_private_directory,write_private_new

class EvidenceAdmission(unittest.TestCase):
    def test_deep_host_artifact_is_bounded_without_relaxing_cloud_reference_depth(self):
        from application.cloud.manifest import safe_relative
        from application.cloud.protocol import CloudError
        with tempfile.TemporaryDirectory(dir=helper.BASE,prefix='retainer-depth-') as directory:
            root=Path(directory);parent=root
            for number in range(9):
                parent=parent/str(number);create_private_directory(parent)
            path=parent/'actual.log';raw=b'actual bounded nonsecret host artifact\n';write_private_new(path,raw)
            with self.assertRaises(CloudError):safe_relative(path.relative_to(root).as_posix())
            captured=helper.CapturedEvidence(root)
            self.assertEqual(captured.capture(path,helper.sha(raw)),raw)
            with self.assertRaises(ValueError):captured.capture(root/'..'/'outside.log')

    def test_idle_proof_requires_same_original_store_receipt_and_no_workflow(self):
        revision='1'*40;facts={'executable_revision':revision};owning={'config_hash':'actual'}
        value=dict(passed=True,revision=revision,identity=facts,all_owned_trees_reaped=True,
            source_and_package_unchanged=True,helper_unchanged=True,workflow_authorized=False,
            owning_profile=dict(original_config_hash='actual',same_original_receipt_ref='actual-receipt',same_original_data_root=True,workflow_authorized=False),
            actual_idle_runtime_summaries=[dict(provider_requests=0,provider_responses=0,market_source='NOT_CONNECTED',run_failures={}) for _ in range(2)])
        helper.require_idle_checkpoint(value,revision,facts,owning,'actual-receipt')
        for key,bad in (('revision','other'),('identity',{}),('workflow_authorized',True),('all_owned_trees_reaped',False)):
            changed=copy.deepcopy(value);changed[key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError):helper.require_idle_checkpoint(changed,revision,facts,owning,'actual-receipt')
        changed=copy.deepcopy(value);changed['owning_profile']['same_original_receipt_ref']='other'
        with self.assertRaises(ValueError):helper.require_idle_checkpoint(changed,revision,facts,owning,'actual-receipt')
        changed=copy.deepcopy(value);changed['actual_idle_runtime_summaries'][0]['provider_requests']=1
        with self.assertRaises(ValueError):helper.require_idle_checkpoint(changed,revision,facts,owning,'actual-receipt')

    def test_stage_log_cannot_redirect_capture_to_other_project_file(self):
        stage=helper.BASE/'unexecuted-stage';labels=('expected',)
        self.assertEqual(helper.canonical_log(stage,'expected','expected.log',labels),stage/'expected.log')
        for ref in (str(helper.BASE/'other-private.log'),'nested/expected.log','../expected.log','different.log'):
            with self.subTest(ref=ref),self.assertRaises(ValueError):helper.canonical_log(stage,'expected',ref,labels)
        with self.assertRaises(ValueError):helper.canonical_log(stage,'unapproved','unapproved.log',labels)

    def test_captured_bytes_stay_bound_and_replacement_or_hardlink_denies(self):
        with tempfile.TemporaryDirectory(dir=helper.BASE,prefix='retainer-unit-') as directory:
            root=Path(directory)/'scope';create_private_directory(root)
            path=root/'receipt-artifact.log';original=b'actual nonsecret unit artifact\n';write_private_new(path,original)
            capture=helper.CapturedEvidence(root)
            self.assertEqual(capture.capture(path,helper.sha(original)),original)
            path.write_bytes(b'replaced')
            self.assertEqual(capture.bytes[path],original)
            with self.assertRaises(ValueError):capture.capture(path,helper.sha(original))
            with self.assertRaises(ValueError):capture.capture(path)
            linked=root/'linked.log';os.link(path,linked)
            with self.assertRaises(ValueError):helper.CapturedEvidence(root).capture(linked)

    def test_stale_identity_profile_receipt_or_unreaped_stage_cannot_be_retained(self):
        revision='1'*40;facts={'executable_revision':revision,'build_hash':'actual'};owning={'config_ref':'actual','config_hash':'actual'}
        rows={name:dict(passed=True,revision=revision,source_unchanged=True) for name in ('build','qualify','headless','native04','portable','unattended','qualified-backup')}
        for name in ('portable','unattended','qualified-backup'):rows[name]['identity']=facts
        rows['portable'].update(complete_bytes_identical=True,first_run={'passed':True})
        for name in ('unattended','qualified-backup'):rows[name].update(owning_profile=owning,all_owned_tree_reaped=True,source_and_package_unchanged=True)
        rows['unattended']['public_source_unchanged']=True
        rows['qualified-backup'].update(receipt_ref='actual-receipt',actual_receipt_equal_across_four_stores=True,
            source_diagnostic_histories_unchanged=True,restored_native_software_admission='DENIED')
        helper.require_stage_bindings(rows,revision,facts,owning,'actual-receipt')
        owning_only=copy.deepcopy(rows);del owning_only['native04']
        helper.require_stage_bindings(owning_only,revision,facts,owning,'actual-receipt')
        for stage,key,bad in [('portable','identity',{'build_hash':'other'}),('unattended','owning_profile',{'config_ref':'other'}),
                ('qualified-backup','receipt_ref','other-receipt'),('unattended','all_owned_tree_reaped',False),
                ('qualified-backup','restored_native_software_admission','ALLOWED'),('headless','source_unchanged',False),
                ('native04','revision','other')]:
            changed=copy.deepcopy(rows);changed[stage][key]=bad
            with self.subTest(stage=stage,field=key),self.assertRaises(ValueError):
                helper.require_stage_bindings(changed,revision,facts,owning,'actual-receipt')

    def test_owning_native04_primary_is_declared_exact_and_matches_actual_subject(self):
        facts={'executable_revision':'1'*40,'build_hash':'actual'}
        with tempfile.TemporaryDirectory(dir=helper.BASE,prefix='retainer-owning04-') as directory:
            root=Path(directory);stage=root/'PQR-04-native-artifacts';create_private_directory(stage)
            path=stage/'native-observations.json';ref=path.relative_to(root).as_posix()
            for bad in (None,'identity','passed','group','undeclared'):
                primary=dict(passed=True,identity=facts,group='PQR-04')
                if bad=='identity':primary['identity']={'build_hash':'other'}
                elif bad=='passed':primary['passed']=False
                elif bad=='group':primary['group']='PQR-07'
                raw=json.dumps(primary).encode();path.write_bytes(raw)
                members=[dict(member_id='PQR-04-native',group_id='PQR-04',artifacts=[dict(ref=ref,hash=helper.sha(raw))])]
                if bad=='undeclared':members[0]['artifacts']=[]
                captured=helper.CapturedEvidence(root)
                if bad is None:self.assertEqual(helper.require_owning_native04(captured,root,members,facts),path)
                else:
                    with self.subTest(bad=bad),self.assertRaises(ValueError):
                        helper.require_owning_native04(captured,root,members,facts)

if __name__=='__main__':unittest.main(verbosity=2)
