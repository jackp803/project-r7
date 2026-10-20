"""Unapplied existing CLOUD-10 authored-example contract checks."""
import json
from prepare_strategy_test_drafts import draft

methods='''    def test_shipped_four_hour_example_has_ema_adx_atr_and_roundtrips_actual_authoring(self):
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

'''

if __name__=='__main__':
    row=draft('tests/application/test_authoring_roundtrip.py','    def module(self):\n',methods)
    print(json.dumps(row))
