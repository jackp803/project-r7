import copy
import json
import unittest

from strategy import StrategyValidationError, compute_content_hash, parse_strategy_definition
from tests.strategy.v02_fixtures import definition_v02, field, operator


class V02ParserTests(unittest.TestCase):
    def test_oversized_or_deep_json_is_structured_before_parsing(self):
        for payload,code in ((b' '*262145,'PAYLOAD_SIZE_LIMIT'),
                             ('['*1500+'0'+']'*1500,'INVALID_JSON'),
                             (b'\xff','INVALID_JSON')):
            with self.subTest(code=code):
                with self.assertRaises(StrategyValidationError) as caught:
                    parse_strategy_definition(payload)
                self.assertEqual(code,caught.exception.code)

    def test_ast_node_limit_includes_all_declared_features(self):
        value=definition_v02()
        expression=field()
        for _ in range(31): expression=operator('ABS',expression)
        value['rules']['features']={'f'+str(i):copy.deepcopy(expression) for i in range(128)}
        value['rules']['long']=operator('GT',field(),field())
        value['rules']['short']=operator('LT',field(),field())
        self.reject(value,'AST_NODE_LIMIT')

    def test_malformed_parameter_reference_returns_typed_error(self):
        value=definition_v02()
        value['rules']['features']['trend']['parameters']['window']={'kind':'parameter','name':[]}
        self.reject(value,'INVALID_IDENTIFIER')

    def test_python_decimal_notation_and_nonfinite_values_are_forbidden(self):
        for text in ('1_0','NaN','Infinity','-'+'1'*35,'1e9999999'):
            with self.subTest(value=text):
                value=definition_v02()
                value['rules']['exit_policy']['stop']['value']=text
                with self.assertRaises(StrategyValidationError) as caught:
                    parse_strategy_definition(value)
                self.assertEqual('INVALID_DECIMAL',caught.exception.code)

    def reject(self,value,code):
        value["content_hash"]=compute_content_hash(value)
        with self.assertRaises(StrategyValidationError) as caught:
            parse_strategy_definition(value)
        self.assertEqual(code,caught.exception.code)

    def test_v02_routes_to_distinct_profile_without_changing_legacy_export(self):
        import strategy
        parsed=parse_strategy_definition(definition_v02())
        self.assertEqual("0.2.0",parsed.runtime_version)
        self.assertEqual("4h",parsed.evaluation_timeframe)
        self.assertEqual("r7-decimal34-v1",parsed.arithmetic_profile)
        self.assertEqual("0.1.0",strategy.RUNTIME_VERSION)

    def test_unknown_version_and_mixed_runtime_profile_are_rejected(self):
        value=definition_v02()
        value["rules"]["dsl_version"]="0.3"
        self.reject(value,"UNSUPPORTED_DSL_VERSION")
        value=definition_v02()
        value["runtime_compatibility"]["runtime_version"]="0.1.0"
        self.reject(value,"RUNTIME_INCOMPATIBLE")

    def test_unknown_keys_operator_arity_and_indicator_version(self):
        for change,code in (
            (lambda v:v["rules"]["long"].update(python="print('forbidden')"),"INVALID_AST_FIELDS"),
            (lambda v:v["rules"]["long"].update(args=[field()]),"INVALID_OPERATOR_ARITY"),
            (lambda v:v["rules"]["features"]["trend"].update(semantic_version="r7-ema-v99"),"UNSUPPORTED_PRIMITIVE_VERSION"),
            (lambda v:v["rules"]["long"].update(name="EXEC"),"UNSUPPORTED_OPERATOR"),
        ):
            with self.subTest(code=code):
                value=definition_v02()
                change(value)
                self.reject(value,code)

    def test_cycle_and_unknown_feature_reference(self):
        value=definition_v02()
        value["rules"]["features"]={"a":{"kind":"feature","name":"b"},"b":{"kind":"feature","name":"a"}}
        value["rules"]["long"]=operator("GT",field(),{"kind":"feature","name":"a"})
        value["rules"]["short"]=operator("LT",field(),{"kind":"feature","name":"a"})
        self.reject(value,"FEATURE_CYCLE")
        value=definition_v02()
        value["rules"]["long"]["args"][1]["name"]="missing"
        self.reject(value,"UNKNOWN_FEATURE")

    def test_price_and_volume_units_cannot_be_compared_or_added(self):
        for name in ("GT","ADD"):
            with self.subTest(operator=name):
                value=definition_v02()
                expression=operator(name,field("close"),field("volume"))
                if name == "GT": value["rules"]["long"]=expression
                else: value["rules"]["features"]["trend"]=expression
                self.reject(value,"INVALID_UNITS")

    def test_window_lag_and_feature_count_security_limits(self):
        for window in (0,10001,True):
            with self.subTest(window=window):
                value=definition_v02()
                value["rules"]["features"]["trend"]["parameters"]["window"]=window
                self.reject(value,"INVALID_WINDOW")
        value=definition_v02()
        value["rules"]["features"]["trend"]={"kind":"lag","source":field(),"bars":-1}
        self.reject(value,"INVALID_LAG")
        value=definition_v02()
        value["rules"]["features"]={"f"+str(i):field() for i in range(129)}
        self.reject(value,"FEATURE_LIMIT")

    def test_ast_depth_is_bounded_before_recursive_evaluation(self):
        value=definition_v02()
        expression=field()
        for _ in range(34): expression=operator("ABS",expression)
        value["rules"]["features"]["trend"]=expression
        self.reject(value,"AST_DEPTH_LIMIT")

    def test_decimal_serialization_is_canonical_under_new_profile_only(self):
        first=definition_v02()
        first["rules"]["exit_policy"]["stop"]["value"]="10.00"
        second=copy.deepcopy(first)
        second["rules"]["exit_policy"]["stop"]["value"]="10"
        self.assertEqual(compute_content_hash(first),compute_content_hash(second))

    def test_duplicate_json_key_is_rejected_and_float_is_not_financial_input(self):
        value=definition_v02()
        raw=json.dumps(value)
        raw=raw.replace('"dsl_version": "0.2"','"dsl_version": "0.2", "dsl_version": "0.2"')
        with self.assertRaises(StrategyValidationError) as caught:
            parse_strategy_definition(raw)
        self.assertEqual("DUPLICATE_JSON_KEY",caught.exception.code)
        value=definition_v02()
        value["rules"]["exit_policy"]["stop"]["value"]=10.5
        with self.assertRaises(StrategyValidationError) as caught:
            parse_strategy_definition(value)
        self.assertEqual("BINARY_FLOAT_FORBIDDEN",caught.exception.code)
