from stocklook.crypto.gdax.feeds.book_feed import GdaxBookFeed
from stocklook.crypto.gdax.feeds import GdaxTradeFeed
from stocklook.crypto.gdax.feeds.websocket_client import GdaxWebsocketClient
from .account import GdaxAccount
from .api import Gdax, GdaxAPIError
from .book import GdaxOrderBook
from .chartdata import GdaxChartData
from .db import GdaxDatabase
from .order import (GdaxOrder,
                    GdaxOrderSides,
                    GdaxOrderTypes,
                    GdaxOrderSystem)
from .product import GdaxProducts, GdaxProduct
from .tables import (GdaxBase,
                     GdaxSQLProduct,
                     GdaxSQLQuote,
                     GdaxSQLOrder,
                     GdaxSQLHistory,
                     GdaxSQLFeedEntry)
from .trader import GdaxTrader, GdaxAnalyzer


def scan_price(gdax,
               product,
               alert_method,
               low_notify=None,
               high_notify=None,
               interval=60,
               end_time=None,
               change_rate=.015,
               alert_addr=None):
    """
    Scans a GdaxProduct's orderbook regularly evaluating
    ask prices and sending notifications when price hits a high or low target.

    This function is designed to run for days, weeks, and months at a time as
    it makes adjustments to target high and low prices as they're reached.

    :param gdax: (gdax.api.Gdax)
        The Gdax API object to be used when calling.

    :param product: (str)
        ETH-USD, LTC-USD, BTC-USD

    :param alert_method: (callable)
        Should be a method that can be called like so:
            alert_method(alert_addr, text)

    :param low_notify: (numeric, default None)
        The lower trigger price to alert on.
        None will default to: price - (price * change_rate)
        This value is decreased by the change rate when reached.
        This value is increased by the change rate when the
        high_notify price is reached.

    :param high_notify: (numeric, default None)
        The upper trigger price to alert on.
        None will default to: price + (price * change_rate)
        This value is increased by the change rate when reached.
        This value is decreased by the change rate when
        the low_notify price is reached.

    :param interval: (int, default 60)
        Number of seconds between order book scans.

    :param end_time: (DateTime, default None)
        The date/time to stop scanning the books
        None will default to 99 weeks from function start time.

    :param change_rate: (float, default 0.015)
        The rate at which the high_notify & low_notify
        target values change as the price moves.

    :return: None
    """
    from time import sleep
    from datetime import datetime
    from pandas import DateOffset
    if alert_addr is None:
        alert_addr = '9495728323@tmomail.net'
    both_flags = all((low_notify, high_notify))

    if not both_flags:
        prod = gdax.get_product(product)
        p = prod.price

        if low_notify is None:
            low = p - (p * change_rate)
            low_notify = round(low, 2)

        if high_notify is None:
            high = p + (p * change_rate)
            high_notify = round(high, 2)

    if end_time is None:
        end_time = datetime.now() + DateOffset(weeks=99)

    ask_store, last_ping, i = list(), None, 0
    print("Initializing {} price scan "
          "looking for low {} "
          "and high {}".format(product, low_notify, high_notify))

    # This value is increased by ~30%
    # every time a notification is sent.
    # It represents how many minutes to wait before
    # re-sending the same notification
    wait_time = 5

    while True:
        i += 1
        now = datetime.now()

        try:
            book = gdax.get_book(product, level=1)
        except Exception as e:
            sleep(interval)
            print(e)
            continue

        asks = book['asks']
        lowest_ask = float(asks[0][0])

        diff_high = round(high_notify - lowest_ask, 2)
        diff_low = round(low_notify - lowest_ask, 2)
        pct_away_high = round(100 - ((lowest_ask/high_notify)*100), 2)
        pct_away_low = round(100 - ((lowest_ask/low_notify)*100), 2)
        meets_low = (low_notify and lowest_ask <= low_notify)
        meets_high = (high_notify and lowest_ask >= high_notify)
        meets_criteria = meets_low or meets_high
        # This information should probably somehow get stored?
        # NOTE: the program is threaded so it'd need to generate it's own
        # SQL connection ....or open and write to a file every 50 lines or something
        #ask_store.append([now, lowest_ask, diff_high, pct_away_high, diff_low, pct_away_low])

        msg = 'Price: ${} -' \
              'Target: ${} - away: ${}/{}% -' \
              'Stop: ${}- away: ${}/%{}'.format(lowest_ask,
                                                high_notify,
                                                diff_high,
                                                pct_away_high,
                                                low_notify,
                                                diff_low,
                                                pct_away_low)
        msg = '{}: ({}-{})\n{}'.format(str(now)[:19],
                                       i,
                                       product,
                                       msg)
        print(msg)
        print("\n")

        if meets_criteria:
            send_msg = True
            m = int(wait_time)
            min_time = now - DateOffset(minutes=m)
            if last_ping and last_ping > min_time:
                send_msg = False

            if send_msg:
                alert_method(alert_addr, msg)
                last_ping = now

                # Increase/decrease the target price by change_rate
                if meets_low:
                    v = round(low_notify * change_rate, 2)
                    low_notify -= v
                    high_notify -= v

                if meets_high:
                    v = round(high_notify * change_rate, 2)
                    high_notify += v
                    low_notify += v

        if end_time and now >= end_time:
            break

        sleep(interval)

    return ask_store


