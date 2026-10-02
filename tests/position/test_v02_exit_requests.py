from dataclasses import replace
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import importlib.util
import unittest

from market_data.current import MarketSnapshot
from strategy import compute_content_hash,parse_strategy_definition
from strategy.v02.temporal import build_asof_bundle
from tests.indicators.v02_fixtures import bars
from tests.strategy.v02_fixtures import definition_v02,field,operator
from tests.position import test_close_action as close_fixtures


NOW=datetime(2026,10,2,12,tzinfo=timezone.utc)


class ExitRequestTests(unittest.TestCase):
    def test_exit_request_rejects_unknown_authority_fields_and_mutually_mixed_shapes(self):
        request,api=self.request()
        from strategy.v02.exits import ExitRequest
        import json
        value=request.as_dict()
        value['risk_budget']='1000000'
        with self.assertRaises(ValueError): ExitRequest(json.dumps(value))
        del value['risk_budget']
        value['exit_policy']['stop']['python']='exec'
        with self.assertRaises(ValueError): ExitRequest(json.dumps(value))

    def test_stop_and_target_close_both_sides_through_existing_e5_authority(self):
        for side,price,reason in (('LONG','59300','E5_STOP_REACHED'),('LONG','61300','E5_TARGET_REACHED'),
                                  ('SHORT','60700','E5_STOP_REACHED'),('SHORT','58700','E5_TARGET_REACHED')):
            with self.subTest(side=side,price=price):
                request,api=self.request(side=side)
                position,plan=self.facts(request,side=side)
                position['lifecycle_state']='OPEN_PROTECTED'
                anchor=api.anchor_exit_request(request,position,plan)
                at=NOW+timedelta(seconds=3)
                outcome=api.interpret_exit_request(request,api.CurrentExitAuthority(position,plan,anchor,self.market(at,price),
                                               'FRESH',at,at+timedelta(seconds=30)))
                self.assertEqual('EXIT',outcome.position_action['action'])
                self.assertIn(reason,outcome.position_action['reason_codes'])

    def test_time_exit_does_not_wait_for_market_or_entry_candle(self):
        request,api=self.request()
        position,plan=self.facts(request)
        anchor=api.anchor_exit_request(request,position,plan)
        at=NOW+timedelta(seconds=62)
        position.update(lifecycle_state='OPEN_PROTECTED',broker_state_observed_at='2026-10-02T12:01:02Z')
        authority=api.CurrentExitAuthority(position,plan,anchor,None,'UNKNOWN',at,at+timedelta(seconds=30))
        outcome=api.interpret_exit_request(request,authority)
        self.assertIsNotNone(outcome.position_action)
        self.assertEqual('EXIT',outcome.position_action['action'])
        self.assertIn('E5_MAX_HOLD_REACHED',outcome.position_action['reason_codes'])

    def test_changed_approved_target_or_policy_cannot_reuse_first_fill_binding(self):
        request,api=self.request()
        position,plan=self.facts(request)
        anchor=api.anchor_exit_request(request,position,plan)
        at=NOW+timedelta(seconds=3)
        changed=dict(plan,protection_instruction=dict(plan['protection_instruction'],target_level='62000'))
        authority=api.CurrentExitAuthority(position,changed,anchor,self.market(at),'FRESH',at,at+timedelta(seconds=30))
        with self.assertRaises(api.ExitRequestError): api.interpret_exit_request(request,authority)

    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('strategy.v02.exits'),'E2 exit request missing')
        self.assertIsNotNone(importlib.util.find_spec('position.exit_requests'),'E5 exit consumer missing')
        from strategy.v02.exits import build_exit_request
        from position import exit_requests
        return build_exit_request,exit_requests

    def request(self,*,side='LONG',stop=None,target=None,trailing=None,atr=False,hold=60):
        build,api=self.api()
        value=definition_v02()
        value['rules']['features']={}
        value['rules']['long']=operator('GT' if side=='LONG' else 'LT',field(),{'kind':'decimal','value':'0'})
        value['rules']['short']=operator('LT' if side=='LONG' else 'GT',field(),{'kind':'decimal','value':'0'})
        if atr:
            value['rules']['features']={'atr':{'kind':'indicator','name':'ATR','semantic_version':'r7-atr-wilder-v1',
                                                'timeframe':'4h','parameters':{'window':1},'output':'value'}}
        value['rules']['exit_policy']={'stop':stop or {'kind':'fixed_distance','value':'600'},
                                      'target':target or {'kind':'reward_risk','multiple':'2'},
                                      'trailing':trailing,'max_hold_seconds':hold}
        value['content_hash']=compute_content_hash(value)
        row=bars([60000],ohlc=[(60100,59900)],timeframe='4h')[0]
        row=replace(row,symbol='BTC_USDT_PERP',open_time=NOW-timedelta(hours=4),close_time=NOW,received_at=NOW)
        return build(parse_strategy_definition(value),build_asof_bundle({'4h':(row,)},NOW,NOW)),api

    def facts(self,request,*,side='LONG'):
        base=close_fixtures.CloseActionProducerTests()
        plan=base._plan(strategy_id='fixture-v02-trend',strategy_version='0.2.0',direction=side,
                        created_at='2026-10-02T11:59:50Z',expires_at='2026-10-02T12:00:30Z')
        plan['protection_instruction'].update(stop_level='59400' if side=='LONG' else '60600',
                                              target_level='61200' if side=='LONG' else '58800')
        position=base._position(side=side,opened_at='2026-10-02T12:00:02Z',broker_state_observed_at='2026-10-02T12:00:03Z')
        return position,plan

    def market(self,at,price='60000'):
        return MarketSnapshot('contracts-v0.1','BTC_USDT_PERP',at,at,'HEALTHY','local-market-fixture',
                              last_price=Decimal(price),freshness_ms=0)

    def test_fixed_distance_and_reward_risk_resolve_both_sides_without_sizing(self):
        for side,stop,target in (('LONG','59400','61200'),('SHORT','60600','58800')):
            request,api=self.request(side=side)
            result=api.resolve_exit_constraints(request)
            self.assertEqual(Decimal(stop),result.stop_level)
            self.assertEqual(Decimal(target),result.target_level)
            self.assertEqual(60,result.max_hold_seconds)

    def test_atr_uses_exact_bound_e2_observation(self):
        request,api=self.request(atr=True,stop={'kind':'atr_multiple','feature':'atr','multiple':'3'})
        result=api.resolve_exit_constraints(request)
        self.assertEqual(Decimal('59400'),result.stop_level)
        self.assertEqual('200',request.as_dict()['feature_anchors']['atr']['value'])
        self.assertEqual(request.as_dict()['market_boundary_ref'],request.as_dict()['feature_anchors']['atr']['market_boundary_ref'])

    def test_wrong_stop_geometry_and_equal_target_are_rejected(self):
        for stop,target in (({'kind':'fixed_price','value':'60000'},None),
                            ({'kind':'fixed_price','value':'60600'},None),
                            (None,{'kind':'fixed_price','value':'60000'})):
            request,api=self.request(stop=stop,target=target)
            with self.assertRaises(api.ExitRequestError): api.resolve_exit_constraints(request)

    def test_initial_protection_uses_actual_partial_exposure_and_real_fp03_evidence(self):
        request,api=self.request()
        position,plan=self.facts(request)
        anchor=api.anchor_exit_request(request,position,plan)
        at=NOW+timedelta(seconds=3)
        authority=api.CurrentExitAuthority(position,plan,anchor,self.market(at), 'FRESH',at,at+timedelta(seconds=30))
        outcome=api.interpret_exit_request(request,authority)
        self.assertEqual('PROTECT',outcome.position_action['action'])
        self.assertEqual('0.0012',outcome.position_action['quantity'])
        self.assertEqual('ACTIONABLE',outcome.trigger_validity_evidence['validity_status'])

    def test_partial_fill_never_resets_first_fill_holding_deadline_or_authorizes_new_entry(self):
        request,api=self.request()
        position,plan=self.facts(request)
        anchor=api.anchor_exit_request(request,position,plan)
        self.assertEqual(NOW+timedelta(seconds=62),anchor.hold_deadline)
        position.update(actual_quantity='0.002',average_entry_price='60005',opened_at='2026-10-02T12:00:20Z',
                        broker_state_observed_at='2026-10-02T12:01:02Z',lifecycle_state='OPEN_PROTECTED')
        at=NOW+timedelta(seconds=62)
        authority=api.CurrentExitAuthority(position,plan,anchor,self.market(at),'FRESH',at,at+timedelta(seconds=30))
        outcome=api.interpret_exit_request(request,authority)
        self.assertEqual('EXIT',outcome.position_action['action'])
        self.assertEqual('0.002',outcome.position_action['quantity'])
        self.assertIn('E5_MAX_HOLD_REACHED',outcome.position_action['reason_codes'])
        self.assertEqual('EXIT_REQUESTED',outcome.lifecycle_intent)
        self.assertEqual(anchor.first_fill_at,outcome.anchor.first_fill_at)

    def test_shared_trailing_geometry_tightens_both_sides_and_rejects_widened_loss_bound(self):
        from position import exit_requests as api
        self.assertTrue(hasattr(api,'propose_trailing_stop'),'Missing shared E5 geometry owner')
        self.assertEqual(Decimal(103),api.propose_trailing_stop('LONG',Decimal(90),Decimal(100),Decimal(104),Decimal(99),Decimal(1)))
        self.assertEqual(Decimal(97),api.propose_trailing_stop('SHORT',Decimal(110),Decimal(100),Decimal(104),Decimal(96),Decimal(1)))
        with self.assertRaises(api.ExitRequestError): api.propose_trailing_stop('LONG',Decimal(100),Decimal(90),Decimal(104),Decimal(99),Decimal(1))

    def test_trailing_proposal_is_monotonic_without_claiming_provider_execution(self):
        request,api=self.request(trailing={'kind':'fixed_distance','value':'300'},hold=1800)
        position,plan=self.facts(request)
        position['lifecycle_state']='OPEN_PROTECTED'
        anchor=api.anchor_exit_request(request,position,plan)
        at=NOW+timedelta(seconds=3)
        outcome=api.interpret_exit_request(request,api.CurrentExitAuthority(position,plan,anchor,self.market(at,'60100'),
                                           'FRESH',at,at+timedelta(seconds=30)))
        self.assertEqual(Decimal('59800'),outcome.anchor.proposed_stop)
        self.assertEqual('NON_EXECUTABLE_PROFILE',outcome.status)
        self.assertEqual('MODIFY_PROTECTION',outcome.position_action['action'])
        at+=timedelta(seconds=1)
        position['broker_state_observed_at']='2026-10-02T12:00:04Z'
        second=api.interpret_exit_request(request,api.CurrentExitAuthority(position,plan,outcome.anchor,self.market(at,'60000'),
                                          'FRESH',at,at+timedelta(seconds=30)))
        self.assertGreaterEqual(second.anchor.proposed_stop,outcome.anchor.proposed_stop)

    def test_mismatched_plan_stop_and_changed_request_cannot_reuse_anchor(self):
        request,api=self.request()
        position,plan=self.facts(request)
        wrong=dict(plan,protection_instruction=dict(plan['protection_instruction'],stop_level='59000'))
        with self.assertRaises(api.ExitRequestError): api.anchor_exit_request(request,position,wrong)
        anchor=api.anchor_exit_request(request,position,plan)
        changed,api=self.request(hold=61)
        at=NOW+timedelta(seconds=3)
        authority=api.CurrentExitAuthority(position,plan,anchor,self.market(at),'FRESH',at,at+timedelta(seconds=30))
        with self.assertRaises(api.ExitRequestError): api.interpret_exit_request(changed,authority)

