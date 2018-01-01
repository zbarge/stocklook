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
import requests
import pandas as pd
from datetime import datetime
import calendar
import urllib
import json
import time
import hmac, hashlib
import urllib.request as urllib2
from stocklook.config import config, POLONIEX_SECRET, POLONIEX_KEY
from stocklook.utils.security import Credentials
from stocklook.utils.timetools import (timestamp_from_utc,
                                       timestamp_to_utc_int as timestamp_to_utc,
                                       create_timestamp, today, one_week_ago)

POLONIEX_DATA_TYPE_MAP = {
    'lowestAsk': float,
    'last': float,
    'isFrozen': int,
    'percentChange': float,
    'low24hr': float,
    'highestBid': float,
    'id': int,
    'baseVolume': float,
    'quoteVolume': float,
    'close': float,
    'date': pd.Timestamp,
    'high': float,
    'low': float,
    'volume': float,
    'weightedAverage': float,
    'high24hr': float,

}

# Currency Pairs
USDT_BTC = 'USDT_BTC'
USDT_ETH = 'USDT_ETH'
USDT_LTC = 'USDT_LTC'

# Field names from polo_return_chart_data()
QUOTE_VOLUME = 'quoteVolume'
WEIGHTED_AVG = 'weightedAverage'
CLOSE = 'close'
HIGH = 'high'
VOLUME = 'volume'
LOW = 'low'
DATE = 'date'

# Time periods available for unix time.
FIVE_MINUTE = 60 * 5
THIRTY_MINUTE = 60 * 30
TWO_HOURS = 60 * 60 * 2
FOUR_HOURS = 60 * 60 * 4
ONE_DAY = 60 * 60 * 24


def polo_return_chart_data(currency_pair,
                           start_unix=None,
                           end_unix=None,
                           period_unix=14400,
                           format_dates=True,
                           to_frame=True):
    """
    Returns public exchange data for the given
    currency_pair between the start_unix and end_unix
    timeframes.

    :param currency_pair: The curreny pair
    :param start_unix: (int, str) unix timestamp corresponding to the start date/time.
    :param end_unix: (int, str) unix timestamp corresponding to the end date/time.
    :param period_unix: (int, str) unix timestamp corresponding to the start period.
    :param format_dates: (bool, default True)
        True formats the 'date' values into pandas.Timestamp rather than unix date/times.
    :param to_frame: (bool, default True)
        True returns a pandas.DataFrame with the data contained
        False returns a list of dictionary objects containing the data for each period.
    :return:
        - close (float)
        - date (pd.Timestamp)
        - high (float)
        - low (float)
        - open (float)
        - quoteVolume (float)
        - volume (float)
        - weightedAverage (float)
    """

    if not start_unix:
        start_unix = timestamp_to_utc(datetime.now() - pd.DateOffset(years=10))

    if not end_unix:
        end_unix = timestamp_to_utc(datetime.now())

    params = {'currencyPair': currency_pair,
              'start': start_unix,
              'end': end_unix,
              'period': str(period_unix)}

    res = requests.get('https://poloniex.com/public?'
                       'command=returnChartData',
                       params=params).json()

    if hasattr(res, 'get'):
        error = res.get('error', None)
        if error:
            raise Exception('{}: {}'.format(error, currency_pair))

    if format_dates is True and not isinstance(res, str):
        for r in res:
            r[DATE] = timestamp_from_utc(r[DATE])

    if to_frame is True and not isinstance(res, str):
        res = pd.DataFrame(data=res, index=range(len(res)))

    return res


