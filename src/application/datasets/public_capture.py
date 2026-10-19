"""Typed private-backup coverage of bounded public acquisition audit bytes.

This validates an archive inventory, never research eligibility or a provider
authentication claim. A prepared receipt alone cannot prove network dispatch.
Incomplete captures remain audit evidence; this validator does not admit them
as dataset inputs.
"""
from pathlib import PurePosixPath
import re
from urllib.parse import urlsplit,parse_qsl,urlencode

from application.cloud.manifest import safe_component
from application.datasets.catalog import canonical,decode,digest,read_local,utc,hash_value,DatasetCatalog
from application.datasets.okx_public import BASE,HISTORY,FUNDING,INSTRUMENT,MAX_RESPONSE,timestamp

_BASE_KEYS={'schema_version','status','start','end','symbol','timeframe','provider','credentials',
    'provider_mutation','private_requests','promotion','volume_mapping','funding_mapping',
    'offline_qualification','reason_code','provider_requests','provider_responses'}
_SUCCESS_KEYS={'dataset_ref','manifest_hash','candle_rows','funding_rows','missing_ranges','duplicate_ranges'}

def require(condition):
    if not condition:raise ValueError('PUBLIC_CAPTURE_INVENTORY_INVALID')
def exact(value,keys):require(isinstance(value,dict) and set(value)==set(keys))
def integer(value,lower,upper):require(type(value) is int and lower<=value<=upper)

def _attempt(value,sequence):
    exact(value,{'method','url','attempt','prepared_at','dispatch_state','authentication','mutation'})
    require(value['method']=='GET' and value['attempt']==sequence and type(value['attempt']) is int)
    require(value['dispatch_state']=='PREPARED_BEFORE_IO' and value['authentication']=='NONE' and value['mutation'] is False)
    utc(value['prepared_at']);url=value['url'];require(isinstance(url,str) and len(url)<=512)
    parts=urlsplit(url)
    require(parts.scheme=='https' and parts.netloc=='www.okx.com' and not parts.fragment and parts.path in (HISTORY,FUNDING))
    pairs=parse_qsl(parts.query,strict_parsing=True);params=dict(pairs)
    require(len(params)==len(pairs) and set(params)==({'instId','after','limit','bar'} if parts.path==HISTORY else {'instId','after','limit'}))
    require(params['instId']==INSTRUMENT and params['limit']=='100' and (parts.path!=HISTORY or params['bar']=='4H'))
    timestamp(params['after'])
    require(url==BASE+parts.path+'?'+urlencode(sorted(params.items())))