def dollars(x):
    return round(float(x), 2)


def percent(x):
    return round(float(x), 2)


def get_buypoint(c: GdaxChartData):
    df = c.df
    current = c.gdax.get_ticker(c.product)
    stats = c.gdax.get_24hr_stats(c.product)
    price = float(current['price'])
    vol = float(current['volume'])
    high = float(stats['high'])
    low = float(stats['low'])
    vol_ratio = percent(vol / c.avg_vol)
    price_ratio = percent(price / c.avg_close)
    high_ratio = percent(price / high)
    low_ratio = percent(price / low)
    rng = dollars(high - low)
    high_diff = dollars(high - price)
    low_diff = dollars(price - low)

    print('ticker:{}\n'
          'price: {}\n'
          'day high: {}\n'
          'day low: {}\n'
          'day vol: {}\n'
          'vol ratio: {}\n'
          'price ratio: {}\n'
          'high ratio: {}\n'
          'high diff: {}\n'
          'low ratio: {}\n'
          'low diff: {} '.format(c.product,
                                 price,
                                 high,
                                 low,
                                 vol,
                                 vol_ratio,
                                 price_ratio,
                                 high_ratio,
                                 high_diff,
                                 low_ratio,
                                 low_diff))

    print("\n\nRange Analysis:")
    if rng <= .02 * price:
        # Not even a 2% move in price today... tight range
        print("Tight range today - ${}".format(rng))
    elif rng >= .1 * price:
        # 10% swing today...pretty volatile.
        print("Volatile range today - ${}".format(rng))
    else:
        print("Average-ish range today - ${}".format(rng))

    heavy_vol = vol_ratio > 1.5
    low_vol = vol_ratio < .5
    print("\n\nVolume Analysis\n\n"
          "current {}\n"
          "average {}:".format(int(vol), int(c.avg_vol)))
    if heavy_vol:
        print("Heavy volume - ratio {}".format(vol_ratio))
    elif low_vol:
        print("Low volume - ratio {}".format(vol_ratio))
    else:
        print("Average-ish volume - ratio {}".format(vol_ratio))

    print("\n\nPrice analysis:")

    price_chg1 = dollars(df.loc[1:12, 'price_change'].mean())
    price_chg2 = dollars(df.loc[12:, 'price_change'].mean())
    price_chg3 = dollars(df.loc[1:7, 'price_change'].mean())

    print("Avg price change (last 10 periods): {}".format(price_chg1))
    print("Avg price change (last 6 periods): {}".format(price_chg3))
    print("Avg price change prior to last 10 periods: {}".format(price_chg2))

    price_decreasing = price_chg1 < price_chg2
    price_increasing = price_chg1 > price_chg2
    if price_decreasing:
        print("Price is decreasing over last 10 periods.")
    elif price_increasing:
        print("Price is increasing over last 10 periods.")

    lower_rng = price < high - (rng / 2)
    upper_rng = not lower_rng
    peak_rng = price > high - (rng * .1)

    if lower_rng:
        txt = "Price is in the lower range - " \
              "it might be a nice dip to buy."
        if heavy_vol:
            txt += 'Volume is heavy so be careful for bearish patterns.'
            if price_decreasing:
                txt += 'price is also decreasing so thats an extra warning.'
        elif low_vol and price_increasing:
            txt += 'Volume is low and the price is increasing ' \
                   'over the last 10 periods so it ' \
                   'appears to be healthy consolidation.'
        elif low_vol and price_decreasing:
            txt += 'Volume is low and the price is increasing ' \
                   'over the last 10 periods so it ' \
                   'appears to be healthy consolidation.'
        print(txt)
    elif upper_rng and not peak_rng:
        print("Price is in the upper range - "
              "it's either about to break out or down."
              "Still off the peak by {}".format(dollars(high - price)))
    elif peak_rng:
        print("Price is near the peak range - "
              "watch for break out/down now.")


def generate_candles(product, gdax=None, out_path=None, start=None, end=None, granularity=60*60*24):
    """
    Generates a .csv file containing open, high, low, close & volume
    information for a given product.

    :param product:
    :param gdax:
    :param out_path:
    :param start:
    :param end:
    :param granularity:
    :return: (GdaxChartData, str)
        Returns the generated ChartData object along with the out_path.
    """

    if gdax is None:
        gdax = Gdax()

    if out_path is None:
        import os
        from stocklook.config import config
        d = config['DATA_DIRECTORY']
        c = product.split('-')[0]
        n = '{}_candles.csv'.format(c)
        out_path = os.path.join(d, n)

    if start is None:
        from stocklook.utils.timetools import now_minus
        start = now_minus(weeks=4)

    if end is None:
        from stocklook.utils.timetools import now
        end = now()

    data = GdaxChartData(gdax, product, start, end, granularity)
    data.df.to_csv(out_path, index=False)
    get_buypoint(data)

    return data, out_path


def sync_database(gdax, db=None, interval=60):
    """
    Updates a GdaxDatabase with
    pricing information on a regular basis.

    :param gdax: (gdax.api.Gdax)
        The api object
    :param db: (gdax.db.GdaxDatabase)
        The database to load updates into.
    :param interval: (int, default 60)
        The number of seconds to wait between updates.
    :return:
    """
    from time import sleep
    if db is None:
        db = GdaxDatabase(gdax)

    while True:
        db.sync_quotes()
        sleep(interval)
