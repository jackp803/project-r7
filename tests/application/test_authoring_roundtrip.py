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
    def test_shipped_unsupported_feature_example_retains_actual_typed_gap_receipt(self):
        import json
        from strategy import compute_content_hash
        example=Path(__file__).resolve().parents[2]/'docs/strategy/authoring-v0.2/examples/unsupported-feature'
        definition=json.loads((example/'strategy.json').read_bytes())
        receipt=json.loads((example/'gap_receipt.json').read_bytes())
        self.assertEqual(definition['content_hash'],compute_content_hash(definition))
        with TemporaryDirectory() as temporary:
            destination=Path(temporary)/'rejected'
            with self.assertRaises(self.module().AuthoringError) as caught:
                self.module().emit_package(definition,destination,submission_id='shipped-unsupported-feature')
            self.assertEqual(caught.exception.code,'CAPABILITY_GAP')
            self.assertEqual(receipt,dict(code=caught.exception.code,gaps=list(caught.exception.gaps)))
            self.assertTrue(any(row['reason']=='UNSUPPORTED_FEATURE' for row in receipt['gaps']))
            self.assertFalse(destination.exists())

    def test_shipped_four_hour_example_has_ema_adx_atr_and_roundtrips_actual_authoring(self):
        import json
        from strategy import compute_content_hash,parse_strategy_definition
        example=Path(__file__).resolve().parents[2]/'docs/strategy/authoring-v0.2/examples/four-hour/strategy.json'
        definition=json.loads(example.read_bytes())
        self.assertEqual(definition['content_hash'],compute_content_hash(definition))
        parsed=parse_strategy_definition(definition)
        self.assertEqual(parsed.evaluation_timeframe,'4h')
        self.assertEqual(set(definition['required_timeframes']),{'4h'})
        indicators={row['name'] for row in definition['rules']['features'].values() if row['kind']=='indicator'}
        self.assertTrue({'EMA','ADX','ATR'}<=indicators)
        with TemporaryDirectory() as temporary:
            target=Path(temporary)/'four-hour'
            result=self.module().emit_package(definition,target,submission_id='authored-four-hour')
            emitted=parse_strategy_definition((target/'strategy.json').read_bytes())
            self.assertEqual(emitted.content_hash,parsed.content_hash)
            self.assertEqual(result['execution_evidence'],'NOT_RUN')
            self.assertEqual(result['financial_authority'],'NONE')

    def test_shipped_multitimeframe_example_has_four_hour_direction_and_fifteen_minute_donchian(self):
        import json
        from strategy import compute_content_hash,parse_strategy_definition
        example=Path(__file__).resolve().parents[2]/'docs/strategy/authoring-v0.2/examples/multitimeframe/strategy.json'
        definition=json.loads(example.read_bytes())
        self.assertEqual(definition['content_hash'],compute_content_hash(definition))
        parsed=parse_strategy_definition(definition)
        self.assertEqual(set(definition['required_timeframes']),{'15m','4h'})
        self.assertEqual(parsed.evaluation_timeframe,'15m')
        indicators=[row for row in definition['rules']['features'].values() if row['kind']=='indicator']
        self.assertTrue(any(row['name']=='EMA' and row.get('source',{}).get('timeframe')=='4h' for row in indicators))
        channels=[row for row in indicators if row['name']=='DONCHIAN']
        self.assertTrue(channels)
        self.assertTrue(all(row['timeframe']=='15m' and row['parameters'].get('lag_bars',1)==1 for row in channels))
        with TemporaryDirectory() as temporary:
            target=Path(temporary)/'multitimeframe'
            result=self.module().emit_package(definition,target,submission_id='authored-multitimeframe')
            emitted=parse_strategy_definition((target/'strategy.json').read_bytes())
            self.assertEqual(emitted.content_hash,parsed.content_hash)
            self.assertEqual(result['execution_evidence'],'NOT_RUN')

    def test_unsupported_authoring_returns_distinct_source_bound_capability_gaps(self):
        module=self.module()
        for field,value,reason,requested in (('name','UNAVAILABLE_FEATURE','UNSUPPORTED_FEATURE','r7-ema-v1'),
            ('semantic_version','r7-ema-v99','UNSUPPORTED_VERSION','r7-ema-v99')):
            with self.subTest(field=field),TemporaryDirectory() as temporary:
                definition=definition_v02()
                definition['rules']['features']['trend'][field]=value
                destination=Path(temporary)/'unsupported'
                with self.assertRaises(module.AuthoringError) as caught:
                    module.emit_package(definition,destination,submission_id='unsupported')
                self.assertEqual(caught.exception.code,'CAPABILITY_GAP')
                gaps=[row for row in caught.exception.gaps if row['reason']==reason]
                self.assertEqual(len(gaps),1)
                gap=gaps[0]
                self.assertEqual(gap['requested_version'],requested)
                self.assertEqual(gap['source_location'],'/rules/features/trend')
                self.assertEqual(gap['capability_id'],'indicator:'+('UNAVAILABLE_FEATURE' if field=='name' else 'EMA'))
                self.assertEqual(gap['available_version'],None if field=='name' else 'r7-ema-v1')
                self.assertTrue(gap['reevaluation_conditions'])
                self.assertFalse(destination.exists())

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
