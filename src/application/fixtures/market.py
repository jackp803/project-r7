"""Named synthetic E1 scenario for the public isolated FIXTURE Paper owner.

An explicitly synthetic UTC clock drives the accelerated scenario; process
health keeps its actual clock. Two aligned mechanical uptrend candles are
supplied only to an empty run; durable state drives the synthetic target.
This producer has no provider port and writes no lifecycle or execution facts.
"""
from datetime import datetime,timedelta,timezone
from decimal import Decimal

from execution.models import require_utc
from market_data.candle import Candle
from market_data.current import MarketSnapshot
from application.paper.service import PaperMarketEvent


class FixtureScenarioClock:
    """Product-owned virtual clock; never a real-forward time producer."""
    def __init__(self,*,temporal=None):
        actual=datetime.now(timezone.utc)
        self.value=actual.replace(minute=0,second=0,microsecond=0)+timedelta(hours=1)
        self.origin=None
        if temporal is not None:
            from .temporal import validate,utc
            document=validate(temporal)
            if document['case']=='research-expire-before-robustness':
                raise ValueError('Research-only temporal case cannot initialize Paper timing')
            self.value=utc(document['validity']['until'])
            if document['case']=='paper-expire-after-protection':self.value-=timedelta(seconds=2)
            self.origin=self.value

    def __call__(self):
        return self.value

    def resume(self,observed_at):
        if observed_at is not None:
            value=datetime.fromisoformat(observed_at.replace('Z','+00:00'))
            require_utc(value,'retained fixture clock')
            if self.origin is not None and (value<self.origin or value+timedelta(seconds=1)<self.value):
                raise ValueError('Retained named fixture observation regressed')
            self.value=value+timedelta(seconds=1)

    def advance(self):
        self.value+=timedelta(seconds=1)


def fixture_market_event(runtime_state,now,*,timeframe='1h',paper_case=None):
    require_utc(now,'fixture market observation')
    seconds={'1h':3600,'1m':60}[timeframe]
    position=runtime_state['position']
    price='60020' if position is not None else '60000'
    stale=False
    if paper_case is not None:
        from .faults import validate,HOLD_SECONDS
        case=validate(paper_case)['case']
        price='60000'
        anchor=runtime_state['exit_anchor']
        if position is not None and anchor is not None:
            first=datetime.fromisoformat(anchor['payload']['first_fill_at'].replace('Z','+00:00'))
            require_utc(first,'original fixture first-fill anchor')
            age=(now-first).total_seconds()
            if age<0:raise ValueError('Fixture market clock predates original first fill')
            if age>=HOLD_SECONDS:price='60020'
            if position['lifecycle_state']=='OPEN_PROTECTED' and case=='missing-market-hold' and 1<=age<8:
                # Retain last-known facts while withholding fresh acquisitions
                # beyond the unchanged five-second owner freshness threshold.
                return None
            if position['lifecycle_state']=='OPEN_PROTECTED' and 1<=age<2:
                if case=='stale-market-hold':stale=True
                if case=='duplicate-market-hold':
                    from application.paper.engine import _market
                    if runtime_state['last_market'] is None:raise ValueError('Actual original snapshot required for duplicate input')
                    return PaperMarketEvent(_market(runtime_state['last_market']),(),'FIXTURE')
    snapshot=MarketSnapshot('contracts-v0.1','BTC_USDT_PERP',now-timedelta(seconds=10) if stale else now,now,
        'HEALTHY','SYNTHETIC_FIXTURE',last_price=Decimal(price),freshness_ms=10000 if stale else 0)
    boundary=now.replace(second=0,microsecond=0)
    if timeframe=='1h':boundary=boundary.replace(minute=0)
    candles=tuple(Candle('contracts-v0.1','BTC_USDT_PERP',timeframe,
        boundary-timedelta(seconds=(2-index)*seconds),boundary-timedelta(seconds=(1-index)*seconds),
        Decimal(value),Decimal(value)+1,Decimal(value)-1,Decimal(value),Decimal('1'),
        True,'SYNTHETIC_FIXTURE',received_at=boundary)
        for index,value in enumerate(('59000','60000'))) if not runtime_state['candles'] else ()
    return PaperMarketEvent(snapshot,candles,'FIXTURE')
