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


def fixture_market_event(runtime_state,now):
    require_utc(now,'fixture market observation')
    position=runtime_state['position']
    price='60020' if position is not None else '60000'
    snapshot=MarketSnapshot('contracts-v0.1','BTC_USDT_PERP',now,now,
        'HEALTHY','SYNTHETIC_FIXTURE',last_price=Decimal(price),freshness_ms=0)
    boundary=now.replace(minute=0,second=0,microsecond=0)
    candles=tuple(Candle('contracts-v0.1','BTC_USDT_PERP','1h',
        boundary-timedelta(hours=2-index),boundary-timedelta(hours=1-index),
        Decimal(value),Decimal(value)+1,Decimal(value)-1,Decimal(value),Decimal('1'),
        True,'SYNTHETIC_FIXTURE',received_at=boundary)
        for index,value in enumerate(('59000','60000'))) if not runtime_state['candles'] else ()
    return PaperMarketEvent(snapshot,candles,'FIXTURE')
