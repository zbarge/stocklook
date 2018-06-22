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

import pandas as pd
import logging as lg
from warnings import warn
import hmac, hashlib, time, requests, base64, json
from requests.auth import AuthBase
from stocklook.utils import rate_limited
from stocklook.utils.api import call_api
from stocklook.utils.security import Credentials
from stocklook.config import config, GDAX_SECRET, GDAX_KEY, GDAX_PASSPHRASE
from stocklook.utils.timetools import timestamp_to_iso8601, timestamp_from_utc, timeout_check
from .account import GdaxAccount
from .product import GdaxProduct, GdaxProducts
from .feeds.memory_client import GdaxMemoryWebSocketClient
logger = lg.getLogger(__name__)


class GdaxAPIError(Exception):
    pass


@rate_limited(0.33)
def gdax_call_api(url, method='get', **kwargs):
    """
    This method is rate limited to ~3 calls per second max.
    It should handle ALL communication with the Gdax API.
    :param url:
    :param method: ('get', 'delete', 'post')
    :param kwargs:
    :return:
    """
    return call_api(url, method, _api_exception_cls=GdaxAPIError, **kwargs)


class CoinbaseExchangeAuth(AuthBase):
    """
    A custom authorization class for GDAX
    exchange requests. Used with requests module.
    """
    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    def __call__(self, request):
        timestamp = str(time.time())
        body = request.body

        if isinstance(body, bytes):
            body = body.decode('utf-8')
        elif not body:
            body = ''

        message = '{}{}{}{}'.format(timestamp,
                                    request.method,
                                    request.path_url,
                                    body)

        hmac_key = base64.b64decode(self.secret_key)
        signature = hmac.new(hmac_key, bytes(str(message).encode('utf8')), hashlib.sha256)
        signature_b64 = base64.standard_b64encode(signature.digest())

        request.headers.update({
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        })
        return request


class CoinbaseWebsocketFeedAuth(CoinbaseExchangeAuth):
    """
    A custom authorization class for GDAX
    WebSocketFeed requests. Used with requests module.
    """
    def __init__(self, api_key, secret_key, passphrase, product_ids):
        CoinbaseExchangeAuth.__init__(self, api_key, secret_key, passphrase)
        self.product_ids = product_ids

    def __call__(self, request):
        request = super(CoinbaseWebsocketFeedAuth, self).__call__(request)
        request.headers.update({'type': 'subscribe',
                                'product_ids': self.product_ids})
        return request


