"""Actual pinned private file checks only, never native qualification credit."""
from pathlib import Path
from tempfile import TemporaryDirectory
import time,unittest
import copy,json
from dataclasses import replace
import verify_qualified_backup_checkpoint as helper
from storage.paper_selection import OperationalSelection
from application.platform.private_files import create_private_directory,write_private_new

class QualifiedBackupHelperFileChecks(unittest.TestCase):
    def actual_selection(self):
        # Actual normal native configure-paper output, read only. Never insert
        # a handmade terminal state or substitute a guessed record shape.
        path=helper.PROJECT/'artifacts/q-7d821f2-first/canonical.sqlite3'
        return helper.read_runtime_selection(path)

    def test_stopped_selection_uses_actual_canonical_envelope_and_owner(self):
        original=self.actual_selection();record=original.as_dict()
        self.assertNotIn('namespace',record)
        self.assertNotIn('product_config_hash',record)
        idle=dict(selection_generation=original.generation,
            owning_profile=dict(idle_config_hash=record['envelope']['product_config_hash']))
        helper.require_stopped_selection(original,idle)
        for field,value in (('generation',original.generation+1),('config_hash','sha256:'+'0'*64)):
            changed=copy.deepcopy(idle)
            if field=='generation':changed['selection_generation']=value
            else:changed['owning_profile']['idle_config_hash']=value
            with self.subTest(field=field),self.assertRaises(ValueError):helper.require_stopped_selection(original,changed)

    def test_backup_attempt_paths_are_explicit_and_never_overwrite_first_failure(self):
        revision='7d821f29837e95e46bcd5fe32f14d536a28c9aa8'
        self.assertEqual(helper.backup_output(revision,'retry01').name,'qualified-backup-7d821f2-retry01')
        self.assertNotEqual(helper.backup_output(revision,'first'),helper.backup_output(revision,'retry01'))
        for attempt in ('../first','retry1','latest',''):
            with self.subTest(attempt=attempt),self.assertRaises(ValueError):helper.backup_output(revision,attempt)

    def test_idle_backup_binding_requires_actual_same_stopped_store_and_receipt(self):
        revision='1'*40;facts={'executable_revision':revision}
        owning=dict(config_ref='profile.json',data_root_ref='data',canonical_ref='data/e6.sqlite',
            product_instance_id='source-fixture',config_hash='actual-config')
        value=dict(passed=True,revision=revision,identity=facts,all_owned_trees_reaped=True,
            source_and_package_unchanged=True,helper_unchanged=True,workflow_authorized=False,selection_generation=1,
            owning_profile=dict(original_config_ref='profile.json',original_data_root_ref='data',
                original_canonical_ref='data/e6.sqlite',original_product_instance_id='source-fixture',
                original_config_hash='actual-config',same_original_receipt_ref='actual-receipt',
                same_original_data_root=True,workflow_authorized=False))
        helper.require_idle_backup_binding(value,revision,facts,owning,'actual-receipt')
        for key,bad in (('passed',False),('revision','other'),('identity',{}),('all_owned_trees_reaped',False),('workflow_authorized',True)):
            changed=copy.deepcopy(value);changed[key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError):
                helper.require_idle_backup_binding(changed,revision,facts,owning,'actual-receipt')
        for key in ('original_data_root_ref','original_canonical_ref','original_product_instance_id','original_config_ref','same_original_receipt_ref'):
            changed=copy.deepcopy(value);changed['owning_profile'][key]='other'
            with self.subTest(binding=key),self.assertRaises(ValueError):
                helper.require_idle_backup_binding(changed,revision,facts,owning,'actual-receipt')

    def test_four_store_selection_equality_preserves_original_false_workflow_and_generation(self):
        original=self.actual_selection();envelope=original.as_dict()
        helper.require_runtime_selection_equal(original,(original,original,original))
        for changed in (None,replace(original,generation=2),replace(original,config_hash='sha256:'+'2'*64),
                replace(original,canonical_json=json.dumps({**envelope,'envelope':{**envelope['envelope'],'product_config_hash':'other'}}))):
            with self.subTest(changed=changed),self.assertRaises(ValueError):
                helper.require_runtime_selection_equal(original,(original,changed,original))
        with self.assertRaises(ValueError):helper.require_runtime_selection_equal(original,(original,original))
        authorized=replace(original,canonical_json=json.dumps({**envelope,'owner':{**envelope['owner'],'workflow_authorized':True}}))
        with self.assertRaises(ValueError):helper.require_runtime_selection_equal(authorized,(authorized,authorized,authorized))
        foreign=replace(original,canonical_json=json.dumps({**envelope,'owner':{**envelope['owner'],'namespace':'FIXTURE'}}))
        with self.assertRaises(ValueError):helper.require_runtime_selection_equal(foreign,(foreign,foreign,foreign))

    def test_valid_sealed_snapshot_copies_match_and_one_changed_seal_denies(self):
        with TemporaryDirectory(dir=helper.BASE,prefix='backup-helper-unit-') as temporary:
            roots=[Path(temporary)/name for name in ('original','captured','restored','recaptured')]
            relative='snapshots/'+'1'*64+'/.seal.json';raw=b'{"immutable_snapshot":"bounded_source_fixture"}\n'
            for root in roots:
                create_private_directory(root);create_private_directory(root/'snapshots');create_private_directory(root/'snapshots'/('1'*64))
                write_private_new(root/relative,raw)
            row=dict(relative_path=relative,bytes=len(raw),sha256=helper.sha(raw))
            helper.require_same_captured_file(roots,row,time.monotonic()+30)
            (roots[2]/relative).write_bytes(raw+b' ')
            with self.assertRaisesRegex(ValueError,'four-way file equality'):helper.require_same_captured_file(roots,row,time.monotonic()+30)

if __name__=='__main__':unittest.main(verbosity=2)
