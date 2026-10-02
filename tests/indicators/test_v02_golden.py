from dataclasses import replace
from decimal import Decimal,localcontext
import unittest
from tests.indicators.v02_fixtures import api,bars,spec


class GoldenIndicatorTests(unittest.TestCase):
    def test_derived_numeric_series_preserves_declared_units_in_value_and_snapshot_identity(self):
        module=api(self)
        import inspect
        self.assertIn('source_dimensions',inspect.signature(module.FeatureSpec).parameters)
        scalar=module.FeatureSpec('EMA','r7-ema-v1',{'window':2},'value','1h',source_dimensions=(0,0))
        price=module.FeatureSpec('EMA','r7-ema-v1',{'window':2},'value','1h')
        observed=module.evaluate_feature(scalar,module.CandlePrefix(bars([1,2]),(Decimal('10'),Decimal('12'))))
        self.assertEqual(Decimal('11'),observed.value)
        self.assertEqual('dimensionless',observed.units)
        self.assertNotEqual(price.spec_hash,scalar.spec_hash)

    def test_all_families_flat_gap_and_insufficient_prefix(self):
        module=api(self)
        profiles=[('SMA','value',{'window':2},'5'),('EMA','value',{'window':2},'5'),
                  ('RSI','value',{'window':2},'50'),('ATR','value',{'window':2},'0'),
                  *[('ADX',out,{'window':2},'0') for out in ('value','plus_di','minus_di')],
                  *[('MACD',out,{'fast':2,'slow':3,'signal_window':2},'0') for out in ('line','signal','histogram')],
                  *[('BOLLINGER',out,{'window':2,'k':'2'},'0' if out=='stddev' else '5') for out in ('middle','upper','lower','stddev')],
                  *[('DONCHIAN',out,{'window':2},'5') for out in ('upper','lower','middle')]]
        rows=bars([5]*6,ohlc=[(5,5)]*6)
        for name,output,parameters,want in profiles:
            feature=spec(module,name,output=output,**parameters)
            with self.subTest(name=name,output=output):
                result=module.evaluate_feature(feature,module.CandlePrefix(rows))
                self.assertEqual(Decimal(want),result.value)
                self.assertFalse(module.evaluate_feature(feature,module.CandlePrefix(())).ready)
                self.assertFalse(module.evaluate_feature(feature,module.CandlePrefix(rows[:1])).ready)
                result=module.evaluate_feature(feature,module.CandlePrefix((rows[0],*rows[2:])))
                self.assertFalse(result.ready)
                self.assertEqual('GAP_IN_HISTORY',result.reason_code)

    def observation(self,name,prices,*,output='value',ohlc=None,**params):
        module=api(self)
        return module.evaluate_feature(spec(module,name,output=output,**params),module.CandlePrefix(bars(prices,ohlc=ohlc)))

    def test_sma_exact_signed_mean_and_no_partial_window(self):
        self.assertEqual(Decimal('-2'),self.observation('SMA',[-3,-1],window=2).value)
        warm=self.observation('SMA',[1],window=2)
        self.assertFalse(warm.ready)
        self.assertIsNone(warm.value)
        self.assertEqual('INSUFFICIENT_HISTORY',warm.reason_code)

    def test_ema_seeds_mean_then_uses_declared_alpha(self):
        for prices,want in (([1,2,3],'2'),([1,2,3,4],'3'),([1,2,3,4,5],'4')):
            with self.subTest(prices=prices):
                self.assertEqual(Decimal(want),self.observation('EMA',prices,window=3).value)
        self.assertFalse(self.observation('EMA',[1,2],window=3).ready)

    def test_rsi_wilder_seed_update_and_flat_extremes(self):
        for prices,want in (([10,12,11],'66.66666666666666666666666666666667'),
                            ([10,12,11,13],'85.71428571428571428571428571428571'),
                            ([10,10,10],'50'),([10,11,12],'100'),([12,11,10],'0')):
            with self.subTest(prices=prices):
                self.assertEqual(Decimal(want),self.observation('RSI',prices,window=2).value)
        self.assertFalse(self.observation('RSI',[10,11],window=2).ready)

    def test_atr_first_range_gap_true_range_seed_and_wilder(self):
        prices=[10,12,9,15]
        ranges=[(11,9),(13,10),(12,8),(16,13)]
        for count,want in ((2,'2.5'),(3,'3.25'),(4,'5.125')):
            self.assertEqual(Decimal(want),self.observation('ATR',prices[:count],ohlc=ranges[:count],window=2).value)
        self.assertFalse(self.observation('ATR',prices[:1],ohlc=ranges[:1],window=2).ready)

    def test_adx_independent_di_and_adx_readiness(self):
        prices=[10,12,14,16]
        ranges=[(11,9),(13,11),(15,13),(17,15)]
        self.assertFalse(self.observation('ADX',prices[:2],ohlc=ranges[:2],output='plus_di',window=2).ready)
        plus=self.observation('ADX',prices[:3],ohlc=ranges[:3],output='plus_di',window=2)
        self.assertEqual(Decimal('66.66666666666666666666666666666667'),plus.value)
        self.assertFalse(self.observation('ADX',prices[:3],ohlc=ranges[:3],window=2).ready)
        self.assertEqual(Decimal('100'),self.observation('ADX',prices,ohlc=ranges,window=2).value)
        self.assertEqual(Decimal('0'),self.observation('ADX',prices,ohlc=ranges,output='minus_di',window=2).value)
        self.assertEqual(Decimal('66.66666666666666666666666666666667'),
                         self.observation('ADX',[16,14,12],ohlc=[(17,15),(15,13),(13,11)],output='minus_di',window=2).value)

    def test_adx_directional_ties_and_zero_tr_have_no_fabricated_strength(self):
        self.assertEqual(Decimal('0'),self.observation('ADX',[2,2],ohlc=[(3,1),(4,0)],window=1).value)
        self.assertEqual(Decimal('0'),self.observation('ADX',[2,2,2,2],ohlc=[(2,2)]*4,window=2).value)

    def test_macd_line_signal_histogram_have_independent_warmup(self):
        params={'fast':2,'slow':3,'signal_window':2}
        self.assertEqual(Decimal('0.5'),self.observation('MACD',[1,2,3],output='line',**params).value)
        self.assertFalse(self.observation('MACD',[1,2,3],output='signal',**params).ready)
        self.assertFalse(self.observation('MACD',[1,2,3],output='histogram',**params).ready)
        self.assertEqual(Decimal('0.5'),self.observation('MACD',[1,2,3,4],output='signal',**params).value)
        self.assertEqual(Decimal('0'),self.observation('MACD',[1,2,3,4],output='histogram',**params).value)
        self.assertEqual(Decimal('-0.5'),self.observation('MACD',[-1,-2,-3],output='line',**params).value)

    def test_bollinger_population_variance_signed_bands(self):
        for output,want in (('middle','0'),('stddev','1'),('upper','2'),('lower','-2')):
            self.assertEqual(Decimal(want),self.observation('BOLLINGER',[-1,1],output=output,window=2,k='2').value)
        self.assertEqual(Decimal('0'),self.observation('BOLLINGER',[4,4],output='stddev',window=2,k='2').value)
        self.assertEqual(Decimal('0.8164965809277260327324280249019638'),
                         self.observation('BOLLINGER',[1,2,3],output='stddev',window=3,k='2').value)

    def test_donchian_default_lag_excludes_decision_bar(self):
        for output,want in (('upper','12'),('lower','8'),('middle','10')):
            self.assertEqual(Decimal(want),self.observation('DONCHIAN',[9,10,50],ohlc=[(10,8),(12,9),(100,1)],
                                                        output=output,window=2).value)
        self.assertFalse(self.observation('DONCHIAN',[9,10],output='upper',window=2).ready)
        self.assertEqual(Decimal('100'),self.observation('DONCHIAN',[9,10,50],ohlc=[(10,8),(12,9),(100,1)],
                                                       output='upper',window=2,lag_bars=0).value)

    def test_window_one_is_explicit_for_each_family(self):
        for name,params,output,prices,want in (
            ('SMA',{'window':1},'value',[3],'3'),('EMA',{'window':1},'value',[3,4],'4'),
            ('RSI',{'window':1},'value',[3,4],'100'),('ATR',{'window':1},'value',[3],'4'),
            ('ADX',{'window':1},'value',[3,4],'100'),
            ('BOLLINGER',{'window':1,'k':'2'},'stddev',[3],'0'),
            ('DONCHIAN',{'window':1},'middle',[3,4],'3'),
            ('MACD',{'fast':1,'slow':2,'signal_window':1},'histogram',[3,4],'0')):
            with self.subTest(name=name):
                self.assertEqual(Decimal(want),self.observation(name,prices,output=output,**params).value)

    def test_ambient_decimal_context_does_not_change_numeric_facts(self):
        with localcontext() as context:
            context.prec=4
            result=self.observation('RSI',[10,12,11,13],window=2)
        self.assertEqual(Decimal('85.71428571428571428571428571428571'),result.value)

    def test_gap_and_unfinalized_input_are_invalid_instead_of_forward_filled(self):
        module=api(self)
        rows=bars([10,11,12,13])
        gap=module.evaluate_feature(spec(module,'EMA',window=2),module.CandlePrefix((rows[0],*rows[2:])))
        self.assertFalse(gap.ready)
        self.assertEqual('GAP_IN_HISTORY',gap.reason_code)
        pending=module.evaluate_feature(spec(module,'EMA',window=2),module.CandlePrefix((*rows[:-1],replace(rows[-1],is_closed=False))))
        self.assertFalse(pending.ready)
        self.assertEqual('UNFINALIZED_INPUT',pending.reason_code)

    def test_invalid_primitive_profile_and_parameters_cannot_be_approximated(self):
        module=api(self)
        for name,version,params,output in (
            ('EMA','r7-ema-v99',{'window':2},'value'),('EMA','r7-ema-v1',{'window':0},'value'),
            ('EMA','r7-ema-v1',{'window':True},'value'),('MACD','r7-macd-v1',{'fast':3,'slow':2,'signal_window':1},'line'),
            ('BOLLINGER','r7-bollinger-pop-v1',{'window':2,'k':'0'},'upper'),
            ('SMA','r7-sma-v1',{'window':2,'extra':1},'value')):
            with self.subTest(name=name,parameters=params):
                with self.assertRaises(ValueError): module.FeatureSpec(name,version,params,output,'1h')

    def test_malformed_timeframe_and_candle_source_field_are_rejected(self):
        module=api(self)
        for timeframe,field in (([], 'close'),('1h','__dict__')):
            with self.subTest(timeframe=timeframe,field=field):
                with self.assertRaises(ValueError):
                    module.FeatureSpec('ATR','r7-atr-wilder-v1',{'window':2},'value',timeframe,field)

    def test_window_upper_bound_is_valid_but_not_ready_prematurely(self):
        module=api(self)
        feature=spec(module,'EMA',window=10000)
        self.assertFalse(module.evaluate_feature(feature,module.CandlePrefix(bars([1]))).ready)
        with self.assertRaises(ValueError): spec(module,'EMA',window=10001)

    def test_bad_identity_alignment_and_binary_float_source_are_unhealthy(self):
        module=api(self)
        from datetime import timedelta
        rows=bars([1,2])
        for changed,reason in ((replace(rows[1],symbol='OTHER'),'SYMBOL_MISMATCH'),
                               (rows[0],'GAP_IN_HISTORY'),
                               (replace(rows[1],open_time=rows[1].open_time+timedelta(minutes=1),
                                        close_time=rows[1].close_time+timedelta(minutes=1)),'MISALIGNED_INPUT')):
            state=module.new_feature_state(spec(module,'EMA',window=2))
            module.update_feature(state,rows[0])
            result=module.update_feature(state,changed).observation
            self.assertFalse(result.ready)
            self.assertEqual(reason,result.reason_code)
        state=module.new_feature_state(spec(module,'EMA',window=2))
        result=module.update_feature(state,rows[0],source_value=1.5).observation
        self.assertFalse(result.ready)
        self.assertEqual('NON_DECIMAL_INPUT',result.reason_code)

