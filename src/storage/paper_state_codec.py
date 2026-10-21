"""Pure lossless physical checkpoint codec; no persistence or financial authority.

Logical JSON hashes are unchanged. Closed envelopes bind run/revision and the
exact predecessor hash; decoding traverses at most127 deltas. The E6 caller still
validates complete broker/runtime state and owns transactions/audit/admission.
"""
import base64
import hashlib
import json
import re
import zlib

CODEC='r7-paper-state-zlib-delta-v0.1'
KEYFRAME_INTERVAL=128
MAX_PAYLOAD=16*1024**2
MAX_ENCODED=24*1024**2
MAX_DELTA_PAYLOAD=64*1024
MAX_CHAIN_BYTES=32*1024**2
_HASH=re.compile(r'sha256:[0-9a-f]{64}\Z')
_FIELDS={'codec','run_id','revision','kind','payload_bytes','payload_hash','data'}


def _fail(reason):raise ValueError('PAPER_STATE_CODEC_'+reason)


def _digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()


def _pairs(items):
    value={}
    for key,item in items:
        if key in value:_fail('DUPLICATE_KEY')
        value[key]=item
    return value


def _constant(value):_fail('NONFINITE_JSON')


def _loads(raw):
    try:return json.loads(raw,object_pairs_hook=_pairs,parse_constant=_constant)
    except (ValueError,RecursionError,UnicodeError) as error:
        if isinstance(error,ValueError) and str(error).startswith('PAPER_STATE_CODEC_'):raise
        _fail('JSON_INVALID')


def _canonical(value,*,limit=MAX_PAYLOAD):
    try:raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
    except (ValueError,TypeError,RecursionError,UnicodeError):_fail('JSON_INVALID')
    if len(raw)>limit:_fail('PAYLOAD_LIMIT')
    return raw


def _pure(value,*,patch=False):
    stack=[(value,0)];count=0
    while stack:
        item,depth=stack.pop();count+=1
        if depth>(96 if patch else 32) or count>(900000 if patch else 300000):_fail('COMPLEXITY_LIMIT')
        if type(item) is dict:
            for key,child in item.items():
                if type(key) is not str or not key or len(key)>256 or '\x00' in key:_fail('KEY_INVALID')
                stack.append((child,depth+1))
        elif type(item) is list:stack.extend((child,depth+1) for child in item)
        elif type(item) is str:
            if len(item)>4096 or '\x00' in item:_fail('TEXT_LIMIT')
        elif type(item) is int:
            if abs(item)>2**63-1:_fail('INTEGER_LIMIT')
        elif item is not None and type(item) is not bool:_fail('PURE_JSON_REQUIRED')


def _raw(text,limit):
    if type(text) is not str:_fail('TEXT_REQUIRED')
    if len(text)>limit:_fail('PAYLOAD_LIMIT')
    try:raw=text.encode('utf-8')
    except UnicodeError:_fail('TEXT_INVALID')
    if len(raw)>limit:_fail('PAYLOAD_LIMIT')
    return raw


def _logical(text):
    raw=_raw(text,MAX_PAYLOAD);value=_loads(text);_pure(value)
    if type(value) is not dict or _canonical(value)!=raw:_fail('LOGICAL_CANONICAL_REQUIRED')
    return value,raw


def _identity(run_id,revision):
    if type(run_id) is not str or not run_id.strip() or len(run_id)>256 or '\x00' in run_id:_fail('RUN_INVALID')
    if type(revision) is not int or not 0<=revision<=2**63-1:_fail('REVISION_INVALID')


def _same(left,right):
    # Python equality alone conflates bool and int, including inside containers.
    if type(left) is not type(right):return False
    if type(left) is dict:return left.keys()==right.keys() and all(_same(left[key],right[key]) for key in left)
    if type(left) is list:return len(left)==len(right) and all(_same(a,b) for a,b in zip(left,right))
    return left==right


