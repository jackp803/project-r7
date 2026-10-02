"""Explicit profile compilation; recognition does not confer execution authority."""

from collections.abc import Mapping
import hashlib
import json
from types import MappingProxyType

from indicators.v02.common import canonical_decimal,finite_decimal
from strategy.runtime import (_REQUIRED_DEFINITION_FIELDS, _freeze, _format_utc,
                              _load_definition, _parse_utc, RUNTIME_FAMILY,
                              StrategyValidationError)
from strategy.v02.ast import AstBuilder,BOOLEAN,PRICE,exact,fail,identifier
from strategy.v02.models import ParsedStrategyV02

RUNTIME_VERSION="0.2.0"
DSL_VERSION="0.2"
PAYLOAD_LIMIT=256*1024


def canonical_definition(value):
    """Normalize explicit numeric strings only in the additive profile."""
    def normalize(item,depth=0):
        if depth>128: fail("AST_DEPTH_LIMIT")
        if isinstance(item,float): fail("BINARY_FLOAT_FORBIDDEN")
        if isinstance(item,Mapping):
            result={key:normalize(child,depth+1) for key,child in item.items()}
            kind=result.get("kind")
            fields=("value",) if kind in {"decimal","fixed_price","fixed_distance"} else ("multiple",) if kind in {"reward_risk","atr_multiple"} else ()
            for field in fields:
                if field in result:
                    try: result[field]=canonical_decimal(result[field])
                    except ValueError: fail("INVALID_DECIMAL")
            if kind=="indicator" and result.get("name")=="BOLLINGER" and isinstance(result.get("parameters"),dict) and "k" in result["parameters"]:
                try: result["parameters"]["k"]=canonical_decimal(result["parameters"]["k"])
                except ValueError: fail("INVALID_DECIMAL")
            return result
        if isinstance(item,(list,tuple)): return [normalize(child,depth+1) for child in item]
        return item
    try:
        result=normalize(value)
        serialized=json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
    except StrategyValidationError:
        raise
    except (ValueError,TypeError,RecursionError):
        fail("NON_SERIALIZABLE_STRATEGY")
    if len(serialized.encode("utf-8"))>PAYLOAD_LIMIT: fail("PAYLOAD_SIZE_LIMIT")
    return result


def compute_v02_content_hash(definition):
    material=canonical_definition(definition)
    material.pop("content_hash",None)
    raw=json.dumps(material,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
    return "sha256:"+hashlib.sha256(raw).hexdigest()


def _text(value,maximum=256):
    if not isinstance(value,str) or not value.strip() or len(value)>maximum or any(ord(char)<32 for char in value):
        fail("INVALID_FIELD")
    return value


def _exits(policy,builder):
    exact(policy,{"stop","target","trailing","max_hold_seconds"},"INVALID_EXIT_POLICY")
    for role in ("stop","target","trailing"):
        item=policy[role]
        if item is None: continue
        if not isinstance(item,dict) or not isinstance(item.get("kind"),str): fail("INVALID_EXIT_POLICY")
        kind=item["kind"]
        allowed={"fixed_price","fixed_distance","atr_multiple"}
        if role=="target": allowed.add("reward_risk")
        if role=="trailing": allowed={"fixed_distance"}
        if kind not in allowed: fail("INVALID_EXIT_POLICY")
        keys={"kind","feature","multiple"} if kind=="atr_multiple" else {"kind","multiple"} if kind=="reward_risk" else {"kind","value"}
        exact(item,keys,"INVALID_EXIT_POLICY")
        numeric="multiple" if kind in {"atr_multiple","reward_risk"} else "value"
        try: number=finite_decimal(item[numeric])
        except ValueError: fail("INVALID_EXIT_VALUE")
        if number<=0: fail("INVALID_EXIT_VALUE")
        if kind=="atr_multiple":
            expression=builder.feature(item["feature"])
            while expression.kind=="feature": expression=builder.features[expression.data["name"]]
            if expression.kind!="indicator" or expression.data["name"]!="ATR" or expression.units.signature()!=PRICE.signature():
                fail("ATR_FEATURE_REQUIRED")
    hold=policy["max_hold_seconds"]
    if hold is not None and (type(hold) is not int or not 1<=hold<=31536000): fail("INVALID_MAX_HOLD")


def parse_v02(payload) -> ParsedStrategyV02:
    if isinstance(payload,(str,bytes,bytearray)):
        size=len(payload.encode("utf-8")) if isinstance(payload,str) else len(payload)
        if size>PAYLOAD_LIMIT: fail("PAYLOAD_SIZE_LIMIT")
    raw=canonical_definition(_load_definition(payload))
    if raw.keys()!=_REQUIRED_DEFINITION_FIELDS: fail("INVALID_DEFINITION_FIELDS")
    if raw["schema_version"]!="contracts-v0.1": fail("UNSUPPORTED_SCHEMA_VERSION")
    strategy_id=_text(raw["strategy_id"],96)
    version=_text(raw["strategy_version"],96)
    name=_text(raw["name"])
    symbol=_text(raw["symbol"],128)
    created_at=_format_utc(_parse_utc(raw["created_at"],"created_at"))
    timeframes=raw["required_timeframes"]
    if (not isinstance(timeframes,list) or not 1<=len(timeframes)<=4
            or any(not isinstance(item,str) or item not in {"1m","15m","1h","4h"} for item in timeframes)
            or len(set(timeframes))!=len(timeframes)):
        fail("INVALID_REQUIRED_TIMEFRAMES")
    runtime=raw["runtime_compatibility"]
    if runtime!={"runtime_family":RUNTIME_FAMILY,"runtime_version":RUNTIME_VERSION}: fail("RUNTIME_INCOMPATIBLE")
    rules=raw["rules"]
    exact(rules,{"dsl_version","behavior_profile","evaluation_timeframe","features","long","short","exit_policy"},"INVALID_DSL")
    if rules["dsl_version"]!=DSL_VERSION: fail("UNSUPPORTED_DSL_VERSION")
    if rules["behavior_profile"]!="r7-closed-bar-v0.2": fail("UNSUPPORTED_BEHAVIOR_PROFILE")
    if rules["evaluation_timeframe"] not in timeframes: fail("UNDECLARED_TIMEFRAME")
    parameters=raw["parameters"]
    if not isinstance(parameters,dict) or len(parameters)>128: fail("INVALID_PARAMETER_DOMAIN")
    for key,value in parameters.items():
        identifier(key)
        if type(value) is not int or not -(2**31)<=value<2**31: fail("INVALID_PARAMETER_DOMAIN")
    builder=AstBuilder(rules["features"],parameters,timeframes)
    for feature in sorted(rules["features"]): builder.feature(feature)
    long_expression=builder.compile(rules["long"])
    short_expression=builder.compile(rules["short"])
    if long_expression.units!=BOOLEAN or short_expression.units!=BOOLEAN: fail("BOOLEAN_ENTRY_REQUIRED")
    _exits(rules["exit_policy"],builder)
    computed=compute_v02_content_hash(raw)
    if raw["content_hash"]!=computed: fail("CONTENT_HASH_MISMATCH")
    canonical=json.dumps(raw,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
    return ParsedStrategyV02("contracts-v0.1",strategy_id,version,name,symbol,tuple(timeframes),rules["evaluation_timeframe"],
                             _freeze(parameters),_freeze(rules),MappingProxyType(builder.features),tuple(builder.order),
                             long_expression,short_expression,_freeze(rules["exit_policy"]),RUNTIME_FAMILY,RUNTIME_VERSION,
                             computed,created_at,canonical)
