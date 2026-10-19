"""Controlled public HTTP only; these tests issue no real provider requests."""
from dataclasses import asdict, replace
from datetime import datetime,timedelta,timezone
import io,json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest,uuid
from urllib.parse import urlsplit,parse_qs

from application.paper.public_market import MarketSubscription

NOW=datetime(2026,10,19,8,1,tzinfo=timezone.utc)
def ms(at):return str(int(at.timestamp()*1000))
class Response(io.BytesIO):
    status=200
    def geturl(self):return self.url

class PublicPaperAcquisitionTests(unittest.TestCase):
    def module(self):
        import importlib
        return importlib.import_module('application.paper.public_acquisition')
    def setUp(self):
        temp=TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)/'capture'
        self.subscription=MarketSubscription('run-1','LOCAL_RESEARCH',str(uuid.uuid4()),1,'sha256:'+'1'*64,
            'BTC_USDT_PERP',(('4h',3,100,None),),None)
        self.calls=[];self.gap=False;self.final=True;self.age=0
    def opener(self,request,timeout):
        self.calls.append(request);url=urlsplit(request.full_url);query=parse_qs(url.query)
        self.assertEqual(url.hostname,'www.okx.com');self.assertEqual(query['instId'],['BTC-USDT-SWAP'])
        self.assertEqual(request.get_method(),'GET');self.assertNotIn('Authorization',request.headers)
        if url.path.endswith('/ticker'):
            rows=[dict(instId='BTC-USDT-SWAP',ts=ms(NOW-timedelta(seconds=self.age)),last='101',bidPx='100',askPx='102')]
        else:
            self.assertTrue(url.path.endswith('/history-candles'))
            end=NOW.replace(hour=8,minute=0)
            step={'4H':timedelta(hours=4),'1H':timedelta(hours=1)}[query['bar'][0]]
            rows=[[ms(end-step*i),'100','102','99','101','700','7','707','1' if self.final else '0'] for i in (1,2,3)]
            if self.gap:rows.pop(1)
            rows=[row for row in rows if int(row[0])<int(query['after'][0])]
        response=Response(json.dumps(dict(code='0',data=rows,msg='')).encode());response.url=request.full_url;return response
    def acquire(self,subscriptions=None):
        return self.module().acquire_batch(self.root,subscriptions or (self.subscription,),_opener=self.opener,
            _clock=lambda:NOW,_minimum_interval=0)
    def test_bounded_history_then_actual_ticker_closed_candles_and_base_volume(self):
        result=self.acquire()
        self.assertEqual(result['status'],'PUBLIC_MARKET_ACQUIRED');self.assertEqual(result['provider_requests'],2)
        self.assertEqual(result['provider_responses'],2);self.assertTrue(self.calls[-1].full_url.split('?')[0].endswith('/ticker'))
        self.assertEqual(len(result['candles']['4h']),3);self.assertEqual(result['candles']['4h'][0]['volume'],'7')
        self.assertTrue(all(row['received_at'] and row['is_closed'] for row in result['candles']['4h']))
        self.assertEqual(len(list((self.root/'requests').glob('*-response.bin'))),2)
    def test_cached_runs_share_one_quote_and_do_not_refetch_or_retimestamp_closed_bars(self):
        cached=replace(self.subscription,frames=(('4h',3,100,'2026-10-19T08:00:00.000Z'),))
        result=self.acquire((cached,replace(cached,run_id='run-2')))
        self.assertEqual(result['provider_requests'],1);self.assertEqual(result['candles'],{})

    def test_shared_batch_for_distinct_strategy_frames_filters_each_owning_event(self):
        hourly=replace(self.subscription,run_id='hourly',frames=(('1h',3,100,None),))
        result=self.acquire((self.subscription,hourly));self.assertEqual(result['provider_requests'],3)
        for selected,frame in ((self.subscription,'4h'),(hourly,'1h')):
            event=self.module().event_for(selected,result,now=NOW)
            self.assertEqual({row.timeframe for row in event.candles},{frame});self.assertEqual(len(event.candles),3)
    def test_gap_unconfirmed_and_stale_quote_are_actual_rejections_with_actual_counts(self):
        for mode in ('gap','final','age'):
            with self.subTest(mode=mode),TemporaryDirectory() as directory:
                self.root=Path(directory)/'capture';self.calls=[];self.gap=mode=='gap';self.final=mode!='final';self.age=30 if mode=='age' else 0
                result=self.acquire();self.assertEqual(result['status'],'PUBLIC_MARKET_REJECTED')
                self.assertGreater(result['provider_requests'],0);self.assertNotIn('snapshot',result)
                self.assertEqual(json.loads((self.root/'acquisition.json').read_bytes()),result)
    def test_fixture_private_symbol_duplicate_run_and_overflow_requests_rejected_before_io(self):
        module=self.module()
        for subscriptions in ((replace(self.subscription,namespace='FIXTURE'),),(replace(self.subscription,symbol='ETH_USDT_PERP'),),
                              (self.subscription,self.subscription),(replace(self.subscription,frames=(('4h',5000,5000,None),)),)):
            with self.subTest(subscriptions=subscriptions),self.assertRaises(ValueError):
                module.validate_subscriptions([asdict(value) for value in subscriptions])
        self.assertEqual(self.calls,[])
    def test_background_publication_requires_same_native_and_e6_generation_and_new_quote(self):
        module=self.module();result=self.acquire()
        self.assertIsNotNone(module.event_for(self.subscription,result,now=NOW))
        for changed in (replace(self.subscription,e6_generation=2),replace(self.subscription,runtime_token=str(uuid.uuid4())),
                        replace(self.subscription,strategy_content_hash='sha256:'+'2'*64),
                        replace(self.subscription,last_observed_at=result['snapshot']['observed_at'])):
            with self.subTest(changed=changed):self.assertIsNone(module.event_for(changed,result,now=NOW))
    def test_delayed_result_has_no_new_quote_health_or_future_candle_rewrite(self):
        module=self.module();result=self.acquire()
        with self.assertRaises(ValueError):module.event_for(self.subscription,result,now=NOW+timedelta(seconds=30))
        result['candles']['4h'][-1]['close_time']='2026-10-20T08:00:00.000Z'
        with self.assertRaises(ValueError):module.event_for(self.subscription,result,now=NOW)

    def test_malformed_child_uuid_decimal_and_timestamp_stay_within_rejection_boundary(self):
        from copy import deepcopy
        module=self.module();original=self.acquire()
        for change in ('uuid','quote','candle','time'):
            result=deepcopy(original)
            if change=='uuid':result['subscriptions'][0]['runtime_token']=1
            if change=='quote':result['snapshot']['last_price']='not-a-number'
            if change=='candle':result['candles']['4h'][0]['close']='not-a-number'
            if change=='time':result['candles']['4h'][0]['received_at']=None
            with self.subTest(change=change),self.assertRaises(ValueError):module.event_for(self.subscription,result,now=NOW)
