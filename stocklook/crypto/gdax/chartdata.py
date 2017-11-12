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
from stockstats import StockDataFrame
from stocklook.patterns import InsideBars, HigherHighs


def mean(numbers):
    return float(sum(numbers)) / max(len(numbers), 1)


def velocity(range, avg_range, volume, avg_volume):
    """
    The average of the average of the range and volume for a period.
    :param range:
    :param avg_range:
    :param volume:
    :param avg_volume:
    :return:
    """
    rng_rate = range / avg_range
    vol_rate = volume / avg_volume
    total = sum((rng_rate, vol_rate))
    return round(total / 2, 2)


class GdaxChartData:
    SYNC_INTERVAL = 60*5
    OPEN = 'open'
    HIGH = 'high'
    LOW = 'low'
    CLOSE = 'close'
    TIME = 'time'
    SMA5 = 'sma5'
    SMA8 = 'sma8'
    SMA18 = 'sma18'
    SMA50 = 'sma50'
    SMA100 = 'sma100'
    SMA200 = 'sma200'
    RANGE = 'range'
    RSI = 'rsi'
    MACD = 'macd'
    MACDS = 'macds'
    MACDH = 'macdh'
    RSI6 = 'rsi_6'
    RSI12 = 'rsi_12'
    TR = 'tr'
    ATR = 'atr'

    PRICE_CHANGE = 'price_change'
    VELOCITY = 'velocity'
    VOLUME = 'volume'

    def __init__(self, gdax, product, start, end, granularity=60*60, df=None):
        self.gdax = gdax
        self.product = product
        self.start = start
        self.end = end
        self.granularity = granularity
        self._df = df
        self._price = None
        self._volume = None
        self._ticker_updated = None

    @property
    def df(self):
        if self._df is None:
            self.get_candles()
        return self._df

    @property
    def avg_range(self):
        rng = self.RANGE
        df = self.df
        mask = df[rng].isin(df[rng].dropna())
        return df.loc[mask, rng].mean()

    @property
    def avg_rsi(self):
        rsi = self.RSI
        df = self.df
        return df.loc[df[rsi] > 0, rsi].mean()

    @property
    def avg_vol(self):
        df = self.df
        mask = df[self.VOLUME] > 0
        return df.loc[mask, self.VOLUME].mean()

    @property
    def avg_close(self):
        return self.df['close'].mean()

    def refresh(self, start=None, end=None):
        if start:
            self.start = start
        if end:
            self.end = end

        self.get_candles()

    def get_candles(self):
        from stocklook.quant import RSI
        df = self.gdax.get_candles(self.product,
                                   self.start,
                                   self.end,
                                   self.granularity,
                                   convert_dates=True,
                                   to_frame=True)
        df = StockDataFrame.retype(df)
        close = df[self.CLOSE]
        df.loc[:, self.SMA5] = close.rolling(5).mean()
        df.loc[:, self.SMA8] = close.rolling(8).mean()
        df.loc[:, self.SMA18] = close.rolling(18).mean()
        df.loc[:, self.SMA50] = close.rolling(50).mean()
        df.loc[:, self.SMA100] = close.rolling(100).mean()
        df.loc[:, self.SMA200] = close.rolling(200).mean()
        df.loc[:, self.RANGE] = df.high - df.low
        df.loc[:, self.RSI] = RSI(close, 14)
        df.loc[:, self.PRICE_CHANGE] = close - close.shift(-1)
        self._df = df

        ar = self.avg_range
        av = self.avg_vol
        v = velocity

        df.loc[:, self.VELOCITY] = df.apply(lambda row: v(row[self.RANGE],
                                                          ar,
                                                          row[self.VOLUME],
                                                          av),
                                            axis=1)

        for c in df.columns:
            if not c.startswith('sma'):
                continue
            label = c + '_diff'
            df.loc[:, label] = close - df[c]

        df['macd']
        df['macds']
        df['macdh']
        df['rsi_6']
        df['rsi_12']
        df['tr']
        df['atr']

        return df

    def get_inside_bars(self, df=None):
        data = []
        if df is None:
            df = self.df

        for idx, rec in df.iterrows():
            o, h, l, c, t = rec['open'], rec['high'], rec['low'], rec['close'], rec['time']
            if not data:
                data.append([o, h, l, c, t])
            else:
                _, last_h, last_l, _, _ = data[-1]
                if h <= last_h and l >= last_l:
                    # current bar is inside the last bar
                    data.append([o, h, l, c, t])
                else:
                    break

        if len(data) > 1:
            return InsideBars(data)

    def get_last_inside_bars(self, df=None):
        inside_bars = None
        if df is None:
            df = self.df
        for i in range(df.index.size):
            inside_bars = self.get_inside_bars(df[i:])
            if inside_bars is not None:
                break
        return inside_bars

    def get_higher_highs(self, df=None):
        data = list()
        if df is None:
            df = self.df
        for idx, rec in df.iterrows():
            o, h, l, c, t = rec['open'], rec['high'], rec['low'], rec['close'], rec['time']
            if not data:
                data.append([o, h, l, c, t])
            else:
                _, last_h, last_l, _, _ = data[-1]
                if h > last_h and l > last_l:
                    data.append([o, h, l, c, t])
                else:
                    break
        if len(data) > 1:
            return HigherHighs(data=data)

    def get_last_higher_highs(self, df=None):
        highs = None
        if df is None:
            df = self.df

        for i in range(df.index.size):
            highs = self.get_higher_highs(df[i:])
            if highs is not None:
                break
        return highs

    def get_lower_lows(self, df=None):
        data = list()
        if df is None:
            df = self.df
        for idx, rec in df.iterrows():
            o, h, l, c, t = rec['open'], rec['high'], rec['low'], rec['close'], rec['time']
            if not data:
                data.append([o, h, l, c, t])
            else:
                _, last_h, last_l, _, _ = data[-1]
                if h < last_h and l < last_l:
                    data.append([o, h, l, c, t])
                else:
                    break
        if len(data) > 1:
            return HigherHighs(data=data)

