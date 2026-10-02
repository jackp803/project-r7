import copy
from dataclasses import replace
from decimal import Decimal
import unittest
from tests.indicators.v02_fixtures import api,bars,spec


class IncrementalIndicatorTests(unittest.TestCase):
    def cases(self,module):
        for name in ('SMA','EMA','RSI','ATR','ADX'):
            for output in ('value','plus_di','minus_di') if name=='ADX' else ('value',):
                yield spec(module,name,output=output,window=3)
        for output in ('line','signal','histogram'):
            yield spec(module,'MACD',output=output,fast=2,slow=4,signal_window=3)
        for output in ('middle','upper','lower','stddev'):
            yield spec(module,'BOLLINGER',output=output,window=3,k='2')
        for output in ('upper','lower','middle'):
            yield spec(module,'DONCHIAN',output=output,window=3)

    def test_batch_and_actual_incremental_updates_match_each_prefix_all_outputs(self):
        module=api(self)
        rows=bars([10,11,10,12,9,8,11,15,16,14,14,18])
        for feature in self.cases(module):
            with self.subTest(name=feature.name,output=feature.output):
                state=module.new_feature_state(feature)
                for i,row in enumerate(rows):
                    actual=module.update_feature(state,row).observation
                    batch=module.evaluate_feature(feature,module.CandlePrefix(rows[:i+1]))
                    self.assertEqual(batch,actual)
                    self.assertEqual(i+1,state.count)
                    self.assertEqual(row.close_time,actual.source_boundary)

    def test_restart_snapshot_replay_binds_prefix_parameters_and_arithmetic(self):
        module=api(self)
        rows=bars([10,11,10,12,9,8,11,15,16,14,14,18])
        for feature in self.cases(module):
            state=module.new_feature_state(feature)
            for row in rows[:7]: module.update_feature(state,row)
            snapshot=module.snapshot_feature(state)
            restored=module.restore_feature(feature,module.CandlePrefix(rows[:7]),snapshot)
            self.assertEqual('VALIDATED_REPLAY',restored.recovery_reason)
            for row in rows[7:]:
                expected=module.update_feature(state,row).observation
                self.assertEqual(expected,module.update_feature(restored,row).observation)

    def test_modified_or_wrong_prefix_snapshot_is_recomputed(self):
        module=api(self)
        feature=spec(module,'EMA',window=3)
        rows=bars([1,2,3,4,5,6])
        state=module.new_feature_state(feature)
        for row in rows[:4]: module.update_feature(state,row)
        snapshot=module.snapshot_feature(state)
        for change in (lambda value:value.update(prefix_hash='sha256:'+'0'*64),
                       lambda value:value.update(arithmetic_profile='binary-float'),
                       lambda value:value.update(state={'invented':'999'})):
            corrupted=copy.deepcopy(snapshot)
            change(corrupted)
            recovered=module.restore_feature(feature,module.CandlePrefix(rows[:4]),corrupted)
            self.assertEqual('RECOMPUTED_SNAPSHOT_MISMATCH',recovered.recovery_reason)
            self.assertEqual(Decimal('4'),module.update_feature(recovered,rows[4]).observation.value)
        changed=tuple(replace(row,source='different verified dataset') for row in rows[:4])
        recovered=module.restore_feature(feature,module.CandlePrefix(changed),snapshot)
        self.assertEqual('RECOMPUTED_SNAPSHOT_MISMATCH',recovered.recovery_reason)

    def test_changed_feature_parameters_cannot_reuse_smoothing_state(self):
        module=api(self)
        rows=bars([1,2,3,4])
        state=module.new_feature_state(spec(module,'EMA',window=2))
        for row in rows: module.update_feature(state,row)
        feature=spec(module,'EMA',window=3)
        restored=module.restore_feature(feature,module.CandlePrefix(rows),module.snapshot_feature(state))
        self.assertEqual('RECOMPUTED_SNAPSHOT_MISMATCH',restored.recovery_reason)
        self.assertEqual(Decimal('3'),restored.observation.value)

    def test_invalid_source_never_turns_into_zero_or_false(self):
        module=api(self)
        state=module.new_feature_state(spec(module,'EMA',window=2))
        rows=bars([1,2,3])
        module.update_feature(state,rows[0])
        observed=module.update_feature(state,rows[1],source_value=None).observation
        self.assertFalse(observed.ready)
        self.assertIsNone(observed.value)
        self.assertEqual('MISSING_SOURCE_VALUE',observed.reason_code)
        self.assertFalse(module.update_feature(state,rows[2]).observation.ready)

    def test_incremental_state_retains_bounded_window_not_entire_history(self):
        module=api(self)
        state=module.new_feature_state(spec(module,'EMA',window=3))
        for row in bars(range(1000)): module.update_feature(state,row)
        snapshot=module.snapshot_feature(state)
        import json
        self.assertLess(len(json.dumps(snapshot)),8192)
        self.assertEqual(1000,state.count)

