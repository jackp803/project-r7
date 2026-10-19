"""Source-only actual byte/link and mixed-provenance refusal checks."""
import copy,os,tempfile,unittest
from pathlib import Path
import retain_current_checkpoint as helper
from application.platform.private_files import create_private_directory,write_private_new

class EvidenceAdmission(unittest.TestCase):
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
        for stage,key,bad in [('portable','identity',{'build_hash':'other'}),('unattended','owning_profile',{'config_ref':'other'}),
                ('qualified-backup','receipt_ref','other-receipt'),('unattended','all_owned_tree_reaped',False),
                ('qualified-backup','restored_native_software_admission','ALLOWED'),('headless','source_unchanged',False),
                ('native04','revision','other')]:
            changed=copy.deepcopy(rows);changed[stage][key]=bad
            with self.subTest(stage=stage,field=key),self.assertRaises(ValueError):
                helper.require_stage_bindings(changed,revision,facts,owning,'actual-receipt')

if __name__=='__main__':unittest.main(verbosity=2)
