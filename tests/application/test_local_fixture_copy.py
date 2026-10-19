"""Actual bounded local bytes only; no network, process or bridge runner fake."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from application.platform.private_files import create_private_directory, write_private_new


class LocalFixtureCopyTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix='R7 local copy ')
        self.addCleanup(temporary.cleanup)
        self.scope = Path(temporary.name) / 'scope'
        create_private_directory(self.scope)
        self.stage, self.work, self.remote = [self.scope / name for name in ('stage', 'work', 'remote')]
        for root in (self.stage, self.work, self.remote):
            create_private_directory(root)
        self.marker = b'{"root_id":"r7-synthetic-fixture-cloud-v1"}'
        for root in (self.stage, self.remote):
            write_private_new(root / '.r7-root.json', self.marker)
        self.profile = self.scope / 'local-copy.json'
        self.document = dict(schema_version='r7-local-fixture-copy-v1', data_class='SYNTHETIC_FIXTURE_ONLY',
            scope_root=str(self.scope), stage_root=str(self.stage), work_root=str(self.work),
            remote_root=str(self.remote), remote_alias='fixture', drive_root_folder_id='fixture-root-0001')
        self.save_profile()
        path = Path(__file__).resolve().parents[2] / 'tools/local_fixture_copy.py'
        spec = importlib.util.spec_from_file_location('local_fixture_copy_under_test', path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def save_profile(self):
        raw = json.dumps(self.document).encode()
        if self.profile.exists():
            self.profile.write_bytes(raw)
        else:
            write_private_new(self.profile, raw)

    def argv(self, *arguments):
        return [*arguments, '--config', str(self.profile), '--drive-root-folder-id', 'fixture-root-0001',
            '--drive-skip-shortcuts', '--retries', '1', '--low-level-retries', '1', '--log-level', 'ERROR',
            '--cache-dir', str(self.work / 'rclone-cache')]

    def invoke(self, *arguments, expected=0):
        stdout, stderr = io.BytesIO(), io.StringIO()
        code = self.module.main(self.argv(*arguments), stdout=stdout, stderr=stderr)
        self.assertEqual(code, expected, stderr.getvalue())
        if expected:
            self.assertEqual(stdout.getvalue(), b'')
            self.assertEqual(stderr.getvalue(), 'LOCAL_FIXTURE_COPY_REJECTED\n')
        return stdout.getvalue()

    def source(self, raw=b'actual synthetic report'):
        folder = self.work / 'publication-01'
        create_private_directory(folder)
        path = folder / 'report.html'
        write_private_new(path, raw)
        return path

    def upload(self, source, remote='fixture:paper/run-01/report.html', expected=0):
        return self.invoke('copyto', str(source), remote, '--immutable', '--checksum', '--transfers', '1',
            '--checkers', '1', '--max-transfer', '16777216B', '--max-duration', '60s', expected=expected)

    def test_actual_upload_listing_readback_and_identical_replay(self):
        source = self.source()
        self.upload(source)
        target = self.remote / 'paper/run-01/report.html'
        self.assertEqual(target.read_bytes(), source.read_bytes())
        self.upload(source)
        self.assertEqual(self.invoke('cat', 'fixture:paper/run-01/report.html', '--head', '262145'), source.read_bytes())
        rows = json.loads(self.invoke('lsjson', 'fixture:', '--recursive', '--hash', '--no-modtime'))
        entry = next(row for row in rows if row['Path'] == 'paper/run-01/report.html')
        self.assertEqual(entry['Hashes']['SHA-256'], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(entry['Size'], len(source.read_bytes()))
        self.assertFalse(entry['IsDir'])
        self.assertEqual(self.invoke('cat', 'fixture:.r7-root.json', '--head', '4097'), self.marker)

    def test_stage_source_is_allowed_and_immutable_conflict_preserves_original(self):
        source = self.stage / 'feedback.json'
        write_private_new(source, b'first')
        self.upload(source)
        source.write_bytes(b'changed')
        self.upload(source, expected=2)
        self.assertEqual((self.remote / 'paper/run-01/report.html').read_bytes(), b'first')

    def test_readback_head_is_actual_bounded_prefix(self):
        source = self.source(b'123456')
        self.upload(source)
        self.assertEqual(self.invoke('cat', 'fixture:paper/run-01/report.html', '--head', '3'), b'123')

    def test_disjoint_private_descendant_work_root_matches_normal_bridge_layout(self):
        data = self.scope / 'data'
        create_private_directory(data)
        self.work = data / 'bridge-work'
        create_private_directory(self.work)
        self.document['work_root'] = str(self.work)
        self.save_profile()
        self.upload(self.source())
        self.assertEqual((self.remote / 'paper/run-01/report.html').read_bytes(), b'actual synthetic report')

    def test_remote_marker_loss_or_change_denies_all_operations_without_repair(self):
        marker = self.remote / '.r7-root.json'
        marker.rename(self.remote / 'retained-marker.json')
        self.invoke('lsjson', 'fixture:', '--recursive', '--hash', '--no-modtime', expected=2)
        self.assertFalse(marker.exists())
        write_private_new(marker, b'{"root_id":"different"}')
        self.upload(self.source(), expected=2)
        self.assertEqual(marker.read_bytes(), b'{"root_id":"different"}')

    def test_source_outside_named_roots_and_remote_download_are_denied(self):
        outside = self.scope / 'outside.txt'
        write_private_new(outside, b'private synthetic input')
        self.upload(outside, expected=2)
        self.upload('fixture:paper/x', remote=str(self.work / 'download'), expected=2)
        self.assertFalse((self.work / 'download').exists())

    def test_traversal_wrong_alias_and_author_destinations_are_denied(self):
        source = self.source()
        for remote in ('fixture:../escape', 'fixture:paper/../escape', 'else:paper/a',
                       'fixture:inbox/a', 'fixture:.r7-root.json', 'fixture:paper\\a'):
            with self.subTest(remote=remote):
                self.upload(source, remote, expected=2)

    def test_unknown_flags_operations_and_policy_ranges_are_denied(self):
        for arguments in (('copy', 'x', 'y'), ('delete', 'fixture:'),
                ('lsjson', 'fixture:', '--recursive', '--hash', '--no-modtime', '--extra'),
                ('cat', 'fixture:.r7-root.json', '--head', '999999999'),
                ('cat', 'fixture:.r7-root.json', '--head', '0')):
            with self.subTest(arguments=arguments):
                self.invoke(*arguments, expected=2)
        arguments = self.argv('lsjson', 'fixture:', '--recursive', '--hash', '--no-modtime')
        arguments[arguments.index('--retries')+1] = '9'
        self.assertEqual(self.module.main(arguments, stdout=io.BytesIO(), stderr=io.StringIO()), 2)

    def test_upload_policy_bounds_and_suffix_identity_are_closed(self):
        source = self.source()
        args = ['copyto', str(source), 'fixture:paper/a', '--immutable', '--checksum', '--transfers', '1',
            '--checkers', '1', '--max-transfer', '16777216B', '--max-duration', '60s']
        for index, value in ((7, '2'), (9, '0B'), (11, '301s')):
            changed = list(args)
            changed[index] = value
            self.invoke(*changed, expected=2)
        for flag, value in (('--drive-root-folder-id', 'another-root-0001'), ('--cache-dir', str(self.remote))):
            argv = self.argv('lsjson', 'fixture:', '--recursive', '--hash', '--no-modtime')
            argv[argv.index(flag)+1] = value
            self.assertEqual(self.module.main(argv, stdout=io.BytesIO(), stderr=io.StringIO()), 2)

    def test_changed_stage_marker_and_unknown_remote_file_deny_before_copy(self):
        source = self.source()
        marker = self.stage / '.r7-root.json'
        marker.write_bytes(b'{"root_id":"changed-stage"}')
        self.upload(source, expected=2)
        marker.write_bytes(self.marker)
        write_private_new(self.remote / 'unrecognized.json', b'original')
        self.upload(source, expected=2)
        self.assertFalse((self.remote / 'paper').exists())
        self.assertEqual((self.remote / 'unrecognized.json').read_bytes(), b'original')

    def test_destination_hardlink_and_missing_profile_are_denied(self):
        source = self.source()
        self.upload(source)
        target = self.remote / 'paper/run-01/report.html'
        os.link(target, self.scope / 'outside-alias.html')
        self.upload(source, expected=2)
        self.assertEqual(target.read_bytes(), source.read_bytes())
        self.profile.rename(self.scope / 'retained-config.json')
        self.invoke('lsjson', 'fixture:', '--recursive', '--hash', '--no-modtime', expected=2)

    def test_replay_at_total_byte_limit_is_idempotent(self):
        source = self.source(b'12345')
        self.upload(source)
        self.module.MAX_TOTAL_BYTES = len(self.marker) + 5
        self.upload(source)

    def test_config_schema_root_overlap_escape_and_identity_flags_are_denied(self):
        original = dict(self.document)
        for changes in ({'credentials': 'synthetic-forbidden'}, {'data_class': 'REAL'},
                {'stage_root': str(self.work)}, {'remote_root': str(self.stage / 'nested')},
                {'work_root': str(self.scope.parent)}, {'remote_alias': 'wrong:alias'},
                {'stage_root': str(self.scope / 'stage/../stage')}, {'stage_root': '//server/share'}):
            with self.subTest(changes=changes):
                self.document = {**original, **changes}
                self.save_profile()
                self.invoke('lsjson', 'fixture:', '--recursive', '--hash', '--no-modtime', expected=2)

    def test_oversized_source_never_creates_destination(self):
        source = self.source(b'x' * (262144 + 1))
        self.upload(source, expected=2)
        self.assertFalse((self.remote / 'paper').exists())

    def test_hardlink_source_is_denied(self):
        source = self.source()
        alias = self.work / 'hardlink.html'
        os.link(source, alias)
        self.upload(alias, expected=2)
        self.assertFalse((self.remote / 'paper').exists())

    def test_case_alias_and_available_symlink_remote_are_denied(self):
        source = self.source()
        self.upload(source, 'fixture:paper/Run-01/report.html')
        self.upload(source, 'fixture:paper/run-01/another.html', expected=2)
        self.assertFalse((self.remote / 'paper/Run-01/another.html').exists())
        # Additional real link coverage when the host permits symlink creation.
        # The case-alias boundary above is exercised on every host.
        self.document['remote_root'] = str(self.scope / 'other-remote')
        create_private_directory(Path(self.document['remote_root']))
        write_private_new(Path(self.document['remote_root']) / '.r7-root.json', self.marker)
        self.save_profile()
        self.remote = Path(self.document['remote_root'])
        link = self.remote / 'paper'
        try:
            link.symlink_to(self.stage, target_is_directory=True)
        except OSError:
            return
        self.upload(source, expected=2)
        self.assertFalse((self.stage / 'run-01').exists())


if __name__ == '__main__':
    unittest.main()
