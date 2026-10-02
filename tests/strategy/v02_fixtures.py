from tests.strategy.test_slice1_runtime import make_definition
from strategy import compute_content_hash


def field(name="close", timeframe="4h"):
    return {"kind":"field", "timeframe":timeframe, "field":name}


def operator(name, *args):
    return {"kind":"operator", "name":name, "args":list(args)}


def definition_v02():
    value=make_definition()
    value.update(strategy_id="fixture-v02-trend",strategy_version="0.2.0",required_timeframes=["4h"],parameters={"fast_window":2})
    value["runtime_compatibility"]["runtime_version"]="0.2.0"
    value["rules"]={
        "dsl_version":"0.2", "behavior_profile":"r7-closed-bar-v0.2", "evaluation_timeframe":"4h",
        "features":{"trend":{"kind":"indicator","name":"EMA","semantic_version":"r7-ema-v1", "source":field(),"parameters":{"window":2},"output":"value"}},
        "long":operator("GT",field(),{"kind":"feature","name":"trend"}),
        "short":operator("LT",field(),{"kind":"feature","name":"trend"}),
        "exit_policy":{"stop":{"kind":"fixed_distance","value":"10"}, "target":{"kind":"reward_risk","multiple":"2"}, "trailing":None,"max_hold_seconds":14400},
    }
    value["content_hash"]=compute_content_hash(value)
    return value
