"""E4 controlled allocated-ledger source, never an actual provider adapter.

Only the registered FIXTURE wire is implemented. There is no production
fallback and no caller completeness flag. See FIXTURE_FUNDING_LEDGER_SOURCE.
"""
from collections import OrderedDict
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Context, Decimal, Inexact, InvalidOperation, Overflow, Rounded, localcontext
import hashlib
import json
import re

from execution.funding import (FundingEvidenceError, FUNDING_EVIDENCE_PROFILE_VERSION,
    INTERVAL_SEMANTICS, SCHEMA_VERSION, _fmt_utc, _validate_plan_and_flat_position,
    stable_funding_evidence_id)

FIXTURE_WIRE_PROFILE='r7-fixture-allocated-funding-page-v0.1'
FIXTURE_SOURCE='R7_FIXTURE_ALLOCATED_FUNDING_LEDGER'
FIXTURE_SOURCE_VERSION='r7-fixture-allocated-ledger-v0.1'
FIXTURE_READ_PATH='/r7-fixture/v1/allocated-funding'
MAX_PAGES=16
MAX_RECORDS=1000
MAX_WIRE_BYTES=1048576
_PAGE_FIELDS=frozenset(('profile','snapshot_id','snapshot_at','subject','coverage_start',
    'complete_through','page_index','cursor','next_cursor','records'))
_ROW_FIELDS=frozenset(('record_id','event_time','funding_cost','cost_currency','allocation'))


def _fail(code):raise FundingEvidenceError(code,code)


def _identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}',value):
        _fail('FUNDING_LEDGER_IDENTIFIER_INVALID')
    return value


def _time(value):
    if isinstance(value,datetime):
        if value.tzinfo is None or value.utcoffset()!=timezone.utc.utcoffset(value):
            _fail('FUNDING_LEDGER_UTC_REQUIRED')
        return value.astimezone(timezone.utc)
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z',value):
        _fail('FUNDING_LEDGER_UTC_REQUIRED')
    try:return datetime.fromisoformat(value[:-1]+'+00:00')
    except ValueError:_fail('FUNDING_LEDGER_UTC_REQUIRED')


