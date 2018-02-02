from pandas import DataFrame, Series
from stockstats import StockDataFrame
from stocklook.utils.timetools import timestamp_to_utc_int

O = 'open'
H = 'high'
L = 'low'
C = 'close'
T = 'time'
V = 'volume'

OHLC_COLUMNS = [O, H, L, C, T, V]


class OhlcData:
    def __init__(self, data=None, columns=None, update_method=None):
        self._update_method = update_method
        self._raw_data = data
        self._columns = columns
        self._df = None
        self._idx = 0
        self._setup()

    def _setup(self):
        self._setup_raw_data()

    def _setup_raw_data(self):
        if self._raw_data is None:
            return None

        if self._columns is None:
            self._columns = OHLC_COLUMNS.copy()
        else:
            check = [c for c in self._columns if c not in OHLC_COLUMNS]
            if check:
                raise TypeError("Unexpected columns: {}\n"
                                "Allowed Columns: {}".format(
                                 check, OHLC_COLUMNS))

        d = (self._raw_data if not hasattr(self._raw_data, 'copy')
             else self._raw_data.copy())

        if isinstance(d, DataFrame):
            self._df = d
            self._raw_data = d

        elif isinstance(d, (tuple, list)):
            first = d[0]
            if len(first) != len(self._columns):
                raise ValueError("Length of data ({}) does not "
                                 "match the length of columns ({}). "
                                 "Columns should be: {}".format(
                    len(first), len(self._columns), self._columns))
            self._df = DataFrame(data=d, columns=self._columns)

        else:
            raise NotImplementedError("Expected data to be DataFrame, "
                                      "list, tuple, not {}".format(type(d)))

        self._df.loc[:, T] = self._df[T].apply(timestamp_to_utc_int)


    def next(self):
        try:
            d = self._df.iloc[self._idx]
        except (IndexError, KeyError):
            self._idx = 0
            return None
        self._idx += 1
        return d

    def last(self):
        if self._idx == 0:
            return None
        return self._df.iloc[self._idx-1]

    def _mk_series(self, series, idx):
        return OhlcSeries(series, self, idx)




class OhlcSeries:
    def __init__(self, series, ohlc_data, idx):
        self.series = series
        self._ohlc = ohlc_data
        self._idx = idx

    def get_forward(self, offset=0):
        pass





