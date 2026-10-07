import unittest
from application.qualification import parse_result

class FingerprintProofTests(unittest.TestCase):
    def result(self):
        return parse_result('Ran 1 test in 0.1s\n\nOK\n',returncode=0)

    def test_successful_test_with_unreaped_tree_cannot_emit_pass(self):
        from s12_fingerprint_proof import bound_result
        facts=bound_result(self.result(),tree_reaped=False,inputs_unchanged=True)
        self.assertTrue(facts['test_result_passed'])
        self.assertFalse(facts['passed'])

    def test_source_input_changes_invalidate_successful_owned_execution(self):
        from s12_fingerprint_proof import bound_result
        self.assertFalse(bound_result(self.result(),tree_reaped=True,inputs_unchanged=False)['passed'])
        self.assertTrue(bound_result(self.result(),tree_reaped=True,inputs_unchanged=True)['passed'])
