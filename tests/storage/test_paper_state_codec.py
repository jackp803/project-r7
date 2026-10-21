"""Lossless physical codec only; no DB, financial authority or provider calls."""
import base64
from copy import deepcopy
import hashlib
import importlib
import json
import random
import unittest
from unittest.mock import patch
import zlib


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(raw):return 'sha256:'+hashlib.sha256(raw.encode()).hexdigest()


class PaperStateCodecTests(unittest.TestCase):
    def codec(self):
        self.assertIsNotNone(importlib.util.find_spec('storage.paper_state_codec'),
            'Versioned lossless E6 physical checkpoint codec is not implemented')
        return importlib.import_module('storage.paper_state_codec')

    def populated(self):
        return dict(runtime=dict(clock=0,bars=[dict(at=i,price=str(60000+i),
            raw=hashlib.sha256(str(i).encode()).hexdigest()) for i in range(200)]),
            broker=dict(state='FLAT',quantity='0.000',flags=[False,0,True,1,None,'繁體中文']))

    def encode(self,value,revision=0,previous=None,run='run-1'):
        return self.codec().encode_state(canonical(value),run_id=run,revision=revision,
            previous_raw=None if previous is None else canonical(previous))

    def decode(self,encoded,value,revision=0,rows=None,run='run-1'):
        def read(previous):return rows[previous]
        return self.codec().decode_state(encoded,run_id=run,revision=revision,
            expected_hash=digest(canonical(value)),read_previous=read)

    def changed_payload(self,encoded,value):
        envelope=json.loads(encoded);raw=canonical(value).encode()
        envelope.update(payload_bytes=len(raw),payload_hash='sha256:'+hashlib.sha256(raw).hexdigest(),
            data=base64.b64encode(zlib.compress(raw,1)).decode())
        return canonical(envelope)

    def test_keyframe_exact_unicode_raw_and_semantic_hash(self):
        value=self.populated();encoded=self.encode(value)
        self.assertEqual(json.loads(encoded)['kind'],'KEYFRAME')
        self.assertEqual(self.decode(encoded,value),canonical(value))

    def test_delta_exact_nested_deletion_array_roll_and_type_distinctions(self):
        previous=self.populated();original=deepcopy(previous);value=deepcopy(previous)
        value['runtime']['clock']=1
        del value['broker']['state'];value['broker']['flags']=[0,False,1,True,{},[],None]
        zero=self.encode(previous);one=self.encode(value,1,previous)
        self.assertEqual(json.loads(one)['kind'],'DELTA')
        self.assertEqual(self.decode(one,value,1,{0:(zero,digest(canonical(previous)))}),canonical(value))
        rolled=deepcopy(value);rolled['runtime']['bars']=rolled['runtime']['bars'][1:]+[{'at':200,'price':'60200'}]
        two=self.encode(rolled,2,value)
        self.assertEqual(self.decode(two,rolled,2,{0:(zero,digest(canonical(previous))),1:(one,digest(canonical(value)))}),canonical(rolled))
        self.assertEqual(previous,original)

    def test_unchanged_state_uses_small_delta_without_type_coercion(self):
        value=self.populated();zero=self.encode(value);one=self.encode(value,1,value)
        self.assertLess(len(one),len(zero)//2)
        self.assertEqual(self.decode(one,value,1,{0:(zero,digest(canonical(value)))}),canonical(value))
        altered=deepcopy(value);altered['broker']['flags'][0]=0
        two=self.encode(altered,2,value)
        self.assertEqual(self.decode(two,altered,2,{0:(zero,digest(canonical(value))),1:(one,digest(canonical(value)))}),canonical(altered))

    def test_128_boundary_is_keyframe_and_chain_is_bounded(self):
        value=self.populated();rows={};previous=None;calls=[]
        for revision in range(129):
            encoded=self.encode(value,revision,previous);rows[revision]=(encoded,digest(canonical(value)));previous=deepcopy(value)
            value['runtime']['clock']+=1
        self.assertEqual(json.loads(rows[128][0])['kind'],'KEYFRAME')
        value['runtime']['clock']=127
        decoded=self.codec().decode_state(rows[127][0],run_id='run-1',revision=127,
            expected_hash=digest(canonical(value)),read_previous=lambda r:(calls.append(r) or rows[r]))
        self.assertEqual(decoded,canonical(value));self.assertEqual(len(calls),127)

    def test_smaller_keyframe_can_replace_inefficient_delta(self):
        old=self.populated();value={'runtime':{},'broker':{}}
        encoded=self.encode(value,1,old)
        self.assertEqual(json.loads(encoded)['kind'],'KEYFRAME')
        self.assertEqual(self.decode(encoded,value,1),canonical(value))

    def test_wrong_run_revision_hash_or_base_is_refused(self):
        value=self.populated();zero=self.encode(value);value['runtime']['clock']=1
        one=self.encode(value,1,self.populated());original=json.loads(one)
        mutations=[('run_id','other'),('revision',True),('revision',2),('base_revision',True),
            ('base_revision',1),('base_hash','sha256:'+'0'*64),('codec','future-v99')]
        for key,item in mutations:
            with self.subTest(key=key,item=item):
                altered=dict(original);altered[key]=item
                with self.assertRaisesRegex(ValueError,'PAPER_STATE_CODEC_'):
                    self.decode(canonical(altered),value,1,{0:(zero,digest(canonical(self.populated())))})
        with self.assertRaisesRegex(ValueError,'PAPER_STATE_CODEC_'):
            self.codec().decode_state(one,run_id='run-1',revision=1,expected_hash='sha256:'+'0'*64,
                read_previous=lambda r:(zero,digest(canonical(self.populated()))))

    def test_missing_or_foreign_predecessor_cannot_supply_state(self):
        value=self.populated();encoded=self.encode(value,1,value)
        for rows in ({},{0:(self.encode(value,run='foreign'),digest(canonical(value)))},
                     {0:(encoded,digest(canonical(value)))}):
            with self.subTest(rows=len(rows)),self.assertRaisesRegex(ValueError,'PAPER_STATE_CODEC_'):
                self.decode(encoded,value,1,rows)

    def test_duplicate_noncanonical_or_float_logical_inputs_refused(self):
        for raw in ('{"a":1,"a":2}','{ "a":1}','{"a":1.0}','{"a":NaN}','{"a":Infinity}'):
            with self.subTest(raw=raw),self.assertRaisesRegex(ValueError,'PAPER_STATE_CODEC_'):
                self.codec().encode_state(raw,run_id='run-1',revision=0)

    def test_envelope_duplicate_fields_and_noncanonical_base64_refused(self):
        value=self.populated();encoded=self.encode(value);original=json.loads(encoded)
        invalid=[encoded[:-1]+',"kind":"KEYFRAME"}',encoded+' ',canonical(dict(original,data='%%%%')),
            canonical(dict(original,payload_bytes=True)),canonical(dict(original,extra='no'))]
        for raw in invalid:
            with self.subTest(raw=raw[:60]),self.assertRaisesRegex(ValueError,'PAPER_STATE_CODEC_'):
                self.decode(raw,value)

    def test_corrupt_trailing_or_truncated_compressed_stream_refused(self):
        value=self.populated();encoded=self.encode(value);original=json.loads(encoded)
        compressed=base64.b64decode(original['data'])
        for raw in (compressed[:-1],compressed+b'trailing',compressed[:-1]+bytes([compressed[-1]^1])):
            bad=dict(original,data=base64.b64encode(raw).decode())
            with self.subTest(size=len(raw)),self.assertRaisesRegex(ValueError,'PAPER_STATE_CODEC_'):
                self.decode(canonical(bad),value)

    def test_expansion_and_declared_payload_bounds_are_checked_before_large_allocation(self):
        codec=self.codec();value=self.populated();encoded=self.encode(value)
        original=json.loads(encoded);payload=zlib.decompress(base64.b64decode(original['data']))
        original['payload_bytes']=10
        with self.assertRaisesRegex(ValueError,'PAPER_STATE_CODEC_'):
            self.decode(canonical(original),value)
        with patch.object(codec,'MAX_PAYLOAD',len(payload)-1),self.assertRaisesRegex(ValueError,'PAPER_STATE_CODEC_'):
            self.decode(encoded,value)

    def test_hostile_patch_shapes_and_boolean_splice_counts_are_refused(self):
        previous=self.populated();zero=self.encode(previous);value=deepcopy(previous);value['runtime']['clock']=1
        one=self.encode(value,1,previous);rows={0:(zero,digest(canonical(previous)))}
        for bad in ({'op':'unknown'},{'op':'object','remove':['runtime','runtime'],'set':{}},
                    {'op':'array','prefix':False,'remove':0,'suffix':0,'insert':[]},
                    {'op':'replace','value':value,'extra':1}):
            with self.subTest(patch=bad['op']),self.assertRaisesRegex(ValueError,'PAPER_STATE_CODEC_'):
                self.decode(self.changed_payload(one,bad),value,1,rows)

    def test_boundary_delta_and_invalid_api_types_cannot_bypass_profile(self):
        value=self.populated();encoded=json.loads(self.encode(value,1,value))
        encoded.update(revision=128,base_revision=127)
        with self.assertRaisesRegex(ValueError,'PAPER_STATE_CODEC_'):
            self.decode(canonical(encoded),value,128,{})
        for revision in (False,-1,2**63):
            with self.subTest(revision=revision),self.assertRaisesRegex(ValueError,'PAPER_STATE_CODEC_'):
                self.codec().encode_state(canonical(value),run_id='run-1',revision=revision)

    def test_aggregate_decoding_chain_bytes_are_bounded_not_only_each_payload(self):
        codec=self.codec();value=self.populated();zero=self.encode(value);one=self.encode(value,1,value)
        size=sum(json.loads(encoded)['payload_bytes'] for encoded in (zero,one))
        with patch.object(codec,'MAX_CHAIN_BYTES',size-1,create=True),self.assertRaisesRegex(ValueError,'PAPER_STATE_CODEC_'):
            self.decode(one,value,1,{0:(zero,digest(canonical(value)))})

    def test_large_delta_uses_early_keyframe_to_keep_all_generated_chains_within_budget(self):
        codec=self.codec();previous=self.populated();value=deepcopy(previous);value['runtime']['clock']=1
        with patch.object(codec,'MAX_DELTA_PAYLOAD',64,create=True):
            encoded=self.encode(value,1,previous)
        self.assertEqual(json.loads(encoded)['kind'],'KEYFRAME')
        self.assertEqual(self.decode(encoded,value,1),canonical(value))

    def test_reproducible_mixed_changes_preserve_every_logical_revision(self):
        rng=random.Random(20261021);value=self.populated();rows={};previous=None
        for revision in range(260):
            value['runtime']['clock']=revision
            value['broker']['flags']=[rng.choice((None,False,0,True,1,'0.001')),{'中文':revision}]
            if revision%7==0:value['runtime']['bars']=value['runtime']['bars'][1:]+[{'at':revision,'price':str(60000+revision)}]
            if revision%5==0:value['runtime']['optional']=[revision,[],{'empty':{}}]
            else:value['runtime'].pop('optional',None)
            encoded=self.encode(value,revision,previous);rows[revision]=(encoded,digest(canonical(value)))
            self.assertEqual(self.decode(encoded,value,revision,rows),canonical(value))
            previous=deepcopy(value)

    def test_write_roundtrip_checks_exact_result_against_already_verified_logical_base(self):
        codec=self.codec()
        self.assertTrue(callable(getattr(codec,'verify_write_state',None)),
            'Codec lacks a bounded write-roundtrip check using the owner-verified predecessor')
        old=self.populated();value=deepcopy(old);value['runtime']['clock']=1
        for revision,previous in ((0,None),(1,old)):
            encoded=self.encode(value,revision,previous)
            actual=codec.verify_write_state(encoded,run_id='run-1',revision=revision,
                expected_hash=digest(canonical(value)),previous_raw=None if previous is None else canonical(previous))
            self.assertEqual(actual,canonical(value))

    def test_write_roundtrip_rejects_wrong_semantic_result_or_wrong_base(self):
        codec=self.codec()
        self.assertTrue(callable(getattr(codec,'verify_write_state',None)),
            'Codec write-roundtrip validation is not implemented')
        old=self.populated();value=deepcopy(old);value['runtime']['clock']=1
        encoded=self.encode(value,1,old)
        for expected,base in ((digest(canonical(old)),canonical(old)),(digest(canonical(value)),canonical(value)),
                              (digest(canonical(value)),None)):
            with self.subTest(expected=expected,base_missing=base is None),self.assertRaisesRegex(ValueError,'PAPER_STATE_CODEC_'):
                codec.verify_write_state(encoded,run_id='run-1',revision=1,expected_hash=expected,previous_raw=base)


if __name__=='__main__':unittest.main()
