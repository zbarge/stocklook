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
from pandas import Timestamp, DateOffset
from datetime import datetime
import requests


BTC_HISTORICAL_URL = 'http://api.coindesk.com/v1/bpi/historical/close.json'
BTC_BLOCK_HEIGHT_URL = 'https://blockchain.info/q/getblockcount'
BTC_NEXT_BLOCK_ETA_URL = 'https://blockchain.info/q/eta'
BTC_UNCONFIRMED_TX_CT_URL = 'https://blockchain.info/q/unconfirmedcount'

BITCOIN_INFO = [None, None]


def btc_get_price_usd():
    """
    Returns a float of the current
    BTC-USD price via the coindesk.com API.
    :return: (float)
    """
    b = BITCOIN_INFO
    if b[0] is None:

        res = requests.get(BTC_HISTORICAL_URL).json()
        i = sorted(res['bpi'].items())

        for date, price in reversed(i):
            b[0] = float(price)
            b[1] = Timestamp(date)
            break

    elif b[1] < datetime.now() - DateOffset(days=2):
        b[0] = None
        btc_get_price_usd()

    return b[0]


def btc_to_usd(btc_val):
    """
    Returns the USD value of a BTC denomination
    multiplying it by the current BTC-USD
    price using the coindesk.com API.
    :param btc_val: (float, int)
    :return: (float)
    """
    return btc_val * btc_get_price_usd()


def btc_get_block_height():
    """
    Returns an integer of the current
    BTC block height of the longest chain.
    :return: (int)
    """
    return int(requests.get(BTC_BLOCK_HEIGHT_URL).json())


def btc_get_secs_to_next_block():
    """
    Returns the estimated number of
    seconds until the next block is due.
    If the next block is later than
    expected a negative number may be returned.
    :return: (int)
    """
    return int(requests.get(BTC_NEXT_BLOCK_ETA_URL).json())


def btc_get_unconfirmed_tx_count():
    """
    Returns the number of currently
    unconfirmed transactions on the BTC network.
    :return:
    """
    return int(requests.get(BTC_UNCONFIRMED_TX_CT_URL).json())




if __name__ == '__main__':


    print(btc_get_secs_to_next_block())
    exit()
    for i in range(50):
        print(btc_get_price_usd())

