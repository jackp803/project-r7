"""E4 registered Paper model using settled public rates, never account truth.

Network-free validation/allocation. The trusted acquisition owner supplies raw
public request/response captures, not a caller completeness or financial PASS.
The model conservatively finalizes only through a published settled boundary.
"""
from collections import OrderedDict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import (Clamped, Context, Decimal, DecimalException, Inexact,
    InvalidOperation, Overflow, Rounded, Subnormal, Underflow, localcontext)
import hashlib
import json
import re

from execution.funding import (FundingEvidenceError, FUNDING_EVIDENCE_PROFILE_VERSION,
    INTERVAL_SEMANTICS, SCHEMA_VERSION, _fmt_utc, _utc,
    _validate_plan_and_flat_position, stable_funding_evidence_id)
from execution.models import Fill, OrderRequest, Side
from indicators.v02.common import finite_decimal

SOURCE = 'R7_PUBLIC_RECORDED_PAPER_FUNDING_MODEL'
SOURCE_VERSION = 'paper-public-recorded-entry-notional-v0.1'
FUNDING_MODEL = 'OKX_PUBLIC_RECORDED_ENTRY_NOTIONAL_V1'
OBSERVATION_PROFILE = 'r7-public-recorded-funding-observation-v0.1'
STEP = timedelta(hours=8)
MAX_PAGES = 16
MAX_RECORDS = 1000
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_CAPTURE_BYTES = 8 * 1024 * 1024
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_PAGE_FIELDS = {'url', 'request_started_at', 'received_at', 'http_status', 'response_body'}
_URL = re.compile(r'https://www\.okx\.com/api/v5/public/funding-rate-history\?after=([0-9]{1,16})&instId=BTC-USDT-SWAP&limit=100\Z')


def _fail(code):
    raise FundingEvidenceError(code, code)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _hash(value):
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _context():
    return Context(prec=128, Emin=-256, Emax=256,
        traps=[Inexact, Rounded, InvalidOperation, Overflow, Underflow, Clamped, Subnormal])


def _decimal(value):
    if type(value) is Decimal:
        if not value.is_finite() or len(value.as_tuple().digits) > 34 or value.as_tuple().exponent < -18 or value.adjusted() > 17:
            _fail('FUNDING_MODEL_DECIMAL_UNSUPPORTED')
        value = format(value, 'f')
    if type(value) is not str or len(value) > 64 or not re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?', value):
        _fail('FUNDING_MODEL_DECIMAL_UNSUPPORTED')
    integer, _, fraction = value.lstrip('-').partition('.')
    digits = (integer + fraction).lstrip('0')
    if len(integer) > 18 or len(fraction) > 18 or len(digits) > 34:
        _fail('FUNDING_MODEL_DECIMAL_UNSUPPORTED')
    return Decimal(value)


def _text(value):
    if value.is_zero():
        return '0'
    result = format(value, 'f')
    return result.rstrip('0').rstrip('.') if '.' in result else result


