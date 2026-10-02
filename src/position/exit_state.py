"""E5 codec retaining immutable first-fill clocks and monotonic exit anchors."""
from dataclasses import fields
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re

from execution.models import require_utc
from .exit_requests import (
    ExitAnchor, _validate_exit_anchor_binding, positive,
)

PROFILE = 'r7-exit-anchor-state-v0.2'
_TIMES = {'first_fill_at', 'hold_deadline', 'last_market_at'}
_DECIMALS = {'initial_reference_price', 'initial_stop', 'target_level',
             'high_water', 'low_water', 'proposed_stop'}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _hash(value): return 'sha256:' + hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()


def _decode(payload):
    if not isinstance(payload, dict) or set(payload) != {field.name for field in fields(ExitAnchor)}:
        raise ValueError('Exact E5 exit anchor fields required')
    result = {}
    for field, value in payload.items():
        if value is None:
            if field not in ('target_level', 'last_market_at'): raise ValueError('Required E5 anchor cannot be null')
        elif field in _DECIMALS:
            if not isinstance(value, str) or len(value) > 128: raise ValueError('E5 anchor requires decimal strings')
            try: value = Decimal(value)
            except InvalidOperation as exc: raise ValueError('Invalid E5 anchor decimal') from exc
            if not value.is_finite() or value <= 0: raise ValueError('E5 anchor prices must be finite and positive')
        elif field in _TIMES:
            if not isinstance(value, str) or not value.endswith('Z') or len(value) > 40:
                raise ValueError('E5 anchor requires explicit UTC clocks')
            value = datetime.fromisoformat(value[:-1] + '+00:00'); require_utc(value, field)
        elif not isinstance(value, str) or not value or len(value) > 256 or '\x00' in value:
            raise ValueError('E5 anchor requires bounded text identity')
        result[field] = value
    anchor = ExitAnchor(**result)
    for field in ('request_hash', 'approved_plan_hash'):
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', getattr(anchor, field)):
            raise ValueError('E5 anchor exact subject hashes required')
    if anchor.side not in ('LONG', 'SHORT'): raise ValueError('Invalid E5 anchor side')
    long = anchor.side == 'LONG'
    if (anchor.low_water > anchor.initial_reference_price or anchor.high_water < anchor.initial_reference_price
        or anchor.low_water > anchor.high_water or anchor.hold_deadline <= anchor.first_fill_at
        or (anchor.last_market_at is not None and anchor.last_market_at < anchor.first_fill_at)):
        raise ValueError('E5 anchor extrema/clocks inconsistent')
    if ((anchor.initial_stop >= anchor.initial_reference_price if long else anchor.initial_stop <= anchor.initial_reference_price)
        or (anchor.proposed_stop < anchor.initial_stop if long else anchor.proposed_stop > anchor.initial_stop)
        or (anchor.target_level is not None and
            (anchor.target_level <= anchor.initial_reference_price if long else anchor.target_level >= anchor.initial_reference_price))):
        raise ValueError('E5 anchor geometry widened or inconsistent')
    return anchor


def encode_exit_anchor(anchor):
    if not isinstance(anchor, ExitAnchor): raise ValueError('E5 ExitAnchor required')
    payload = {}
    for field in fields(anchor):
        value = getattr(anchor, field.name)
        if isinstance(value, datetime):
            require_utc(value, field.name)
            value = value.isoformat().replace('+00:00', 'Z')
        elif isinstance(value, Decimal): value = str(value)
        payload[field.name] = value
    _decode(payload)
    return {'schema_version': PROFILE, 'payload': payload, 'payload_hash': _hash(payload)}


def restore_exit_anchor(value, *, request, position, plan):
    if not isinstance(value, dict) or set(value) != {'schema_version', 'payload', 'payload_hash'} or value['schema_version'] != PROFILE:
        raise ValueError('Unsupported E5 exit anchor checkpoint')
    try:
        if len(_canonical(value).encode('utf-8')) > 8192 or _hash(value['payload']) != value['payload_hash']:
            raise ValueError('E5 anchor checkpoint hash/size mismatch')
    except (TypeError, RecursionError) as exc: raise ValueError('Invalid E5 anchor JSON') from exc
    anchor = _decode(value['payload'])
    _validate_exit_anchor_binding(request, position, plan, anchor)
    target = plan['protection_instruction'].get('target_level')
    expected_target = positive(target) if target is not None else None
    if anchor.target_level != expected_target: raise ValueError('E5 anchor approved target changed')
    return anchor
