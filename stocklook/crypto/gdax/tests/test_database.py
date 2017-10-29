import pytest
from stocklook.crypto.gdax.db import GdaxOHLCViewer, GdaxDatabase
from pandas import Timestamp, DateOffset, DataFrame

from stocklook.utils.timetools import now, now_minus, now_plus, timestamp_to_local, timestamp_from_utc


def get_sample_chart(size=31, price_factor=1.25, minute_interval=5):
    data = list()
    start = now_minus(hours=10)
    price = 1
    for i in range(1, size + 1):
        data.append((start, price))
        start += DateOffset(minutes=minute_interval)
        price *= price_factor

    return DataFrame(data=data,
                     columns=['time', 'price'],
                     index=range(len(data)))


def test_ohlc_database():
    pair = 'LTC-USD'
    v = GdaxOHLCViewer()
    v.set_pair(pair)
    v.sync_ohlc(months=6, thread=False)





