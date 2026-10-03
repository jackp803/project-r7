"""Bounded production REST mechanics, explicitly composed by trusted local code.

No environment/file secret fallback, implicit credential discovery, redirects,
proxy inheritance, retries or account-setting endpoints. Construction does not
read credentials or open a socket. Product admission remains a separate gate.
"""
from dataclasses import dataclass
import http.client,json,math,re,ssl
from types import MappingProxyType
from urllib.parse import urlencode,urlsplit,parse_qsl
from brokers.okx_demo import OKXCredentials,sign_okx_rest_request,PreparedOKXRequest


class OKXProductionTransportError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)


@dataclass(frozen=True)
class OKXProductionTransportConfig:
    rest_base_url:str
    operator_confirmed_rest_base_url:str
    timeout_seconds:float=10
    maximum_response_bytes:int=1048576

    def __post_init__(self):
        if self.rest_base_url!=self.operator_confirmed_rest_base_url:
            raise OKXProductionTransportError('PROVIDER_DOMAIN_CONFIRMATION_MISMATCH')
        if self.rest_base_url!='https://www.okx.com':
            raise OKXProductionTransportError('PROVIDER_DOMAIN_OUTSIDE_BOUNDED_PROFILE')
        if (isinstance(self.timeout_seconds,bool) or not isinstance(self.timeout_seconds,(int,float)) or
            not math.isfinite(self.timeout_seconds) or not 1<=self.timeout_seconds<=30 or
            type(self.maximum_response_bytes) is not int or not 1024<=self.maximum_response_bytes<=1048576):
            raise OKXProductionTransportError('PROVIDER_TRANSPORT_BOUNDS_REQUIRED')


class LocalSecureCredentialProvider:
    """Trusted OS-vault reader interface; no default reader or automatic enrollment.

    Native composition must supply its explicit OS secure-storage implementation.
    This provider is never constructed from API/cloud JSON. Only the selected
    account's three named items are read, at an authorized operator boundary.
    """
    def __init__(self,*,read_secret):
        if not callable(read_secret):raise OKXProductionTransportError('LOCAL_SECURE_VAULT_REQUIRED')
        self._read=read_secret

    def load(self,handle):
        if not isinstance(handle,str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,63}',handle):
            raise OKXProductionTransportError('LOCAL_CREDENTIAL_HANDLE_INVALID')
        try:
            values=[self._read('r7.okx.'+handle,name) for name in ('api-key','secret-key','passphrase')]
            if any(not isinstance(value,str) or not value or len(value)>4096 or any(c in value for c in '\r\n\x00') for value in values):
                raise ValueError()
            return OKXCredentials(*values)
        except Exception:
            raise OKXProductionTransportError('LOCAL_PROVIDER_CREDENTIALS_UNAVAILABLE') from None


_GET_QUERIES={
    '/api/v5/account/config':set(),'/api/v5/account/positions':{'instId','posId'},
    '/api/v5/trade/order':{'instId','clOrdId','ordId'},
    '/api/v5/trade/orders-pending':{'instId','instType','after','before','limit'},
    '/api/v5/trade/fills':{'instId','instType','after','before','limit'},
    '/api/v5/trade/orders-algo-pending':{'instId','ordType','after','before','limit'},
    '/api/v5/trade/order-algo':{'algoId','algoClOrdId'},
}
_POST_PATHS={'/api/v5/trade/order','/api/v5/trade/order-algo','/api/v5/trade/cancel-order','/api/v5/trade/cancel-algos'}
_DECIMAL=re.compile(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+)?')


def _query(path,query):
    if not isinstance(query,dict) or not set(query)<=_GET_QUERIES[path]:raise OKXProductionTransportError('PROVIDER_QUERY_OUTSIDE_PROFILE')
    required={
        '/api/v5/account/positions':{'instId'},'/api/v5/trade/order':{'instId'},
        '/api/v5/trade/orders-pending':{'instId','instType'},'/api/v5/trade/fills':{'instId','instType'},
        '/api/v5/trade/orders-algo-pending':{'instId','ordType'},
    }.get(path,set())
    if not required<=set(query):raise OKXProductionTransportError('PROVIDER_READBACK_SCOPE_REQUIRED')
    if path=='/api/v5/trade/order' and len(set(query)&{'clOrdId','ordId'})!=1:raise OKXProductionTransportError('PROVIDER_EXACT_ORDER_IDENTITY_REQUIRED')
    if path=='/api/v5/trade/order-algo' and len(set(query)&{'algoClOrdId','algoId'})!=1:raise OKXProductionTransportError('PROVIDER_EXACT_ORDER_IDENTITY_REQUIRED')
    for key,value in query.items():
        if not isinstance(value,str) or len(value)>64:raise OKXProductionTransportError('PROVIDER_QUERY_OUTSIDE_PROFILE')
        valid={'instId':value=='BTC-USDT-SWAP','instType':value=='SWAP','ordType':value=='conditional',
               'limit':value.isascii() and value.isdecimal() and 1<=int(value)<=100}
        if key in valid:
            if not valid[key]:raise OKXProductionTransportError('PROVIDER_QUERY_OUTSIDE_PROFILE')
        elif key in ('clOrdId','algoClOrdId'):
            if not re.fullmatch('[A-Za-z0-9]{1,32}',value):raise OKXProductionTransportError('PROVIDER_QUERY_OUTSIDE_PROFILE')
        elif not re.fullmatch('[0-9]{1,64}',value):raise OKXProductionTransportError('PROVIDER_QUERY_OUTSIDE_PROFILE')


