"""ONE intrinsic actual EXIT decision-corruption case.

Three mutations forward genuine owner JSON to the real stage writer. No mocked
validation result, raw financial/terminal SQL, anchor hash mutation or new POST.
"""
from copy import deepcopy
from datetime import datetime,timedelta
import json
import unittest
from unittest.mock import patch

from position.close import DEFAULT_EXIT_REASON_CODES
from position.lifecycle_execution_binding import LifecycleExecutionBindingError
from storage.product_dispatch import ProductDispatchError,_stamp
from tests.product import h01_original_exit_fixture as original_fixtures
from tests.product import h01_exit_failure_fixtures as helpers


class TradingExitDecisionCorruptionV02Tests(unittest.TestCase):
    def test_real_stage_rejects_changed_reason_clock_and_genuine_foreign_projection_binding_without_effect(self):
        with original_fixtures.H01OriginalExitFixture(self) as c:
            f=c.f;entry_id=c.entry_decision.decision_id
            anchor,arguments=helpers.at_original_deadline(c)
            baseline_graph=c.assert_binding()
            baseline_rows=helpers.exit_rows(f.dispatch,c.service.run_id,entry_id)
            baseline_calls=tuple(c.provider.calls)
            self.assertEqual('OPEN_PROTECTED',baseline_graph.current_position_projection.payload['lifecycle_state'])
            self.assertNotEqual(c.first_binding.payload['lifecycle_projection_id'],
                baseline_graph.current_position_projection.canonical_id)
            self.assertEqual((),baseline_rows['product_exit_decisions'])
            original_stage=f.dispatch.stage_exit_decision

            def change_only_reason(value):
                self.assertEqual(['E5_MAX_HOLD_REACHED'],value['position_action']['reason_codes'])
                value['position_action']['reason_codes']=list(DEFAULT_EXIT_REASON_CODES)

            def change_only_interpretation_clock(value):
                value['interpreted_at']=_stamp(datetime.fromisoformat(
                    value['interpreted_at'].replace('Z','+00:00'))+timedelta(seconds=1))

            def substitute_genuine_earlier_binding(value):
                value['source_binding']=deepcopy(c.first_binding.payload)

            vectors=(
                ('reason-only',change_only_reason,ProductDispatchError,'EXIT_ORIGINAL_AUTHORIZED_ACTION_REQUIRED'),
                # obj.effects reinterprets E5 before stage checks future clock:
                # +1sec changes real E5 created_at/action ID, so mismatch wins.
                ('clock-only',change_only_interpretation_clock,ProductDispatchError,'EXIT_ORIGINAL_AUTHORIZED_ACTION_REQUIRED'),
                ('earlier-real-binding',substitute_genuine_earlier_binding,LifecycleExecutionBindingError,
                 'BINDING_PROJECTION_ID_MISMATCH'))
            for label,mutate,error_type,expected_code in vectors:
                forwarded=[]
                def forward_corrupted_real_evidence(run_id,original_entry_id,evidence_json,*,lease,now):
                    genuine=json.loads(evidence_json)
                    self.assertEqual(entry_id,original_entry_id)
                    self.assertEqual(c.service.run_id,run_id)
                    self.assertEqual(baseline_graph.current_position_projection.payload,genuine['source_position'])
                    self.assertEqual(baseline_graph.current_lifecycle_execution_binding.payload,genuine['source_binding'])
                    self.assertEqual(['E5_MAX_HOLD_REACHED'],genuine['position_action']['reason_codes'])
                    changed=deepcopy(genuine)
                    mutate(changed)
                    if label=='reason-only':
                        self.assertEqual(genuine['position_action']['position_action_id'],changed['position_action']['position_action_id'])
                        restored=deepcopy(changed)
                        restored['position_action']['reason_codes']=genuine['position_action']['reason_codes']
                        self.assertEqual(genuine,restored)
                    elif label=='clock-only':
                        self.assertEqual(genuine['position_action'],changed['position_action'])
                        self.assertEqual(_stamp(now+timedelta(seconds=1)),changed['interpreted_at'])
                        restored=deepcopy(changed);restored['interpreted_at']=genuine['interpreted_at']
                        self.assertEqual(genuine,restored)
                    else:
                        self.assertEqual(c.first_binding.payload,changed['source_binding'])
                        self.assertEqual(genuine['source_position'],changed['source_position'])
                        restored=deepcopy(changed);restored['source_binding']=genuine['source_binding']
                        self.assertEqual(genuine,restored)
                    forwarded.append(genuine)
                    # Real stage recomputes hashes and executes its actual E5/
                    # binding validators. This wrapper supplies no result/PASS.
                    return original_stage(run_id,original_entry_id,json.dumps(changed,sort_keys=True,
                        separators=(',',':'),ensure_ascii=False,allow_nan=False),lease=lease,now=now)
                with self.subTest(vector=label):
                    with patch.object(f.dispatch,'stage_exit_decision',side_effect=forward_corrupted_real_evidence):
                        with self.assertRaises(error_type) as caught:
                            c.runner.evaluate_original_exit(f.bundle.boundary,**arguments)
                    self.assertEqual(expected_code,caught.exception.code)
                    self.assertEqual(1,len(forwarded),'Each vector must reach actual normal staging boundary')
                    self.assertIsNone(f.dispatch.exit_decision(c.service.run_id,entry_id))
                    self.assertEqual((),f.dispatch.pending_exit_publications(c.service.run_id))
                    self.assertIsNone(f.dispatch.operation(c.service.run_id,forwarded[0]['operation_id']))
                    self.assertEqual(anchor,f.dispatch.exit_anchor(c.service.run_id,entry_id))
                    self.assertEqual(baseline_rows,helpers.exit_rows(f.dispatch,c.service.run_id,entry_id))
                    self.assertEqual(baseline_graph,c.assert_binding())
                    self.assertEqual(baseline_calls,tuple(c.provider.calls))
                    self.assertFalse(any(row.payload.get('action')=='EXIT' for row in c.recover().position_actions))
                    self.assertEqual(c.entry_decision,f.dispatch.entry_decision(c.service.run_id,
                        f.authority.identity,f.bundle.boundary))
            self.assertEqual(2,len([row for row in c.provider.calls if row['method']=='POST']))
            self.assertFalse(c.provider._responses)