def _diff(old,new):
    if _same(old,new):return {'op':'same'}
    if type(old) is dict and type(new) is dict:
        return dict(op='object',remove=sorted(old.keys()-new.keys()),
            set={key:_diff(old[key],new[key]) if key in old else dict(op='replace',value=new[key])
                 for key in sorted(new) if key not in old or not _same(old[key],new[key])})
    if type(old) is list and type(new) is list:
        prefix=suffix=0
        while prefix<min(len(old),len(new)) and _same(old[prefix],new[prefix]):prefix+=1
        while suffix<min(len(old),len(new))-prefix and _same(old[-1-suffix],new[-1-suffix]):suffix+=1
        return dict(op='array',prefix=prefix,remove=len(old)-prefix-suffix,suffix=suffix,
            insert=new[prefix:len(new)-suffix])
    return dict(op='replace',value=new)


def _apply(old,change,*,depth=0):
    if depth>32 or type(change) is not dict:_fail('PATCH_INVALID')
    op=change.get('op')
    if op=='same' and set(change)=={'op'}:return old
    if op=='replace' and set(change)=={'op','value'}:return change['value']
    if op=='object' and set(change)=={'op','remove','set'} and type(old) is dict:
        removed,changed=change['remove'],change['set']
        if (type(removed) is not list or type(changed) is not dict
                or any(type(key) is not str for key in removed)
                or len(set(removed))!=len(removed) or any(key not in old for key in removed)
                or set(removed)&changed.keys()):_fail('PATCH_INVALID')
        removed_keys=set(removed)
        value={key:item for key,item in old.items() if key not in removed_keys}
        for key,child in changed.items():
            if key not in old and (type(child) is not dict or child.get('op')!='replace'):_fail('PATCH_INVALID')
            value[key]=_apply(old.get(key),child,depth=depth+1)
        return value
    if op=='array' and set(change)=={'op','prefix','remove','suffix','insert'} and type(old) is list:
        prefix,removed,suffix=change['prefix'],change['remove'],change['suffix']
        if (any(type(item) is not int or item<0 for item in (prefix,removed,suffix))
                or prefix+removed+suffix!=len(old) or type(change['insert']) is not list):_fail('PATCH_INVALID')
        return old[:prefix]+change['insert']+old[len(old)-suffix:]
    _fail('PATCH_INVALID')


def _envelope(payload,*,run_id,revision,kind,base_hash=None):
    value=dict(codec=CODEC,run_id=run_id,revision=revision,kind=kind,payload_bytes=len(payload),
        payload_hash=_digest(payload),data=base64.b64encode(zlib.compress(payload,1)).decode('ascii'))
    if kind=='DELTA':value.update(base_revision=revision-1,base_hash=base_hash)
    return _canonical(value,limit=MAX_ENCODED).decode('utf-8')


def encode_state(raw,*,run_id,revision,previous_raw=None):
    """Encode already-owner-validated logical state; does not grant admission."""
    _identity(run_id,revision);value,payload=_logical(raw)
    keyframe=_envelope(payload,run_id=run_id,revision=revision,kind='KEYFRAME')
    if revision%KEYFRAME_INTERVAL==0 or previous_raw is None:return keyframe
    previous,previous_bytes=_logical(previous_raw)
    delta=_diff(previous,value)
    try:patch=_canonical(delta)
    except ValueError as error:
        if str(error)=='PAPER_STATE_CODEC_PAYLOAD_LIMIT':return keyframe
        raise
    if len(patch)>MAX_DELTA_PAYLOAD:return keyframe
    encoded=_envelope(patch,run_id=run_id,revision=revision,kind='DELTA',base_hash=_digest(previous_bytes))
    return encoded if len(encoded)<len(keyframe) else keyframe