class Poloniex:
    Credentials.register_config_object_mapping(
        Credentials.POLONIEX, {
        POLONIEX_KEY: 'api_key',
        POLONIEX_SECRET: 'secret'}
    )

    def __init__(self, key=None, secret=None):
        self.api_key = key
        self.secret = secret
        if not all((key, secret)):
            c = Credentials()
            c.configure_object_vars(
                self, c.POLONIEX, 'api_key', ['secret'])

    def post_process(self, before):
        after = before

        # Add timestamps if there isnt one but is a datetime
        if ('return' in after):
            if (isinstance(after['return'], list)):
                for x in range(0, len(after['return'])):
                    if (isinstance(after['return'][x], dict)):
                        if ('datetime' in after['return'][x] and 'timestamp' not in after['return'][x]):
                            after['return'][x]['timestamp'] = float(create_timestamp(after['return'][x]['datetime']))

        return after

    def api_query(self, command, req={}):
        """
        Queries poloniex
        Most Poloniex methods call this function.

        :param command: (str)
            returnTicker
            return24hVolume
            returnOrderBook
            returnMarketTradeHistory
        :param req: (dict)
            containing parameters that can be encoded into the URL.

        :return:
        """
        if command == "returnTicker" or command == "return24hVolume":
            url = 'https://poloniex.com/public?command=' + command
            ret = urllib2.urlopen(urllib2.Request(url))
            return json.loads(ret.read().decode('utf8'))

        elif command == "returnOrderBook":
            ret = urllib2.urlopen(urllib2.Request(
                'https://poloniex.com/public?command=' + command + '&currencyPair=' + str(req['currencyPair'])))
            return json.loads(ret.read().decode('utf8'))

        elif command == "returnMarketTradeHistory":
            ret = urllib2.urlopen(urllib2.Request(
                'https://poloniex.com/public?command=' + "returnTradeHistory" + '&currencyPair=' + str(
                    req['currencyPair'])))
            return json.loads(ret.read().decode('utf8'))

        else:
            req['command'] = command
            req['nonce'] = int(time.time() * 1000)
            post_data = urllib.parse.urlencode(req)
            s = bytes(self.secret, encoding='utf8')
            post_data = bytes(post_data, encoding='utf8')
            sign = hmac.new(s, post_data, hashlib.sha512).hexdigest()
            headers = {
                'Sign': sign,
                'Key': self.api_key
            }

            ret = urllib2.urlopen(urllib2.Request('https://poloniex.com/tradingApi', post_data, headers))

            jsonRet = json.loads(ret.read().decode('utf8'))
            return self.post_process(jsonRet)

    @staticmethod
    def format_value(field, value, astype=None):
        if astype is not None:
            return astype(value)

        try:
            return POLONIEX_DATA_TYPE_MAP[field](value)
        except (KeyError, TypeError):
            return value

    def return_ticker(self):
        """
        Returns a JSON object containing the following information
        for each currency pair:

        {currency_pair: {id: currency_id (int),
                         highestBid: highest_bid (float),
                         isFrozen: (0, 1) (int)
                         quoteVolume: quote_volume (float)
                         low24hr: low_24_hr (float),
                         lowestAsk: lowest_ask (float),
                         high24hr: high_24_hr (float),
                         percentChange: pct_change (float),
                         last: last (float),
                         baseVolume: base_volume (float)
                        }
        }

        :return: ^
        """
        res = self.api_query("returnTicker")
        for currency_pair, data in res.items():
            for field, value in data.items():
                data[field] = self.format_value(field, value)
        return res

    def return_24_volume(self):
        """
        Returns a JSON object containing
        {currency_pair: {currency: volume,
                         base_currency: volume}}
        :return:
        """
        res = self.api_query("return24hVolume")
        for currency_pair, data in res.items():
            if not hasattr(data, 'items'):
                continue
            for currency, value in data.items():
                data[currency] = self.format_value(None, data[currency], float)

        return res

    def return_currency_pairs(self):
        """
        Returns a list of available currency_pairs in Poloniex
        by taking the keys from Poloniex.return_24_volume.
        :return:
        """
        return list(sorted(list(c for c in self.return_24_volume().keys()
                                if not c.startswith('total'))))

    def return_order_book(self, currency_pair):
        return self.api_query("returnOrderBook", {'currencyPair': currency_pair})

    def return_market_trade_history(self, currency_pair):
        return self.api_query("returnMarketTradeHistory", {'currencyPair': currency_pair})

    def return_balances(self, hide_zero=True):
        """
        # Returns all of your balances.
        # Outputs:
        # {"BTC":"0.59098578","LTC":"3.31117268", ... }
        :param hide_zero:
        :return:
        """
        res = self.api_query('returnBalances')
        if hide_zero:
            res = {k: float(v) for k, v in res.items() if float(v) > 0}
        else:

            res = {k: float(v) for k, v in res.items()}
        return res

    def return_open_orders(self, currency_pair):
        """
        Returns your open orders for a given market,
        specified by the "currency_pair" POST parameter, e.g. "BTC_XCP"

        :param currency_pair: The currency pair e.g. "BTC_XCP"
        :return:
            # orderNumber   The order number
            # type          sell or buy
            # rate          Price the order is selling or buying at
            # Amount        Quantity of order
            # total         Total value of order (price * quantity)
        """
        return self.api_query('returnOpenOrders', {"currencyPair": currency_pair})

    def return_trade_history(self, currency_pair):
        """
        Returns your trade history for a given market,
        specified by the "currency_pair" POST parameter

        :param currency_pair: The currency pair e.g. "BTC_XCP"
        :return:
            # date          Date in the form: "2014-02-19 03:44:59"
            # rate          Price the order is selling or buying at
            # amount        Quantity of order
            # total         Total value of order (price * quantity)
            # type          sell or buy
        """
        return self.api_query('returnTradeHistory', {"currencyPair": currency_pair})

    def buy(self, currency_pair, rate, amount):
        """
        # Places a buy order in a given market.
        :param currency_pair: The curreny pair
        :param rate: price the order is buying at
        :param amount: Amount of coins to buy
        :return:
        """
        return self.api_query('buy', {"CurrencyPair": currency_pair, "rate": rate, "amount": amount})

    def sell(self, currency_pair, rate, amount):
        """
        # Places a sell order in a given market.

        :param currency_pair: The curreny pair
        :param rate: price the order is selling at
        :param amount: Amount of coins to sell
        :return: The order number
        """
        return self.api_query('sell', {"currencyPair": currency_pair, "rate": rate, "amount": amount})

    def cancel(self, currency_pair, order_number):
        """
        # Cancels an order you have placed in a given market.
        Required POST parameters are "currency_pair" and "order_number".
        :param currency_pair: The curreny pair
        :param order_number: The order number to cancel
        :return: succes        1 or 0
        """
        return self.api_query('cancelOrder', {"currencyPair": currency_pair, "orderNumber": order_number})

    def withdraw(self, currency, amount, address):
        """
        # Immediately places a withdrawal for a given currency, with no email confirmation.
        # In order to use this method, the withdrawal privilege must be enabled for your API key.
        # Required POST parameters are "currency", "amount", and "address".

        :param currency: The currency to withdraw
        :param amount: The amount of this coin to withdraw
        :param address: The withdrawal address
        :return:  Text containing message about the withdrawal
        # Sample output: {"response":"Withdrew 2398 NXT."}
        """
        return self.api_query('withdraw', {"currency": currency, "amount": amount, "address": address})


