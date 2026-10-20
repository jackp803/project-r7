"""Write unapplied, AST-checked test drafts outside the guarded repository."""
import ast
import json
from pathlib import Path

ART=Path(__file__).resolve().parent
REPO=ART.parents[1]/'workspaces/project-r7-productization-master-20261002'

def draft(relative,anchor,methods):
    path=REPO/relative
    source=path.read_text(encoding='utf-8')
    assert source.count(anchor)==1
    proposed=source.replace(anchor,methods+anchor)
    ast.parse(proposed)
    patch='*** Begin Patch\n*** Update File: '+str(path)+'\n@@\n'
    patch+=''.join('+'+line+'\n' for line in methods.splitlines())+' '+anchor+'*** End Patch\n'
    target=ART/('postcheckpoint_'+path.stem+'_tests.patch')
    target.write_text(patch,encoding='utf-8',newline='\n')
    return dict(ref=target.name,methods=methods.count('    def test_'),status='DRAFT_ONLY_NOT_EXECUTED')

indicator='''    def test_ema_nonlinear_update_has_exact_recursive_alpha(self):
        warm = self.observation('EMA', [1,2], window=3)
        self.assertFalse(warm.ready)
        self.assertIsNone(warm.value)
        for prices, expected in (([1,2,3], '2'), ([1,2,3,10], '6'), ([1,2,3,10,2], '4')):
            with self.subTest(prices=prices):
                self.assertEqual(self.observation('EMA', prices, window=3).value, Decimal(expected))

    def test_adx_window_one_requires_two_actual_bars_for_all_outputs(self):
        for output in ('value', 'plus_di', 'minus_di'):
            with self.subTest(output=output):
                early = self.observation('ADX', [10], ohlc=[(11,9)], output=output, window=1)
                self.assertFalse(early.ready)
                self.assertIsNone(early.value)
                self.assertEqual(early.reason_code, 'INSUFFICIENT_HISTORY')
                ready = self.observation('ADX', [10,12], ohlc=[(11,9),(13,11)], output=output, window=1)
                self.assertTrue(ready.ready)
                self.assertEqual(ready.value, Decimal('100' if output=='value' else '66.66666666666666666666666666666667' if output=='plus_di' else '0'))

'''

