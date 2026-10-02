from dataclasses import dataclass
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re

from application.cloud.manifest import safe_relative
from application.cloud.protocol import CloudError
from application.cloud.safe_files import _windows_read,_posix_read

class DatasetError(ValueError):
    def __init__(self,code): self.code=code; super().__init__(code)

def fail(code): raise DatasetError(code)
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(raw): return 'sha256:'+hashlib.sha256(raw).hexdigest()
def z(value): return value.isoformat().replace('+00:00','Z')
def utc(value):
    if not isinstance(value,str) or len(value)>40 or not value.endswith('Z'): fail('INVALID_UTC')
    try: result=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError: fail('INVALID_UTC')
    if result.utcoffset().total_seconds()!=0: fail('INVALID_UTC')
    return result.astimezone(timezone.utc)
def text(value):
    if not isinstance(value,str) or not 1<=len(value)<=256 or any(ord(c)<32 for c in value): fail('INVALID_TEXT')
    return value
def hash_value(value):
    if not isinstance(value,str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',value): fail('INVALID_HASH')
    return value
def exact(value,keys):
    if not isinstance(value,dict) or set(value)!=set(keys): fail('INVALID_MANIFEST_FIELDS')
def positive_int(value,maximum):
    if type(value) is not int or not 1<=value<=maximum: fail('INVALID_INTEGER')
    return value
def read_local(root,relative,limit):
    try:
        safe_relative(relative)
        path=Path(root).absolute()/relative
        return (_windows_read if os.name=='nt' else _posix_read)(path,limit)
    except CloudError as error: fail(error.reason)
def decode(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result: fail('DUPLICATE_FIELD')
            result[key]=value
        return result
    try: result=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:fail('INVALID_JSON_NUMBER'))
    except (ValueError,UnicodeError,RecursionError): fail('INVALID_JSON')
    stack=[(result,0)]; count=0
    while stack:
        value,depth=stack.pop(); count+=1
        if count>8192 or depth>32: fail('MANIFEST_COMPLEXITY_LIMIT')
        if isinstance(value,float): fail('BINARY_FLOAT_FORBIDDEN')
        if isinstance(value,dict): stack.extend((child,depth+1) for child in value.values())
        if isinstance(value,list): stack.extend((child,depth+1) for child in value)
    return result

@dataclass(frozen=True)
class DatasetManifest:
    canonical_json: str
    manifest_hash: str
    def as_dict(self): return json.loads(self.canonical_json)

class DatasetCatalog:
    def __init__(self,root): self.root=Path(root).absolute(); self._identities={}
    def load(self,relative):
        raw=decode(read_local(self.root,relative,65536))
        exact(raw,('schema_version','dataset_id','dataset_version','namespace','symbol','source_instrument',
                   'normalization_version','alignment','availability_model','information_cutoff','units','candles','funding','created_at'))
        if raw['schema_version']!='r7-dataset-v0.2' or raw['normalization_version']!='r7-canonical-e1-v0.2': fail('UNSUPPORTED_DATASET_PROFILE')
        for key in ('dataset_id','dataset_version','symbol','source_instrument'): text(raw[key])
        if raw['namespace'] not in ('FIXTURE','LOCAL_RESEARCH'): fail('INVALID_DATASET_NAMESPACE')
        if raw['alignment']!='UTC': fail('INVALID_ALIGNMENT')
        if raw['availability_model'] not in ('recorded_received_at','historical_close_assumption'): fail('INVALID_AVAILABILITY_MODEL')
        utc(raw['information_cutoff']); utc(raw['created_at'])
        expected=dict(price='USDT_PER_BASE',volume='BASE',quantity='BASE',settlement='USDT',instrument_type='LINEAR_PERPETUAL')
        if raw['units']!=expected: fail('UNSUPPORTED_CONTRACT_OR_COST_UNITS')
        if not isinstance(raw['candles'],list) or not 1<=len(raw['candles'])<=4: fail('INVALID_CANDLE_CONTAINERS')
        timeframes=set(); paths=set()
        from market_data.timeframes import SUPPORTED_TIMEFRAMES,is_timeframe_aligned
        for container in raw['candles']:
            exact(container,('path','timeframe','start','end','rows','finalized_rows','missing_ranges','duplicate_ranges','logical_hash','byte_hash'))
            timeframe=container['timeframe']
            if not isinstance(timeframe,str) or timeframe not in SUPPORTED_TIMEFRAMES or timeframe in timeframes: fail('INVALID_TIMEFRAME')
            timeframes.add(timeframe)
            try: safe_relative(container['path'])
            except CloudError: fail('INVALID_CONTAINER_PATH')
            if not container['path'].endswith('.parquet') or container['path'] in paths: fail('INVALID_CONTAINER_PATH')
            paths.add(container['path'])
            start,end=utc(container['start']),utc(container['end'])
            if start>=end or not is_timeframe_aligned(start,timeframe) or not is_timeframe_aligned(end,timeframe): fail('INVALID_CONTAINER_RANGE')
            positive_int(container['rows'],200000)
            if type(container['finalized_rows']) is not int or container['finalized_rows']!=container['rows']: fail('UNFINALIZED_COVERAGE')
            if container['missing_ranges']!=[] or container['duplicate_ranges']!=[]: fail('INCOMPLETE_COVERAGE')
            hash_value(container['byte_hash']); hash_value(container['logical_hash'])
        funding=raw['funding']
        if not isinstance(funding,dict) or not isinstance(funding.get('mode'),str): fail('INVALID_FUNDING_PROFILE')
        if funding['mode']=='MISSING': exact(funding,('mode',))
        elif funding['mode']=='RECORDED':
            exact(funding,('mode','path','start','end','rows','interval_seconds','logical_hash','byte_hash','rate_unit','notional_basis'))
            try: safe_relative(funding['path'])
            except CloudError: fail('INVALID_CONTAINER_PATH')
            if not funding['path'].endswith('.parquet') or funding['path'] in paths: fail('INVALID_CONTAINER_PATH')
            positive_int(funding['rows'],200000); positive_int(funding['interval_seconds'],86400)
            if funding['rate_unit']!='FRACTION_PER_EVENT' or funding['notional_basis']!='ENTRY_FILL_PRICE_X_BASE_QUANTITY': fail('UNSUPPORTED_FUNDING_UNITS')
            start,end=utc(funding['start']),utc(funding['end'])
            if start>=end: fail('INVALID_FUNDING_COVERAGE')
            hash_value(funding['byte_hash']); hash_value(funding['logical_hash'])
        else: fail('UNSUPPORTED_FUNDING_PROFILE')
        serialized=canonical(raw); identity=(raw['dataset_id'],raw['dataset_version']); identity_hash=digest(serialized.encode())
        if identity in self._identities and self._identities[identity]!=identity_hash: fail('IMMUTABLE_DATASET_IDENTITY_CHANGED')
        self._identities[identity]=identity_hash
        return DatasetManifest(serialized,identity_hash)
