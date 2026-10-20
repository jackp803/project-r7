"""Regression: original issued terminal commitment cannot be relabeled."""
from dataclasses import replace
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
from tests.product.trading_finalization_fixtures import FinalizationFixture


class TradingFinalizationTerminalHashV02Tests(FinalizationFixture,unittest.TestCase):
    def test_changed_terminal_hash_in_actual_owner_produced_bundle_denies_before_outbox(self):
        from storage.product_dispatch import _json
        self.settled();reads=self.final_reads()
        before=self.flow.recover();calls=deepcopy(self.provider.calls);changed=[]
        original=self.service.dispatch.stage_finalization
        def replace_only_commitment(canonical,run_id,operation_id,observation,**kwargs):
            source=json.loads(observation.source_json)
            original_hash=source['terminal_confirmation']['source_hash']
            source['terminal_confirmation']['source_hash']='sha256:'+'a'*64
            self.assertNotEqual(original_hash,source['terminal_confirmation']['source_hash'])
            changed.append(True)
            return original(canonical,run_id,operation_id,replace(observation,source_json=_json(source)),**kwargs)
        with patch.object(self.service.dispatch,'stage_finalization',side_effect=replace_only_commitment):
            with self.assertRaises(ValueError):self.finalize(reads)
        self.assertTrue(changed)
        self.assertIsNone(self.service.dispatch.finalization_batch(self.service.run_id,self.close_id))
        self.assertEqual(before,self.flow.recover())
        self.assertEqual(calls,self.provider.calls)
