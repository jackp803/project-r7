"""Offline deterministic acquisition checks; no real provider requests."""
from datetime import datetime,timedelta,timezone
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.parse import urlsplit,parse_qs

from application.datasets.catalog import DatasetCatalog,DatasetError
from application.datasets.resolver import DatasetResolver

START=datetime(2026,10,1,tzinfo=timezone.utc)
END=START+timedelta(days=2)
def ms(value): return str(int(value.timestamp()*1000))

class Response(io.BytesIO):
    status=200
    def geturl(self): return self.url

class PublicDatasetTests(unittest.TestCase):
    def setUp(self):
        temp=TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)/'fresh';self.requests=[]
        self.candles=[[ms(START+timedelta(hours=i)), '100','102','99','101','700','7','707','1'] for i in range(0,48,4)]
        self.funding=[dict(instId='BTC-USDT-SWAP',fundingTime=ms(START+timedelta(hours=i)),realizedRate='0.0001',fundingRate='0.0002') for i in range(0,48,8)]

    def opener(self,request,timeout):
        self.requests.append(request)
        parts=urlsplit(request.full_url);query=parse_qs(parts.query)
        self.assertEqual(parts.hostname,'www.okx.com');self.assertEqual(request.get_method(),'GET')
        self.assertEqual(query['instId'],['BTC-USDT-SWAP']);self.assertFalse(any('key' in key.lower() or 'auth' in key.lower() for key in request.headers))
        rows=self.candles if parts.path.endswith('history-candles') else self.funding
        stamp=(lambda row:int(row[0])) if isinstance(rows[0],list) else (lambda row:int(row['fundingTime']))
        rows=sorted((row for row in rows if stamp(row)<int(query['after'][0])),key=stamp,reverse=True)[:100]
        response=Response(json.dumps(dict(code='0',data=rows,msg='')).encode());response.url=request.full_url
        return response

    def run_acquisition(self):
        from application.datasets.okx_public import acquire_okx_public_dataset
        return acquire_okx_public_dataset(self.root,start=START,end=END,_opener=self.opener,_minimum_interval=0)

    def test_real_schema_resolves_base_volume_and_settled_rates_with_audited_requests(self):
        result=self.run_acquisition()
        self.assertEqual(result['status'],'DATASET_ACQUIRED');self.assertEqual(result['provider_requests'],2)
        self.assertEqual(result['provider_responses'],2)
        resolved=DatasetResolver(DatasetCatalog(self.root)).resolve('dataset.json')
        self.assertEqual(len(resolved.candles_by_timeframe['4h']),12)
        self.assertEqual(str(resolved.candles_by_timeframe['4h'][0].volume),'7')
        self.assertEqual(str(resolved.funding_model.events[0][1]),'0.0001')
        self.assertEqual(len(list((self.root/'requests').glob('*-attempt.json'))),2)
        self.assertEqual(len(list((self.root/'requests').glob('*-response.bin'))),2)
        self.assertEqual(result['promotion'],'NOT_ASSESSED')

    def test_gap_rejected_no_manifest_but_actual_request_accounting_retained(self):
        self.candles.pop(5)
        result=self.run_acquisition()
        self.assertEqual(result['status'],'ACQUISITION_REJECTED')
        self.assertEqual(result['reason_code'],'CANDLE_COVERAGE_GAP')
        self.assertGreater(result['provider_requests'],0);self.assertFalse((self.root/'dataset.json').exists())
        self.assertEqual(json.loads((self.root/'acquisition.json').read_bytes()),result)

    def test_missing_settled_rate_or_funding_gap_never_becomes_zero_funding(self):
        self.funding[1]['realizedRate']=''
        result=self.run_acquisition()
        self.assertEqual(result['status'],'ACQUISITION_REJECTED');self.assertFalse((self.root/'dataset.json').exists())
        self.assertEqual(result['reason_code'],'SETTLED_FUNDING_RATE_REQUIRED')

    def test_network_failure_counted_and_existing_destination_never_overwritten(self):
        from application.datasets.okx_public import acquire_okx_public_dataset
        def offline(*args,**kwargs): raise OSError('no network; internal details must not escape')
        result=acquire_okx_public_dataset(self.root,start=START,end=END,_opener=offline,_minimum_interval=0)
        self.assertEqual(result['provider_requests'],1);self.assertEqual(result['provider_responses'],0)
        self.assertEqual(result['reason_code'],'PUBLIC_TRANSPORT_UNAVAILABLE')
        self.assertNotIn('internal details',json.dumps(result))
        with self.assertRaises(ValueError): self.run_acquisition()

    def test_unclosed_bar_rejected(self):
        self.candles[1][-1]='0'
        self.assertEqual(self.run_acquisition()['reason_code'],'UNFINALIZED_CANDLE')

    def test_funding_gap_is_rejected_without_an_imputed_rate(self):
        self.funding.pop(2)
        self.assertEqual(self.run_acquisition()['reason_code'],'FUNDING_COVERAGE_OR_INTERVAL_UNSUPPORTED')
        self.assertFalse((self.root/'dataset.json').exists())

    def test_wrong_funding_instrument_rejected(self):
        self.funding[1]['instId']='ETH-USDT-SWAP'
        self.assertEqual(self.run_acquisition()['reason_code'],'FUNDING_INSTRUMENT_MISMATCH')

    def test_ambiguous_volume_schema_rejected_without_contract_relabeling(self):
        self.candles[1].pop(7)
        self.assertEqual(self.run_acquisition()['reason_code'],'DOCUMENTED_BASE_VOLUME_SHAPE_REQUIRED')

    def test_duplicate_across_pages_is_not_silently_deduplicated(self):
        from application.datasets.okx_public import acquire_okx_public_dataset
        def repeat(request,timeout):
            response=Response(json.dumps(dict(code='0',data=[self.candles[-1]])).encode());response.url=request.full_url
            return response
        result=acquire_okx_public_dataset(self.root,start=START,end=END,_opener=repeat,_minimum_interval=0)
        self.assertEqual(result['reason_code'],'DUPLICATE_CANDLE');self.assertEqual(result['provider_requests'],2)

    def test_http_rejection_and_oversized_response_have_nonzero_accounting(self):
        from application.datasets.okx_public import acquire_okx_public_dataset,MAX_RESPONSE
        def oversized(request,timeout):
            response=Response(b' '* (MAX_RESPONSE+1));response.url=request.full_url
            return response
        result=acquire_okx_public_dataset(self.root,start=START,end=END,_opener=oversized,_minimum_interval=0)
        self.assertEqual(result['reason_code'],'PUBLIC_RESPONSE_TOO_LARGE')
        self.assertEqual((result['provider_requests'],result['provider_responses']),(1,1))

    def test_incomplete_http_body_retains_partial_bytes_and_final_request_counts(self):
        from application.datasets.okx_public import acquire_okx_public_dataset
        from http.client import IncompleteRead
        class Broken(Response):
            def read1(self,size): raise IncompleteRead(b'{"code":',100)
        def broken(request,timeout):
            response=Broken(b'');response.url=request.full_url;return response
        result=acquire_okx_public_dataset(self.root,start=START,end=END,_opener=broken,_minimum_interval=0)
        self.assertEqual(result['reason_code'],'PUBLIC_TRANSPORT_UNAVAILABLE')
        self.assertEqual((result['provider_requests'],result['provider_responses']),(1,1))
        self.assertEqual((self.root/'requests/001-partial-response.bin').read_bytes(),b'{"code":')
        self.assertEqual(json.loads((self.root/'acquisition.json').read_bytes()),result)

    def test_failed_predispatch_receipt_does_not_count_an_unmade_network_attempt(self):
        from application.datasets.okx_public import PublicTransport
        from unittest.mock import patch
        self.root.mkdir();transport=PublicTransport(self.root,opener=self.opener,minimum_interval=0)
        with patch('application.datasets.okx_public.save',side_effect=OSError('local disk failure')),self.assertRaises(OSError):
            transport.get('/api/v5/market/history-candles',dict(instId='BTC-USDT-SWAP',after=ms(END),limit='100',bar='4H'))
        self.assertEqual(transport.attempts,0);self.assertEqual(self.requests,[])

    def test_forbidden_endpoint_rejected_before_network_or_attempt_ledger(self):
        from application.datasets.okx_public import PublicTransport
        self.root.mkdir();transport=PublicTransport(self.root,opener=self.opener,minimum_interval=0)
        for endpoint in ('/api/v5/trade/order','/api/v5/account/balance','https://evil.invalid/api/v5/market/history-candles'):
            with self.subTest(endpoint=endpoint),self.assertRaises(ValueError): transport.get(endpoint,{'instId':'BTC-USDT-SWAP'})
        self.assertEqual(transport.attempts,0);self.assertEqual(self.requests,[])

    def test_different_contract_and_caller_auth_parameters_rejected_before_network(self):
        from application.datasets.okx_public import PublicTransport
        self.root.mkdir();transport=PublicTransport(self.root,opener=self.opener,minimum_interval=0)
        for params in ({'instId':'ETH-USDT-SWAP','after':'1','bar':'4H','limit':'100'},
                       {'instId':'BTC-USDT-SWAP','after':'1','bar':'4H','limit':'100','apiKey':'forbidden'}):
            with self.subTest(params=params),self.assertRaises(ValueError): transport.get('/api/v5/market/history-candles',params)
        self.assertEqual(transport.attempts,0)

    def test_cli_uses_configured_local_namespace_and_never_accepts_an_endpoint_or_key(self):
        from application import cli
        from contextlib import redirect_stdout,redirect_stderr
        from unittest.mock import patch
        config=self.root.parent/'config.json'
        with redirect_stdout(io.StringIO()):
            cli.main(['init-profile','--config',str(config),'--data-root',str(self.root),'--instance-id','public-acquisition-test'])
        # Test CLI parsing separately while actual acquisition is the owner above.
        with patch('application.datasets.okx_public.acquire_okx_public_dataset',return_value={'status':'DATASET_ACQUIRED'}) as acquire,redirect_stdout(io.StringIO()):
            code=cli.main(['acquire-public-data','--config',str(config),'--dataset-id','bounded-btc',
                           '--start','2026-10-01T00:00:00Z','--end','2026-10-03T00:00:00Z'])
            self.assertEqual(code,0)
            self.assertEqual(acquire.call_args.args[0],self.root/'datasets'/'bounded-btc')
        with self.assertRaises(SystemExit),redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            cli.main(['acquire-public-data','--config',str(config),'--dataset-id','bounded-btc',
                      '--start','2026-10-01T00:00:00Z','--end','2026-10-03T00:00:00Z','--api-key','FORBIDDEN'])

    def test_edited_profile_cannot_write_public_dataset_inside_installation(self):
        from application import cli
        from contextlib import redirect_stdout
        from unittest.mock import patch
        config=self.root.parent/'config.json'
        with redirect_stdout(io.StringIO()):
            cli.main(['init-profile','--config',str(config),'--data-root',str(self.root),'--instance-id','public-installation-test'])
        before=list(self.root.parent.rglob('*'))
        with patch('application.entrypoints.installed_root',return_value=self.root), \
             patch('application.datasets.okx_public.acquire_okx_public_dataset',return_value={'status':'DATASET_ACQUIRED'}) as acquire, \
             self.assertRaises(ValueError):
            cli.main(['acquire-public-data','--config',str(config),'--dataset-id','bounded-btc',
                      '--start','2026-10-01T00:00:00Z','--end','2026-10-03T00:00:00Z'])
        acquire.assert_not_called();self.assertEqual(before,list(self.root.parent.rglob('*')))
