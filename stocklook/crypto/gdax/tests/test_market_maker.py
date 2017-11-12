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


if __name__ == '__main__':
    import os
    from time import sleep
    from stocklook.crypto.gdax.api import Gdax
    from stocklook.crypto.gdax.chartdata import GdaxChartData
    from stocklook.crypto.gdax.market_maker import GdaxMarketMaker
    from stocklook.utils.timetools import now, now_minus
    from stocklook.config import config
    chart_path = os.path.join(config['DATA_DIRECTORY'], 'rsi_check.csv')
    g = Gdax()

    def export_chart():
        d = GdaxChartData(g, 'ETH-USD', now_minus(days=1), now(), granularity=60*5,)
        d.df.to_csv(chart_path, index=False)

    m = GdaxMarketMaker(product_id='ETH-USD', gdax=g)
    m.book_feed.start()
    sleep(10)


    def adj_market():
        for _ in range(2):
            m.adjust_to_market_conditions()
            sleep(5)

        for c_name, cdf in m._charts.items():
            f_path = os.path.join(config['DATA_DIRECTORY'], 'eth_{}.csv'.format(c_name))
            last_bars = cdf.get_last_inside_bars()
            print(last_bars)
            cdf.df.to_csv(f_path, index=False)

    adj_market()