exit_requests='''    def test_atr_target_uses_bound_e2_observation_and_existing_e5_authority(self):
        for side, expected, price in (('LONG','61200','61300'), ('SHORT','58800','58700')):
            with self.subTest(side=side):
                request, api = self.request(side=side, atr=True, target={'kind':'atr_multiple','feature':'atr','multiple':'6'})
                value = request.as_dict()
                feature = value['feature_anchors']['atr']
                self.assertEqual(feature, dict(value='200', semantic_version='r7-atr-wilder-v1',
                    market_boundary_ref=value['market_boundary_ref'], observed_at=value['observed_at']))
                constraints = api.resolve_exit_constraints(request)
                self.assertEqual(constraints.target_level, Decimal(expected))
                self.assertEqual(constraints.stop_level, Decimal('59400' if side=='LONG' else '60600'))
                position, plan = self.facts(request, side=side)
                position['lifecycle_state'] = 'OPEN_PROTECTED'
                original_position, original_plan = json.loads(json.dumps(position)), json.loads(json.dumps(plan))
                anchor = api.anchor_exit_request(request, position, plan)
                at = NOW+timedelta(seconds=3)
                result = api.interpret_exit_request(request, api.CurrentExitAuthority(position,plan,anchor,
                    self.market(at,price),'FRESH',at,at+timedelta(seconds=30)))
                self.assertEqual(result.position_action['action'], 'EXIT')
                self.assertIn('E5_TARGET_REACHED', result.position_action['reason_codes'])
                self.assertEqual(result.position_action['quantity'], position['actual_quantity'])
                self.assertEqual(result.anchor.first_fill_at, anchor.first_fill_at)
                self.assertEqual(result.anchor.hold_deadline, anchor.hold_deadline)
                self.assertEqual(position, original_position)
                self.assertEqual(plan, original_plan)

    def test_atr_target_rejects_missing_foreign_future_or_changed_anchor(self):
        import json
        from strategy import StrategyValidationError
        from strategy.v02.exits import ExitRequest
        for side, changed_target in (('LONG','61206'), ('SHORT','58794')):
            request, api = self.request(side=side, atr=True, target={'kind':'atr_multiple','feature':'atr','multiple':'6'})
            missing = request.as_dict()
            missing['feature_anchors'] = {}
            with self.assertRaises(api.ExitRequestError) as caught:
                api.resolve_exit_constraints(ExitRequest(json.dumps(missing)))
            self.assertEqual(caught.exception.code, 'ATR_ANCHOR_BINDING_MISMATCH')
            for field, changed, code in (('market_boundary_ref','sha256:'+'f'*64,'EXIT_FEATURE_BINDING_MISMATCH'),
                ('semantic_version','unknown-atr-v1','EXIT_FEATURE_BINDING_MISMATCH'),
                ('observed_at','2026-10-02T12:00:01Z','FUTURE_EXIT_FEATURE_ANCHOR')):
                with self.subTest(side=side,field=field), self.assertRaises(StrategyValidationError) as caught:
                    value=request.as_dict()
                    value['feature_anchors']['atr'][field]=changed
                    ExitRequest(json.dumps(value))
                self.assertEqual(caught.exception.code, code)
            value=request.as_dict()
            value['feature_anchors']['atr']['value']='201'
            changed=ExitRequest(json.dumps(value))
            self.assertEqual(api.resolve_exit_constraints(changed).target_level, Decimal(changed_target))
            position, plan=self.facts(request,side=side)
            with self.assertRaises(api.ExitRequestError) as caught: api.anchor_exit_request(changed,position,plan)
            self.assertEqual(caught.exception.code, 'APPROVED_TARGET_CONSTRAINT_MISMATCH')

    def test_fixed_price_stop_and_target_resolve_and_close_under_e5(self):
        for side, stop, target, price in (('LONG','59400','61200','61300'), ('SHORT','60600','58800','58700')):
            with self.subTest(side=side):
                request, api=self.request(side=side,stop={'kind':'fixed_price','value':stop},target={'kind':'fixed_price','value':target})
                constraints=api.resolve_exit_constraints(request)
                self.assertEqual((constraints.stop_level,constraints.target_level,constraints.max_hold_seconds),
                    (Decimal(stop),Decimal(target),60))
                position,plan=self.facts(request,side=side)
                position['lifecycle_state']='OPEN_PROTECTED'
                anchor=api.anchor_exit_request(request,position,plan)
                at=NOW+timedelta(seconds=3)
                result=api.interpret_exit_request(request,api.CurrentExitAuthority(position,plan,anchor,
                    self.market(at,price),'FRESH',at,at+timedelta(seconds=30)))
                self.assertEqual(result.position_action['action'],'EXIT')
                self.assertIn('E5_TARGET_REACHED',result.position_action['reason_codes'])
                self.assertEqual(result.position_action['quantity'],position['actual_quantity'])
                self.assertEqual(result.anchor.first_fill_at,anchor.first_fill_at)
                self.assertEqual(result.anchor.hold_deadline,anchor.hold_deadline)

'''
# Only the first method needs json without a module-level import.
exit_requests=exit_requests.replace('        for side, expected, price', '        import json\n        for side, expected, price',1)

cross='''    def test_parsed_cross_uses_immediately_previous_finalized_pair(self):
        value=definition_v02()
        value['rules']['features']={}
        value['rules']['long']=operator('CROSS_ABOVE',field(),{'kind':'decimal','value':'10'})
        value['rules']['short']=operator('CROSS_BELOW',field(),{'kind':'decimal','value':'10'})
        value['content_hash']=compute_content_hash(value)
        parsed=parse_strategy_definition(value)
        api=self.api()
        for prices,direction in (([9,11,12],'LONG'),([11,9,8],'SHORT')):
            rows=received(bars(prices,timeframe='4h'))
            with self.subTest(prices=prices):
                early=StrategyRuntime().evaluate(parsed,api.build_asof_bundle({'4h':rows},utc(4),utc(4)),utc(4))
                self.assertEqual((early['direction'],early['reason_codes']),('NO_TRADE',['INSUFFICIENT_HISTORY']))
                middle=StrategyRuntime().evaluate(parsed,api.build_asof_bundle({'4h':rows},utc(8),utc(8)),utc(8))
                self.assertEqual((middle['direction'],middle['reason_codes']),(direction,[direction+'_RULE_MATCHED']))
                final=StrategyRuntime().evaluate(parsed,api.build_asof_bundle({'4h':rows},utc(12),utc(12)),utc(12))
                self.assertEqual((final['direction'],final['reason_codes']),('NO_TRADE',['NO_RULE_MATCHED']))
                changed=(*rows[:-1],replace(rows[-1],open=Decimal('100'),high=Decimal('100'),low=Decimal('100'),close=Decimal('100')))
                unchanged=StrategyRuntime().evaluate(parsed,api.build_asof_bundle({'4h':changed},utc(8),utc(8)),utc(8))
                self.assertEqual(middle,unchanged)

    def test_parsed_cross_cannot_replace_unavailable_predecessor_with_older_bar(self):
        value=definition_v02()
        value['rules']['features']={}
        value['rules']['long']=operator('CROSS_ABOVE',field(),{'kind':'decimal','value':'10'})
        value['rules']['short']=operator('CROSS_BELOW',field(),{'kind':'decimal','value':'10'})
        value['content_hash']=compute_content_hash(value)
        parsed=parse_strategy_definition(value)
        api=self.api()
        for prices in ([9,11,12],[11,9,8]):
            with self.subTest(prices=prices):
                rows=list(received(bars(prices,timeframe='4h')))
                rows[1]=replace(rows[1],received_at=utc(8)+timedelta(seconds=5))
                signal=StrategyRuntime().evaluate(parsed,api.build_asof_bundle({'4h':tuple(rows)},utc(12),utc(12)),utc(12))
                self.assertEqual((signal['direction'],signal['reason_codes']),('NO_TRADE',['INSUFFICIENT_HISTORY']))

'''

