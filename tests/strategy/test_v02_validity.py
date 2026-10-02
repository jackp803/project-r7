from datetime import datetime,timedelta,timezone
import importlib.util
import unittest


class ValidityTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('strategy.v02.temporal'),'Validity service missing')
        from strategy.v02 import temporal
        return temporal

    def test_evergreen_and_tactical_are_not_inferred_from_four_hour_timeframe(self):
        api=self.api()
        now=datetime(2026,10,2,tzinfo=timezone.utc)
        evergreen={'intent_class':'EVERGREEN_STRATEGY','validity':{'from':None,'until':None}}
        self.assertEqual('VALID',api.assess_submission_validity(evergreen,now).status)
        tactical={'intent_class':'TACTICAL_STRATEGY','validity':{'from':now.isoformat().replace('+00:00','Z'),
                  'until':(now+timedelta(hours=4)).isoformat().replace('+00:00','Z')}}
        self.assertEqual('VALID',api.assess_submission_validity(tactical,now).status)
        decision=api.assess_submission_validity(tactical,now+timedelta(hours=4))
        self.assertEqual('EXPIRED',decision.status)
        self.assertFalse(decision.new_entry_allowed)
        self.assertTrue(decision.required_management_allowed)

    def test_before_interval_is_waiting_and_invalid_tactical_interval_blocks(self):
        api=self.api()
        now=datetime(2026,10,2,tzinfo=timezone.utc)
        manifest={'intent_class':'TACTICAL_STRATEGY','validity':{'from':'2026-10-02T01:00:00Z','until':'2026-10-02T05:00:00Z'}}
        self.assertEqual('NOT_YET_VALID',api.assess_submission_validity(manifest,now).status)
        manifest['validity']['until']=None
        with self.assertRaises(ValueError): api.assess_submission_validity(manifest,now)

    def test_entry_deadline_never_extends_the_approved_plan_expiry(self):
        api=self.api()
        now=datetime(2026,10,2,tzinfo=timezone.utc)
        self.assertEqual(now+timedelta(seconds=30),api.entry_deadline(now+timedelta(hours=4),now+timedelta(seconds=30)))
        self.assertFalse(api.entry_is_current(now,now))

