"""Fixed product inventory is installed code, never caller PASS or command input."""
import importlib
import importlib.util
import unittest


class FixedPaperInventoryTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.inventory'))
        return importlib.import_module('application.paper.inventory')

    def test_fixed_seven_groups_are_nonempty_and_no_caller_command_is_accepted(self):
        m=self.module()
        for target in ('windows-11-x86_64','ubuntu-24.04-x86_64','ubuntu-26.04-x86_64'):
            profile=m.fixed_profile(target)
            self.assertEqual(tuple(g['check_id'] for g in profile['groups']),tuple(f'PQR-{i:02d}' for i in range(1,8)))
            self.assertTrue(all(g['members'] for g in profile['groups']))
            self.assertTrue(all(c['test_cases'] or c['assertions'] for g in profile['groups'] for c in g['members']))
            self.assertEqual(profile['decision_ref'],'PM_PAPER_RELEASE_MAPPING_DECISION_20261013')
            profile['groups'].clear()
            self.assertEqual(len(m.fixed_profile(target)['groups']),7)
        for target in ('windows','ubuntu','SOURCE_QUALIFIED',None):
            with self.subTest(target=target),self.assertRaises(ValueError):m.fixed_profile(target)

    def test_inventory_binds_source_tools_tests_and_explicit_os_predicates(self):
        m=self.module();profile=m.fixed_profile('windows-11-x86_64')
        self.assertTrue(profile['source_files'])
        self.assertTrue(all(h.startswith('sha256:') for h in profile['source_files'].values()))
        native=[c for g in profile['groups'][1:] for c in g['members']]
        self.assertTrue(all(c['timeout_seconds']==900 for c in profile['groups'][0]['members']))
        self.assertTrue(all(c['timeout_seconds']==1200 for c in native))
        self.assertTrue(all(c['kind']=='NATIVE_ASSERTIONS' and c['target_predicate']=='NAMED_NATIVE_TARGET' for c in native))
        self.assertEqual(profile['os_applicability']['systemd'],'OS_INAPPLICABLE_WINDOWS')
        self.assertEqual(m.fixed_profile('ubuntu-24.04-x86_64')['os_applicability']['systemd'],'REQUIRED_ACTUAL_UNPRIVILEGED_SERVICE')


if __name__=='__main__':unittest.main()
