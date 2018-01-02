import io
from pandas import Timestamp
from stocklook.config import config
import os

try:
    import backtrader as bt

except ImportError as e:
    import warnings
    src_url = 'https://github.com/mementum/backtrader'
    cmd = 'pip install {}/zipball/master'.format(src_url)
    raise ImportError("backtrader package not found - install "
                      "using the following command:\n\t{}".format(cmd))


DATA_DIRECTORY = config['DATA_DIRECTORY']
BTRADER_DIRECTORY = os.path.join(DATA_DIRECTORY, 'backtrader')


def get_symbol_csv_path(symbol):
    return os.path.join(BTRADER_DIRECTORY, '{}.csv'.format(symbol))


class SmaCross(bt.SignalStrategy):
    def __init__(self):
        sma1, sma2 = bt.ind.SMA(period=4), bt.ind.SMA(period=8)
        crossover = bt.ind.CrossOver(sma1, sma2)
        self.signal_add(bt.SIGNAL_LONG, crossover)


class PoloniexDataFeed(bt.feeds.feed.CSVDataBase):

    def start(self):
        from pandas import DateOffset
        from stocklook.crypto.poloniex import (polo_return_chart_data,
                                               timestamp_to_utc,
                                               today)

        start = timestamp_to_utc(Timestamp(self.params.fromdate))
        end = timestamp_to_utc(Timestamp(self.p.todate))
        period = self.params.period

        data = polo_return_chart_data(self.p.dataname,
                                          start_unix=start,
                                          end_unix=end,
                                          period_unix=period,
                                          format_dates=True,
                                          to_frame=False)
        self.params.period = 'd'
        prices = ['open', 'high', 'low', 'close']
        takes = prices + ['volume', 'date']

        n = self.params.dataname
        convert_price = n.startswith('BTC') and not n.endswith('USDT')

        if convert_price:
            from stocklook.crypto import btc_to_usd
            for d in data:
                for c in prices:
                    d[c] = btc_to_usd(d[c])

        f = io.StringIO(newline=None)
        for d in data:
            line = ",".join(str(d[t]) for t in takes)
            f.write(line + '\n')

        f.seek(0)
        self.f = f
        super(PoloniexDataFeed, self).start()

    def _loadline(self, linetokens):
        while True:
            nullseen = False
            for tok in linetokens[1:]:
                if tok == 'null':
                    nullseen = True
                    linetokens = self._getnextline()  # refetch tokens
                    if not linetokens:
                        return False  # cannot fetch, go away

                    # out of for to carry on with while True logic
                    break

            if not nullseen:
                break  # can proceed

        o = float(linetokens[0])
        h = float(linetokens[1])
        l = float(linetokens[2])
        c = float(linetokens[3])
        v = float(linetokens[4])
        d = Timestamp(linetokens[5])
        d = bt.utils.date2num(d)

        self.lines.datetime[0] = d
        self.lines.openinterest[0] = 0.0
        self.lines.open[0] = o
        self.lines.high[0] = h
        self.lines.low[0] = l
        self.lines.close[0] = c
        self.lines.volume[0] = v

        return True



if __name__ == "__main__":
    from stocklook.utils.timetools import today
    from pandas import DateOffset

    start = today() - DateOffset(years=1)
    end = today()
    period = 2*60*60

    cerebro = bt.Cerebro()
    cerebro.addstrategy(SmaCross)

    data0 = PoloniexDataFeed(
        dataname='BTC_LTC',
        fromdate=start,
        todate=end,
        period=period)
    cerebro.adddata(data0)

    cerebro.run()
    cerebro.plot()