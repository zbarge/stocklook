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
from pandas import DateOffset
from stocklook.utils.timetools import now, now_minus, now_plus
from .chartdata import GdaxChartData


class GdaxTrader:
    def __init__(self, gdax, product, analyzers=None, interval=10):
        self.gdax = gdax
        self.product = product
        self.currency = product.split('-')[0]
        self.account = gdax.accounts[self.currency]
        self.usd_account = gdax.accounts[self.account.USD]
        self.analyzers = dict()
        self.interval = interval
        self.h = None
        self.d = None
        self.w = None
        self.m = None
        self.times = dict()
        self.sync_intervals = dict(h=60*3,
                                   d=60*15,
                                   w=60*60*2,
                                   m=60*60*6)

        if analyzers is not None:
            self.register_analyzers(analyzers)

    @property
    def cash_available(self):
        return self.usd_account.usd_value

    def sync_chart_data(self):
        """
        Ensures GdaxChartData objects are created and kept up-to-date.
        These objects are assigned to GdaxAnalyzer objects so they'll
        all be analyzing the same set(s) of data refreshed on a timely basis.

        ChartData objects are assigned as follows:
            GdaxTrader.h: 4 hours of data, 5 minutes timeframes
            GdaxTrader.d: 1 day of data, 15 minutes timeframes
            GdaxTrader.w: 1 week of data, 4 hours timeframes
            GdaxTrader.m 1 month of data, 4 hours timeframes

        Default Timeframes are as follows:
            GdaxTrader.h: 3 minute refreshes - most-up-to-date
            GdaxTrader.d: 15 minute refreshes
            GdaxTrader.w: 2 hour refreshes
            GdaxTrader.m: 6 hour refreshes

        :return:
        """

        times = self.get_next_sync_times()
        t = now()
        h_due = times['h'] <= t
        d_due = times['d'] <= t
        w_due = times['w'] <= t
        m_due = times['m'] <= t

        # Hour Chart
        if self.h is None or h_due:
            start, end = now_minus(hours=4), now()
            granularity = 60 * 5

            if self.h is None:
                self.h = GdaxChartData(self.gdax,
                                       self.product,
                                       start,
                                       end,
                                       granularity)
            else:
                self.h.refresh(start=start, end=end)

            self.times['h'] = end

        # Day chart
        if self.d is None or d_due:
            start, end = now_minus(hours=24), now()
            granularity = 60 * 15
            if self.d is None:
                self.d = GdaxChartData(self.gdax,
                                       self.product,
                                       start,
                                       end,
                                       granularity)
            else:
                self.d.refresh(start=start, end=end)

            self.times['d'] = end

        # Week chart
        if self.w is None or w_due:
            start = now_minus(days=7)
            end = now()
            granularity = 60 * 60 * 4
            if self.w is None:
                self.w = GdaxChartData(self.gdax,
                                       self.product,
                                       start,
                                       end,
                                       granularity)
            else:
                self.w.refresh(start=start, end=end)

            self.times['w'] = end

        # Month chart
        if self.m is None or m_due:
            start = now_minus(months=1)
            end = now()
            granularity = 60 * 60 * 24
            if self.m is None:
                self.m = GdaxChartData(self.gdax,
                                       self.product,
                                       start,
                                       end,
                                       granularity)
            else:
                self.m.refresh(start=start, end=end)
            self.times['m'] = end

        book = self.gdax.get_book(self.product)
        # Make sure analyzers aren't missing charts.
        # if h chart is missing all are probably missing.
        for a in self.analyzers.values():
            if a.h is None:
                a.register_data(self.h, self.d, self.w, self.m)

        return self.h, self.d, self.w, self.m

    def get_next_sync_times(self):
        times = dict()
        for ctype, interval in self.sync_intervals.items():
            synced = self.times.get(ctype, None)
            if synced is None:
                times[ctype] = now()
            else:
                due = synced + DateOffset(seconds=interval)
                times[ctype] = due
        return times

    def run_once(self):
        self.sync_chart_data()
        for a in self.analyzers.values():
            book = self.gdax.get_book(self.product)
            candles = None
            a.execute(book, candles)

        sleep(self.interval)

    def run(self):
        while True:
            self.run_once()

    def register_analyzer(self, name, analyzer):
        """
        Registers an analyzer
        :param name:
        :param analyzer:
        :return:
        """
        if not hasattr(analyzer, 'execute'):
            raise AttributeError("Analyzer must have 'execute' method.")
        self.analyzers[name] = analyzer

    def remove_analyzer(self, name):
        self.analyzers.pop(name)

    def register_analyzers(self, analyzers):
        """
        Register GdaxAnalyzer(s) to the GdaxTrader.

        :param analyzers: (list, tuple, dict, GdaxAnalyzer)
            (list, tuple)
            An iterable of GdaxAnalyzer objects.

        :return:
        """
        if isinstance(analyzers, (list, tuple)):
            for a in analyzers:
                self.register_analyzer(a.name, a)

        elif isinstance(analyzers, dict):
            for name, method in analyzers.items():
                self.register_analyzer(name, method)

        else:
            self.register_analyzer(analyzers.name, analyzers)


class GdaxAnalyzer:
    BUY = 'buy'
    HOLD = 'hold'
    CLOSE = 'close'

    def __init__(self, name, product, gdax, order_sys):
        self.name = name
        self.gdax = gdax
        self.sys = order_sys
        self._orders = list()
        self.product = product
        self.coin_currency, self.base_currency = product.split('-')

        self.h = None # ChartData of past hour, 5 minute candles
        self.d = None # ChartData of past day, 15 minute candles
        self.w = None # ChartData of past week, 4 hour candles
        self.m = None # ChartData of past month, daily candles

    def register_data(self, h=None, d=None, w=None, m=None):
        if h is not None:
            self.h = h  # ChartData of past hour, 5 minute candles

        if d is not None:
            self.d = d  # ChartData of past day, 15 minute candles

        if w is not None:
            self.w = w  # ChartData of past week, 4 hour candles

        if m is not None:
            self.m = m  # ChartData of past month, daily candles

    @property
    def orders(self):
        return self._orders

    def buy(self, gdax_order):
        raise NotImplementedError("Child classes must implement this method")

    def sell(self, gdax_order):
        raise NotImplementedError("Child classes must implement this method")

    def execute(self, book, candles):
        """
        This method should use the data from the book and candles
        to decide whether to open, hold, or close order(s).

        Step 1: Review the available data
        Step 2: Decide which criteria it meets - open, hold, close
        Step 3: Open an order, hold your orders and do nothing, or close your order
        :param book:
        :param candles:
        :return:
        """
        raise NotImplementedError("Child classes must implement this method")

    def signal(self):
        """
        Should return GdaxAnalyzer.BUY, GdaxAnalyzer.HOLD, or GdaxAnalyzer.CLOSE
        :return:
        """



class LTCLongAnalyzer(GdaxAnalyzer):

    def execute(self, book, chart_data):
        asks = book['asks']
        bids = book['bids']
        ask1 = float(asks[0][0])
        bid1 = float(asks[0][0])
        # Get lowest price in past month
        # Get lowest price in past week
        # Get lowest price in past day

        if ask1 > 4300 < 4400:
            print("PLACING BUY ORDER ON ASK: {}".format(ask1))