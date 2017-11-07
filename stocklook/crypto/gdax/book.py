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
from pandas import DataFrame, concat

class GdaxOrderBook:
    def __init__(self, gdax, product, data=None, level=2):
        self.gdax = gdax
        self.product = product
        self._data = (data if data is not None else dict())
        self.level = level

    @property
    def data(self):
        if not self._data:
            self._update_book()
        return self._data

    @property
    def bids(self):
        return self.data['bids']

    @property
    def asks(self):
        return self.data['asks']

    def get_ask_vol(self):
        v = (a[1] for a in self.asks)
        return sum(v)

    def get_bid_vol(self):
        v = (b[1] for b in self.bids)
        return sum(v)

    def get_next_resistance(self, qty_min=100):
        for row in self.asks:
            ask, qty, seq = row
            if qty <= qty_min:
                continue
            return ask, qty
        return 0, 0

    def get_data_frame(self):
        """
        Returns a pandas.DataFrame of the order book
        containing the following columns:

        1) price (float)
        2) qty (float)
        3) seq (unknown int)
        4) type (str, (bid, ask))
        5) total (float) The cumulative total
        5) pct_total (float) The quantity percent of total bid/ask
        :return:
        """
        a = self.asks
        b = self.bids

        cols = ['price', 'qty', 'seq']

        adf = DataFrame(data=a, columns=cols, index=range(len(a)))
        bdf = DataFrame(data=b, columns=cols, index=range(len(b)))

        adf.loc[:, 'type'] = 'ask'
        bdf.loc[:, 'type'] = 'bid'

        for df in (adf, bdf):
            df.loc[:, 'total'] = df['qty'].cumsum()
            df.loc[:, 'pct_total'] = df['qty'] / df['qty'].sum()

        return concat((adf, bdf))

    def get_next_support(self, qty_min=100):
        for row in self.bids:
            bid, qty, s = row
            if qty <= qty_min:
                continue
            return bid, qty
        return 0, 0

    def _convert_dtypes(self):
        a = self.asks
        b = self.bids
        num_types = (float, int)

        for d in (a, b):
            n = isinstance(d[0], num_types)
            if n:
                # Already been converted
                continue

            rng = range(len(d))

            for i in rng:
                d[i][0] = float(d[i][0])
                d[i][1] = float(d[i][1])

    def _update_book(self):
        b = self.gdax.get_book(self.product, self.level)
        self._data.update(b)
        self._convert_dtypes()



