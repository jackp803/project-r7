"""Synthetic secrets/fake HTTPS only; never connects to a provider or vault."""
import importlib,json,unittest
from datetime import datetime,timezone
from brokers.okx_demo import OKXCredentials


class Response:
    status=200
    def __init__(self,body=b'{"code":"0","data":[]}'):self.body=body
    def read(self,limit):return self.body[:limit]


class Connection:
    def __init__(self,host,*,timeout,context):self.host=host;self.requests=[];self.closed=False;self.response=Response()
    def request(self,method,path,body=None,headers=None):self.requests.append((method,path,body,headers))
    def getresponse(self):return self.response
    def close(self):self.closed=True


class OKXProductionTransportTests(unittest.TestCase):
    def api(self):
        try:return importlib.import_module('brokers.okx_production_transport')
        except ModuleNotFoundError:self.fail('Missing bounded production request/HTTPS and local credential interface')

    def fixture(self):
        api=self.api(); calls=[]
        def factory(*args,**kwargs):
            value=Connection(*args,**kwargs);calls.append(value);return value
        config=api.OKXProductionTransportConfig(rest_base_url='https://www.okx.com',operator_confirmed_rest_base_url='https://www.okx.com')
        transport=api.OKXProductionHTTPTransport(config,connection_factory=factory)
        credentials=OKXCredentials('synthetic-local-api-key','synthetic-local-secret','synthetic-local-passphrase')
        return api,config,transport,credentials,calls

    def test_signed_production_request_has_no_demo_header_or_secret_repr_and_exact_canonical_body(self):
        api,config,transport,credentials,calls=self.fixture()
        request=api.prepare_production_private_request(config,credentials,method='POST',path='/api/v5/trade/order',
            timestamp='2026-10-03T00:00:00.000Z',body={'instId':'BTC-USDT-SWAP','tdMode':'isolated','side':'buy','posSide':'net','ordType':'market','sz':'1','clOrdId':'r7Synthetic1'})
        self.assertNotIn('x-simulated-trading',request.headers)
        self.assertIn('OK-ACCESS-SIGN',request.headers)
        for secret in ('synthetic-local-api-key','synthetic-local-secret','synthetic-local-passphrase'):
            self.assertNotIn(secret,repr(request));self.assertNotIn(secret,repr(credentials))
        self.assertEqual(json.dumps(json.loads(request.body_text),sort_keys=True,separators=(',',':')),request.body_text)
        self.assertEqual({'code':'0','data':[]},transport.send(request));self.assertEqual('www.okx.com',calls[0].host)
        self.assertEqual(1,len(calls[0].requests));self.assertTrue(calls[0].closed)

    def test_nonallowlisted_domain_method_path_or_query_is_denied_before_dispatch(self):
        api,config,transport,credentials,calls=self.fixture()
        for domain in ('https://evil.example','http://www.okx.com','https://user@www.okx.com','https://www.okx.com:443','https://www.okx.com/path'):
            with self.subTest(domain=domain),self.assertRaises(api.OKXProductionTransportError):
                api.OKXProductionTransportConfig(rest_base_url=domain,operator_confirmed_rest_base_url=domain)
        with self.assertRaises(api.OKXProductionTransportError):
            api.OKXProductionTransportConfig(rest_base_url='https://www.okx.com',operator_confirmed_rest_base_url='https://openapi.okx.com')
        for method,path,query in [('DELETE','/api/v5/trade/order',None),('POST','/api/v5/account/set-leverage',None),('GET','https://evil.example',None),
                                  ('GET','/api/v5/account/positions',{'instId':'ETH-USDT-SWAP'}),('GET','/api/v5/account/positions',{'unknown':'x'})]:
            with self.subTest(path=path),self.assertRaises(api.OKXProductionTransportError):
                request=api.prepare_production_private_request(config,credentials,method=method,path=path,timestamp='2026-10-03T00:00:00.000Z',query=query)
                transport.send(request)
        self.assertEqual([],calls)

    def test_redirect_oversize_duplicate_keys_and_nonfinite_response_fail_closed_without_retry(self):
        api,config,transport,credentials,calls=self.fixture()
        request=api.prepare_production_private_request(config,credentials,method='GET',path='/api/v5/account/config',timestamp='2026-10-03T00:00:00.000Z')
        for status,body in [(302,b'private-secret-should-never-echo'),(200,b'x'*(config.maximum_response_bytes+1)),
                            (200,b'{"code":"0","code":"1","data":[]}'),(200,b'{"code":"0","data":[NaN]}'),(200,b'[]')]:
            def factory(*args,**kwargs):
                value=Connection(*args,**kwargs);value.response=Response(body);value.response.status=status;calls.append(value);return value
            bounded=api.OKXProductionHTTPTransport(config,connection_factory=factory)
            with self.subTest(status=status,body_length=len(body)),self.assertRaises(api.OKXProductionTransportError) as caught:bounded.send(request)
            self.assertNotIn('private-secret',str(caught.exception));self.assertTrue(calls[-1].closed);self.assertEqual(1,len(calls[-1].requests))
        self.assertEqual(5,len(calls))

    def test_timeout_is_ambiguous_sanitized_and_not_retried(self):
        api,config,transport,credentials,calls=self.fixture()
        class TimeoutConnection(Connection):
            def getresponse(self):raise TimeoutError('synthetic-local-secret')
        def factory(*args,**kwargs):
            value=TimeoutConnection(*args,**kwargs);calls.append(value);return value
        transport=api.OKXProductionHTTPTransport(config,connection_factory=factory)
        request=api.prepare_production_private_request(config,credentials,method='GET',path='/api/v5/account/config',timestamp='2026-10-03T00:00:00.000Z')
        with self.assertRaises(api.OKXProductionTransportError) as caught:transport.send(request)
        self.assertEqual('AMBIGUOUS_PROVIDER_TRANSPORT_FAILURE',caught.exception.code);self.assertNotIn('synthetic',str(caught.exception))
        self.assertEqual(1,len(calls));self.assertTrue(calls[0].closed)

    def test_local_credentials_require_trusted_handle_and_never_env_or_file_fallback(self):
        api=self.api();requested=[]
        def read(service,name):requested.append((service,name));return {'api-key':'synthetic-key','secret-key':'synthetic-secret','passphrase':'synthetic-passphrase'}[name]
        provider=api.LocalSecureCredentialProvider(read_secret=read)
        with self.assertRaises(api.OKXProductionTransportError):provider.load('../outside')
        self.assertEqual([],requested)
        value=provider.load('operator-selected-account');self.assertIsInstance(value,OKXCredentials)
        self.assertEqual([('r7.okx.operator-selected-account',key) for key in ('api-key','secret-key','passphrase')],requested)
        for secret in ('synthetic-key','synthetic-secret','synthetic-passphrase'):self.assertNotIn(secret,repr(value))
        failing=api.LocalSecureCredentialProvider(read_secret=lambda *_:None)
        with self.assertRaises(api.OKXProductionTransportError) as caught:failing.load('operator-selected-account')
        self.assertEqual('LOCAL_PROVIDER_CREDENTIALS_UNAVAILABLE',caught.exception.code)

    def test_readback_requires_instrument_scope_and_one_exact_order_identity(self):
        api,config,transport,credentials,calls=self.fixture()
        for path,query in [('/api/v5/account/positions',{}),('/api/v5/trade/fills',{'instType':'SWAP'}),
                           ('/api/v5/trade/order',{'instId':'BTC-USDT-SWAP'}),
                           ('/api/v5/trade/order',{'instId':'BTC-USDT-SWAP','clOrdId':'r7Synthetic1','ordId':'123'}),
                           ('/api/v5/trade/order-algo',{}),('/api/v5/trade/orders-algo-pending',{'instId':'BTC-USDT-SWAP'})]:
            with self.subTest(path=path),self.assertRaises(api.OKXProductionTransportError):
                request=api.prepare_production_private_request(config,credentials,method='GET',path=path,
                    timestamp='2026-10-03T00:00:00.000Z',query=query)
                transport.send(request)
        self.assertEqual([],calls)


if __name__=='__main__':unittest.main()
