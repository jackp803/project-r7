from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Units:
    price: int=0
    volume: int=0
    boolean: bool=False
    literal: bool=False

    def signature(self): return self.price,self.volume,self.boolean


@dataclass(frozen=True)
class Expression:
    kind: str
    data: Mapping
    children: tuple
    units: Units
    source_timeframes: frozenset[str]
    minimum_history: int=1
    height: int=1


@dataclass(frozen=True)
class ParsedStrategyV02:
    schema_version: str
    strategy_id: str
    strategy_version: str
    name: str
    symbol: str
    required_timeframes: tuple[str,...]
    evaluation_timeframe: str
    parameters: Mapping
    rules: Mapping
    features: Mapping[str,Expression]
    feature_order: tuple[str,...]
    long_expression: Expression
    short_expression: Expression
    exit_policy: Mapping
    runtime_family: str
    runtime_version: str
    content_hash: str
    created_at: str
    canonical_json: str
    arithmetic_profile: str="r7-decimal34-v1"

    @property
    def required_timeframe(self): return self.evaluation_timeframe
