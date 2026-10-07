"""Controlled leaf interleavings; no native Linux filesystem claim."""
import importlib,unittest

class Removal:
    def __init__(self,replacement=None,reoccupied=None):
        self.original='owned-inode';self.quarantine=None;self.replacement=replacement;self.reoccupied=reoccupied;self.deleted=[]
    def expect_original(self,expected):
        if self.original!=expected:raise ValueError('Different original')
    def move_to_quarantine(self):
        if self.replacement is not None:self.original=self.replacement
        self.quarantine=self.original;self.original=None
        if self.reoccupied is not None:self.original=self.reoccupied
    def quarantined_facts(self):return self.quarantine
    def restore_noreplace(self):
        if self.original is not None:raise FileExistsError('Replacement preserved')
        self.original=self.quarantine;self.quarantine=None
    def unlink_verified(self):self.deleted.append(self.quarantine);self.quarantine=None
    def original_exists(self):return self.original is not None

class RemovalProtocolTests(unittest.TestCase):
    def module(self):return importlib.import_module('application.platform.service_admin_removal')
    def test_verified_original_is_deleted_only_after_transfer_and_verification(self):
        operation=Removal();self.module().remove_verified_leaf(operation,'owned-inode')
        self.assertEqual(operation.deleted,['owned-inode']);self.assertIsNone(operation.original)
    def test_leaf_replacement_between_snapshot_and_transfer_is_restored_and_never_deleted(self):
        operation=Removal(replacement='unverified-replacement')
        with self.assertRaises(ValueError):self.module().remove_verified_leaf(operation,'owned-inode')
        self.assertEqual(operation.original,'unverified-replacement');self.assertEqual(operation.deleted,[])
    def test_replacement_is_preserved_in_quarantine_when_public_name_is_reoccupied(self):
        operation=Removal(replacement='unverified-replacement',reoccupied='another-replacement')
        with self.assertRaises(ValueError):self.module().remove_verified_leaf(operation,'owned-inode')
        self.assertEqual(operation.quarantine,'unverified-replacement');self.assertEqual(operation.original,'another-replacement')
        self.assertEqual(operation.deleted,[])

if __name__=='__main__':unittest.main()
