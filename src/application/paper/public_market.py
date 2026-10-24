"""Explicit keyless public market selection and immutable owner subscriptions.

Selection permits public reads only. Paper eligibility, workflow, risk, and E6
run authority continue to be checked by their existing owners.
"""
from contextlib import ExitStack
from dataclasses import dataclass
import os
from pathlib import Path

from application.config import load_config, product_namespace
from application.cloud.protocol import CloudError
from application.cloud.safe_files import _windows_read, _posix_read, write_immutable
from application.datasets.catalog import canonical, decode, digest, read_local
from application.platform.restoration import require_valid_restoration
from application.platform.scope_lock import ProcessScopeLock, operational_lock_root
from application.platform.supervision import PROCESS_ROLES

SELECTION_FILE='public-market.json'
PROFILE_KEYS={'schema_version','namespace','provider','symbol','source_kind','read_only',
              'workflow_authorized','poll_interval_seconds'}


def validate_profile(value):
    if (not isinstance(value,dict) or set(value)!=PROFILE_KEYS
            or value['schema_version']!='r7-public-market-v0.2'
            or value['namespace']!='LOCAL_RESEARCH' or value['provider']!='OKX_PUBLIC'
            or value['symbol']!='BTC_USDT_PERP' or value['source_kind']!='PUBLIC_MARKET'
            or value['read_only'] is not True or value['workflow_authorized'] is not True
            or type(value['poll_interval_seconds']) is not int or not 1<=value['poll_interval_seconds']<=60):
        raise ValueError('Exact explicitly authorized BTC public read-only selection required')
    return dict(value)


def load_market_profile(config):
    if product_namespace(config)!='LOCAL_RESEARCH':
        raise ValueError('Public market selection requires ordinary local namespace')
    if not (config.local_data_root/SELECTION_FILE).exists():return None
    return validate_profile(decode(read_local(config.local_data_root,SELECTION_FILE,16384)))


def configure_market_data(config_path,selection_profile):
    config=load_config(config_path)
    from application.entrypoints import _outside_installation
    _outside_installation(config.local_data_root)
    if product_namespace(config)!='LOCAL_RESEARCH':raise ValueError('Ordinary local profile required')
    profile=Path(selection_profile)
    if not profile.is_absolute() or '..' in profile.parts or str(profile).startswith(('\\\\','//')):
        raise ValueError('Absolute local operator public market profile required')
    try:resolved=profile.resolve(strict=True)
    except OSError:raise ValueError('Local public market selection unavailable') from None
    if config.cloud_root is not None and resolved.is_relative_to(config.cloud_root):
        raise ValueError('Public market selection must be outside cloud staging')
    _outside_installation(resolved)
    try:raw=(_windows_read if os.name=='nt' else _posix_read)(profile,16384,require_single_link=True)
    except CloudError:raise ValueError('Local public market selection unavailable') from None
    selected=validate_profile(decode(raw));raw=canonical(selected).encode('utf-8')
    with ExitStack() as stack:
        for role in PROCESS_ROLES:
            stack.enter_context(ProcessScopeLock(role+':'+config.product_instance_id,lock_root=operational_lock_root(config)))
        if load_config(config_path)!=config:raise ValueError('Configuration changed during public selection')
        if require_valid_restoration(config)['status']!='NOT_RESTORED':
            raise ValueError('Restored product requires separate reauthorization')
        existing=(config.local_data_root/SELECTION_FILE).exists()
        if existing:
            if load_market_profile(config)!=selected:raise ValueError('Existing public market selection must be preserved')
        else:
            from application.platform.private_files import create_private_directory,require_private
            if config.local_data_root.exists():require_private(config.local_data_root,directory=True)
            else:create_private_directory(config.local_data_root)
            write_immutable(config.local_data_root,SELECTION_FILE,raw)
    return dict(status='ALREADY_CONFIGURED' if existing else 'PUBLIC_MARKET_CONFIGURED',
        namespace='LOCAL_RESEARCH',selection_hash=digest(raw),market='NOT_STARTED',paper='NOT_STARTED',
        provider_requests=0,credentials='NONE',provider_mutation=0,capital='NONE')


@dataclass(frozen=True)
class MarketSubscription:
    run_id:str
    namespace:str
    runtime_token:str
    e6_generation:int
    strategy_content_hash:str
    symbol:str
    # frame, requested warmup bars, cache capacity, last durable close (or None).
    frames:tuple
    last_observed_at:str|None


def subscription(runtime,namespace,runtime_token):
    """Called only by the owner; no connection, service or mutable state escapes."""
    recovered=runtime.service.process.management_snapshot(runtime.run_id)
    if recovered.process_generation!=runtime.coordinator.generation:return None
    strategy=runtime.engine.strategy;cap=runtime.engine.config['maximum_cached_candles_per_timeframe']
    expressions=tuple(getattr(strategy,'features',{}).values())+tuple(value for value in
        (getattr(strategy,'long_expression',None),getattr(strategy,'short_expression',None)) if value is not None)
    requested=max([1]+[expression.minimum_history for expression in expressions]) if expressions else cap
    state=recovered.state['runtime'];frames=[]
    for frame in strategy.required_timeframes:
        cached=state['candles'].get(frame,[])
        frames.append((frame,min(cap,requested+1),cap,cached[-1]['close_time'] if cached else None))
    market=state['last_market']
    return MarketSubscription(runtime.run_id,namespace,runtime_token,recovered.process_generation,
        strategy.content_hash,strategy.symbol,tuple(frames),None if market is None else market['observed_at'])
