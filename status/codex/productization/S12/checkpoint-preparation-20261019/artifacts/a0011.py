"""No final success-shaped index can escape a failed final source guard."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import index_current_qualification as helper

class CurrentIndexPublicationTests(unittest.TestCase):
    def test_changed_final_subject_prevents_final_publication(self):
        with TemporaryDirectory(dir=helper.BASE,prefix='index-helper-unit-') as directory:
            target=Path(directory)/'final.json'
            def changed():raise ValueError('Final actual subject changed')
            with self.assertRaises(ValueError):helper.publish_index(target,dict(cases=[dict(status='PASS')]),changed)
            self.assertFalse(target.exists())

if __name__=='__main__':unittest.main(verbosity=2)