def _json(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def _hash(value):return hashlib.sha256(_json(value).encode()).hexdigest()


def _decimal(value):
    if not isinstance(value,str) or len(value)>128 or not re.fullmatch(r'-?(?:0|[1-9]\d*)(?:\.\d+)?',value):
        _fail('FUNDING_LEDGER_DECIMAL_INVALID')
    return Decimal(value)


def _decimal_text(value):
    if value==0:return '0'
    text=format(value,'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


@dataclass(frozen=True)
class FundingLedgerSubject:
    trade_plan_id:str
    position_id:str
    symbol:str
    account_hash:str
    provider_ref:str
    native_position_id:str
    interval_start:str
    interval_end:str


def _subject(value):
    if type(value) is not FundingLedgerSubject:_fail('FUNDING_LEDGER_TYPED_SUBJECT_REQUIRED')
    document=asdict(value)
    for key in ('trade_plan_id','position_id','symbol','provider_ref','native_position_id'):_identifier(document[key])
    if not isinstance(value.account_hash,str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',value.account_hash):
        _fail('FUNDING_LEDGER_ACCOUNT_SCOPE_REQUIRED')
    start,end=(_time(value.interval_start),_time(value.interval_end))
    if start>=end or any(document[k]!=_fmt_utc(t) for k,t in (('interval_start',start),('interval_end',end))):
        _fail('FUNDING_LEDGER_EXACT_INTERVAL_REQUIRED')
    return document,start,end


@dataclass(frozen=True)
class _ObservedAllocation:
    subject:FundingLedgerSubject
    material_json:str
    funding_cost:str
    record_count:int
    complete_through:str


class FixtureFundingLedgerSource:
    """Trusted E4 FIXTURE composition; callback is not an HTTP-supplied object.

    Application composition wraps an actual guarded FakeProductProvider GET.
    Unit callbacks exercise only this source wire and normalization semantics.
    """
    def __init__(self,read_page):
        if not callable(read_page):_fail('FUNDING_LEDGER_READER_REQUIRED')
        self._read_page=read_page;self._issued=OrderedDict()

    def read_interval(self,subject,*,request_started_at,received_at):
        document,start,end=_subject(subject)
        started=_time(request_started_at)
        if end>started:_fail('FUNDING_LEDGER_OBSERVATION_CLOCK_INVALID')
        allocation={k:v for k,v in document.items() if k not in ('interval_start','interval_end')}
        cursor=None;seen_cursors=set();seen_ids=set();records=[];page_hashes=[];wire_size=0;anchor=None
        for index in range(MAX_PAGES):
            try:page=self._read_page(dict(subject=deepcopy(document),cursor=cursor))
            except (StopIteration,ValueError,OSError):_fail('FUNDING_LEDGER_PAGE_UNAVAILABLE')
            if type(page) is not dict or set(page)!=_PAGE_FIELDS or page['profile']!=FIXTURE_WIRE_PROFILE:
                _fail('FUNDING_LEDGER_PAGE_INVALID')
            if (type(page['page_index']) is not int or page['page_index']!=index or
                    page['cursor']!=cursor or type(page['subject']) is not dict or page['subject']!=document):
                _fail('FUNDING_LEDGER_PAGE_SCOPE_OR_CHAIN_INVALID')
            snapshot_id=_identifier(page['snapshot_id']);snapshot=_time(page['snapshot_at'])
            coverage,through=_time(page['coverage_start']),_time(page['complete_through'])
            if not coverage<=start<end<=through<=snapshot<=started:
                _fail('FUNDING_LEDGER_INCOMPLETE_OR_FUTURE_SNAPSHOT')
            current=(snapshot_id,_fmt_utc(snapshot),_fmt_utc(coverage),_fmt_utc(through))
            if anchor is not None and current!=anchor:_fail('FUNDING_LEDGER_SNAPSHOT_CHANGED')
            anchor=current
            rows=page['records']
            if type(rows) is not list or len(rows)+len(seen_ids)>MAX_RECORDS:_fail('FUNDING_LEDGER_RECORD_LIMIT')
            for row in rows:
                if type(row) is not dict or set(row)!=_ROW_FIELDS:_fail('FUNDING_LEDGER_ROW_INVALID')
                identity=_identifier(row['record_id'])
                if identity in seen_ids:_fail('FUNDING_LEDGER_DUPLICATE_RECORD')
                seen_ids.add(identity)
                if type(row['allocation']) is not dict or row['allocation']!=allocation:
                    _fail('FUNDING_LEDGER_FOREIGN_ALLOCATION')
                if row['cost_currency']!='USDT':_fail('FUNDING_LEDGER_UNSUPPORTED_CURRENCY')
                event=_time(row['event_time']);cost=_decimal(row['funding_cost'])
                if not coverage<=event<=through:_fail('FUNDING_LEDGER_EVENT_OUTSIDE_COVERAGE')
                if start<=event<end:
                    records.append(dict(record_id=identity,event_time=_fmt_utc(event),funding_cost=_decimal_text(cost)))
            following=page['next_cursor']
            if following is not None:
                _identifier(following)
                if following in seen_cursors:_fail('FUNDING_LEDGER_CURSOR_LOOP')
                seen_cursors.add(following)
            raw=_json(page).encode();wire_size+=len(raw)
            if wire_size>MAX_WIRE_BYTES:_fail('FUNDING_LEDGER_WIRE_LIMIT')
            page_hashes.append(hashlib.sha256(raw).hexdigest())
            if following is None:break
            cursor=following
        else:_fail('FUNDING_LEDGER_PAGE_LIMIT_OR_UNEXHAUSTED')
        received=_time(received_at() if callable(received_at) else received_at)
        if received<started:_fail('FUNDING_LEDGER_OBSERVATION_CLOCK_INVALID')
        records.sort(key=lambda row:(_time(row['event_time']),row['record_id']))
        # 128-character input lexemes with at most1,000 rows need at most259
        # significant digits across their maximum integer/fractional scales.
        context=Context(prec=300,traps=[Inexact,Rounded,InvalidOperation,Overflow])
        with localcontext(context):total=sum((Decimal(row['funding_cost']) for row in records),Decimal(0))
        material=dict(profile=FIXTURE_WIRE_PROFILE,source=FIXTURE_SOURCE,source_version=FIXTURE_SOURCE_VERSION,
            scope_commitment=_hash(allocation),trade_plan_id=subject.trade_plan_id,position_id=subject.position_id,
            symbol=subject.symbol,interval_start=subject.interval_start,interval_end=subject.interval_end,
            snapshot_id=anchor[0],snapshot_at=anchor[1],coverage_start=anchor[2],complete_through=anchor[3],
            page_hashes=page_hashes,records=records)
        observed=_ObservedAllocation(subject,_json(material),_decimal_text(total),len(records),anchor[3])
        self._issued[id(observed)]=(observed,_hash(asdict(observed)))
        while len(self._issued)>128:self._issued.popitem(last=False)
        return observed

    def require(self,observed):
        entry=self._issued.get(id(observed))
        if type(observed) is not _ObservedAllocation or entry is None or entry[0] is not observed or entry[1]!=_hash(asdict(observed)):
            _fail('FUNDING_LEDGER_ORIGINAL_SOURCE_ISSUANCE_REQUIRED')
        return observed


def produce_broker_ledger_funding_evidence(parent_plan,final_position,observed,*,source,calculated_at):
    """Emit existing canonical funding evidence from an exact issued allocation.

    Currently only the named fixture source is registered. This function is
    not a default or credentialed production funding adapter.
    """
    if type(source) is not FixtureFundingLedgerSource:_fail('FUNDING_LEDGER_REGISTERED_SOURCE_REQUIRED')
    source.require(observed)
    facts=_validate_plan_and_flat_position(parent_plan,final_position)
    subject=observed.subject
    if any(facts[key]!=getattr(subject,key) for key in ('trade_plan_id','position_id','symbol','interval_start','interval_end')):
        _fail('FUNDING_LEDGER_CANONICAL_SUBJECT_CHANGED')
    calculated=_time(calculated_at)
    if calculated<facts['interval_end_dt']:_fail('CALCULATED_BEFORE_INTERVAL_END')
    evidence=dict(schema_version=SCHEMA_VERSION,funding_evidence_profile_version=FUNDING_EVIDENCE_PROFILE_VERSION,
        source_kind='BROKER_LEDGER',source=FIXTURE_SOURCE,source_version=FIXTURE_SOURCE_VERSION,
        source_material_hash=hashlib.sha256(observed.material_json.encode()).hexdigest(),
        source_record_count=observed.record_count,source_complete_through=observed.complete_through,
        trade_plan_id=facts['trade_plan_id'],position_id=facts['position_id'],symbol=facts['symbol'],
        interval_start=facts['interval_start'],interval_end=facts['interval_end'],interval_semantics=INTERVAL_SEMANTICS,
        status='INCLUDED' if observed.record_count else 'ZERO_CONFIRMED',funding_cost=observed.funding_cost,
        cost_currency='USDT',calculated_at=_fmt_utc(calculated))
    evidence['funding_evidence_id']=stable_funding_evidence_id(evidence)
    return evidence
