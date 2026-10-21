"""Keyless settled funding capture; actual raw facts, no financial verdict input."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

from application.cloud.safe_files import write_immutable
from application.datasets.catalog import canonical, decode, digest, hash_value, read_local, utc, z
from application.datasets.okx_public import (AcquisitionError, PublicTransport,
    FUNDING, INSTRUMENT, MAX_RESPONSE, millis, save, timestamp)
from application.platform.supervision import _local_path
from execution.funding import FundingEvidenceError, public_recorded_funding_model
from execution.public_recorded_funding import FUNDING_MODEL, MAX_CAPTURE_BYTES, MAX_PAGES, STEP

REQUEST_SCHEMA = 'r7-public-paper-funding-request-v0.1'
CAPTURE_SCHEMA = 'r7-public-paper-funding-capture-v0.1'
SUBJECT_FIELDS = {'namespace', 'runtime_token', 'config_hash', 'selection_hash', 'funding_model'}
RESULT_FIELDS = {'schema_version', 'status', 'reason_code', 'subject', 'request_hash',
    'coverage_start', 'observed_at', 'provider_requests', 'provider_responses',
    'request_accounting', 'credentials', 'provider_mutation', 'private_requests',
    'snapshot_hash', 'complete_through'}


def validate_request(request):
    if (type(request) is not dict or set(request) != {'schema_version','subject','coverage_start'}
            or request['schema_version'] != REQUEST_SCHEMA):
        raise ValueError('Exact recorded funding acquisition request required')
    subject = request['subject']
    if (type(subject) is not dict or set(subject) != SUBJECT_FIELDS
            or subject['namespace'] != 'LOCAL_RESEARCH' or subject['funding_model'] != FUNDING_MODEL):
        raise ValueError('Explicit ordinary recorded funding selection required')
    token = subject['runtime_token']
    if type(token) is not str or len(token) != 36:
        raise ValueError('Current funding owner generation required')
    parsed = uuid.UUID(token)
    if parsed.version != 4 or str(parsed) != token:
        raise ValueError('Current funding owner generation required')
    hash_value(subject['config_hash']); hash_value(subject['selection_hash'])
    start = utc(request['coverage_start'])
    if start.hour % 8 or start.minute or start.second or start.microsecond:
        raise ValueError('Verified eight-hour funding coverage start required')
    return decode(canonical(request)), start


class PublicFundingTransport(PublicTransport):
    request_budget = MAX_PAGES
    deadline_seconds = 120

    def _parameters(self, path, params):
        if path != FUNDING:
            raise ValueError('Only fixed public funding history is supported')
        super()._parameters(path, params)


def _reader(root, read=None):
    def bounded(relative, limit):
        raw=read_local(root,relative,limit) if read is None else read(relative,limit)
        if type(raw) is not bytes or len(raw)>limit:
            raise ValueError('Bounded actual captured bytes required')
        return raw
    return bounded


def _page(root, sequence, *, read=None):
    read=_reader(root,read)
    stem = 'requests/'+f'{sequence:03d}'
    attempt = decode(read(stem+'-attempt.json', 4096))
    result = decode(read(stem+'-result.json', 4096))
    raw = read(stem+'-response.bin', MAX_RESPONSE)
    if (type(attempt) is not dict or set(attempt) != {'method','url','attempt','prepared_at',
            'dispatch_state','authentication','mutation'} or attempt['method'] != 'GET'
            or type(attempt['attempt']) is not int or attempt['attempt'] != sequence
            or attempt['dispatch_state'] != 'PREPARED_BEFORE_IO' or attempt['authentication'] != 'NONE'
            or attempt['mutation'] is not False or type(result) is not dict
            or set(result) != {'http_status','received_at','response_hash','response_bytes'}
            or type(result['response_bytes']) is not int or result['response_bytes'] != len(raw)
            or result['response_hash'] != digest(raw)):
        raise ValueError('Actual immutable public funding receipts required')
    return dict(url=attempt['url'], request_started_at=attempt['prepared_at'], received_at=result['received_at'],
        http_status=result['http_status'], response_body=raw)


def capture_public_funding(root, request, *, _opener=None, _clock=None, _minimum_interval=.25):
    """Fresh fixed-source capture. The private child owner guards its subject.

    Injectable transport/clock are test seams, never CLI parameters. A source
    observation is independently reconstructed from receipts before publication.
    """
    request, start = validate_request(request)
    clock = _clock or (lambda: datetime.now(timezone.utc))
    began = utc(z(clock()))
    if not start < began or began-start > timedelta(days=89):
        raise ValueError('Bounded current funding coverage required')
    root = Path(root).absolute(); _local_path(root)
    if root.exists():
        raise ValueError('Fresh isolated funding capture directory required')
    root.mkdir(parents=True, exist_ok=False)
    raw_request = canonical(request).encode(); write_immutable(root, 'request.json', raw_request)
    transport = PublicFundingTransport(root, opener=_opener, minimum_interval=_minimum_interval, _clock=clock)
    result = dict(schema_version=CAPTURE_SCHEMA, status='PUBLIC_FUNDING_REJECTED', reason_code=None,
        subject=request['subject'], request_hash=digest(raw_request), coverage_start=request['coverage_start'],
        observed_at=z(began), provider_requests=0, provider_responses=0, request_accounting='COMPLETE',
        credentials='NONE', provider_mutation=0, private_requests=0, snapshot_hash=None, complete_through=None)
    try:
        pages = []; cursor = began; total = 0
        while True:
            document = transport.get(FUNDING, dict(instId=INSTRUMENT, after=millis(cursor), limit='100'))
            page = _page(root, transport.attempts)
            total += len(page['response_body'])
            if total > MAX_CAPTURE_BYTES:
                raise AcquisitionError('FUNDING_PUBLIC_CAPTURE_LIMIT')
            pages.append(page)
            rows = document['data']
            if not rows or len(rows) > 100:
                raise AcquisitionError('FUNDING_PUBLIC_SETTLED_ROWS_REQUIRED')
            times = [timestamp(row.get('fundingTime')) for row in rows if type(row) is dict]
            if len(times) != len(rows):
                raise AcquisitionError('FUNDING_PUBLIC_INSTRUMENT_UNSUPPORTED')
            lower = min(times)
            if lower >= cursor:
                raise AcquisitionError('FUNDING_PUBLIC_PAGINATION_NO_PROGRESS')
            if lower <= start:
                break
            cursor = lower
        ended = utc(z(clock()))
        model = public_recorded_funding_model()
        observed = model.observe(tuple(pages), coverage_start=start, observed_at=ended)
        healthy = model.health(observed, now=ended)
        result.update(status='PUBLIC_FUNDING_ACQUIRED' if healthy else 'PUBLIC_FUNDING_PENDING',
            reason_code=None if healthy else 'SETTLED_EVENT_NOT_YET_PUBLISHED', observed_at=z(ended),
            snapshot_hash=observed.snapshot_hash, complete_through=observed.complete_through)
    except (AcquisitionError, FundingEvidenceError) as error:
        result['reason_code'] = error.code
    except (ValueError, TypeError, KeyError, OverflowError):
        result['reason_code'] = 'PUBLIC_FUNDING_CAPTURE_INVALID'
    result.update(provider_requests=transport.attempts, provider_responses=transport.responses)
    save(root, 'acquisition.json', result)
    return result


def observe_funding_capture(root, *, model, subject, now, _read=None):
    """Reissue a source-owned observation from preserved raw bytes after restart.

    Health always uses the original capture clocks, never the reader's time.
    Owner/config/selection guards run outside this network-free readback as well.
    """
    if _read is None:
        root = Path(root).absolute(); _local_path(root)
    read=_reader(root,_read)
    raw_request = read('request.json', 4096)
    request, start = validate_request(decode(raw_request))
    result = decode(read('acquisition.json', 8192))
    if (type(result) is not dict or set(result) != RESULT_FIELDS or result['schema_version'] != CAPTURE_SCHEMA
            or request['subject'] != subject or result['subject'] != subject
            or result['coverage_start'] != request['coverage_start'] or result['request_hash'] != digest(raw_request)
            or result['status'] not in ('PUBLIC_FUNDING_ACQUIRED','PUBLIC_FUNDING_PENDING')
            or result['request_accounting'] != 'COMPLETE' or result['credentials'] != 'NONE'
            or type(result['provider_mutation']) is not int or result['provider_mutation'] != 0
            or type(result['private_requests']) is not int or result['private_requests'] != 0
            or type(result['provider_requests']) is not int or not 1 <= result['provider_requests'] <= MAX_PAGES
            or type(result['provider_responses']) is not int or result['provider_responses'] != result['provider_requests']
            or utc(result['observed_at']) > now):
        raise ValueError('Matching actual public funding acquisition required')
    pages = tuple(_page(root, index,read=read) for index in range(1, result['provider_requests']+1))
    observed = model.observe(pages, coverage_start=start, observed_at=utc(result['observed_at']))
    if observed.snapshot_hash != result['snapshot_hash'] or observed.complete_through != result['complete_through']:
        raise ValueError('Unchanged funding source commitment required')
    expected_healthy = model.health(observed, now=utc(result['observed_at']))
    if ((result['status'] == 'PUBLIC_FUNDING_ACQUIRED') != expected_healthy
            or result['reason_code'] != (None if expected_healthy else 'SETTLED_EVENT_NOT_YET_PUBLISHED')):
        raise ValueError('Source-derived public funding status required')
    return observed
