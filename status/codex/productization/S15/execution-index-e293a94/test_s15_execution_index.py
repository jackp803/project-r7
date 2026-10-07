import unittest

class ExecutedCaseIndexTests(unittest.TestCase):
    def parse(self,raw,count=1,code=0):
        from s15_execution_index import parse_command_cases
        return parse_command_cases(raw.encode('utf-8'),count,code)

    def test_actual_verbose_test_with_interleaved_cli_diagnostic_is_counted_once(self):
        text='test_denial (test_api.OwnerTests.test_denial) ... usage: r7\nr7: error: denied\nok\n\nRan 1 test in 0.1s\n\nOK\n'
        cases=self.parse(text)
        self.assertEqual(['test_api.OwnerTests.test_denial'],[r['reported_test_id'] for r in cases])

    def test_missing_case_completion_cannot_borrow_a_successful_summary(self):
        text='test_denial (test_api.OwnerTests.test_denial) ... diagnostic\n\nRan 1 test in 0.1s\n\nOK\n'
        with self.assertRaises(ValueError):self.parse(text)

    def test_summary_count_cannot_substitute_for_missing_named_cases(self):
        with self.assertRaises(ValueError):self.parse('Ran 1 test in 0.1s\n\nOK\n')

    def test_wrong_case_method_and_failed_process_are_rejected(self):
        with self.assertRaises(ValueError):self.parse('test_wrong (test_api.OwnerTests.test_denial) ... ok\nRan 1 test in 0.1s\nOK\n')
        with self.assertRaises(ValueError):self.parse('test_denial (test_api.OwnerTests.test_denial) ... ok\nRan 1 test in 0.1s\nOK\n',code=1)

    def test_repeated_named_case_is_preserved_as_two_execution_instances(self):
        line='test_denial (test_api.OwnerTests.test_denial) ... ok\n'
        cases=self.parse(line+line+'Ran 2 tests in 0.1s\n\nOK\n',count=2)
        self.assertEqual(2,len(cases))
        self.assertEqual(1,len({r['reported_test_id'] for r in cases}))

    def test_unreaped_tree_or_count_type_cannot_supply_case_evidence(self):
        from s15_execution_index import validate_execution_row
        row=dict(passed=True,tree_reaped=True,returncode=0,tests_run=1,tests_passed=1,
                 failures=0,errors=0,skipped=0,expected_failures=0,unexpected_successes=0)
        validate_execution_row(row)
        with self.assertRaises(ValueError):validate_execution_row(dict(row,tree_reaped=False))
        with self.assertRaises(ValueError):validate_execution_row(dict(row,tests_run=True))

    def log_row(self):
        return dict(passed=True,tree_reaped=True,returncode=0,tests_run=1,tests_passed=1,
            failures=0,errors=0,skipped=0,expected_failures=0,unexpected_successes=0,
            phase='phase_2',suite='e2e',log='001-phase_2-e2e.log')

    def test_canonical_e2e_suite_is_a_valid_bound_execution_log(self):
        import hashlib
        from unittest.mock import patch
        from s15_execution_index import read_command_cases
        raw=b'test_denial (test_api.OwnerTests.test_denial) ... ok\nRan 1 test in 0.1s\n\nOK\n'
        row=dict(self.log_row(),log_sha256=hashlib.sha256(raw).hexdigest())
        with patch('application.datasets.catalog.read_local',return_value=raw):
            self.assertEqual(1,len(read_command_cases('controlled-public-artifacts',row,1)))

    def test_replaced_log_bytes_cannot_supply_named_execution(self):
        from unittest.mock import patch
        from s15_execution_index import read_command_cases
        row=dict(self.log_row(),suite='application',log='001-phase_2-application.log',log_sha256='0'*64)
        with patch('application.datasets.catalog.read_local',return_value=b'changed'),self.assertRaises(ValueError):
            read_command_cases('controlled-public-artifacts',row,1)

    def static_fixture(self,root):
        import hashlib
        source=root/'tests/application/test_owned.py';source.parent.mkdir(parents=True)
        raw=b'class OwnerTests(TestCase):\n    def test_owned(self):\n        pass\n'
        source.write_bytes(raw)
        row=dict(test_id='tests.application.test_owned.OwnerTests.test_owned',source='tests/application/test_owned.py',
            line=2,class_bases=['TestCase'],discovery='STATIC_DECLARATION;ACTUAL_DISCOVERY_AND_EXECUTION_BINDING_PENDING')
        return dict(test_source_hashes={'tests/application/test_owned.py':'sha256:'+hashlib.sha256(raw).hexdigest()},declared_tests=[row])

    def test_empty_partial_or_duplicate_static_inventory_is_rejected(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from s15_execution_index import validate_static_inventory
        with TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary:
            root=Path(temporary).resolve();self.assertTrue(root.is_relative_to(Path(__file__).resolve().parent))
            inventory=self.static_fixture(root);validate_static_inventory(root,inventory)
            for changed in (dict(inventory,test_source_hashes={}),dict(inventory,declared_tests=[]),
                            dict(inventory,declared_tests=inventory['declared_tests']*2)):
                with self.subTest(changed=changed),self.assertRaises(ValueError):validate_static_inventory(root,changed)

    def test_correct_file_hash_does_not_authorize_a_forged_source_position(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from s15_execution_index import validate_static_inventory
        with TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary:
            root=Path(temporary).resolve();self.assertTrue(root.is_relative_to(Path(__file__).resolve().parent))
            inventory=self.static_fixture(root)
            for forged in (dict(inventory['declared_tests'][0],line=999),
                           dict(inventory['declared_tests'][0],source='tests/application/another.py')):
                with self.subTest(forged=forged),self.assertRaises(ValueError):
                    validate_static_inventory(root,dict(inventory,declared_tests=[forged]))

    def test_null_malformed_non_utc_and_reversed_windows_are_rejected(self):
        from s15_execution_index import validate_execution_window
        for start,end in ((None,'2026-10-07T00:00:01Z'),('not-utc','2026-10-07T00:00:01Z'),
                          ('2026-10-07T00:00:00+08:00','2026-10-07T00:00:01Z'),
                          ('2026-10-07T00:00:02Z','2026-10-07T00:00:01Z')):
            with self.subTest(start=start,end=end),self.assertRaises(ValueError):
                validate_execution_window(dict(started_at_utc=start,finished_at_utc=end))

    def test_actual_utc_window_keeps_the_recorded_full_scope(self):
        from s15_execution_index import validate_execution_window
        context=dict(started_at_utc='2026-10-07T00:00:00.123456Z',finished_at_utc='2026-10-07T00:00:01Z')
        window=validate_execution_window(context)
        self.assertEqual(context['started_at_utc'],window['started_at_utc'])
        self.assertIn('NO_PER_TEST_TIMESTAMP_CLAIM',window['scope'])

    def test_actual_builder_rejects_escaping_source_ref_before_any_dereference(self):
        import ast
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from s15_execution_index import validate_static_inventory
        builder=Path(__file__).resolve().parent/'build_s15_execution_index.py'
        nodes=[]
        for node in ast.parse(builder.read_bytes()).body:
            if isinstance(node,ast.For) and 'test_source_hashes' in ast.unparse(node.iter):nodes.append(node)
            elif isinstance(node,ast.Assign) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='validate_static_inventory':nodes.append(node)
        self.assertEqual(2,len(nodes))
        with TemporaryDirectory(dir=builder.parent) as temporary:
            root=Path(temporary).resolve();self.assertTrue(root.is_relative_to(builder.parent))
            inventory=self.static_fixture(root)
            inventory['test_source_hashes']['../../PRIVATE_SENTINEL']='sha256:'+'0'*64
            def forbidden_bind(*args):raise AssertionError('Caller-supplied reference was dereferenced before validation')
            with self.assertRaises(ValueError):
                exec(compile(ast.Module(body=nodes,type_ignores=[]),str(builder),'exec'),
                     dict(repo=root,inventory=inventory,validate_static_inventory=validate_static_inventory,bind=forbidden_bind))
