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

