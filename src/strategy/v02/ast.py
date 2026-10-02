"""Strict typed expressions and an acyclic, bounded feature graph."""

import re
from types import MappingProxyType

from indicators.v02.common import finite_decimal
from strategy.runtime import StrategyValidationError
from strategy.v02.models import Expression,Units

IDENTIFIER=re.compile(r"[A-Za-z][A-Za-z0-9_]{0,95}\Z")
PRICE=Units(price=1)
VOLUME=Units(volume=1)
SCALAR=Units()
BOOLEAN=Units(boolean=True)
LITERAL=Units(literal=True)
PRIMITIVE_VERSIONS={"SMA":"r7-sma-v1","EMA":"r7-ema-v1","RSI":"r7-rsi-wilder-v1", "ATR":"r7-atr-wilder-v1", "ADX":"r7-adx-wilder-v1", "MACD":"r7-macd-v1", "BOLLINGER":"r7-bollinger-pop-v1", "DONCHIAN":"r7-donchian-v1"}
OUTPUTS={"SMA":("value",),"EMA":("value",),"RSI":("value",),"ATR":("value",),"ADX":("value","plus_di","minus_di"),"MACD":("line","signal","histogram"),"BOLLINGER":("middle","upper","lower","stddev"),"DONCHIAN":("upper","lower","middle")}
OPERATORS={"GT","GTE","LT","LTE","EQ","AND","OR","NOT","ADD","SUB","MUL","DIV","ABS","MIN","MAX","CROSS_ABOVE","CROSS_BELOW","LAG","ROLLING_MIN","ROLLING_MAX"}


def fail(code): raise StrategyValidationError(code,code)


def exact(value,keys,code="INVALID_AST_FIELDS"):
    if not isinstance(value,dict) or value.keys()!=set(keys): fail(code)


def identifier(value):
    if not isinstance(value,str) or not IDENTIFIER.fullmatch(value): fail("INVALID_IDENTIFIER")
    return value


def compatible(left,right):
    if left.boolean != right.boolean: fail("INVALID_UNITS")
    if left.literal and not right.boolean: return right
    if right.literal and not left.boolean: return left
    if left.signature()!=right.signature(): fail("INVALID_UNITS")
    return left


