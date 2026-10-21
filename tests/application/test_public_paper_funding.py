"""Controlled public funding capture; no real provider calls or Paper orders."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import uuid

from application.datasets.catalog import canonical, digest
from execution.funding import public_recorded_funding_model

NOW = datetime(2026, 10, 21, 8, 1, tzinfo=timezone.utc)


def ms(value):
    return str(int(value.timestamp() * 1000))


class Response(io.BytesIO):
    status = 200

    def geturl(self):
        return self.url


class PublicPaperFundingTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / 'capture'
        self.now = NOW; self.calls = []; self.mode = 'normal'
        self.subject = dict(namespace='LOCAL_RESEARCH', runtime_token=str(uuid.uuid4()),
            config_hash='sha256:'+'1'*64, selection_hash='sha256:'+'2'*64,
            funding_model='OKX_PUBLIC_RECORDED_ENTRY_NOTIONAL_V1')
        self.request = dict(schema_version='r7-public-paper-funding-request-v0.1',
            subject=self.subject, coverage_start='2026-10-21T00:00:00Z')

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.funding_capture'),
            'Ordinary Paper has no bounded settled-public funding acquisition')
        module = importlib.import_module('application.paper.funding_capture')
        self.assertTrue(callable(getattr(module, 'capture_public_funding', None)))
        return module

    def opener(self, request, timeout):
        from urllib.parse import parse_qs, urlsplit
        self.calls.append(request)
        url = urlsplit(request.full_url); query = parse_qs(url.query)
        self.assertEqual(url.scheme+'://'+url.netloc+url.path,
            'https://www.okx.com/api/v5/public/funding-rate-history')
        self.assertEqual(query['instId'], ['BTC-USDT-SWAP'])
        self.assertEqual(query['limit'], ['100'])
        self.assertEqual(request.get_method(), 'GET')
        self.assertNotIn('Authorization', request.headers)
        if self.mode == 'timeout':
            raise TimeoutError('controlled offline transport')
        latest = NOW.replace(minute=0)
        times = [latest-timedelta(hours=8*i) for i in range(3)]
        if self.mode == 'late': times = times[1:]
        if self.mode == 'gap': times.pop(1)
        if self.mode == 'unsupported': times.insert(1, latest-timedelta(hours=4))
        times = [at for at in times if int(ms(at)) < int(query['after'][0])]
        if self.mode == 'pages': times = times[:1]
        rows = [dict(instId='BTC-USDT-SWAP', fundingTime=ms(at), realizedRate='0.0001', fundingRate='0.9') for at in times]
        if self.mode == 'predicted':
            for row in rows: row['realizedRate'] = ''
        if self.mode == 'zero':
            for row in rows: row['realizedRate'] = '0'
        response = Response(canonical(dict(code='0', msg='', data=rows)).encode())
        response.url = request.full_url
        return response

    def acquire(self):
        return self.module().capture_public_funding(self.root, self.request,
            _opener=self.opener, _clock=lambda: self.now, _minimum_interval=0)

    def observe(self, *, now=None, subject=None):
        model = public_recorded_funding_model()
        observed = self.module().observe_funding_capture(self.root, model=model,
            subject=self.subject if subject is None else subject, now=self.now if now is None else now)
        return model, observed

    def test_actual_raw_receipts_and_realized_rates_derive_owned_observation(self):
        result = self.acquire()
        self.assertEqual(result['status'], 'PUBLIC_FUNDING_ACQUIRED')
        self.assertEqual((result['provider_requests'], result['provider_responses']), (1, 1))
        self.assertEqual(result['request_accounting'], 'COMPLETE')
        model, observed = self.observe()
        self.assertTrue(model.health(observed, now=NOW))
        self.assertEqual({r['rate'] for r in json.loads(observed.canonical_json)['events']}, {'0.0001'})
        self.assertEqual(result['snapshot_hash'], observed.snapshot_hash)
        self.assertEqual(json.loads((self.root/'requests/001-attempt.json').read_bytes())['prepared_at'], NOW.isoformat().replace('+00:00','Z'))
        raw = (self.root/'requests/001-response.bin').read_bytes()
        self.assertEqual(json.loads((self.root/'requests/001-result.json').read_bytes())['response_hash'], digest(raw))
        self.assertEqual(result['credentials'], 'NONE'); self.assertEqual(result['provider_mutation'], 0)

    def test_late_publication_is_unhealthy_valid_history_then_publication_recovers(self):
        self.mode = 'late'; result = self.acquire()
        self.assertEqual(result['status'], 'PUBLIC_FUNDING_PENDING')
        self.assertEqual(result['reason_code'], 'SETTLED_EVENT_NOT_YET_PUBLISHED')
        model, observed = self.observe()
        self.assertFalse(model.health(observed, now=NOW))
        self.assertEqual(observed.complete_through, '2026-10-21T00:00:00Z')

    def test_zero_actual_rate_is_observed_but_forecast_or_missing_is_never_zero(self):
        for mode in ('zero', 'predicted'):
            with self.subTest(mode=mode), TemporaryDirectory() as path:
                self.root=Path(path)/'capture'; self.mode=mode
                result=self.acquire()
                self.assertEqual(result['status'], 'PUBLIC_FUNDING_ACQUIRED' if mode=='zero' else 'PUBLIC_FUNDING_REJECTED')
                if mode=='predicted':
                    with self.assertRaises(ValueError): self.observe()

    def test_unsupported_schedule_and_coverage_gap_are_explicit_not_imputed(self):
        for mode, reason in (('unsupported','FUNDING_SETTLEMENT_INTERVAL_UNSUPPORTED'), ('gap','FUNDING_PUBLIC_COVERAGE_GAP')):
            with self.subTest(mode=mode), TemporaryDirectory() as path:
                self.root=Path(path)/'capture'; self.mode=mode
                if mode=='gap': self.request['coverage_start']='2026-10-20T16:00:00Z'
                result=self.acquire()
                self.assertEqual(result['status'], 'PUBLIC_FUNDING_REJECTED')
                self.assertEqual(result['reason_code'], reason)
                self.assertEqual(result['provider_requests'],1)

    def test_pagination_uses_actual_cursor_and_no_unneeded_history_pages(self):
        self.mode='pages'; result=self.acquire()
        self.assertEqual(result['status'],'PUBLIC_FUNDING_ACQUIRED')
        self.assertEqual(result['provider_requests'],2)
        self.assertEqual(len(list((self.root/'requests').glob('*-response.bin'))),2)
        model, observed=self.observe()
        self.assertTrue(model.health(observed,now=NOW))
        self.assertEqual(observed.snapshot_hash,self.observe()[1].snapshot_hash)

    def test_timeout_keeps_attempt_failure_and_truthful_counts(self):
        self.mode='timeout'; result=self.acquire()
        self.assertEqual(result['status'],'PUBLIC_FUNDING_REJECTED')
        self.assertEqual((result['provider_requests'],result['provider_responses']),(1,0))
        self.assertEqual(result['reason_code'],'PUBLIC_TRANSPORT_UNAVAILABLE')
        self.assertTrue((self.root/'requests/001-attempt.json').exists())
        self.assertTrue((self.root/'requests/001-failure.json').exists())

    def test_stale_and_future_read_clocks_cannot_retimestamp_health(self):
        self.acquire()
        model, observed=self.observe(now=NOW+timedelta(seconds=61))
        self.assertFalse(model.health(observed,now=NOW+timedelta(seconds=61)))
        with self.assertRaises(ValueError): self.observe(now=NOW-timedelta(seconds=1))

    def test_changed_subject_generation_selection_or_namespace_refuses(self):
        self.acquire()
        for key,value in (('runtime_token',str(uuid.uuid4())),('config_hash','sha256:'+'3'*64),
                ('selection_hash','sha256:'+'4'*64),('namespace','FIXTURE'),('funding_model','ZERO')):
            subject={**self.subject,key:value}
            with self.subTest(key=key), self.assertRaises(ValueError): self.observe(subject=subject)

    def test_replay_revalidates_bytes_and_receipts_instead_of_caller_success(self):
        self.acquire()
        files=['requests/001-response.bin','requests/001-result.json','requests/001-attempt.json','acquisition.json']
        for name in files:
            path=self.root/name; original=path.read_bytes()
            try:
                if name.endswith('response.bin'): changed=original.replace(b'0.0001',b'0.0002')
                else:
                    document=json.loads(original)
                    if name.endswith('result.json'): document['response_bytes']+=1
                    elif name.endswith('attempt.json'): document['authentication']='PRIVATE'
                    else: document['provider_requests']=0
                    changed=canonical(document).encode()
                path.write_bytes(changed)
                with self.subTest(name=name), self.assertRaises(ValueError): self.observe()
            finally: path.write_bytes(original)

    def test_no_requests_before_valid_explicit_selection_or_fresh_directory(self):
        module=self.module()
        for key in ('namespace','funding_model','runtime_token'):
            changed=deepcopy(self.request); changed['subject'][key]='invalid'
            with self.subTest(key=key), self.assertRaises(ValueError):
                module.capture_public_funding(self.root,changed,_opener=self.opener,_clock=lambda:NOW)
            self.assertEqual(self.calls,[]); self.assertFalse(self.root.exists())
        self.acquire()
        with self.assertRaises(ValueError): self.acquire()

    def test_source_reissues_from_exact_archived_capture_after_loose_files_are_released(self):
        self.acquire(); original=self.observe()[1]
        from application.paper.capture_archive import PublicCaptureArchive
        archive=PublicCaptureArchive(self.root.parent/'archive')
        token=str(uuid.uuid4())
        archive.reserve(token,kind='funding',maximum_requests=16,maximum_bytes=1024*1024)
        files={path.relative_to(self.root).as_posix():path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        pointer=archive.commit(token,files,requests=1,responses=1,complete=True)
        model=public_recorded_funding_model()
        retained=archive.read_capture(pointer)
        observed=self.module().observe_funding_capture(None,model=model,subject=self.subject,now=NOW,
            _read=lambda name,limit:retained[name])
        self.assertEqual(observed,original); self.assertTrue(model.health(observed,now=NOW))


if __name__ == '__main__':
    unittest.main()
