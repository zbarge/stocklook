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
import pytest
from time import sleep
from stocklook.crypto.gdax.order import GdaxTrailingStop, GdaxOrder


def test_gdax_trailing_stop():
    """
    Places a trailing stop order of 0.1 LTC (around $5) with a $0.10 stop.
    If this much LTC isnt available it is market bought.

    The test passes if it's proven that the account balance was decreased
    whenever the sell order has triggered.

    The test can fail if there's an error anywhere:
        1) Creating the Gdax object (API_KEY/API_SECRET)
        2) Buying LTC (Insufficient account funds available)
        3) Selling LTC (LTC was already sold while order was working)
        4) API error for any internet/gdax related issues.

    :return:
    """
    size = 0.1
    pair = 'LTC-USD'

    order = GdaxTrailingStop(pair,
                             size,
                             stop_amt=0.10,
                             notify='zekebarge@gmail.com')
    gdax = order.gdax
    account = gdax.get_account('LTC')
    bal = account.balance

    if bal < size:
        # Buy some coin so we can do the test.
        o = GdaxOrder(gdax,
                      pair,
                      order_type='market',
                      size=size)
        o.post()
        sleep(1)
        account.update()
        # Proves the coin was bought.
        # Cant do a test without coin.
        assert account.balance >= size

    order.start()
    sleep(15)

    while not order.sell_order:
        # Check and output price/away information about the order
        # Every 30 seconds.
        print("{}: price: {}, mark: {}, away: {}".format(order.pair,
                                                         order.price,
                                                         order.sell_mark,
                                                         order.away))
        sleep(30)

    bal = account.balance
    account.update()

    # Proves the balance was decreased now that the stop has triggered.
    assert account.balance == (bal - size)
    print(order.sell_order)
