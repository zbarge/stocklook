from stocklook.crypto.gdax.tests import *
from stocklook.crypto.bitcoin import *
from stocklook.crypto.etherium import *
from stocklook.crypto.poloniex import *
from stocklook.crypto.coinmarketcap import *
import pytest


coinmc_api = CoinMarketCap()


def test_coinmc_stats():
    """
    tests stocklook.crypto.coinmarketcap.CoinMarketCap.stats()
    """
    s = coinmc_api.stats()
    assert int(s['active_markets']) > 1000
    assert len(s.keys()) > 5


def test_coinmc_ticker():
    """
    tests stocklook.crypto.coinmarketcap.CoinMarketCap.ticker()
    """
    s = coinmc_api.ticker()
    s = sorted(s, reverse=True,
        key=lambda x: float(x['percent_change_24h']))

    for coin in s:
        assert len(coin['symbol']) > 1
        assert len(coin['name']) > 1

