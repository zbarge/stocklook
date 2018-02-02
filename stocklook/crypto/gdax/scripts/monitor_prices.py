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
BTC_LOW = None
BTC_HIGH = None

LTC_LOW = None
LTC_HIGH = None

ETH_LOW = None
ETH_HIGH = None

SCAN_INTERVAL_SECONDS = 60

BTC_CHANGE_RATE = 0.005
ETH_CHANGE_RATE = 0.0075
LTC_CHANGE_RATE = 0.0075

if __name__ == '__main__':
    from time import sleep
    from threading import Thread
    from stocklook.utils.emailsender import send_message
    from stocklook.crypto.gdax import Gdax, scan_price, GdaxProducts as G

    gdax = Gdax()
    interval = SCAN_INTERVAL_SECONDS
    end_time = None
    print("total account value: {} ".format(gdax.get_total_value()))
    btc, ltc, eth = G.BTC_USD, G.LTC_USD, G.ETH_USD
    btc_args = (gdax, btc, send_message, BTC_LOW, BTC_HIGH, interval, end_time, BTC_CHANGE_RATE)
    ltc_args = (gdax, ltc, send_message, LTC_LOW, LTC_HIGH, interval, end_time, LTC_CHANGE_RATE)
    eth_args = (gdax, eth, send_message, ETH_LOW, ETH_HIGH, interval, end_time, ETH_CHANGE_RATE)

    btc_thread = Thread(target=scan_price, args=btc_args)
    ltc_thread = Thread(target=scan_price, args=ltc_args)
    eth_thread = Thread(target=scan_price, args=eth_args)

    threads = [
        #eth_thread,
        btc_thread,
        #ltc_thread,
    ]

    for i, t in enumerate(threads):
        print("starting thread {}".format(i))
        t.start()
        sleep(2)