class AstBuilder:
    def __init__(self,features,parameters,timeframes):
        if not isinstance(features,dict): fail("INVALID_FEATURES")
        if len(features)>128: fail("FEATURE_LIMIT")
        for name in features: identifier(name)
        self.raw_features,self.parameters,self.timeframes=features,parameters,set(timeframes)
        self.features,self.active,self.order={},set(),[]
        self.nodes=0

    def feature(self,name,depth=0):
        identifier(name)
        if name in self.active: fail("FEATURE_CYCLE")
        if name not in self.raw_features: fail("UNKNOWN_FEATURE")
        if name not in self.features:
            self.active.add(name)
            result=self.compile(self.raw_features[name],depth)
            self.active.remove(name)
            self.features[name]=result
            self.order.append(name)
        result=self.features[name]
        if depth+result.height>32: fail("AST_DEPTH_LIMIT")
        return result

    def integer(self,value,*,minimum=1,maximum=10000,code="INVALID_WINDOW"):
        if isinstance(value,dict):
            exact(value,{"kind","name"})
            name=identifier(value['name'])
            if value["kind"]!="parameter" or name not in self.parameters: fail("UNKNOWN_PARAMETER")
            value=self.parameters[value["name"]]
        if type(value) is not int or not minimum<=value<=maximum: fail(code)
        return value

    def timeframe(self,value):
        if not isinstance(value,str) or value not in self.timeframes: fail("UNDECLARED_TIMEFRAME")
        return value

    def compile(self,node,depth=0):
        if depth>=32: fail("AST_DEPTH_LIMIT")
        self.nodes+=1
        if self.nodes>4096: fail("AST_NODE_LIMIT")
        if not isinstance(node,dict) or not isinstance(node.get("kind"),str): fail("INVALID_AST_FIELDS")
        kind=node["kind"]
        children=()
        frames=frozenset()
        history=height=1
        data={}
        if kind=="decimal":
            exact(node,{"kind","value"})
            try: finite_decimal(node["value"])
            except ValueError: fail("INVALID_DECIMAL")
            units=LITERAL
            data={"value":node["value"]}
        elif kind=="parameter":
            exact(node,{"kind","name"})
            name=identifier(node["name"])
            if name not in self.parameters: fail("UNKNOWN_PARAMETER")
            value=self.parameters[name]
            if type(value) is not int: fail("INVALID_PARAMETER_DOMAIN")
            units=SCALAR
            data={"name":name,"value":value}
        elif kind=="field":
            exact(node,{"kind","timeframe","field"})
            timeframe=self.timeframe(node["timeframe"])
            field=node["field"]
            if not isinstance(field,str) or field not in {"open","high","low","close","volume"}: fail("UNSUPPORTED_FIELD")
            units=VOLUME if field=="volume" else PRICE
            frames=frozenset((timeframe,))
            data={"field":field,"timeframe":timeframe}
        elif kind=="feature":
            exact(node,{"kind","name"})
            source=self.feature(node["name"],depth+1)
            units,frames,history=source.units,source.source_timeframes,source.minimum_history
            height=source.height+1
            data={"name":node["name"]}
        elif kind=="lag":
            exact(node,{"kind","source","bars"})
            source=self.compile(node["source"],depth+1)
            bars=self.integer(node["bars"],minimum=0,code="INVALID_LAG")
            units,frames,history=source.units,source.source_timeframes,source.minimum_history+bars
            children=(source,)
            height=source.height+1
            data={"bars":bars}
        elif kind=="indicator":
            name=node.get("name")
            if not isinstance(name,str) or name not in PRIMITIVE_VERSIONS: fail("UNSUPPORTED_PRIMITIVE")
            candle_based=name in {"ATR","ADX","DONCHIAN"}
            exact(node,{"kind","name","semantic_version","parameters","output","timeframe" if candle_based else "source"})
            if node["semantic_version"]!=PRIMITIVE_VERSIONS[name]: fail("UNSUPPORTED_PRIMITIVE_VERSION")
            output=node["output"]
            if output not in OUTPUTS[name]: fail("UNSUPPORTED_PRIMITIVE_OUTPUT")
            parameters=node["parameters"]
            if name=="MACD":
                exact(parameters,{"fast","slow","signal_window"},"INVALID_PRIMITIVE_PARAMETERS")
                values={key:self.integer(value) for key,value in parameters.items()}
                if values["fast"]>=values["slow"]: fail("INVALID_MACD_WINDOWS")
                warmup=values["slow"]+(0 if output=="line" else values["signal_window"]-1)
            elif name=="BOLLINGER":
                exact(parameters,{"window","k"},"INVALID_PRIMITIVE_PARAMETERS")
                window=self.integer(parameters["window"])
                try: positive=finite_decimal(parameters["k"])
                except ValueError: fail("INVALID_MULTIPLIER")
                if positive<=0: fail("INVALID_MULTIPLIER")
                values={"window":window,"k":parameters["k"]}
                warmup=window
            elif name=="DONCHIAN":
                if not isinstance(parameters,dict) or parameters.keys() not in ({"window"},{"window","lag_bars"}): fail("INVALID_PRIMITIVE_PARAMETERS")
                values={"window":self.integer(parameters["window"]),"lag_bars":self.integer(parameters.get("lag_bars",1),minimum=0,code="INVALID_LAG")}
                warmup=values["window"]+values["lag_bars"]
            else:
                exact(parameters,{"window"},"INVALID_PRIMITIVE_PARAMETERS")
                window=self.integer(parameters["window"])
                values={"window":window}
                warmup=window+1 if name=="RSI" else (2*window if name=="ADX" and output=="value" else window+1 if name=="ADX" else window)
            if candle_based:
                timeframe=self.timeframe(node["timeframe"])
                frames=frozenset((timeframe,))
                units=SCALAR if name=="ADX" else PRICE
                data["timeframe"]=timeframe
                history=warmup
            else:
                source=self.compile(node["source"],depth+1)
                if source.units.boolean: fail("INVALID_UNITS")
                if not source.source_timeframes or len(source.source_timeframes)!=1: fail("INDICATOR_SERIES_REQUIRED")
                if name=="RSI" and source.units.signature()!=PRICE.signature(): fail("INVALID_UNITS")
                children=(source,)
                units=SCALAR if name=="RSI" else source.units
                frames=source.source_timeframes
                history=source.minimum_history+warmup-1
                height=source.height+1
            data.update(name=name,semantic_version=node["semantic_version"],parameters=MappingProxyType(values),output=output)
        elif kind=="operator":
            name=node.get("name")
            if not isinstance(name,str) or name not in OPERATORS: fail("UNSUPPORTED_OPERATOR")
            rolling=name in {"ROLLING_MIN","ROLLING_MAX"}
            exact(node,{"kind","name","args","window","lag_bars"} if rolling else {"kind","name","args"})
            args=node["args"]
            lower,upper=(2,128) if name in {"AND","OR","MIN","MAX"} else (1,1) if name in {"ABS","NOT"} or rolling else (2,2)
            if not isinstance(args,list) or not lower<=len(args)<=upper: fail("INVALID_OPERATOR_ARITY")
            children=tuple(self.compile(arg,depth+1) for arg in args)
            frames=frozenset().union(*(child.source_timeframes for child in children))
            history=max(child.minimum_history for child in children)
            height=max(child.height for child in children)+1
            if name in {"AND","OR","NOT"}:
                if any(not child.units.boolean for child in children): fail("INVALID_UNITS")
                units=BOOLEAN
            elif name=="LAG":
                lag_node=children[1]
                if lag_node.kind not in {"parameter","decimal"}: fail("INVALID_LAG")
                try: lag_value=int(str(lag_node.data["value"]))
                except (ValueError,KeyError): fail("INVALID_LAG")
                lag=self.integer(lag_value,minimum=0,code="INVALID_LAG")
                units=children[0].units
                history=children[0].minimum_history+lag
                data["bars"]=lag
            elif name in {"MUL","DIV"}:
                if any(child.units.boolean for child in children): fail("INVALID_UNITS")
                left,right=(child.units for child in children)
                sign=1 if name=="MUL" else -1
                units=Units(left.price+sign*right.price,left.volume+sign*right.volume)
            elif rolling:
                units=children[0].units
                if units.boolean or not frames or len(frames)!=1: fail("INVALID_UNITS")
                window=self.integer(node["window"])
                lag=self.integer(node["lag_bars"],minimum=0,code="INVALID_LAG")
                history+=window+lag-1
                data.update(window=window,lag_bars=lag)
            else:
                units=children[0].units
                if units.boolean and name!="EQ": fail("INVALID_UNITS")
                for child in children[1:]: units=compatible(units,child.units)
                if name in {"GT","GTE","LT","LTE","EQ","CROSS_ABOVE","CROSS_BELOW"}:
                    units=BOOLEAN
                    if name.startswith("CROSS_"): history+=1
            data["name"]=name
        else: fail("UNSUPPORTED_AST_KIND")
        if depth+height>32: fail("AST_DEPTH_LIMIT")
        return Expression(kind,MappingProxyType(data),children,units,frames,history,height)
