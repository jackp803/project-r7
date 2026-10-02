"""Bounded immutable protocol primitives for E3 research assessments."""
from dataclasses import dataclass
from datetime import datetime,timezone
import hashlib
import json
import re
from indicators.v02.common import finite_decimal,canonical_decimal

class RobustnessError(ValueError):
    def __init__(self,code): self.code=code; super().__init__(code)
def fail(code): raise RobustnessError(code)
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(value): return 'sha256:'+hashlib.sha256(value if isinstance(value,bytes) else canonical(value).encode()).hexdigest()
def freeze(value,limit=262144):
    try: raw=canonical(value)
    except (TypeError,ValueError,RecursionError): fail('INVALID_RESEARCH_PROTOCOL')
    if len(raw.encode())>limit: fail('RESEARCH_PROTOCOL_SIZE_LIMIT')
    frozen=json.loads(raw); stack=[(frozen,0)]; count=0
    while stack:
        item,depth=stack.pop(); count+=1
        if depth>32 or count>8192: fail('RESEARCH_PROTOCOL_COMPLEXITY_LIMIT')
        if isinstance(item,float): fail('BINARY_FLOAT_FORBIDDEN')
        if isinstance(item,dict): stack.extend((v,depth+1) for v in item.values())
        if isinstance(item,list): stack.extend((v,depth+1) for v in item)
    return frozen
def exact(value,keys):
    if not isinstance(value,dict) or set(value)!=set(keys): fail('INVALID_RESEARCH_POLICY_FIELDS')
def integer(value,minimum,maximum):
    if type(value) is not int or not minimum<=value<=maximum: fail('INVALID_RESEARCH_INTEGER')
    return value
def text(value):
    if not isinstance(value,str) or not 1<=len(value)<=256 or any(ord(c)<32 for c in value): fail('INVALID_RESEARCH_TEXT')
    return value
def hash_value(value):
    if not isinstance(value,str) or not re.fullmatch('sha256:[0-9a-f]{64}',value): fail('INVALID_RESEARCH_HASH')
    return value
def decimal(value,*,minimum=None,maximum=None):
    try: number=finite_decimal(value)
    except ValueError: fail('INVALID_RESEARCH_DECIMAL')
    if minimum is not None and number<minimum or maximum is not None and number>maximum: fail('RESEARCH_DECIMAL_OUT_OF_RANGE')
    return number
def dec_text(value): return canonical_decimal(str(value))
def utc(value):
    if not isinstance(value,str) or len(value)>40 or not value.endswith('Z'): fail('INVALID_RESEARCH_UTC')
    try: return datetime.fromisoformat(value[:-1]+'+00:00').astimezone(timezone.utc)
    except ValueError: fail('INVALID_RESEARCH_UTC')
def z(value): return value.isoformat().replace('+00:00','Z')

@dataclass(frozen=True)
class RobustnessAssessment:
    canonical_json: str
    assessment_hash: str
    def as_dict(self): return json.loads(self.canonical_json)
def assessment(document):
    raw=canonical(document)
    return RobustnessAssessment(raw,digest(raw.encode()))
