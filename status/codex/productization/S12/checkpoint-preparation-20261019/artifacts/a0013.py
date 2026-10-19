"""Source-only explicit attempt names; no result import or auto-selection."""
import unittest
import run_current_checkpoint as helper
class AttemptPaths(unittest.TestCase):
    def test_explicit_attempts_stay_distinct_and_closed(self):
        revision='1'*40
        self.assertEqual(helper.qualification_output(revision),helper.BASE/'qualify-1111111-first')
        self.assertEqual(helper.qualification_output(revision,'retry01'),helper.BASE/'qualify-1111111-retry01')
        for bad in ('../first','/elsewhere','retry1','retry001','accepted','first/extra'):
            with self.subTest(attempt=bad),self.assertRaises(ValueError):helper.qualification_output(revision,bad)
        with self.assertRaises(ValueError):helper.qualification_output('partial','retry01')
if __name__=='__main__':unittest.main(verbosity=2)
