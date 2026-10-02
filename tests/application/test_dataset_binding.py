import importlib
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tests.application.dataset_fixtures import dataset,save_manifest,split_policy,START

class DatasetBindingTests(unittest.TestCase):
    def test_public_versioned_schemas_accept_bindings_and_reject_wrong_units_or_external_pass(self):
        import copy,json,jsonschema
        contracts=Path(__file__).resolve().parents[2]/'contracts'
        schemas={}
        for name in ('dataset_profile_v0_2','split_policy_v0_2','replay_cost_policy_v0_2','split_plan_v0_2'):
            path=contracts/(name+'.schema.json')
            self.assertTrue(path.is_file(),'Missing versioned schema '+name)
            schemas[name]=jsonschema.Draft202012Validator(json.loads(path.read_text()))
        from tests.application.test_research_pipeline import configured
        api=self.api()
        from application.datasets.split_plan import resolve_split
        with TemporaryDirectory() as root:
            configured(root)
            for name,relative in (('dataset_profile_v0_2','dataset.json'),('split_policy_v0_2','split.json'),('replay_cost_policy_v0_2','cost.json')):
                value=json.loads((Path(root)/relative).read_text()); schemas[name].validate(value)
                forged=copy.deepcopy(value); forged['decision']='PASS'
                self.assertTrue(list(schemas[name].iter_errors(forged)))
            manifest=json.loads((Path(root)/'dataset.json').read_text()); manifest['units']['quantity']='CONTRACTS'
            self.assertTrue(list(schemas['dataset_profile_v0_2'].iter_errors(manifest)))
            split=resolve_split(self.resolve(api,root),split_policy())
            self.assertTrue(hasattr(split,'to_dict'),'Missing immutable split plan interchange')
            schemas['split_plan_v0_2'].validate(split.to_dict())

    def test_parquet_numeric_schema_and_oversized_row_group_fail_before_record_decode(self):
        api=self.api()
        import pyarrow as pa
        import pyarrow.parquet as pq
        from tests.application.dataset_fixtures import candle_schema,hashed
        for kind in ('float','row_group'):
            with self.subTest(kind=kind),TemporaryDirectory() as root:
                m=dataset(root); path=Path(root)/'candles.parquet'
                if kind=='float':
                    schema=candle_schema(); table=pq.read_table(path)
                    index=schema.get_field_index('open'); table=table.set_column(index,pa.field('open',pa.float64(),False),table.column(index).cast(pa.float64()))
                    pq.write_table(table,path,row_group_size=4)
                else:
                    # Keep the decoder bound meaningful even for compressed input.
                    table=pq.read_table(path); table=pa.concat_tables([table]*751)
                    pq.write_table(table,path,row_group_size=9012)
                    m['candles'][0]['rows']=m['candles'][0]['finalized_rows']=9012
                m['candles'][0]['byte_hash']=hashed(path.read_bytes()); save_manifest(root,m)
                with self.assertRaises(api.DatasetError) as caught: self.resolve(api,root)
                self.assertEqual('PARQUET_SCHEMA_MISMATCH' if kind=='float' else 'PARQUET_ROW_GROUP_LIMIT',caught.exception.code)

    def test_late_receipt_and_missing_recorded_funding_coverage_are_not_silently_repaired(self):
        api=self.api()
        import pyarrow.parquet as pq
        from tests.application.dataset_fixtures import hashed
        with TemporaryDirectory() as root:
            dataset(root,mutate=lambda rows:rows[3].update(received_at=START+timedelta(hours=13)))
            with self.assertRaises(api.DatasetError) as caught: self.resolve(api,root)
            self.assertEqual('DATA_OUTSIDE_INFORMATION_CUTOFF',caught.exception.code)
        with TemporaryDirectory() as root:
            m=dataset(root); path=Path(root)/'funding.parquet'; table=pq.read_table(path).slice(0,1); pq.write_table(table,path)
            m['funding']['rows']=1; m['funding']['byte_hash']=hashed(path.read_bytes()); save_manifest(root,m)
            with self.assertRaises(api.DatasetError) as caught: self.resolve(api,root)
            self.assertEqual('MISSING_FUNDING_COVERAGE',caught.exception.code)

    def api(self):
        try: return importlib.import_module('application.datasets.resolver')
        except ModuleNotFoundError: self.fail('Missing pinned E1 dataset resolver')

    def resolve(self,api,root):
        from application.datasets.catalog import DatasetCatalog
        return api.DatasetResolver(DatasetCatalog(Path(root))).resolve('dataset.json')

    def test_container_encoding_changes_byte_identity_but_preserves_logical_identity(self):
        api=self.api()
        with TemporaryDirectory() as a,TemporaryDirectory() as b:
            dataset(a,compression='NONE'); dataset(b,compression='ZSTD',row_group_size=3)
            one,two=self.resolve(api,a),self.resolve(api,b)
            self.assertEqual(one.logical_hash,two.logical_hash)
            self.assertNotEqual(one.manifest_hash,two.manifest_hash)
            self.assertNotEqual(one.container_hashes,two.container_hashes)
            self.assertEqual(12,len(one.candles_by_timeframe['1h']))
            self.assertEqual('100',str(one.candles_by_timeframe['1h'][0].open))
            self.assertEqual('FIXTURE',one.namespace)

    def test_changed_container_cannot_reuse_prior_manifest_or_mutate_resolved_input(self):
        api=self.api()
        with TemporaryDirectory() as root:
            dataset(root); bound=self.resolve(api,root)
            p=Path(root)/'candles.parquet'; p.write_bytes(p.read_bytes()+b'x')
            with self.assertRaises(api.DatasetError) as caught: self.resolve(api,root)
            self.assertEqual('CONTAINER_HASH_MISMATCH',caught.exception.code)
            self.assertEqual(12,len(bound.candles_by_timeframe['1h']))
            with self.assertRaises(TypeError): bound.candles_by_timeframe['1h']=()

    def test_logical_hash_is_verified_independently_of_container_hash(self):
        api=self.api()
        with TemporaryDirectory() as root:
            m=dataset(root); m['candles'][0]['logical_hash']='sha256:'+'0'*64; save_manifest(root,m)
            with self.assertRaises(api.DatasetError) as caught: self.resolve(api,root)
            self.assertEqual('LOGICAL_HASH_MISMATCH',caught.exception.code)

    def test_gap_duplicate_unclosed_and_missing_arrival_fail_before_e2(self):
        api=self.api()
        for kind in ('gap','duplicate','unclosed','arrival'):
            with self.subTest(kind=kind),TemporaryDirectory() as root:
                def mutate(rows):
                    if kind=='gap': del rows[3]
                    if kind=='duplicate': rows[3]=rows[2].copy()
                    if kind=='unclosed': rows[3]['is_closed']=False
                    if kind=='arrival': rows[3]['received_at']=None
                dataset(root,mutate=mutate)
                with self.assertRaises(api.DatasetError): self.resolve(api,root)

    def test_missing_funding_is_explicit_blocker_never_factual_zero(self):
        api=self.api()
        with TemporaryDirectory() as root:
            m=dataset(root); m['funding']={'mode':'MISSING'}; save_manifest(root,m)
            bound=self.resolve(api,root)
            self.assertFalse(bound.promotion_data_ready)
            self.assertIn('MISSING_FUNDING',bound.reason_codes)
            self.assertIsNone(bound.funding_model)

    def test_wrong_units_unknown_fields_and_path_escape_rejected(self):
        api=self.api()
        for kind in ('units','field','path'):
            with self.subTest(kind=kind),TemporaryDirectory() as root:
                m=dataset(root)
                if kind=='units': m['units']['quantity']='CONTRACTS'
                if kind=='field': m['decision']='PASS'
                if kind=='path': m['candles'][0]['path']='../outside.parquet'
                save_manifest(root,m)
                with self.assertRaises(api.DatasetError): self.resolve(api,root)

    def test_split_is_frozen_sealed_and_has_feature_only_warmup(self):
        api=self.api()
        from application.datasets.split_plan import resolve_split
        with TemporaryDirectory() as root:
            dataset(root); bound=self.resolve(api,root); policy=split_policy()
            split=resolve_split(bound,policy)
            policy['development']['end']=policy['sealed_oos']['end']
            self.assertEqual(START+timedelta(hours=8),split.development.end)
            self.assertEqual(START+timedelta(hours=8),split.sealed_oos.start)
            self.assertEqual(START+timedelta(hours=2),split.development.warmup_start)
            self.assertEqual(START+timedelta(hours=5),split.development.entry_start)
            self.assertEqual(START+timedelta(hours=7),split.development.entry_end)
            self.assertTrue(split.sealed_oos.sealed)
            self.assertTrue(split.policy_hash.startswith('sha256:'))

    def test_overlap_unbounded_horizon_and_unspecified_embargo_block_protocol(self):
        api=self.api()
        from application.datasets.split_plan import resolve_split
        for kind in ('overlap','horizon','embargo'):
            with self.subTest(kind=kind),TemporaryDirectory() as root:
                dataset(root); bound=self.resolve(api,root); policy=split_policy()
                if kind=='overlap': policy['development']['start']=policy['training']['start']
                if kind=='horizon': policy['max_holding_seconds']=None
                if kind=='embargo': del policy['embargo_seconds']
                with self.assertRaises(api.DatasetError): resolve_split(bound,policy)