capabilities='''    def test_every_registry_entry_declares_metadata_without_fabricated_verification(self):
        document=self.api().build_capability_snapshot().as_dict()
        rows=document['capabilities']
        expected={
            'SMA':('r7-sma-v1',['value'],'n'),
            'EMA':('r7-ema-v1',['value'],'n'),
            'RSI':('r7-rsi-wilder-v1',['value'],'n+1'),
            'ATR':('r7-atr-wilder-v1',['value'],'n'),
            'ADX':('r7-adx-wilder-v1',['value','plus_di','minus_di'],'DI:n+1; ADX:2*n'),
            'MACD':('r7-macd-v1',['line','signal','histogram'],'line:slow; signal/histogram:slow+signal_window-1'),
            'BOLLINGER':('r7-bollinger-pop-v1',['middle','upper','lower','stddev'],'n'),
            'DONCHIAN':('r7-donchian-v1',['upper','lower','middle'],'n+lag_bars')}
        self.assertEqual(len(rows),9)
        self.assertEqual({row['capability_id'] for row in rows},{'grammar:0.2',*('indicator:'+name for name in expected)})
        self.assertEqual(document['runtime_profiles'],['0.1.0','0.2.0'])
        self.assertRegex(document['implementation_revision'],r'^sha256:[0-9a-f]{64}$')
        for row in rows:
            with self.subTest(capability=row['capability_id']):
                self.assertIsInstance(row['parameters'],dict)
                for name in ('output_type','units','minimum_history','missing_data_behavior'):
                    self.assertIsInstance(row[name],str)
                    self.assertTrue(row[name])
                self.assertEqual(row['supported_timeframes'],['1m','15m','1h','4h'])
                self.assertEqual(row['arithmetic_profile'],'r7-decimal34-v1')
                self.assertEqual(row['implementation_revision'],document['implementation_revision'])
                self.assertIs(row['validator_available'],True)
                self.assertIs(row['IMPLEMENTED'],True)
                for name in ('VERIFIED_REFERENCE','PAPER_AVAILABLE','LIVE_PROVIDER_AVAILABLE'):
                    self.assertIs(row[name],False)
                self.assertEqual(row['verification_refs'],[])
                if row['capability_id'].startswith('indicator:'):
                    version,outputs,history=expected[row['capability_id'].removeprefix('indicator:')]
                    self.assertEqual(row['semantic_version'],version)
                    self.assertEqual(set(row['outputs']),set(outputs))
                    self.assertEqual(len(row['outputs']),len(outputs))
                    self.assertEqual(row['minimum_history'],history)
                else:
                    self.assertEqual(row['semantic_version'],'r7-closed-bar-v0.2')
        self.assertEqual(document['platform_verification'],
            dict(Windows11='NOT_RUN',**{'Ubuntu24.04':'NOT_RUN','Ubuntu26.04':'NOT_RUN'}))

'''

if __name__=='__main__':
    rows=[draft('tests/indicators/test_v02_golden.py',
                '    def test_derived_numeric_series_preserves_declared_units_in_value_and_snapshot_identity(self):\n',indicator),
          draft('tests/position/test_v02_exit_requests.py',
                '    def test_exit_request_rejects_unknown_authority_fields_and_mutually_mixed_shapes(self):\n',exit_requests),
          draft('tests/strategy/test_v02_capabilities.py',
                '    def test_source_inventory_ignores_unreadable_non_executable_file_metadata(self):\n',capabilities),
          draft('tests/strategy/test_v02_multitimeframe.py',
                '    def test_visible_out_of_profile_financial_input_returns_structured_boundary_error(self):\n',cross)]
    print(json.dumps(dict(status='UNAPPLIED_AST_CHECK_ONLY',drafts=rows,tracked_writes=0),indent=2))
