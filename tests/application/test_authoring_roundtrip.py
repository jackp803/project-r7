from datetime import datetime,timezone
import importlib
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from application.cloud.manifest import byte_hash,canonical_bytes,parse_manifest,validate_package
from application.cloud.synced_folder import SyncedFolderCloudTransport
from application.intake.ledger import IntakeLedger
from application.intake.service import StrategyInboxService
from storage import open_sqlite_platform
from registry import StrategyIdentity
from strategy.v02.capabilities import build_capability_snapshot
from tests.strategy.test_slice1_runtime import make_definition
from tests.strategy.v02_fixtures import definition_v02,field,operator


class AuthoringRoundtripTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.cloud.authoring'))
        return importlib.import_module('application.cloud.authoring')

    def test_actual_legacy_four_hour_multitimeframe_and_tactical_packages_reach_e2_e6(self):
        module=self.module();now=datetime(2026,10,5,tzinfo=timezone.utc)
        definitions=[('legacy',make_definition(),'0.1'),('four-hour',definition_v02(),'0.2'),('multi',definition_v02(),'0.2'),('tactical',definition_v02(),'0.2')]
        definitions[2][1]['strategy_id']='fixture-multi'
        definitions[2][1]['required_timeframes']=['1h','4h']
        definitions[2][1]['rules']['long']=operator('GT',field(timeframe='1h'),field(timeframe='4h'))
        definitions[3][1]['strategy_id']='fixture-tactical'
        with TemporaryDirectory(prefix='R7 作者 往返 ') as temporary:
            root=Path(temporary);cloud=root/'author-stage';cloud.mkdir()
            (cloud/'.r7-root.json').write_bytes(canonical_bytes(dict(root_id='author-fixture')))
            (cloud/'inbox/strategies').mkdir(parents=True)
            transport=SyncedFolderCloudTransport(cloud,expected_root_id='author-fixture')
            with IntakeLedger(root/'intake.sqlite',instance_id='author-fixture') as ledger,open_sqlite_platform(root/'canonical.sqlite') as e6:
                for name,definition,version in definitions:
                    with self.subTest(profile=name):
                        options=dict(intent_class='TACTICAL_STRATEGY',validity={'from':'2026-10-05T00:00:00Z','until':'2026-10-05T04:00:00Z'}) if name=='tactical' else {}
                        result=module.emit_package(definition,cloud/'inbox/strategies'/name,submission_id=name,package_version=version,
                            created_at='2026-10-05T00:00:00Z',created_by='offline synthetic author',
                            requested_dataset_profile='fixture-data',requested_validation_profile='diagnostic',requested_robustness_profile='diagnostic',
                            research_hypothesis='合成封裝測試',**options)
                        manifest=parse_manifest((cloud/'inbox/strategies'/name/'manifest.json').read_bytes())
                        spec=manifest.payloads[0];raw=(cloud/'inbox/strategies'/name/spec.relative_path).read_bytes()
                        self.assertEqual(spec.sha256,byte_hash(raw));self.assertNotEqual(spec.sha256,manifest.strategy_content_hash)
                        self.assertEqual(result['execution_evidence'],'NOT_RUN')
                service=StrategyInboxService(transport,ledger,e6,snapshot_root=root/'snapshots',owner_id='author-worker',
                    capability_snapshot_hash=build_capability_snapshot().snapshot_hash)
                first=service.scan_once(now);self.assertEqual(first.accepted,4);self.assertEqual(first.blocked,0)
                self.assertEqual(service.scan_once(now).idempotent,4)
                for descriptor in transport.discover():
                    verified=validate_package(transport.snapshot(descriptor,root/'snapshots'))
                    self.assertFalse(verified.compatibility_execution_pass)
                    self.assertEqual(e6.get_strategy(StrategyIdentity(verified.strategy.strategy_id,verified.strategy.strategy_version)).current_lifecycle_state,'DRAFT')

    def test_missing_capability_secret_notes_and_existing_output_are_refused_without_overwrite(self):
        module=self.module()
        with TemporaryDirectory() as temporary:
            root=Path(temporary);definition=definition_v02()
            definition['rules']['features']['trend']['name']='UNAVAILABLE_FEATURE'
            with self.assertRaises(module.AuthoringError) as caught:
                module.emit_package(definition,root/'missing',submission_id='missing')
            self.assertEqual(caught.exception.code,'CAPABILITY_GAP')
            self.assertFalse((root/'missing').exists())
            with self.assertRaises(module.AuthoringError):
                module.emit_package(definition_v02(),root/'notes',submission_id='notes',notes='api_secret=SYNTHETIC_REJECTED')
            self.assertFalse((root/'notes').exists())
            existing=root/'existing';existing.mkdir();(existing/'keep.txt').write_bytes(b'preserved')
            with self.assertRaises(module.AuthoringError):module.emit_package(definition_v02(),existing,submission_id='existing')
            self.assertEqual((existing/'keep.txt').read_bytes(),b'preserved')

    def test_cli_creates_actual_json_artifacts_and_capability_snapshot(self):
        from application.cli import main
        from contextlib import redirect_stdout
        from io import StringIO
        import json
        with TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'definition.json';source.write_bytes(canonical_bytes(definition_v02()))
            output=StringIO()
            with redirect_stdout(output):
                code=main(['author-package','--definition',str(source),'--destination',str(root/'author-package'),
                           '--submission-id','cli-author','--dataset-profile','fixture-data'])
            self.assertEqual(code,0);self.assertEqual(json.loads(output.getvalue())['execution_evidence'],'NOT_RUN')
            self.assertTrue((root/'author-package/strategy.json').is_file());self.assertTrue((root/'author-package/manifest.json').is_file())
            output=StringIO()
            with redirect_stdout(output):code=main(['export-capabilities','--destination',str(root/'capabilities.json')])
            self.assertEqual(code,0)
            raw=(root/'capabilities.json').read_bytes();self.assertEqual(byte_hash(raw),json.loads(output.getvalue())['snapshot_hash'])
            self.assertEqual(json.loads(raw)['runtime_0_2_execution'],'IMPLEMENTED')
            self.assertTrue(all(v=='NOT_RUN' for v in json.loads(raw)['platform_verification'].values()))


if __name__=='__main__':unittest.main()
