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

from stocklook.crypto.gdax import Gdax, GdaxProducts, GdaxOrderBook, GdaxChartData, get_buypoint, GdaxDatabase
from stocklook.utils.timetools import now_minus, now



if __name__ == '__main__':
    g = Gdax()
    #for a in g.accounts.values():
    #    print(a)
    #    print("\n")
    # print("Total account value: ${}".format(g.get_total_value()))
    pair = GdaxProducts.LTC_USD
    book = GdaxOrderBook(g, pair)
    product = g.get_product(pair)


    start = now_minus(days=5)
    end = now()
    granularity = 60*60*24
    chart = GdaxChartData(g, pair, start, end, granularity)

    price = product.price
    res_price, res_qty = book.get_next_resistance()
    su_price, su_qty = book.get_next_support()
    avg_vol = int(chart.avg_vol)
    avg_range = round(chart.avg_range, 2)
    avg_close = round(chart.avg_close, 2)
    avg_rsi = round(chart.avg_rsi, 2)

    cdf = chart.df
    bdf = book.get_data_frame()

    bdf = bdf[bdf['qty'] >= 5]
    bid_qty = int(bdf[bdf['type'] == 'bid']['qty'].sum())
    ask_qty = int(bdf[bdf['type'] == 'ask']['qty'].sum())

    print(bdf)
    print("Price of {} is ${}".format(pair, price))

    print("Next resistance level "
          "is {} {} "
          "at ${}".format(res_qty, pair, res_price))

    print("Next support level "
          "is {} {} "
          "at ${}".format(su_qty, pair, su_price))

    print("{}: bid/ask total: "
          "{}/{}".format(pair, bid_qty, ask_qty))

    print("Averages:\n")
    print("Start: {}\nEnd: {}\nGranularity:{}".format(start, end, granularity))
    print("Average volume: {}".format(avg_vol))
    print("Average range: {}".format(avg_range))
    print("Average close: {}".format(avg_close))
    print("Average rsi: {}".format(avg_rsi))
    print("\n")
    get_buypoint(chart)





