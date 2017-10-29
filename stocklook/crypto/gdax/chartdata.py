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
    CLOSE = 'close'
    SMA5 = 'sma5'
    SMA8 = 'sma8'
    SMA18 = 'sma18'
    SMA50 = 'sma50'
    SMA100 = 'sma100'
    SMA200 = 'sma200'
    RANGE = 'range'
    RSI = 'rsi'
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
        return self.df[self.RANGE].mean()

    @property
    def avg_rsi(self):
        return self.df[self.RSI].mean()

    @property
    def avg_vol(self):
        return self.df[self.VOLUME].mean()

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

        close = df[self.CLOSE]
        df.loc[:, self.SMA5] = close.rolling(5).mean()
        df.loc[:, self.SMA8] = close.rolling(8).mean()
        df.loc[:, self.SMA18] = close.rolling(18).mean()
        df.loc[:, self.SMA50] = close.rolling(50).mean()
        df.loc[:, self.SMA100] = close.rolling(50).mean()
        df.loc[:, self.SMA200] = close.rolling(50).mean()
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



        return df


class DataSet:
    def __init__(self, gdax, product, data):
        self.gdax = gdax
        self.product = product
        self.data = data

    def sync(self):
        pass

