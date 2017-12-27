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
from time import sleep
from stocklook.utils.timetools import timestamp_from_utc, now, now_minus
from pandas import Timestamp


class GdaxProducts:
    """
    Stores available GDAX products.
    """
    BTC_USD = 'BTC-USD'
    ETH_USD = 'ETH-USD'
    LTC_USD = 'LTC-USD'
    BCH_USD = 'BCH-USD'
    LIST = [BTC_USD, ETH_USD, LTC_USD, BCH_USD]


class GdaxProduct:
    CHART3DAY = 'CHART3DAY'
    CHART7DAY = 'CHART7DAY'
    CHART14DAY = 'CHART14DAY'
    CHART30DAY = 'CHART30DAY'
    CHART90DAY = 'CHART90DAY'

    def __init__(self, name, gdax, sync_interval=60*5):
        self.name = name
        self.currency = name.split('-')[0]
        self.gdax = gdax
        self.account = gdax.get_account(self.currency)
        self._price = None
        self._volume24hr = None
        self._charts = dict()
        self._high24hr = None
        self._low24hr = None
        self.times = dict()  # Sync date/times are stored here.
        self.sync_interval = sync_interval

    @property
    def price(self):
        self.sync_ticker_info(force=False)
        return self._price

    @property
    def volume24hr(self):
        self.sync_ticker_info(force=False)
        return self._volume24hr

    @property
    def high24hr(self):
        self.sync_24hr_stats(force=False)
        return self._high24hr

    @property
    def low24hr(self):
        self.sync_24hr_stats(force=False)
        return self._low24hr

    def get_chart(self, name):
        return self._charts[name]

    def remove_chart(self, name):
        return self._charts.pop(name)

    def sync_charts(self, names=None):
        if names is None:
            names = self._charts.keys()

        for n in names:
            c = self._charts[n]
            c._df = None
            c.df

    def sync_ticker_info(self, force=True):
        u = self.times.get('t')
        if not force and u:
            t = now_minus(seconds=self.sync_interval)
            if u > t:
                return False

        t = self.gdax.get_ticker(self.name)
        self._price = float(t['price'])
        self._volume24hr = float(t['volume'])
        self.times['t'] = now()

    def sync_account_info(self, force=True):
        u = self.times.get('a')
        if not force and u:
            t = now_minus(seconds=self.sync_interval)
            if u > t:
                return False

        self.gdax.sync_accounts()
        self.times['a'] = now()

    def sync_24hr_stats(self, force=True):
        u = self.times.get('s')
        if not force and u:
            t = now_minus(seconds=self.sync_interval)
            if u > t:
                return False

        s = self.gdax.get_24hr_stats(self.name)
        self._volume24hr = float(s['volume'])
        self._high24hr = float(s['high'])
        self._low24hr = float(s['low'])
        self.times['s'] = now()