def _body(path,body):
    if path=='/api/v5/trade/cancel-algos':
        if not isinstance(body,list) or len(body)!=1 or not isinstance(body[0],dict) or set(body[0])!={'instId','algoId'} or body[0]['instId']!='BTC-USDT-SWAP' or not isinstance(body[0]['algoId'],str) or not re.fullmatch('[0-9]{1,64}',body[0]['algoId']):
            raise OKXProductionTransportError('PROVIDER_BODY_OUTSIDE_PROFILE')
        return
    if not isinstance(body,dict):raise OKXProductionTransportError('PROVIDER_BODY_OUTSIDE_PROFILE')
    if path=='/api/v5/trade/cancel-order':
        if set(body)!={'instId','clOrdId'} or body['instId']!='BTC-USDT-SWAP' or not isinstance(body['clOrdId'],str) or not re.fullmatch('[A-Za-z0-9]{1,32}',body['clOrdId']):raise OKXProductionTransportError('PROVIDER_BODY_OUTSIDE_PROFILE')
        return
    required={'instId','tdMode','posSide','side','ordType','sz','clOrdId'}
    if path.endswith('order-algo'):required=(required-{'clOrdId'})|{'algoClOrdId','slTriggerPx','slOrdPx','slTriggerPxType','reduceOnly'}
    if not required<=set(body) or not set(body)<=required|{'reduceOnly'}:raise OKXProductionTransportError('PROVIDER_BODY_OUTSIDE_PROFILE')
    if body['instId']!='BTC-USDT-SWAP' or body['tdMode']!='isolated' or body['posSide']!='net' or body['side'] not in ('buy','sell'):
        raise OKXProductionTransportError('PROVIDER_BODY_OUTSIDE_PROFILE')
    from decimal import Decimal
    if not isinstance(body['sz'],str) or len(body['sz'])>128 or not _DECIMAL.fullmatch(body['sz']) or Decimal(body['sz'])<=0:raise OKXProductionTransportError('PROVIDER_BODY_OUTSIDE_PROFILE')
    key='algoClOrdId' if path.endswith('order-algo') else 'clOrdId'
    if not isinstance(body[key],str) or not re.fullmatch('[A-Za-z0-9]{1,32}',body[key]):raise OKXProductionTransportError('PROVIDER_BODY_OUTSIDE_PROFILE')
    if path.endswith('order-algo'):
        if body['ordType']!='conditional' or body['slOrdPx']!='-1' or body['slTriggerPxType']!='last' or body['reduceOnly'] is not True or not isinstance(body['slTriggerPx'],str) or len(body['slTriggerPx'])>128 or not _DECIMAL.fullmatch(body['slTriggerPx']) or Decimal(body['slTriggerPx'])<=0:
            raise OKXProductionTransportError('PROVIDER_BODY_OUTSIDE_PROFILE')
    elif body['ordType']!='market' or ('reduceOnly' in body and type(body['reduceOnly']) is not bool):raise OKXProductionTransportError('PROVIDER_BODY_OUTSIDE_PROFILE')


