"""Wrong-subject/failed/escaping observations cannot issue scoped acceptance."""
from copy import deepcopy
from pathlib import Path
import json,unittest
from unittest.mock import patch
import review_bffc_semantic_clauses as helper
BASE=Path(__file__).resolve().parent
class SemanticAdmissionTests(unittest.TestCase):
 def setUp(self):
  self.row=json.loads((BASE/'portable-bffc558-first/checkpoint.json').read_bytes())
  self.smoke=json.loads((BASE/'portable-bffc558-first/first-run-smoke/native-smoke.json').read_bytes())
  self.facts=json.loads((BASE/'build-bffc558/build-result.json').read_bytes())['identity']
 def test_actual_current_portable_is_admitted(self):
  self.assertEqual(self.row,helper.require_current_portable(self.row,self.smoke,self.facts))
 def test_failed_or_wrong_subject_portable_refuses(self):
  for key,value in (('passed',False),('revision','0'*40),('source_unchanged',False),('copied_auth',True)):
   with self.subTest(key=key):
    value_row=deepcopy(self.row);value_row[key]=value
    with self.assertRaises(ValueError):helper.require_current_portable(value_row,self.smoke,self.facts)
 def test_wrong_identity_and_unreaped_smoke_refuse(self):
  for role in ('identity','cleanup'):
   with self.subTest(role=role):
    smoke=deepcopy(self.smoke)
    if role=='identity':smoke['identity']['build_hash']='sha256:'+'0'*64
    else:smoke['commands'][0]['tree_reaped']=False
    with self.assertRaises(ValueError):helper.require_current_portable(self.row,smoke,self.facts)
 def test_missing_or_reordered_http_inventory_refuses(self):
  for role in ('empty','short','route','status','reordered'):
   with self.subTest(role=role):
    smoke=deepcopy(self.smoke);rows=smoke['http_assertions']
    if role=='empty':smoke['http_assertions']=[]
    elif role=='short':rows.pop()
    elif role=='route':rows[0]['path']='/unknown'
    elif role=='status':rows[0].update(actual_status=204,expected_status=204)
    else:rows[0],rows[1]=rows[1],rows[0]
    with self.assertRaises(ValueError):helper.require_current_portable(self.row,smoke,self.facts)
 def test_duplicate_unknown_or_reordered_execution_inventory_refuses(self):
  for field in ('scenarios','commands'):
   for role in ('duplicate','unknown','reordered'):
    with self.subTest(field=field,role=role):
     smoke=deepcopy(self.smoke);rows=smoke[field]
     if role=='duplicate':rows[1]=deepcopy(rows[0])
     elif role=='unknown':rows[0]['name']='UNKNOWN'
     else:rows[0],rows[1]=rows[1],rows[0]
     with self.assertRaises(ValueError):helper.require_current_portable(self.row,smoke,self.facts)
 def test_self_declared_exit_code_cannot_override_producer(self):
  smoke=deepcopy(self.smoke);smoke['commands'][0].update(exit_code=2,expected_exit_code=2)
  with self.assertRaises(ValueError):helper.require_current_portable(self.row,smoke,self.facts)
 def test_actual_unit_command_retains_its_original_mixed_attempt_scope(self):
  rows=helper.read_frontend_unit_proof();self.assertEqual(18,len(rows))
  key='ui/src/api.test.ts::cannot send a product command to a remote URL or without a CSRF proof'
  self.assertFalse(rows[key]['parent_attempt_passed'])
  self.assertEqual('NONE',rows[key]['native_qualification_membership'])
 def test_changed_frontend_observation_refuses_before_any_source_read(self):
  with patch.object(helper,'capture',return_value=b'{}'),patch.object(helper,'artifact_bytes') as reader:
   with self.assertRaises(ValueError):helper.read_frontend_unit_proof()
   reader.assert_not_called()
 def test_actual_canonical_source_underscore_file_is_read_without_cloud_grammar(self):
  ref='src/application/__init__.py'
  self.assertEqual((helper.ROOT/ref).read_bytes(),helper.source_bytes(ref))
 def test_source_reader_denies_escape_and_noncanonical_alias_before_read(self):
  for ref in ('../private/key','C:/private/key','src/../key','src//key','src/./key','private/key'):
   with self.subTest(ref=ref),patch.object(helper,'source_reader',create=True) as reader:
    with self.assertRaises(ValueError):helper.source_bytes(ref)
    reader.assert_not_called()
 def test_source_reader_keeps_bound_and_single_link_protection(self):
  with patch.object(helper,'source_reader',return_value=b'public',create=True) as reader:
   self.assertEqual(b'public',helper.source_bytes('src/application/__init__.py'))
   reader.assert_called_once_with(helper.ROOT/'src/application/__init__.py',8*1024*1024,require_single_link=True)
 def test_exact_source_map_is_admitted_without_reading_source(self):
  values={'src/allowed.py':'sha256:'+'1'*64}
  with patch.object(helper,'artifact_bytes') as reader:
   self.assertEqual(values,helper.require_source_map(values,{'src/allowed.py'}));reader.assert_not_called()
 def test_escape_extra_missing_source_keys_refuse_before_any_read(self):
  examples=({}, {'../private/key':'sha256:'+'1'*64}, {'C:/private/key':'sha256:'+'1'*64},
   {'src/allowed.py':'sha256:'+'1'*64,'src/unexpected.py':'sha256:'+'2'*64})
  for mapping in examples:
   with self.subTest(keys=list(mapping)),patch.object(helper,'artifact_bytes') as reader:
    with self.assertRaises(ValueError):helper.require_source_map(mapping,{'src/allowed.py'})
    reader.assert_not_called()
 def test_oversized_public_document_refuses(self):
  with patch.object(helper,'artifact_bytes',side_effect=ValueError('ARTIFACT_SIZE_LIMIT')) as reader:
   with self.assertRaises(ValueError):helper.load(BASE/'oversized-public.json')
   reader.assert_called_once()
if __name__=='__main__':unittest.main(verbosity=2)