class TradeSettings:
    def __init__(self):
        self.max_pct_of_portfolio_per_order = None
        self.max_frequency_of_buys = None
        self.sync_interval = None
        self.pct_change_today_min = None
        self.pct_change_today_max = None
        self.pct_below_ma_min = None
        self.pct_below_ma_max = None
        self.pct_above_ma_min = None
        self.pct_above_ma_max = None
        self.volume_min = None
        self.volume_max = None


class PoloCurrencyPair:
    def __init__(self, currency_pair, key=None, secret=None, polo_con=None, sync=True):
        if polo_con is not None:
            self.api = polo_con
        else:
            self.api = Poloniex(key, secret)
        self.cur_pair = currency_pair

        self.quote_volume = None
        self.high_24_hr = None
        self.low_24_hr = None
        self.is_frozen = None
        self.highest_bid = None
        self.lowest_ask = None
        self.base_volume = None
        self.pct_change = None
        self.last = None
        self.id = None
        self.last_synced = None
        self.chart = None

        if sync:
            self.sync()

    @property
    def spread(self):
        return self.lowest_ask - self.highest_bid

    @property
    def price_vs_low24(self):
        return self.last - self.low_24_hr

    @property
    def price_vs_high24(self):
        return self.last - self.high_24_hr

    def sync(self):
        ticker = self.api.return_ticker()[self.cur_pair]
        self.last_synced = datetime.now()
        self.quote_volume = ticker['quoteVolume']
        self.high_24_hr = ticker['high24hr']
        self.low_24_hr = ticker['low24hr']
        self.highest_bid = ticker['highestBid']
        self.lowest_ask = ticker['lowestAsk']
        self.is_frozen = (True if ticker['isFrozen'] == 1 else False)
        self.pct_change = ticker['percentChange']
        self.base_volume = ticker['baseVolume']
        self.last = ticker['last']
        self.base_volume = ticker['baseVolume']
        self.id = ticker['id']
        self.chart = self.get_days_chart_data()

    def get_days_chart_data(self):
        return polo_return_chart_data(self.cur_pair,
                                      start_unix=timestamp_to_utc(today()),
                                      period_unix=FIVE_MINUTE)

    def get_price_change(self, df=None):
        if df is None:
            df = self.chart
        first = df.iloc[0]
        last = df.iloc[-1]
        return last['weightedAverage'] - first['weightedAverage']

    def find_last_support(self, price=None):
        if price is None:
            price = self.last
        df = polo_return_chart_data(self.cur_pair,
                                    start_unix=timestamp_to_utc(one_week_ago()),
                                    end_unix=timestamp_to_utc(datetime.now() - pd.DateOffset(hours=2)),
                                    period_unix=FIVE_MINUTE)
        df = df.loc[df['close'] <= price, :]
        return df.iloc[-1]






if __name__ == '__main__':
    #res = polo_return_chart_data(USDT_BTC)
    #print(res.head(10))
    import os
    key = None
    secret = None
    chart_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'usdt_btc.csv')
    p = Poloniex(key, secret)

    btc = PoloCurrencyPair(USDT_BTC, polo_con=p)
    print(btc.get_price_change())
    print("Price VS High: " + str(btc.price_vs_high24))
    print("Price VS Low: " + str(btc.price_vs_low24))
    print("BTC Spread: " + str(btc.spread))
    print("Current Price: " + str(btc.last))
    last_support = btc.find_last_support()
    print("Last Support: \n{}".format(last_support))
    print("Last Last Support: \n {}".format(btc.find_last_support(price=last_support['low'])))

    from stocklook.quant.analysis import macd, moving_average, exp_weighted_moving_average, rate_of_change, acceleration

    df = btc.get_days_chart_data()
    close_list = df.loc[:, 'close'].tolist()
    roc = rate_of_change(3, close_list)
    for close, rate in zip(close_list, roc):
        print("close:{} rate: {}".format(close, round(rate*100,3)))
    ac = acceleration(3, close_list)
    print("Acceleration: {}".format(ac))
    #print("Rate of Change: {}".format(zip(close_list, roc)))
    df.to_csv(chart_path, index=False)




