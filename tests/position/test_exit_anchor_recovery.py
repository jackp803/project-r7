import copy
import hashlib
import importlib.util
import json
import unittest
from datetime import timedelta

from tests.position import test_v02_exit_requests as fixtures


def _rehash(value):
    value['payload_hash'] = 'sha256:' + hashlib.sha256(json.dumps(
        value['payload'], sort_keys=True, separators=(',', ':'), ensure_ascii=False,
        allow_nan=False).encode('utf-8')).hexdigest()
    return value


class ExitAnchorRecoveryTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('position.exit_state'),
                             'E5 first-fill anchor recovery is not implemented')
        from position import exit_state
        return exit_state

    def facts(self, *, trailing=None):
        helper = fixtures.ExitRequestTests()
        request, owner = helper.request(trailing=trailing)
        position, plan = helper.facts(request)
        position['lifecycle_state'] = 'OPEN_PROTECTED'
        return helper, request, owner, position, plan

    def test_recovered_first_fill_deadline_survives_later_partial_fill_clock(self):
        api = self.api()
        _, request, owner, position, plan = self.facts()
        original = owner.anchor_exit_request(request, position, plan)
        payload = json.loads(json.dumps(api.encode_exit_anchor(original)))
        position.update(opened_at='2026-10-02T12:00:30Z', actual_quantity='0.003',
                        broker_state_observed_at='2026-10-02T12:01:02Z')
        restored = api.restore_exit_anchor(payload, request=request, position=position, plan=plan)
        at = fixtures.NOW + timedelta(seconds=62)
        outcome = owner.interpret_exit_request(request, owner.CurrentExitAuthority(
            position, plan, restored, None, 'UNKNOWN', at, at + timedelta(seconds=30)))
        self.assertEqual(restored.first_fill_at, fixtures.NOW + timedelta(seconds=2))
        self.assertEqual(restored.hold_deadline, fixtures.NOW + timedelta(seconds=62))
        self.assertEqual(outcome.position_action['action'], 'EXIT')
        self.assertIn('E5_MAX_HOLD_REACHED', outcome.position_action['reason_codes'])

    def test_recovered_trailing_extremes_cannot_widen_after_restart(self):
        api = self.api()
        helper, request, owner, position, plan = self.facts(trailing={'kind': 'fixed_distance', 'value': '600'})
        anchor = owner.anchor_exit_request(request, position, plan)
        at = fixtures.NOW + timedelta(seconds=4)
        first = owner.interpret_exit_request(request, owner.CurrentExitAuthority(
            position, plan, anchor, helper.market(at, '60500'), 'FRESH', at, at + timedelta(seconds=30)))
        restored = api.restore_exit_anchor(api.encode_exit_anchor(first.anchor),
                                         request=request, position=position, plan=plan)
        at += timedelta(seconds=1)
        second = owner.interpret_exit_request(request, owner.CurrentExitAuthority(
            position, plan, restored, helper.market(at, '60100'), 'FRESH', at, at + timedelta(seconds=30)))
        self.assertEqual(second.anchor.high_water, 60500)
        self.assertEqual(second.anchor.proposed_stop, 59900)
        self.assertEqual(second.status, 'NON_EXECUTABLE_PROFILE')

    def test_rehashed_extended_deadline_wrong_plan_and_widened_stop_rejected(self):
        api = self.api()
        _, request, owner, position, plan = self.facts()
        original = api.encode_exit_anchor(owner.anchor_exit_request(request, position, plan))
        for field, value in (('hold_deadline', '2026-10-02T12:02:00Z'),
                             ('trade_plan_id', 'different'), ('initial_reference_price', 'NaN'),
                             ('proposed_stop', '58000'), ('target_level', '63000')):
            changed = copy.deepcopy(original)
            changed['payload'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                api.restore_exit_anchor(_rehash(changed), request=request, position=position, plan=plan)


if __name__ == '__main__': unittest.main()
