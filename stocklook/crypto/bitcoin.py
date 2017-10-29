from pandas import Timestamp, DateOffset
from datetime import datetime
import requests


BITCOIN_HISTORICAL_URL = 'http://api.coindesk.com/v1/bpi/historical/close.json'

BITCOIN_INFO = [None, None]


def get_bitcoin_price():
    b = BITCOIN_INFO
    if b[0] is None:

        u = BITCOIN_HISTORICAL_URL
        res = requests.get(u).json()
        i = sorted(res['bpi'].items())

        for date, price in reversed(i):
            b[0] = float(price)
            b[1] = Timestamp(date)
            break
    elif b[1] < datetime.now() - DateOffset(days=2):
        b[0] = None
        get_bitcoin_price()
    return b[0]


def btc_to_usd(btc_val):
    return btc_val * get_bitcoin_price()



if __name__ == '__main__':
    for i in range(50):
        print(get_bitcoin_price())

