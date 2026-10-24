import importlib.util,sqlite3,unittest
from pathlib import Path
from unittest.mock import patch


class CompactPrototypeTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('compact_prototype',Path(__file__).with_name('compact_fact_prototype.py'))
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.db=sqlite3.connect(':memory:');self.addCleanup(self.db.close)
        self.store=self.module.PrototypeStore(self.db,'C')

    def test_metadata_text_is_exact_not_semantic_normalization(self):
        values=['中文😀\x00','sha256:'+'a'*64,'pos_'+'f'*64,'2026-10-24T00:00:00Z',
            '2026-10-24T00:00:00.000Z','2026-10-24T00:00:00.000001+00:00','deadline:2026-10-24T00:00:00+00:00','0001-01-01T00:00:00Z','']
        for value in values:
            with self.subTest(value=value):self.assertEqual(self.store.text(self.store.atom(value)),value)

    def test_exact_payload_delta_and_keyframe_boundaries(self):
        last=None
        for revision in range(260):
            raw=(b'{"unchanged":"'+b'x'*2048+b'","clock":'+str(revision).encode()+b'}')
            last=self.store.payload(raw,'CANON:POSITION_PROJECTION',str(revision),'position-1')
            self.assertEqual(self.store.raw(last),raw)
        self.store.clear_cache();self.assertTrue(self.store.raw(last).endswith(b'259}'))
        self.assertLessEqual(self.db.execute('SELECT max(depth) FROM blobs').fetchone()[0],127)

    def test_missing_foreign_identity_and_corruption_refuse(self):
        value=self.store.payload(b'{"a":1}','CANON:POSITION_PROJECTION','p1','position-1')
        with self.assertRaises(ValueError):self.store.raw(99999)
        with self.assertRaises(ValueError):self.store.raw(value,expected=('CANON:POSITION_PROJECTION','wrong','position-1'))
        self.db.execute('UPDATE blobs SET raw_hash=? WHERE id=?',(bytes(32),value));self.store.clear_cache()
        with self.assertRaises(ValueError):self.store.raw(value)

    def test_outcome_shares_exact_payload_bytes_without_creating_membership(self):
        raw=b'{"effects":[{"kind":"POSITION_PROJECTION","payload":{"lifecycle_projection_id":"p1","position_id":"position-1","text":"\\u4e2d"}}],"reason_codes":[],"status":"HOLD"}'
        # Noncanonical escaping must remain exact even if no span sharing applies.
        value=self.store.payload(raw,'OUTCOME','op-1','run-1');self.assertEqual(self.store.raw(value),raw)
        self.assertEqual(self.db.execute("SELECT count(*) FROM sqlite_master WHERE name='paper_position_lifecycle_projections'").fetchone()[0],0)

    def test_payload_bound_and_delta_parent_cycle_refuse(self):
        with self.assertRaises(ValueError):self.store.payload(b'x'*(self.module.MAX_PAYLOAD+1),'K','I','L')
        first=self.store.payload(b'a'*2000+b'1','CANON:POSITION_PROJECTION','p1','P')
        value=self.store.payload(b'a'*2000+b'2','CANON:POSITION_PROJECTION','p2','P')
        self.db.execute('UPDATE blobs SET mode=2,previous=id,depth=1 WHERE id=?',(value,));self.store.clear_cache()
        with self.assertRaises(ValueError):self.store.raw(value)

    def test_encoded_atom_candidate_d_keeps_precise_original_text_without_lexical_copy(self):
        with sqlite3.connect(':memory:') as db:
            store=self.module.PrototypeStore(db,'D')
            for text in ('中文😀\x00','sha256:'+'a'*64,'0001-01-01T00:00:00Z','2026-10-24T00:00:00.000Z','2026-10-24T00:00:00Z'):
                self.assertEqual(store.text(store.atom(text)),text)
            self.assertEqual([r[1] for r in db.execute('PRAGMA table_info(atoms)')],['id','encoded'])

    def test_oversized_template_child_refuses_before_decoding_or_accumulating_child_bytes(self):
        child=self.store.payload(b'x'*100,'CANON:POSITION_PROJECTION','p1','P')
        parent=self.store.payload(b'X','OUTCOME','op','run')
        u=self.module.uvar
        data=u(1)+u(0)+u(child)+b''.join(u(self.store.atom(s)) for s in ('CANON:POSITION_PROJECTION','p1','P'))+self.module.sha(b'x'*100)+u(0)
        self.db.execute('UPDATE blobs SET mode=3,data=? WHERE id=?',(data,parent));self.store.clear_cache()
        original=self.store.raw
        with patch.object(self.store,'raw',wraps=original) as read:
            with self.assertRaises(ValueError):original(parent)
            self.assertEqual(read.call_count,0,'Oversized child materialized before enclosing byte budget refusal')


if __name__=='__main__':unittest.main()
