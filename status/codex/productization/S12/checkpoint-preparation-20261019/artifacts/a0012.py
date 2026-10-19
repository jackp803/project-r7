"""Source-only refusal checks for actual delivery linkage."""
import unittest
import write_current_launch_guide as helper

class LaunchGuideBindings(unittest.TestCase):
    def test_stale_portable_subject_or_zip_cannot_be_delivered(self):
        revision='1'*40;facts={'executable_revision':revision,'build_hash':'sha256:'+'2'*64}
        archive=helper.BASE/'build-unit'/'r7-product-0.2.0-windows-1111111.zip';packed=b'actual captured zip'
        portable=dict(revision=revision,identity=facts,archive_ref=archive.relative_to(helper.PROJECT).as_posix(),archive_hash=helper.sha(packed))
        helper.require_delivery_binding(revision,facts,portable,archive,packed)
        for key,bad in [('revision','3'*40),('identity',dict(facts,build_hash='other')),('archive_ref','other.zip'),('archive_hash',helper.sha(b'stale'))]:
            with self.subTest(field=key),self.assertRaises(ValueError):
                helper.require_delivery_binding(revision,facts,dict(portable,**{key:bad}),archive,packed)

if __name__=='__main__':unittest.main(verbosity=2)
