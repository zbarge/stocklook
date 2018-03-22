import pytest, os
from stocklook.crypto.gdax.chartdata import GdaxChartData
from stocklook.crypto.gdax.api import Gdax
from stocklook.utils.timetools import now_minus, now_plus

gdax = Gdax()
yesterday = now_minus(hours=6)
today = now_plus(hours=12)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


def test_chart_rsi():
    fp = os.path.join(FIXTURES_DIR, 'btc_test_chart.csv')
    c = GdaxChartData(gdax,
                      'BTC-USD',
                      yesterday,
                      today,
                      granularity=60*5,)
    c.df.to_csv(fp, index=False)