def prepare_production_private_request(config,credentials,*,method,path,timestamp,query=None,body=None):
    if not isinstance(config,OKXProductionTransportConfig) or not isinstance(credentials,OKXCredentials):raise OKXProductionTransportError('EXPLICIT_PROVIDER_COMPOSITION_REQUIRED')
    if method=='GET' and path in _GET_QUERIES:
        if body is not None:raise OKXProductionTransportError('READ_ONLY_BODY_FORBIDDEN')
        query={} if query is None else query;_query(path,query)
        request_path=path+('?' +urlencode(sorted(query.items())) if query else '');body_text=''
    elif method=='POST' and path in _POST_PATHS:
        if query:raise OKXProductionTransportError('MUTATION_QUERY_FORBIDDEN')
        _body(path,body);request_path=path;body_text=json.dumps(body,sort_keys=True,separators=(',',':'),allow_nan=False)
    else:raise OKXProductionTransportError('PROVIDER_ENDPOINT_OUTSIDE_PROFILE')
    if not isinstance(timestamp,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z',timestamp):raise OKXProductionTransportError('PROVIDER_UTC_TIMESTAMP_REQUIRED')
    for value in (credentials.api_key,credentials.secret_key,credentials.passphrase):
        if len(value)>4096 or any(c in value for c in '\r\n\x00'):raise OKXProductionTransportError('PROVIDER_CREDENTIAL_FORMAT_INVALID')
    headers={'Content-Type':'application/json','OK-ACCESS-KEY':credentials.api_key,'OK-ACCESS-PASSPHRASE':credentials.passphrase,
             'OK-ACCESS-TIMESTAMP':timestamp,'OK-ACCESS-SIGN':sign_okx_rest_request(secret_key=credentials.secret_key,timestamp=timestamp,method=method,request_path=request_path,body_text=body_text)}
    return PreparedOKXRequest(method,request_path,body_text,MappingProxyType(headers),True)


def _unique(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError()
        value[key]=item
    return value


class OKXProductionHTTPTransport:
    def __init__(self,config,*,connection_factory=http.client.HTTPSConnection):
        if not isinstance(config,OKXProductionTransportConfig) or not callable(connection_factory):raise OKXProductionTransportError('EXPLICIT_PROVIDER_COMPOSITION_REQUIRED')
        self.config=config;self._factory=connection_factory

    def send(self,request):
        if not isinstance(request,PreparedOKXRequest) or request.authenticated is not True:raise OKXProductionTransportError('SIGNED_PROVIDER_REQUEST_REQUIRED')
        parts=urlsplit(request.request_path)
        if parts.scheme or parts.netloc or parts.fragment:raise OKXProductionTransportError('PROVIDER_ENDPOINT_OUTSIDE_PROFILE')
        if request.method=='GET' and parts.path in _GET_QUERIES:
            pairs=parse_qsl(parts.query,keep_blank_values=True,strict_parsing=True)
            if len(pairs)!=len(dict(pairs)) or request.body_text:raise OKXProductionTransportError('PROVIDER_QUERY_OUTSIDE_PROFILE')
            _query(parts.path,dict(pairs))
        elif request.method=='POST' and parts.path in _POST_PATHS and not parts.query:
            try:body=json.loads(request.body_text,object_pairs_hook=_unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
            except (ValueError,TypeError):raise OKXProductionTransportError('PROVIDER_BODY_OUTSIDE_PROFILE') from None
            _body(parts.path,body)
        else:raise OKXProductionTransportError('PROVIDER_ENDPOINT_OUTSIDE_PROFILE')
        expected={'Content-Type','OK-ACCESS-KEY','OK-ACCESS-PASSPHRASE','OK-ACCESS-TIMESTAMP','OK-ACCESS-SIGN'}
        if set(request.headers)!=expected or any(not isinstance(value,str) or not value or len(value)>4096 or any(c in value for c in '\r\n\x00') for value in request.headers.values()):raise OKXProductionTransportError('SIGNED_PROVIDER_REQUEST_REQUIRED')
        connection=None
        try:
            connection=self._factory('www.okx.com',timeout=self.config.timeout_seconds,context=ssl.create_default_context())
            connection.request(request.method,request.request_path,body=request.body_text or None,headers=dict(request.headers))
            response=connection.getresponse()
            if response.status!=200:raise OKXProductionTransportError('PROVIDER_HTTP_STATUS_UNAVAILABLE')
            raw=response.read(self.config.maximum_response_bytes+1)
            if len(raw)>self.config.maximum_response_bytes:raise OKXProductionTransportError('PROVIDER_RESPONSE_SIZE_LIMIT')
            value=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
            if not isinstance(value,dict) or not isinstance(value.get('code'),str) or not isinstance(value.get('data'),list):raise ValueError()
            return value
        except OKXProductionTransportError:raise
        except (TimeoutError,ConnectionError,OSError,http.client.HTTPException):raise OKXProductionTransportError('AMBIGUOUS_PROVIDER_TRANSPORT_FAILURE') from None
        except (ValueError,TypeError,UnicodeError):raise OKXProductionTransportError('PROVIDER_RESPONSE_INVALID') from None
        finally:
            if connection is not None:connection.close()
