"""Source-owned codec continuation data; never runtime/audit permission."""
from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch

from storage import paper_state_codec as codec
from tests.storage import test_paper_state_codec as fixture


class PaperCodecReadRecordTests(unittest.TestCase):
    def setUp(self):
        for name in ('decode_state_record','extend_state_record'):
            self.assertTrue(callable(getattr(codec,name,None)),'Verified codec read record missing: '+name)
        self.helper=fixture.PaperStateCodecTests()

    def first(self,value):
        encoded=self.helper.encode(value)
        return codec.decode_state_record(encoded,run_id='run-1',revision=0,
            expected_hash=fixture.digest(fixture.canonical(value)),read_previous=lambda at:None)

    def test_each_original_physical_link_checked_once_with_exact_bytes_and_original_chain_limits(self):
        value=self.helper.populated();record=self.first(value);rows={0:(self.helper.encode(value),fixture.digest(fixture.canonical(value)))}
        budget=json.loads(rows[0][0])['payload_bytes']
        for revision in range(1,260):
            previous=deepcopy(value);value['runtime']['clock']=revision
            encoded=self.helper.encode(value,revision,previous);envelope=json.loads(encoded)
            budget=envelope['payload_bytes'] if envelope['kind']=='KEYFRAME' else budget+envelope['payload_bytes']
            with patch.object(codec,'_unpack',wraps=codec._unpack) as unpack:
                record=codec.extend_state_record(encoded,run_id='run-1',revision=revision,
                    expected_hash=fixture.digest(fixture.canonical(value)),previous=record)
                self.assertEqual(unpack.call_count,1)
            self.assertEqual(record.state_json,fixture.canonical(value))
            self.assertEqual(record.chain_payload_bytes,budget)
            self.assertEqual(record.chain_links,revision%128+1)
            rows[revision]=(encoded,fixture.digest(record.state_json))
        self.assertEqual(codec.decode_state(rows[259][0],run_id='run-1',revision=259,
            expected_hash=rows[259][1],read_previous=lambda at:rows[at]),record.state_json)

    def test_foreign_missing_or_nonadjacent_record_never_supplies_a_base(self):
        value=self.helper.populated();record=self.first(value);changed=deepcopy(value);changed['runtime']['clock']=1
        one=self.helper.encode(changed,1,value)
        for previous in (None,{},record.state_json):
            with self.subTest(previous_type=type(previous).__name__),self.assertRaises(ValueError):
                codec.extend_state_record(one,run_id='run-1',revision=1,
                    expected_hash=fixture.digest(fixture.canonical(changed)),previous=previous)
        for run,revision in (('foreign',1),('run-1',2)):
            with self.subTest(run=run,revision=revision),self.assertRaises(ValueError):
                codec.extend_state_record(one,run_id=run,revision=revision,
                    expected_hash=fixture.digest(fixture.canonical(changed)),previous=record)

    def test_accumulated_budget_and_wrong_full_hash_still_refuse(self):
        value=self.helper.populated();record=self.first(value);changed=deepcopy(value);changed['runtime']['clock']=1
        one=self.helper.encode(changed,1,value);size=json.loads(one)['payload_bytes']
        with patch.object(codec,'MAX_CHAIN_BYTES',record.chain_payload_bytes+size-1),self.assertRaises(ValueError):
            codec.extend_state_record(one,run_id='run-1',revision=1,
                expected_hash=fixture.digest(fixture.canonical(changed)),previous=record)
        with self.assertRaises(ValueError):codec.extend_state_record(one,run_id='run-1',revision=1,
            expected_hash='sha256:'+'0'*64,previous=record)

    def test_standalone_reader_still_needs_every_original_ancestor_and_record_is_not_json_proof(self):
        value=self.helper.populated();record=self.first(value);changed=deepcopy(value);changed['runtime']['clock']=1
        one=self.helper.encode(changed,1,value)
        codec.extend_state_record(one,run_id='run-1',revision=1,
            expected_hash=fixture.digest(fixture.canonical(changed)),previous=record)
        with self.assertRaises(ValueError):codec.decode_state(one,run_id='run-1',revision=1,
            expected_hash=fixture.digest(fixture.canonical(changed)),read_previous=lambda at:None)
        with self.assertRaises(TypeError):json.dumps(record)

    def test_keyframe_continuation_enforces_the_same_total_payload_budget(self):
        value=self.helper.populated();encoded=self.helper.encode(value)
        size=json.loads(encoded)['payload_bytes']
        with patch.object(codec,'MAX_CHAIN_BYTES',size-1):
            with self.assertRaises(ValueError):codec.decode_state_record(encoded,run_id='run-1',revision=0,
                expected_hash=fixture.digest(fixture.canonical(value)),read_previous=lambda at:None)
            with self.assertRaises(ValueError):codec.extend_state_record(encoded,run_id='run-1',revision=0,
                expected_hash=fixture.digest(fixture.canonical(value)),previous=None)


if __name__=='__main__':unittest.main()