class Gdax:
    """
    The main Gdax exchange class exposes the majority of methods
    for calling the API.
    """
    API_URL = 'https://api.gdax.com/'
    API_URL_TESTING = 'https://public.sandbox.gdax.com'
    Credentials.register_config_object_mapping(
        Credentials.GDAX,
            {
            GDAX_KEY: 'api_key',
            GDAX_SECRET: 'api_secret',
            GDAX_PASSPHRASE: 'api_passphrase'
        })

    def __init__(self, key=None, secret=None, passphrase=None, wallet_auth=None, coinbase_client=None):
        """
        The main interface to the Gdax Private API. Most of the API data
        gets broken down into other objects like GdaxAccount, GdaxProduct, GdaxDatabase,
        GdaxOrderSystem, etc. Most of these objects are managed/accessed via this interface.

        To get Gdax API credentials you must do the following (9/9/2017):
            1) Go to https://www.gdax.com/settings/api
            2) Select permissions for view, trade, and manage
            3) Select "Create API Key"
            4) Use the Key, Secret, and Passphrase

        :param key: (str, default None)
            None searches the dictionary located within
            stocklook.config.config under key 'GDAX_KEY' if not provided.

        :param secret: (str, default None)
            None searches the dictionary located within
            stocklook.config.config under key 'GDAX_SECRET' if not provided.

        :param passphrase: (str, default None)
            None searches the dictionary located within
            stocklook.config.config under key 'GDAX_PASSPHRASE' if not provided.

        :param wallet_auth: (requests.auth.Authbase, default None)
            None defaults to a gdax.api.CoinbaseExchangeAuth object.
        :param coinbase_client: (stocklook.crypto.coinbase_api.CoinbaseClient)
            An optionally pre-configured CoinbaseClient.
        """
        self.api_key = key
        self.api_secret = secret
        self.api_passphrase = passphrase

        self._accounts = dict()               # 'GdaxAccount.currency': stocklook.crypto.gdax.account.GdaxAccount
        self._orders = dict()                 # 'GdaxOrder.id': stocklook.crypto.gdax.order.GdaxOrder
        self._products = dict()               # 'GdaxProduct.product': stocklook.crypto.gdax.product.GdaxProduct
        self._timeout_times = dict()          # 'Gdax.caller_method_or_property' : datetime.datetime

        self._wallet_auth = wallet_auth
        self._coinbase_client = coinbase_client
        self.base_url = self.API_URL
        self.timeout_intervals = dict(
            accounts=120,
        )

        self._coinbase_accounts = None
        self._db = None
        self._ws = None

        if not all([key, secret, passphrase]):
            self._set_credentials()

    def _set_credentials(self):
        """
        Sets gdax credentials via secure keyring storage.
        :return:
        """
        c = Credentials()
        c.configure_object_vars(
            self, c.GDAX, 'api_key',
            ['api_secret', 'api_passphrase'])

    def set_testing_url(self):
        """
        Sets base API url to the gdax sandbox
        for testing purposes.
        :return: None
        """
        self.base_url = self.API_URL_TESTING

    def set_production_url(self):
        """
        Sets base API url to gdax production
        address.
        :return: None
        """
        self.base_url = self.API_URL

    @property
    def accounts(self) -> dict:
        """
        Dynamically compiled dictionary gets
        filled with BTC, USD, ETH, & LTC GdaxAccount
        objects when first accessed, caching data
        within the Gdax._accounts dictionary.
        :return:
        """
        timed_out = timeout_check('accounts',
                                  t_data=self._timeout_times,
                                  seconds=self.timeout_intervals['accounts'])
        if not self._accounts or timed_out:
            self.sync_accounts()

        return self._accounts

    @property
    def coinbase_client(self):
        """
        Returns stocklook.crypto.coinbase_api.CoinbaseClient

        If :param coinbase_client was not provided on
        Gdax.__init__, a new CoinbaseClient object will
        be created and cached.

        CoinbaseClient will use
        dict:stocklook.config.config['COINBASE_KEY'] and
        secret cached via keyring and will ask for user
        input if those aren't available.
        :return:
        """
        if self._coinbase_client is None:
            from stocklook.crypto.coinbase_api import CoinbaseClient
            self._coinbase_client = CoinbaseClient()
        return self._coinbase_client

    @property
    def coinbase_accounts(self):
        """
        Coinbase accounts associated to Gdax account
        like {currency: account_dict}
        """
        if self._coinbase_accounts is None:
            self._coinbase_accounts = {
                ac['currency']: ac
                for ac in self.get_coinbase_accounts()
            }
        return self._coinbase_accounts

    @property
    def ws(self):
        # gdax.feeds.websocket_client.GdaxWebsocketClient
        if self._ws is None:
            self._ws = GdaxMemoryWebSocketClient(products=GdaxProducts.LIST)
        return self._ws

    @property
    def db(self):
        """
        Generates/returns a default GdaxDatabase when first accessed.
        To make a custom GdaxDatabase use the Gdax.get_database()
        method and you can supply GdaxDatabase.__init__ kwargs there.
        :return: GdaxDatabase
        """
        if self._db is None:
            self.get_database()
        return self._db

    def get_account(self, currency) -> GdaxAccount:
        """
        Returns a GdaxAccount based on the given
        currency.
        :param currency: (str)
            BTC, LTC, USD, ETH
        :return:
        """
        return self.accounts[currency]

    def sync_accounts(self):
        """
        Iterates through Gdax.get_accounts() data
        creating (or updating) GdaxAccount objects
        and caching within Gdax._accounts dictionary
        :return:
        """
        if self._accounts:
            for acc in self.get_accounts():
                self._accounts[acc['currency']].update(acc)
        else:
            for acc in self.get_accounts():
                a = GdaxAccount(acc, self)
                self._accounts[a.currency] = a

    @property
    def products(self) -> dict:
        """
        Dynamic property compiles GdaxProducts when
        accessed for the first time and caches
        them within the Gdax._products dictionary, returning
        a reference to that dictionary.
        :return:
        """
        if not self._products:
            for p in GdaxProducts.LIST:
                product = GdaxProduct(p, self)
                self._products[p] = product
        return self._products

    def get_product(self, name) -> GdaxProduct:
        """
        Returns a GdaxProduct object for
            LTC-USD
            BTC-USD
            ETH-USD
        :param name: (str) LTC-USD, BTC-USD, ETH-USD
        :return: GdaxProduct
        """
        return self.products[name]

    def get_database(self, **kwargs):
        """
        Generates a GdaxDatabase object assigning
        it to the Gdax.db property as well as returning
        a reference to the object.
        :param kwargs: GdaxDatabase(**kwargs)
        :return: GdaxDatabase
        """
        if kwargs or self._db is None:
            from .db import GdaxDatabase
            self._db = GdaxDatabase(self, **kwargs)
        return self._db

    @property
    def orders(self) -> dict:
        """
        Dynamically generates a dict of GdaxOrder objects
        caching them in the Gdax._orders dictionary using the
        GdaxOrder.id as the keys.
        :return:
        """
        if not self._orders:
            from stocklook.crypto.gdax.order import GdaxOrder
            for o in self.get_orders():
                product = o.pop('product_id')
                o['order_type'] = o.pop('type')
                order = GdaxOrder(self, product, **o)

                self._orders[o['id']] = order
        return self._orders

    def authorize(self, api_key=None, api_secret=None, api_passphrase=None):
        """
        Returns a new or pre-existing CoinbaseExchangeAuth object to be used
        in the auth keyword argument when calling requests.request(). Most users
        will not need to do this as it's called automatically by other methods that
        make requests.

        :param api_key: (str)
        :param api_secret: (str)
        :param api_passphrase: (str)

        :return:
        """
        if api_key:
            self.api_key = api_key

        if api_secret:
            self.api_secret = api_secret

        if api_passphrase:
            self.api_passphrase = api_passphrase

        if hasattr(self._wallet_auth, 'api_key'):
            # Avoid rebuilding the CoinbaseExchangeAuth
            same_key = self._wallet_auth.api_key == self.api_key
            same_secret = self._wallet_auth.secret_key == self.api_secret
            same_passphrase = self._wallet_auth.passphrase == self.api_passphrase
            if all([same_key, same_secret, same_passphrase]):
                # Safe to return the existing wallet auth.
                return self._wallet_auth

        self._wallet_auth = CoinbaseExchangeAuth(self.api_key,
                                                 self.api_secret,
                                                 self.api_passphrase)
        return self._wallet_auth

    @property
    def wallet_auth(self):
        """
        Returns a new or pre-existing CoinbaseExchangeAuth object.
        Used by Gdax.get, Gdax.delete, and Gdax.post methods.
        :return:
        """
        if self._wallet_auth is None:
            self.authorize()

        return self._wallet_auth

    def get(self, url_extension, **kwargs) -> requests.Response:
        """
        Makes a GET request to the GDAX api using the base
        Gdax.API_URL along with the given extension:

        Example:
            resp = Gdax.get('orders')
            contents = resp.json()

        :param url_extension: (str)
        :param kwargs: requests.get(**kwargs)
        :return:
        """
        kwargs.update({
            'auth': kwargs.pop('auth', self.wallet_auth),
            'method': 'get'
        })
        return gdax_call_api(self.base_url + url_extension, **kwargs)

    def post(self, url_extension, **kwargs) -> requests.Response:
        """
        Makes a POST request to the Gdax API using the base Gdax.API_URL
        along with the given extension.

        :param url_extension:
        :param kwargs:
        :return:
        """
        kwargs.update({
            'auth': kwargs.pop('auth', self.wallet_auth),
            'method': 'post'
        })
        return gdax_call_api(self.base_url + url_extension, **kwargs)

    def delete(self, url_extension, **kwargs) -> requests.Response:
        """
        Makes a DELETE request to the Gdax API using the base Gdax.API_URL
        along with the given extension.

        Example:
            res = Gdax.delete('orders/<order_id>')
            data = res.json() # The cancelled order ID should be inside of this list

        :param url_extension: (str)
        :param kwargs:
        :return:
        """
        kwargs.update({
            'auth': kwargs.pop('auth', self.wallet_auth),
            'method': 'delete'
        })
        return gdax_call_api(self.base_url + url_extension, **kwargs)

    def get_current_user(self):
        """
        Returns dictionary of user information.
        """
        return self.get('user').json()

    def get_orders(self, order_id=None, paginate=True, status='all'):
        """
        Returns a list containing data about orders.

        :param order_id: (int, default None)
            A specific order ID to get information about
            should be the long string UID generated by orders like
            Adwafeh-35rhhdfn-adwe3th-wadwagn

        :param paginate: (bool, default True)
            True will make a series of requests collecting
            ~100 chunks of data per request and return all in one list.

            False will only return the first ~100 orders

        :param status (str, default 'all')
            'open', 'pending', 'active'

        :return:
        """
        if order_id:
            ext = 'orders/{}'.format(order_id)
            return self.get(ext).json()
        else:
            ext = 'orders'

        p = (dict(status=status) if status else None)
        res = self.get(ext, params=p)

        if not paginate:
            return res.json()

        data = list(res.json())
        while 'cb-after' in res.headers:
            p = {'after': res.headers['cb-after']}
            res = self.get(ext, params=p)
            data.extend(res.json())

        return data

    def get_coinbase_accounts(self):
        """
        Returns a list of dict objects each
        containing information about a coinbase account.
        :return:
        """
        return self.get('coinbase-accounts').json()

    def get_fills(self, order_id=None, product_id=None, paginate=True, params=None):
        """
        Get a list of recent fills.

        QUERY PARAMETERS
        Param	Default	Description
        order_id	all	Limit list of fills to this order_id
        product_id	all	Limit list of fills to this product_id

        SETTLEMENT AND FEES
        Fees are recorded in two stages.
        Immediately after the matching engine completes a match,
        the fill is inserted into our datastore. Once the fill is recorded, a settlement process
        will settle the fill and credit both trading counterparties.
        The fee field indicates the fees charged for this individual fill.

        LIQUIDITY
        The liquidity field indicates if the fill was the result of a liquidity provider or
        liquidity taker. M indicates Maker and T indicates Taker.

        PAGINATION
        Fills are returned sorted by descending trade_id from the largest trade_id to
        the smallest trade_id. The CB-BEFORE header will have this first trade id so that
        future requests using the cb-before parameter will fetch fills with a greater trade id (newer fills).
        :return:
        """
        if params is None:
            params = dict()
        ext = 'fills'

        if order_id:
            params['order_id'] = order_id

        if product_id:
            params['product_id'] = product_id

        if not params:
            params = None

        res = self.get(ext, params=params)
        if not paginate:
            return res.json()

        data = list(res.json())
        while 'cb-after' in res.headers:
            p = {'after': res.headers['cb-after']}
            res = self.get(ext, params=p)
            data.extend(res.json())

        return data

    def get_book(self, product, level=2):
        """
        Returns a dictionary from the Gdax Order Book like this:
            {
                "sequence": "3",
                "bids": [
                    [ price, size, num-orders ],
                ],
                "asks": [
                    [ price, size, num-orders ],
                ]
            }

        :param product: (str)
            BTC-USD, LTC-USD, or ETH-USD

        :param level:
            Level	Description
            1	    Only the best bid and ask
            2	    Top 50 bids and asks (aggregated)
            3	    Full order book (non aggregated)
        :return:
        """
        ext = 'products/{}/book'.format(product)
        params = dict(level=level)
        return self.get(ext, params=params).json()

    def get_ticker(self, product):
        """
        Snapshot information about the last trade (tick), best bid/ask and 24h volume.
        {
          "trade_id": 4729088,
          "price": "333.99",
          "size": "0.193",
          "bid": "333.98",
          "ask": "333.99",
          "volume": "5957.11914015",
          "time": "2015-11-14T20:46:03.511254Z"
        }
        :param product:
        :return:
        """
        ext = 'products/{}/ticker'.format(product)
        return self.get(ext).json()

    def get_trades(self, product):
        """
        List the latest trades for a product.
        [{
            "time": "2014-11-07T22:19:28.578544Z",
            "trade_id": 74,
            "price": "10.00000000",
            "size": "0.01000000",
            "side": "buy"
        }, {
            "time": "2014-11-07T01:08:43.642366Z",
            "trade_id": 73,
            "price": "100.00000000",
            "size": "0.01000000",
            "side": "sell"
        }]
        :param product:
        :return:
        """
        ext = 'products/{}/trades'.format(product)
        return self.get(ext).json()

    def get_candles(self, product, start, end, granularity=60, convert_dates=False, to_frame=False):
        """
        Historic rates for a product.
        Rates are returned in grouped buckets based on requested granularity.

        PARAMETERS
        Param	         Description
        start	         Start time in ISO 8601
        end	             End time in ISO 8601
        granularity	     Desired timeslice in seconds

        NOTES
        Historical rate data may be incomplete.
        No data is published for intervals where there are no ticks.
        Historical rates should not be polled frequently.
        If you need real-time information, use the trade and book endpoints along with the websocket feed.

        :return:
        Each bucket is an array of the following information:
        time               bucket start time
        low                lowest price during the bucket interval
        high               highest price during the bucket interval
        open               opening price (first trade) in the bucket interval
        close              closing price (last trade) in the bucket interval
        volume             volume of trading activity during the bucket interval
        """
        self._validate_product(product)

        if not isinstance(start, str):
            start = timestamp_to_iso8601(start)

        if not isinstance(end, str):
            end = timestamp_to_iso8601(end)

        ext = 'products/{}/candles'.format(product)
        params = dict(start=start,
                      end=end,
                      granularity=granularity)

        res = self.get(ext, params=params).json()

        if convert_dates:
            for row in res:
                row[0] = timestamp_from_utc(row[0])

        if to_frame:
            columns = ['time', 'low', 'high', 'open', 'close', 'volume']
            res = pd.DataFrame(columns=columns, data=res, index=range(len(res)))

        return res

    def get_24hr_stats(self, product):
        """
        {
            "open": "34.19000000",
            "high": "95.70000000",
            "low": "7.06000000",
            "volume": "2.41000000"
        }
        :param product:
        :return:
        """
        self._validate_product(product)
        ext = 'products/{}/stats'.format(product)
        return self.get(ext).json()

    def get_position(self):
        """
        Returns profile information.

        {
          "status": "active",
          "funding": {
            "max_funding_value": "10000",
            "funding_value": "622.48199522418175",
            "oldest_outstanding": {
              "id": "280c0a56-f2fa-4d3b-a199-92df76fff5cd",
              "order_id": "280c0a56-f2fa-4d3b-a199-92df76fff5cd",
              "created_at": "2017-03-18T00:34:34.270484Z",
              "currency": "USD",
              "account_id": "202af5e9-1ac0-4888-bdf5-15599ae207e2",
              "amount": "545.2400000000000000"
            }
          },
          "accounts": {
            "USD": {
              "id": "202af5e9-1ac0-4888-bdf5-15599ae207e2",
              "balance": "0.0000000000000000",
              "hold": "0.0000000000000000",
              "funded_amount": "622.4819952241817500",
              "default_amount": "0"
            },
            "BTC": {
              "id": "1f690a52-d557-41b5-b834-e39eb10d7df0",
              "balance": "4.7051564815292853",
              "hold": "0.6000000000000000",
              "funded_amount": "0.0000000000000000",
              "default_amount": "0"
            }
          },
          "margin_call": {
            "active": true,
            "price": "175.96000000",
            "side": "sell",
            "size": "4.70515648",
            "funds": "624.04210048"
          },
          "user_id": "521c20b3d4ab09621f000011",
          "profile_id": "d881e5a6-58eb-47cd-b8e2-8d9f2e3ec6f6",
          "position": {
            "type": "long",
            "size": "0.59968368",
            "complement": "-641.91999958602800000000000000",
            "max_size": "1.49000000"
          },
          "product_id": "BTC-USD"
        }
        :return:
        """
        return self.get('position').json()

    def get_accounts(self, account_id=None):
        """
        ACCOUNT FIELDS
        Field	        Description
        id	            Account ID
        currency	    the currency of the account
        balance	        total funds in the account
        holds	        funds on hold (not available for use)
        available	    funds available to withdraw* or trade
        margin_enabled	[margin] true if the account belongs to margin profile
        funded_amount	[margin] amount of funding GDAX is currently providing this account
        default_amount	[margin] amount defaulted on due to not being able to pay back funding
        * Only applicable to non margin accounts. Withdraws on margin accounts are subject to other restrictions.
        :return:
        """
        if account_id is None:
            ext = 'accounts'
        else:
            ext = 'accounts/{}'.format(account_id)
        return self.get(ext).json()

    def get_balances(self, allow_websocket=True, hide_zero=True):
        data = dict()
        if self._ws is not None and allow_websocket:
            # Avoids polling tickers - faster route via websocket.
            for account in self.accounts.values():
                if account.currency == account.USD:
                    value = account.balance
                else:
                    value = self.ws.get_price(account.pair) * account.balance
                if value == 0 and hide_zero:
                    continue
                sub_data = {'symbol': account.pair,
                            'balance': account.balance,
                            'value': round(value, 2)}
                data[sub_data['symbol']] = sub_data
        else:
            for account in self.accounts.values():
                if account.usd_value == 0 and hide_zero:
                    continue
                sub_data = {'symbol': account.pair,
                            'balance': account.balance,
                            'value': account.usd_value}
                data[sub_data['symbol']] = sub_data
        total = sum([int(s['value']) for s in data.values()])
        for sub in data.values():
            sub['allocation'] = round(sub['value']/total, 3)
        return data

    def get_total_value(self):
        """
        Sums up the GdaxAccount.usd_value for each account
        in the user's profile returning a float of the total sum.

        :return:
        """
        vals = [a.usd_value for a in
                self.accounts.values()]
        return round(sum(vals), 2)

    def post_order(self, order_json):
        """
        Post's the output of GdaxOrder.json
        :param order_json: (dict, GdaxOrder.json)
        :return:
            {
                "id": "d0c5340b-6d6c-49d9-b567-48c4bfca13d2",
                "price": "0.10000000",
                "size": "0.01000000",
                "product_id": "BTC-USD",
                "side": "buy",
                "stp": "dc",
                "type": "limit",
                "time_in_force": "GTC",
                "post_only": false,
                "created_at": "2016-12-08T20:02:28.53864Z",
                "fill_fees": "0.0000000000000000",
                "filled_size": "0.00000000",
                "executed_value": "0.0000000000000000",
                "status": "pending",
                "settled": false
            }
        """
        return self.post('orders', json=order_json).json()

    def get_account_ledger_history(self, paginate=True):
        """
        Returns a pandas.DataFrame containing historical transactions for each GdaxAccount
        assigned to the user.

        NOTE: if paginate is set to true this method can take a long time
        to complete as each account may make multiple API calls to gather
        the data.

        [
            {
                "id": "100",
                "created_at": "2014-11-07T08:19:27.028459Z",
                "amount": "0.001",
                "balance": "239.669",
                "type": "fee",
                "details": {
                    "order_id": "d50ec984-77a8-460a-b958-66f114b0de9b",
                    "trade_id": "74",
                    "product_id": "BTC-USD"
                }
            }
        ]
        :return:
        """
        data = []
        for account in self.accounts.values():
            if account.currency == account.USD:
                continue
            chunk = account.get_history(paginate=paginate)
            data.extend(chunk)

        for record in data:
            details = record.pop('details', None)
            if details:
                record.update(details)

        return pd.DataFrame.from_records(data, index=range(len(data)))

    def _validate_product(self, product):
        if product not in GdaxProducts.LIST:
            raise KeyError("Product not in GdaxProducts: "
                           "{} ? {}".format(product, GdaxProducts.LIST))

    def withdraw_to_coinbase(self, currency, amount, coinbase_account_id=None):
        """
        Withdraw funds to a coinbase account.
        You can move funds between your Coinbase accounts and your
        GDAX trading accounts within your daily limits.
        Moving funds between Coinbase and GDAX is instant and free.
        See the Coinbase Accounts section for retrieving your Coinbase accounts.

        HTTP REQUEST

        POST /withdrawals/coinbase

        PARAMETERS

        Param	Description
        amount	The amount to withdraw
        currency	The type of currency
        coinbase_account_id	ID of the coinbase account
        :param currency:
        :param size:
        :return:
        """

        if coinbase_account_id is None:
            try:
                coinbase_account_id = self.coinbase_accounts[currency]['id']
            except KeyError as e:
                raise KeyError("Unable to find coinbase_account_id "
                               "for currency '{}'. Error: "
                               "{}".format(currency, e))

        p = dict(currency=currency,
                 amount=amount,
                 coinbase_account_id=coinbase_account_id)

        return self.post("withdrawals/coinbase", json=json.dumps(p))

    def deposit_from_coinbase(self, currency, amount, coinbase_account_id=None):
        if coinbase_account_id is None:
            try:
                coinbase_account_id = self.coinbase_accounts[currency]['id']
            except KeyError as e:
                raise KeyError("Unable to find coinbase_account_id "
                               "for currency '{}'. Error: "
                               "{}".format(currency, e))

        p = dict(currency=currency,
                 amount=amount,
                 coinbase_account_id=coinbase_account_id)

        return self.post("deposits/coinbase-account", json=json.dumps(p))


