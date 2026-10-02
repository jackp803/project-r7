from datetime import datetime,timedelta,timezone
from decimal import Decimal
from market_data.candle import Candle


def bars(prices,*,ohlc=None,timeframe='1h'):
    seconds={'1m':60,'15m':900,'1h':3600,'4h':14400}[timeframe]
    start=datetime(2026,10,2,tzinfo=timezone.utc)
    rows=[]
    for i,price in enumerate(prices):
        close=Decimal(str(price))
        high,low=(close+2,close-2) if ohlc is None else map(lambda x:Decimal(str(x)),ohlc[i])
        rows.append(Candle('contracts-v0.1','TEST_USDT_PERP',timeframe,start+timedelta(seconds=i*seconds),
                           start+timedelta(seconds=(i+1)*seconds),close,high,low,close,Decimal('100'),True,'local-golden-fixture'))
    return tuple(rows)


def api(test):
    import importlib.util
    test.assertIsNotNone(importlib.util.find_spec('indicators.v02.features'),'Numerical implementation is missing')
    from indicators.v02 import features
    return features


def spec(api,name,*,output='value',**parameters):
    versions={'SMA':'r7-sma-v1','EMA':'r7-ema-v1','RSI':'r7-rsi-wilder-v1','ATR':'r7-atr-wilder-v1',
              'ADX':'r7-adx-wilder-v1','MACD':'r7-macd-v1','BOLLINGER':'r7-bollinger-pop-v1','DONCHIAN':'r7-donchian-v1'}
    return api.FeatureSpec(name,versions[name],parameters,output,'1h')