def _unpack(encoded,run_id,revision):
    raw=_raw(encoded,MAX_ENCODED);value=_loads(encoded)
    if type(value) is not dict or value.get('kind') not in ('KEYFRAME','DELTA'):_fail('ENVELOPE_INVALID')
    delta=value['kind']=='DELTA'
    if (set(value)!=(_FIELDS|{'base_revision','base_hash'} if delta else _FIELDS)
            or value['codec']!=CODEC or value['run_id']!=run_id
            or type(value['revision']) is not int or value['revision']!=revision
            or type(value['payload_bytes']) is not int or not 1<=value['payload_bytes']<=MAX_PAYLOAD
            or type(value['payload_hash']) is not str or not _HASH.fullmatch(value['payload_hash'])
            or type(value['data']) is not str or _canonical(value,limit=MAX_ENCODED)!=raw):_fail('ENVELOPE_INVALID')
    if delta and (revision%KEYFRAME_INTERVAL==0 or type(value['base_revision']) is not int
            or value['base_revision']!=revision-1 or type(value['base_hash']) is not str
            or not _HASH.fullmatch(value['base_hash']) or value['payload_bytes']>MAX_DELTA_PAYLOAD):_fail('BASE_INVALID')
    try:
        compressed=base64.b64decode(value['data'],validate=True)
        if base64.b64encode(compressed).decode('ascii')!=value['data']:_fail('BASE64_INVALID')
        inflater=zlib.decompressobj();payload=inflater.decompress(compressed,value['payload_bytes']+1)
    except (ValueError,zlib.error):_fail('COMPRESSED_INVALID')
    if (len(payload)!=value['payload_bytes'] or inflater.unconsumed_tail or inflater.unused_data
            or not inflater.eof or _digest(payload)!=value['payload_hash']):_fail('PAYLOAD_INVALID')
    try:text=payload.decode('utf-8')
    except UnicodeError:_fail('PAYLOAD_INVALID')
    parsed=_loads(text);_pure(parsed,patch=delta)
    if _canonical(parsed)!=payload:_fail('PAYLOAD_CANONICAL_REQUIRED')
    return value,parsed,text


def decode_state(encoded,*,run_id,revision,expected_hash,read_previous):
    """Reconstruct exact logical JSON, validating every bounded chain link."""
    _identity(run_id,revision)
    if type(expected_hash) is not str or not _HASH.fullmatch(expected_hash) or not callable(read_previous):_fail('HASH_OR_READER_INVALID')
    chain=[];current=encoded;wanted=expected_hash;at=revision;chain_bytes=0
    while True:
        if len(chain)>=KEYFRAME_INTERVAL:_fail('CHAIN_LIMIT')
        envelope,value,text=_unpack(current,run_id,at)
        chain_bytes+=envelope['payload_bytes']
        if chain_bytes>MAX_CHAIN_BYTES:_fail('CHAIN_BYTES_LIMIT')
        chain.append((envelope['kind'],value,wanted))
        if envelope['kind']=='KEYFRAME':break
        at=envelope['base_revision'];wanted=envelope['base_hash']
        try:row=read_previous(at)
        except (KeyError,IndexError,ValueError,TypeError,OSError):_fail('BASE_UNAVAILABLE')
        if type(row) is not tuple or len(row)!=2 or row[1]!=wanted:_fail('BASE_INVALID')
        current=row[0]
    state=None;result=None
    for kind,value,wanted in reversed(chain):
        if kind=='KEYFRAME':state=value
        else:state=_apply(state,value)
        _pure(state);raw=_canonical(state)
        if type(state) is not dict or _digest(raw)!=wanted:_fail('STATE_HASH_MISMATCH')
        result=raw.decode('utf-8')
    return result


def verify_write_state(encoded,*,run_id,revision,expected_hash,previous_raw=None):
    """Verify a new encoding before commit using an E6-verified logical base.

    This pure function is NOT a persistent reader/audit shortcut. Actual stored
    reads still use decode_state and validate every original predecessor link.
    """
    _identity(run_id,revision)
    if type(expected_hash) is not str or not _HASH.fullmatch(expected_hash):_fail('HASH_OR_READER_INVALID')
    envelope,value,text=_unpack(encoded,run_id,revision)
    if envelope['kind']=='DELTA':
        if previous_raw is None:_fail('BASE_UNAVAILABLE')
        previous,raw=_logical(previous_raw)
        if _digest(raw)!=envelope['base_hash']:_fail('BASE_INVALID')
        value=_apply(previous,value)
    _pure(value);raw=_canonical(value)
    if type(value) is not dict or _digest(raw)!=expected_hash:_fail('STATE_HASH_MISMATCH')
    return raw.decode('utf-8')
