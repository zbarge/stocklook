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
import os

PAIR = 'ETH-USD'
SIZE = 2.89
STOP_AMOUNT = 8.50
STOP_PERCENT = None
TARGET_SELL_PRICE = 314.87
NOTIFY_ADDRESS = os.environ['CELL_NOTIFY_ADDRESS']
BUY_NEEDED_COIN = False


if __name__ == '__main__':
    from stocklook.crypto.gdax.order import execute_trailing_stop
    execute_trailing_stop(PAIR,
                          SIZE,
                          stop_amt=STOP_AMOUNT,
                          stop_pct=STOP_PERCENT,
                          target=TARGET_SELL_PRICE,
                          notify=NOTIFY_ADDRESS,
                          buy_needed=BUY_NEEDED_COIN)