def _floor(value):
    return _EPOCH + ((value - _EPOCH) // STEP) * STEP


def _timestamp(value):
    if type(value) is not str or not re.fullmatch(r'[0-9]{1,16}', value):
        _fail('FUNDING_PUBLIC_TIMESTAMP_INVALID')
    try:
        return _EPOCH + timedelta(milliseconds=int(value))
    except (OverflowError, ValueError):
        _fail('FUNDING_PUBLIC_TIMESTAMP_INVALID')


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            _fail('FUNDING_PUBLIC_DUPLICATE_JSON_FIELD')
        result[key] = value
    return result


def _forbidden_number(value):
    _fail('FUNDING_PUBLIC_BINARY_OR_NONFINITE_NUMBER')


@dataclass(frozen=True)
class ObservedPublicFunding:
    canonical_json: str
    snapshot_hash: str
    coverage_start: str
    complete_through: str
    observed_at: str


class PublicRecordedFundingModel:
    """Owns validated observations and derives exact canonical allocations."""
    __slots__ = ('_issued',)

    def __init__(self):
        self._issued = OrderedDict()

    def require(self, observed):
        item = self._issued.get(id(observed))
        if (type(observed) is not ObservedPublicFunding or item is None or item[0] is not observed
                or item[1] != _hash(asdict(observed))):
            _fail('ACTUAL_PUBLIC_FUNDING_OBSERVATION_REQUIRED')
        return observed

    def observe(self, pages, *, coverage_start, observed_at):
        start = _utc(coverage_start, 'coverage_start')
        received = _utc(observed_at, 'observed_at')
        if start != _floor(start) or not start < received or received-start > timedelta(days=89):
            _fail('FUNDING_PUBLIC_COVERAGE_UNSUPPORTED')
        if type(pages) is not tuple or not 1 <= len(pages) <= MAX_PAGES:
            _fail('FUNDING_PUBLIC_PAGE_LIMIT')
        selected = {}; seen = set(); material = []; total = count = 0
        previous_lower = previous_received = None
        for page in pages:
            if type(page) is not dict or set(page) != _PAGE_FIELDS:
                _fail('FUNDING_PUBLIC_PAGE_SHAPE_INVALID')
            match = _URL.fullmatch(page['url']) if type(page['url']) is str else None
            if match is None or type(page['http_status']) is not int or page['http_status'] != 200:
                _fail('FUNDING_PUBLIC_READ_ONLY_SOURCE_REQUIRED')
            began = _utc(page['request_started_at'], 'request_started_at')
            ended = _utc(page['received_at'], 'received_at')
            cursor = _timestamp(match[1])
            if (not began <= ended <= received or cursor > began or previous_received and ended < previous_received
                    or previous_lower is not None and cursor != previous_lower):
                _fail('FUNDING_PUBLIC_PAGE_CLOCK_OR_CURSOR_INVALID')
            raw = page['response_body']
            if type(raw) is not bytes or not 1 <= len(raw) <= MAX_RESPONSE_BYTES:
                _fail('FUNDING_PUBLIC_RESPONSE_LIMIT')
            total += len(raw)
            if total > MAX_CAPTURE_BYTES:
                _fail('FUNDING_PUBLIC_CAPTURE_LIMIT')
            try:
                document = json.loads(raw, object_pairs_hook=_pairs, parse_float=_forbidden_number, parse_constant=_forbidden_number)
            except (ValueError, UnicodeError, RecursionError):
                _fail('FUNDING_PUBLIC_JSON_INVALID')
            if (type(document) is not dict or set(document) != {'code', 'msg', 'data'} or document['code'] != '0'
                    or type(document['msg']) is not str or type(document['data']) is not list or not 1 <= len(document['data']) <= 100):
                _fail('FUNDING_PUBLIC_SETTLED_ROWS_REQUIRED')
            times = []
            for row in document['data']:
                count += 1
                if count > MAX_RECORDS:
                    _fail('FUNDING_PUBLIC_RECORD_LIMIT')
                if type(row) is not dict or row.get('instId') != 'BTC-USDT-SWAP':
                    _fail('FUNDING_PUBLIC_INSTRUMENT_UNSUPPORTED')
                when = _timestamp(row.get('fundingTime'))
                if when != _floor(when):
                    _fail('FUNDING_SETTLEMENT_INTERVAL_UNSUPPORTED')
                if when >= cursor or when > ended or when in seen:
                    _fail('FUNDING_PUBLIC_DUPLICATE_OR_FUTURE_EVENT')
                rate = _decimal(row.get('realizedRate'))
                if rate.copy_abs() >= 1:
                    _fail('FUNDING_PUBLIC_SETTLED_RATE_INVALID')
                seen.add(when); times.append(when)
                if when >= start:
                    selected[when] = dict(event_at=_fmt_utc(when), rate=_text(rate),
                        source='OKX_PUBLIC_REALIZED_FUNDING_RATE')
            if times != sorted(times, reverse=True):
                _fail('FUNDING_PUBLIC_PAGE_ORDER_INVALID')
            lower = min(times)
            if previous_lower is not None and lower >= previous_lower:
                _fail('FUNDING_PUBLIC_PAGINATION_NO_PROGRESS')
            if previous_lower is not None and previous_lower <= start:
                _fail('FUNDING_PUBLIC_UNREQUESTED_PAGE')
            material.append(dict(url=page['url'],request_started_at=_fmt_utc(began),received_at=_fmt_utc(ended),
                response_hash=hashlib.sha256(raw).hexdigest(),response_bytes=len(raw),http_status=200))
            previous_lower, previous_received = lower, ended
        if previous_lower > start or not selected:
            _fail('FUNDING_PUBLIC_PAGINATION_INCOMPLETE')
        through = max(selected)
        expected = [start + i*STEP for i in range((through-start)//STEP+1)]
        if sorted(selected) != expected:
            _fail('FUNDING_PUBLIC_COVERAGE_GAP')
        body = dict(profile=OBSERVATION_PROFILE, source=SOURCE, source_version=SOURCE_VERSION,
            funding_model=FUNDING_MODEL, symbol='BTC_USDT_PERP', interval_seconds=28800,
            coverage_start=_fmt_utc(start), complete_through=_fmt_utc(through), observed_at=_fmt_utc(received),
            pages=material, events=[selected[t] for t in expected])
        observed = ObservedPublicFunding(_canonical(body), _hash(body), body['coverage_start'], body['complete_through'], body['observed_at'])
        self._issued[id(observed)] = (observed, _hash(asdict(observed)))
        while len(self._issued) > 128:
            self._issued.popitem(last=False)
        return observed

    def health(self, observed, *, now):
        try:
            self.require(observed)
            current = _utc(now, 'now'); seen = _utc(observed.observed_at, 'observed_at')
            body = json.loads(observed.canonical_json)
            return (0 <= (current-seen).total_seconds() <= 60 and len(body['events']) >= 2
                and _utc(observed.complete_through, 'complete_through') == _floor(current))
        except (ValueError, TypeError, OverflowError):
            return False

    def allocate(self, parent_plan, final_position, entry_request, entry_fills, *, observed, calculated_at):
        self.require(observed)
        facts = _validate_plan_and_flat_position(parent_plan, final_position)
        start = _utc(facts['interval_start'], 'interval_start'); end = facts['interval_end_dt']
        calculated = _utc(calculated_at, 'calculated_at')
        if (facts['symbol'] != 'BTC_USDT_PERP' or _utc(observed.coverage_start, 'coverage_start') > start
                or _utc(observed.complete_through, 'complete_through') < end):
            _fail('FUNDING_SOURCE_INCOMPLETE')
        if calculated < max(end, _utc(observed.observed_at, 'observed_at')):
            _fail('CALCULATED_BEFORE_SOURCE_OR_INTERVAL_END')
        request = entry_request
        if (type(request) is not OrderRequest or request.schema_version != SCHEMA_VERSION
                or request.trade_plan_id != facts['trade_plan_id'] or request.symbol != facts['symbol']
                or request.side not in (Side.BUY, Side.SELL) or type(request.side) is not Side
                or request.quantity_unit != 'BASE_ASSET' or request.quantity_asset != 'BTC'
                or request.quantity_profile_version != 'base-asset-v0.1'
                or request.position_action_id is not None or request.reduce_only is True
                or request.position_id not in (None, facts['position_id']) or request.order_role not in (None, 'ENTRY')
                or _utc(request.created_at, 'request.created_at') > start
                or parent_plan.get('direction') != ('LONG' if request.side == Side.BUY else 'SHORT')):
            _fail('FUNDING_ENTRY_LINEAGE_INVALID')
        if type(entry_fills) is not tuple or not 1 <= len(entry_fills) <= MAX_RECORDS:
            _fail('FUNDING_ACTUAL_ENTRY_FILLS_REQUIRED')
        seen = set(); fill_material = []; broker = None
        try:
            with localcontext(_context()):
                quantity = basis = Decimal(0)
                for fill in sorted(entry_fills, key=lambda f: f.fill_id if type(f) is Fill else ''):
                    if (type(fill) is not Fill or fill.schema_version != SCHEMA_VERSION
                            or not isinstance(fill.fill_id, str) or not fill.fill_id or len(fill.fill_id) > 256 or fill.fill_id in seen
                            or fill.client_order_id != request.client_order_id or fill.trade_plan_id != request.trade_plan_id
                            or fill.symbol != request.symbol or type(fill.side) is not Side or fill.side != request.side
                            or _utc(fill.filled_at, 'filled_at') != start or fill.position_id not in (None, facts['position_id'])
                            or fill.position_action_id is not None or fill.order_role not in (None, 'ENTRY')
                            or not isinstance(fill.broker_order_id, str) or not fill.broker_order_id
                            or broker is not None and fill.broker_order_id != broker):
                        _fail('FUNDING_ENTRY_FILL_LINEAGE_INVALID')
                    q = _decimal(fill.quantity); price = _decimal(fill.price)
                    if q <= 0 or price <= 0:
                        _fail('FUNDING_ENTRY_FILL_VALUE_INVALID')
                    broker = fill.broker_order_id; seen.add(fill.fill_id)
                    quantity += q; basis += q*price
                    fill_material.append(dict(fill_id=fill.fill_id,quantity=_text(q),price=_text(price),filled_at=_fmt_utc(start)))
                if quantity > _decimal(request.quantity) or quantity <= 0:
                    _fail('FUNDING_ENTRY_FILL_QUANTITY_INVALID')
                body = json.loads(observed.canonical_json)
                events = [row for row in body['events'] if start <= _utc(row['event_at'], 'event_at') < end]
                cost = sum((basis * _decimal(row['rate']) for row in events), Decimal(0))
                if request.side == Side.SELL:
                    cost = -cost
                cost_text = _text(cost)
                finite_decimal(cost_text)
        except DecimalException:
            _fail('FUNDING_MODEL_ARITHMETIC_UNSUPPORTED')
        except ValueError as error:
            if isinstance(error, FundingEvidenceError):
                raise
            _fail('FUNDING_MODEL_OUTPUT_UNSUPPORTED')
        material = dict(source=SOURCE, source_version=SOURCE_VERSION, funding_model=FUNDING_MODEL,
            arithmetic='EXACT_DECIMAL128_BOUNDED_INPUT_OUTPUT_DECIMAL34_V1', basis='ACTUAL_ENTRY_FILL_NOTIONAL',
            entry_side=request.side.value,actual_entry_fills=fill_material,actual_entry_notional=_text(basis),
            source_snapshot_hash=observed.snapshot_hash,source_material=body,
            trade_plan_id=facts['trade_plan_id'],position_id=facts['position_id'],symbol=facts['symbol'],
            interval_start=facts['interval_start'],interval_end=facts['interval_end'],interval_semantics=INTERVAL_SEMANTICS)
        evidence = dict(schema_version=SCHEMA_VERSION,funding_evidence_profile_version=FUNDING_EVIDENCE_PROFILE_VERSION,
            source_kind='PAPER_MODEL',source=SOURCE,source_version=SOURCE_VERSION,source_material_hash=_hash(material),
            source_record_count=len(events),source_complete_through=observed.complete_through,
            trade_plan_id=facts['trade_plan_id'],position_id=facts['position_id'],symbol=facts['symbol'],
            interval_start=facts['interval_start'],interval_end=facts['interval_end'],interval_semantics=INTERVAL_SEMANTICS,
            status='INCLUDED' if events else 'ZERO_CONFIRMED',funding_cost=cost_text,cost_currency='USDT',calculated_at=_fmt_utc(calculated))
        evidence['funding_evidence_id'] = stable_funding_evidence_id(evidence)
        return evidence
