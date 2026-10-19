"""Source-only refusal of unsupported test names and preserving repetitions."""
import unittest
import bind_current_acceptance_records as helper

class NamedSupportBindings(unittest.TestCase):
    def test_duplicate_substitution_or_changed_text_cannot_replace_canonical_requirement(self):
        canonical={'A01':'first requirement','A02':'second requirement'}
        valid=[{'id':key,'requirement':value} for key,value in canonical.items()]
        helper.require_exact_rows(valid,canonical,'id','requirement')
        for bad in ([valid[0],valid[0]],[valid[0],{'id':'X99','requirement':'second requirement'}],
                    [valid[0],{'id':'A02','requirement':'changed requirement'}]):
            with self.subTest(rows=bad),self.assertRaises(ValueError):helper.require_exact_rows(bad,canonical,'id','requirement')

    def test_missing_case_is_unresolved_and_actual_repeated_occurrences_stay_explicit(self):
        one='tests.owner.test_module.Tests.test_one';missing='tests.owner.test_module.Tests.test_missing'
        actual=[dict(test_id=one,execution_instance_id='focused:1'),dict(test_id=one,execution_instance_id='full:1')]
        bound,unresolved=helper.bind_names([one,one,missing],actual)
        self.assertEqual([row['execution_instance_id'] for row in bound],['focused:1','full:1'])
        self.assertEqual(unresolved,[missing])
        self.assertEqual(list(helper.named_ids({'cases':[one,'module.test_one','not evidence',{'test_id':missing}]})),[one,missing])

if __name__=='__main__':unittest.main(verbosity=2)