def public_capture_inventory(root,base,paths,*,deadline=lambda:None):
    """Return exact allowed refs/hashes and an optional *complete* dataset ref."""
    pieces=PurePosixPath(base).parts
    require(len(pieces)==2 and pieces[0]=='datasets');safe_component(pieces[1])
    prefix=base+'/';members={name[len(prefix):] for name in paths if name.startswith(prefix)}
    require(bool(members));allowed=set();hashes={};records={}
    for name in sorted(members):
        deadline()
        if name in ('acquisition.json','dataset.json','candles.parquet','funding.parquet'):continue
        match=re.fullmatch(r'requests/([0-9]{3})-(attempt\.json|result\.json|failure\.json|response\.bin|partial-response\.bin)',name)
        require(match is not None);sequence=int(match[1]);integer(sequence,1,64)
        records.setdefault(sequence,set()).add(match[2])
    require(sorted(records)==list(range(1,len(records)+1)))
    def raw(name,limit):
        deadline();reference=prefix+name;body=read_local(root,reference,limit)
        allowed.add(reference);hashes[reference]=digest(body);return body
    def document(name):return decode(raw(name,65536))
    summary=document('acquisition.json') if 'acquisition.json' in members else None
    complete=False
    if summary is not None:
        require(isinstance(summary,dict));complete=summary.get('status')=='DATASET_ACQUIRED'
        exact(summary,_BASE_KEYS|_SUCCESS_KEYS if complete else _BASE_KEYS)
        for key,expected in dict(schema_version='r7-public-acquisition-v0.2',provider='OKX_PUBLIC',symbol='BTC_USDT_PERP',
            timeframe='4h',credentials='NONE',promotion='NOT_ASSESSED',offline_qualification='NOT_RUN',
            volume_mapping='OKX_VOL_CCY_BASE_BTC;RAW_VOL_CONTRACTS_RETAINED',funding_mapping='REALIZED_RATE_ONLY').items():
            require(summary[key]==expected)
        for key in ('provider_mutation','private_requests'):integer(summary[key],0,0)
        integer(summary['provider_requests'],0,64);integer(summary['provider_responses'],0,summary['provider_requests'])
        require(summary['provider_requests']==len(records))
        start,end=utc(summary['start']),utc(summary['end'])
        require(start<end and (end-start).total_seconds()<=89*86400 and not start.minute and not start.second and not start.microsecond
                and not end.minute and not end.second and not end.microsecond and start.hour%8==0 and end.hour%4==0)
        if complete:
            require(summary['reason_code'] is None and summary['provider_responses']==summary['provider_requests'])
            require(summary['dataset_ref']=='dataset.json' and summary['missing_ranges']==[] and summary['duplicate_ranges']==[])
            hash_value(summary['manifest_hash'])
            for name in ('candle_rows','funding_rows'):integer(summary[name],1,200000)
        else:
            require(summary['status']=='ACQUISITION_REJECTED' and isinstance(summary['reason_code'],str)
                    and re.fullmatch('[A-Z_]{1,64}',summary['reason_code']) is not None)
    observed_responses=0
    for sequence,kinds in sorted(records.items()):
        require('attempt.json' in kinds)
        name=f'requests/{sequence:03d}-';_attempt(document(name+'attempt.json'),sequence)
        result=None
        if 'result.json' in kinds:
            result=document(name+'result.json');exact(result,{'http_status','received_at','response_hash','response_bytes'})
            integer(result['http_status'],100,599);utc(result['received_at']);hash_value(result['response_hash'])
            integer(result['response_bytes'],0,MAX_RESPONSE);require('response.bin' in kinds)
            body=raw(name+'response.bin',MAX_RESPONSE)
            require(len(body)==result['response_bytes'] and digest(body)==result['response_hash'])
            observed_responses+=1
        elif 'response.bin' in kinds:
            # A crash may occur after body publication but before its receipt.
            require(not complete and sequence==len(records));raw(name+'response.bin',MAX_RESPONSE)
        if 'failure.json' in kinds:
            failure=document(name+'failure.json')
            exact(failure,{'reason_code','http_status','response_complete','retained_prefix_bytes','retained_prefix_hash'})
            require(failure['reason_code']=='PUBLIC_TRANSPORT_UNAVAILABLE' and failure['response_complete'] is False)
            if failure['http_status'] is not None:
                integer(failure['http_status'],100,599)
                if result is None:observed_responses+=1
            integer(failure['retained_prefix_bytes'],0,MAX_RESPONSE);hash_value(failure['retained_prefix_hash'])
            body=raw(name+'partial-response.bin',MAX_RESPONSE) if 'partial-response.bin' in kinds else b''
            require(len(body)==failure['retained_prefix_bytes'] and digest(body)==failure['retained_prefix_hash'])
            require(not complete)
        elif 'partial-response.bin' in kinds:
            require(not complete and sequence==len(records));raw(name+'partial-response.bin',MAX_RESPONSE)
        if complete:require(result is not None and result['http_status']==200 and kinds=={'attempt.json','result.json','response.bin'})
        if result is None and 'failure.json' not in kinds:require(not complete and sequence==len(records))
    if summary is not None:require(summary['provider_responses']>=observed_responses)
    dataset_ref=None
    if complete:
        require({'dataset.json','candles.parquet','funding.parquet'}<=members)
        manifest=document('dataset.json');dataset_ref=prefix+'dataset.json'
        require(digest(canonical(manifest).encode())==summary['manifest_hash'])
        value=DatasetCatalog(root).load(dataset_ref).as_dict()
        require(value['namespace']=='LOCAL_RESEARCH' and value['dataset_id']=='okx-public-btc-4h' and value['source_instrument']==INSTRUMENT
                and value['symbol']=='BTC_USDT_PERP' and len(value['candles'])==1)
        candle=value['candles'][0];funding=value['funding']
        require(candle['path']=='candles.parquet' and candle['timeframe']=='4h' and candle['rows']==summary['candle_rows']
                and candle['start']==summary['start'] and candle['end']==summary['end'])
        require(funding['mode']=='RECORDED' and funding['path']=='funding.parquet' and funding['rows']==summary['funding_rows']
                and funding['start']==summary['start'] and funding['end']==summary['end'] and funding['interval_seconds']==28800)
        for spec in (candle,funding):
            # Existing backup stream/copy verifies bytes against these receipts.
            allowed.add(prefix+spec['path']);hashes[prefix+spec['path']]=spec['byte_hash']
    else:
        for name in ('dataset.json','candles.parquet','funding.parquet'):
            if name in members:raw(name,64*1024*1024)
    require({name[len(prefix):] for name in allowed}==members)
    return allowed,hashes,dataset_ref
