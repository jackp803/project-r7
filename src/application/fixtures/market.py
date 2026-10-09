"""Named synthetic E1 scenario for the public isolated FIXTURE Paper owner.

Actual UTC drives observations and protection. Two mechanical uptrend candles
are supplied only to an empty run; durable state drives the synthetic target.
This producer has no provider port and writes no lifecycle or execution facts.
"""
from datetime import timedelta
from decimal import Decimal

from execution.models import require_utc
from market_data.candle import Candle
from market_data.current import MarketSnapshot
from application.paper.service import PaperMarketEvent


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
