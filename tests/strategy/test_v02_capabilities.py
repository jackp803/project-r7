import copy
import importlib.util
import unittest

from tests.strategy.v02_fixtures import definition_v02


class CapabilityTests(unittest.TestCase):
    def test_every_registry_entry_declares_metadata_without_fabricated_verification(self):
        document=self.api().build_capability_snapshot().as_dict()
        rows=document['capabilities']
        expected={
            'SMA':('r7-sma-v1',['value'],'n'),
            'EMA':('r7-ema-v1',['value'],'n'),
            'RSI':('r7-rsi-wilder-v1',['value'],'n+1'),
            'ATR':('r7-atr-wilder-v1',['value'],'n'),
            'ADX':('r7-adx-wilder-v1',['value','plus_di','minus_di'],'DI:n+1; ADX:2*n'),
            'MACD':('r7-macd-v1',['line','signal','histogram'],'line:slow; signal/histogram:slow+signal_window-1'),
            'BOLLINGER':('r7-bollinger-pop-v1',['middle','upper','lower','stddev'],'n'),
            'DONCHIAN':('r7-donchian-v1',['upper','lower','middle'],'n+lag_bars')}
        self.assertEqual(len(rows),9)
        self.assertEqual({row['capability_id'] for row in rows},{'grammar:0.2',*('indicator:'+name for name in expected)})
        self.assertEqual(document['runtime_profiles'],['0.1.0','0.2.0'])
        self.assertRegex(document['implementation_revision'],r'^sha256:[0-9a-f]{64}$')
        for row in rows:
            with self.subTest(capability=row['capability_id']):
                self.assertIsInstance(row['parameters'],dict)
                for name in ('output_type','units','minimum_history','missing_data_behavior'):
                    self.assertIsInstance(row[name],str)
                    self.assertTrue(row[name])
                self.assertEqual(row['supported_timeframes'],['1m','15m','1h','4h'])
                self.assertEqual(row['arithmetic_profile'],'r7-decimal34-v1')
                self.assertEqual(row['implementation_revision'],document['implementation_revision'])
                self.assertIs(row['validator_available'],True)
                self.assertIs(row['IMPLEMENTED'],True)
                for name in ('VERIFIED_REFERENCE','PAPER_AVAILABLE','LIVE_PROVIDER_AVAILABLE'):
                    self.assertIs(row[name],False)
                self.assertEqual(row['verification_refs'],[])
                if row['capability_id'].startswith('indicator:'):
                    version,outputs,history=expected[row['capability_id'].removeprefix('indicator:')]
                    self.assertEqual(row['semantic_version'],version)
                    self.assertEqual(set(row['outputs']),set(outputs))
                    self.assertEqual(len(row['outputs']),len(outputs))
                    self.assertEqual(row['minimum_history'],history)
                else:
                    self.assertEqual(row['semantic_version'],'r7-closed-bar-v0.2')
        self.assertEqual(document['platform_verification'],
            dict(Windows11='NOT_RUN',**{'Ubuntu24.04':'NOT_RUN','Ubuntu26.04':'NOT_RUN'}))

    def test_source_inventory_ignores_unreadable_non_executable_file_metadata(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        with TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'owner.py').write_bytes(b'authority = 1\n')
            (root/'cache.pyc').write_bytes(b'mutable cache')
            before=self.api()._source_revision(root)
            actual_is_file=Path.is_file
            def executable_metadata_only(path):
                if path.suffix not in ('.py','.sql'):
                    raise AssertionError('Non-executable metadata entered authority fingerprint')
                return actual_is_file(path)
            with patch.object(Path,'is_file',executable_metadata_only):
                self.assertEqual(before,self.api()._source_revision(root))

    def test_source_inventory_reads_fresh_exact_sorted_python_sql_contents(self):
        import hashlib
        from pathlib import Path
        from tempfile import TemporaryDirectory
        api=self.api()
        with TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'nested').mkdir()
            (root/'z.sql').write_bytes(b'SELECT 1;\r\n')
            (root/'nested'/'a.py').write_bytes(b'authority = 1\r\n')
            (root/'README.md').write_bytes(b'not executable')
            def expected(rows):
                material=b''.join(name.encode('ascii')+b'\x00'+raw+b'\x00' for name,raw in sorted(rows))
                return 'sha256:'+hashlib.sha256(material).hexdigest()
            initial=expected([('z.sql',b'SELECT 1;\n'),('nested/a.py',b'authority = 1\n')])
            self.assertEqual(initial,api._source_revision(root))
            (root/'nested'/'a.py').write_bytes(b'authority = 2\n')
            changed=expected([('z.sql',b'SELECT 1;\n'),('nested/a.py',b'authority = 2\n')])
            self.assertEqual(changed,api._source_revision(root));self.assertNotEqual(initial,changed)
            (root/'new.py').write_bytes(b'new owner\n')
            self.assertEqual(expected([('z.sql',b'SELECT 1;\n'),('nested/a.py',b'authority = 2\n'),('new.py',b'new owner\n')]),api._source_revision(root))
            (root/'nested'/'a.py').unlink()
            self.assertEqual(expected([('z.sql',b'SELECT 1;\n'),('new.py',b'new owner\n')]),api._source_revision(root))

    def test_same_size_same_mtime_owner_and_sql_replacement_cannot_reuse_identity(self):
        import os
        from pathlib import Path
        from tempfile import TemporaryDirectory
        api=self.api()
        with TemporaryDirectory() as temporary:
            root=Path(temporary)
            owner=root/'owner.py';sql=root/'authority.sql'
            owner.write_bytes(b'owner = 1\n');sql.write_bytes(b'SELECT 1;\n')
            original=api._source_revision(root)
            for path,replacement in ((owner,b'owner = 2\n'),(sql,b'SELECT 2;\n')):
                metadata=path.stat()
                path.write_bytes(replacement)
                os.utime(path,ns=(metadata.st_atime_ns,metadata.st_mtime_ns))
                changed=api._source_revision(root)
                self.assertNotEqual(original,changed)
                original=changed
            owner.rename(root/'renamed.py')
            self.assertNotEqual(original,api._source_revision(root))

    def test_unreadable_owner_directory_cannot_issue_partial_source_identity(self):
        import os
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        with TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'owned').mkdir()
            (root/'visible.py').write_bytes(b'visible = 1\n')
            (root/'owned'/'authority.sql').write_bytes(b'SELECT 1;\n')
            scan=os.scandir
            def deny_owned_directory(path):
                if Path(path)==root/'owned':
                    raise PermissionError('controlled unreadable executable directory')
                return scan(path)
            with patch('os.scandir',side_effect=deny_owned_directory),self.assertRaises(PermissionError):
                self.api()._source_revision(root)

    def test_e1_aggregation_or_e5_exit_semantics_change_requires_fresh_capability_binding(self):
        api=self.api()
        from pathlib import Path
        from unittest.mock import patch
        source=Path(api.__file__).resolve().parents[2]
        initial=api.build_capability_snapshot().snapshot_hash
        actual_read=Path.read_bytes
        for relative in ('market_data/aggregation.py','position/exit_requests.py'):
            target=source/relative
            with self.subTest(module=relative):
                def changed_read(path):
                    raw=actual_read(path)
                    return raw+b'\n# owner semantics changed\n' if path.resolve()==target.resolve() else raw
                with patch.object(Path,'read_bytes',changed_read):
                    changed=api.build_capability_snapshot().snapshot_hash
                self.assertNotEqual(initial,changed)

    def test_checkout_line_endings_do_not_create_different_implementation_identity(self):
        api=self.api()
        from pathlib import Path
        from unittest.mock import patch
        initial=api.build_capability_snapshot().snapshot_hash
        actual_read=Path.read_bytes
        def crlf_read(path):
            return actual_read(path).replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
        with patch.object(Path,'read_bytes',crlf_read):
            changed=api.build_capability_snapshot().snapshot_hash
        self.assertEqual(initial,changed)

    def test_numerical_implementation_change_invalidates_exact_capability_identity(self):
        api=self.api()
        from pathlib import Path
        from unittest.mock import patch
        target=Path(api.__file__).resolve().parents[2]/'indicators/v02/bands.py'
        self.assertTrue(target.is_file())
        initial=api.build_capability_snapshot().snapshot_hash
        actual_read=Path.read_bytes
        def changed_read(path):
            raw=actual_read(path)
            return raw+b'\n# numerical implementation changed\n' if path.resolve()==target.resolve() else raw
        with patch.object(Path,'read_bytes',changed_read):
            changed=api.build_capability_snapshot().snapshot_hash
        self.assertNotEqual(initial,changed)

    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('strategy.v02.capabilities'),
                             'Executable capability registry is missing')
        from strategy.v02 import capabilities
        return capabilities

    def test_recognized_indicator_does_not_claim_verified_execution_or_provider(self):
        snapshot=self.api().build_capability_snapshot()
        ema=next(row for row in snapshot.as_dict()['capabilities'] if row['capability_id']=='indicator:EMA')
        self.assertTrue(ema['validator_available'])
        self.assertTrue(ema['IMPLEMENTED'])
        self.assertFalse(ema['VERIFIED_REFERENCE'])
        self.assertFalse(ema['PAPER_AVAILABLE'])
        self.assertFalse(ema['LIVE_PROVIDER_AVAILABLE'])
        report=self.api().check_compatibility(definition_v02(),snapshot)
        self.assertEqual('BLOCKED',report.status)
        self.assertIn('EXECUTION_NOT_QUALIFIED',[gap.reason for gap in report.gaps])

    def test_missing_actual_handler_is_never_advertised_as_implemented(self):
        from indicators.v02 import features
        self.assertTrue(hasattr(features,'INDICATOR_HANDLERS'),'Missing executable handler registry')
        from unittest.mock import patch
        with patch.dict(features.INDICATOR_HANDLERS,{'EMA':None}):
            snapshot=self.api().build_capability_snapshot()
            ema=next(row for row in snapshot.as_dict()['capabilities'] if row['capability_id']=='indicator:EMA')
            self.assertFalse(ema['IMPLEMENTED'])
            report=self.api().check_compatibility(definition_v02(),snapshot)
            self.assertIn('NOT_IMPLEMENTED',[gap.reason for gap in report.gaps])

    def test_snapshot_hash_is_deterministic_and_snapshot_cannot_be_mutated(self):
        api=self.api()
        snapshot=api.build_capability_snapshot()
        initial=snapshot.as_dict()
        self.assertEqual(snapshot.snapshot_hash,api.build_capability_snapshot().snapshot_hash)
        initial['capabilities'][0]['IMPLEMENTED']=not initial['capabilities'][0]['IMPLEMENTED']
        self.assertNotEqual(initial,snapshot.as_dict())
        self.assertRegex(snapshot.snapshot_hash,r'^sha256:[0-9a-f]{64}$')

    def test_unknown_version_gap_names_exact_source_and_available_version(self):
        api=self.api()
        value=definition_v02()
        value['rules']['features']['trend']['semantic_version']='r7-ema-v99'
        report=api.check_compatibility(value,api.build_capability_snapshot())
        gap=next(gap for gap in report.gaps if gap.reason=='UNSUPPORTED_VERSION')
        self.assertEqual('r7-ema-v99',gap.requested_version)
        self.assertEqual('r7-ema-v1',gap.available_version)
        self.assertEqual('/rules/features/trend',gap.source_location)
        self.assertTrue(gap.reevaluation_conditions)

    def test_changed_snapshot_hash_does_not_transfer_compatibility(self):
        api=self.api()
        report=api.check_compatibility(definition_v02(),api.build_capability_snapshot(),
                                       required_snapshot_hash='sha256:'+'0'*64)
        self.assertEqual('BLOCKED',report.status)
        self.assertEqual('CAPABILITY_SNAPSHOT_MISMATCH',report.gaps[0].reason)

