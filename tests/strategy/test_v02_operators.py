import importlib.util
from decimal import Decimal,localcontext
import unittest


class OperatorTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('strategy.v02.operators'),'Operator execution missing')
        from strategy.v02 import operators
        return operators

    def test_arithmetic_and_comparisons_have_decimal_results(self):
        api=self.api()
        for name,values,want in (
            ('ADD',('2','3'),'5'),('SUB',('2','3'),'-1'),('MUL',('-2','3'),'-6'),
            ('DIV',('1','8'),'0.125'),('ABS',('-3',),'3'),('MIN',('3','-1','2'),'-1'),('MAX',('3','-1','2'),'3')):
            with self.subTest(name=name):
                result=api.evaluate_operator(name,tuple(Decimal(value) for value in values))
                self.assertTrue(result.ready)
                self.assertEqual(Decimal(want),result.value)
        for name,want in (('GT',False),('GTE',True),('LT',False),('LTE',True),('EQ',True)):
            self.assertIs(want,api.evaluate_operator(name,(Decimal('2'),Decimal('2'))).value)

    def test_boolean_missing_required_operand_is_not_short_circuited_to_false(self):
        api=self.api()
        self.assertIs(False,api.evaluate_operator('AND',(True,False)).value)
        self.assertIs(True,api.evaluate_operator('OR',(True,False)).value)
        self.assertIs(False,api.evaluate_operator('NOT',(True,)).value)
        missing=api.evaluate_operator('AND',(False,None))
        self.assertFalse(missing.ready)
        self.assertIsNone(missing.value)
        self.assertEqual('INSUFFICIENT_HISTORY',missing.reason_code)

    def test_division_by_zero_is_invalid_observation(self):
        result=self.api().evaluate_operator('DIV',(Decimal('1'),Decimal('0')))
        self.assertFalse(result.ready)
        self.assertIsNone(result.value)
        self.assertEqual('DIVISION_BY_ZERO',result.reason_code)

    def test_cross_requires_immediately_previous_valid_pair_with_equality_allowed(self):
        api=self.api()
        above=api.evaluate_operator('CROSS_ABOVE',(Decimal('3'),Decimal('2')),
                                     previous_values=(Decimal('2'),Decimal('2')))
        self.assertIs(True,above.value)
        below=api.evaluate_operator('CROSS_BELOW',(Decimal('1'),Decimal('2')),
                                     previous_values=(Decimal('2'),Decimal('2')))
        self.assertIs(True,below.value)
        self.assertIs(False,api.evaluate_operator('CROSS_ABOVE',(Decimal('3'),Decimal('2')),
                                                 previous_values=(Decimal('3'),Decimal('2'))).value)
        missing=api.evaluate_operator('CROSS_ABOVE',(Decimal('3'),Decimal('2')),previous_values=(None,Decimal('2')))
        self.assertFalse(missing.ready)
        self.assertEqual('INSUFFICIENT_HISTORY',missing.reason_code)

    def test_explicit_lag_and_rolling_exclude_current_when_requested(self):
        api=self.api()
        values=tuple(Decimal(value) for value in ('1','3','2','100'))
        self.assertEqual(Decimal('2'),api.evaluate_series_operator('LAG',values,lag_bars=1).value)
        self.assertEqual(Decimal('3'),api.evaluate_series_operator('ROLLING_MAX',values,window=2,lag_bars=1).value)
        self.assertEqual(Decimal('2'),api.evaluate_series_operator('ROLLING_MIN',values,window=2,lag_bars=1).value)
        self.assertFalse(api.evaluate_series_operator('ROLLING_MIN',(None,Decimal('2')),window=2,lag_bars=0).ready)
        self.assertFalse(api.evaluate_series_operator('LAG',(Decimal('1'),),lag_bars=1).ready)

    def test_operator_context_input_bounds_and_arity(self):
        api=self.api()
        with localcontext() as context:
            context.prec=3
            value=api.evaluate_operator('DIV',(Decimal('1'),Decimal('3'))).value
        self.assertEqual(Decimal('0.3333333333333333333333333333333333'),value)
        for name,values in (('ADD',(Decimal('1'),)),('NOT',(Decimal('1'),)),('DIV',(1.0,Decimal('2')))):
            result=api.evaluate_operator(name,values)
            self.assertFalse(result.ready)
            self.assertEqual('INVALID_OPERATOR_INPUT',result.reason_code)
        with self.assertRaises(ValueError): api.evaluate_series_operator('LAG',(Decimal('1'),),lag_bars=-1)

