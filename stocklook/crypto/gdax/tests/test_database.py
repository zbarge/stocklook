"""
MIT License

Copyright (c) 2017 Zeke Barge

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
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





