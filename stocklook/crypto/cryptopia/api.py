"""

This is a wrapper for Cryptopia.co.nz API
Base copied from: https://github.com/crypto-crew-tech/cryptopia-api-python
"""

import urllib
import json
import time
import hmac
import hashlib
import base64
import requests
from stocklook.config import CRYPTOPIA_KEY, CRYPTOPIA_SECRET
from stocklook.utils.security import Credentials


class Cryptopia:
    """ Represents a wrapper for cryptopia API """
    Credentials.register_config_object_mapping(
        Credentials.CRYPTOPIA,
        {CRYPTOPIA_KEY: 'key',
         CRYPTOPIA_SECRET: 'secret'}
    )

    def __init__(self, key=None, secret=None):
        self.key = key
        self.secret = secret
        self.public = ['GetCurrencies', 'GetTradePairs', 'GetMarkets',
                       'GetMarket', 'GetMarketHistory', 'GetMarketOrders', 'GetMarketOrderGroups']
        self.private = ['GetBalance', 'GetDepositAddress', 'GetOpenOrders',
                        'GetTradeHistory', 'GetTransactions', 'SubmitTrade',
                        'CancelTrade', 'SubmitTip', 'SubmitWithdraw', 'SubmitTransfer']

        if not all((key, secret)):
            c = Credentials()
            c.configure_object_vars(
                self, c.CRYPTOPIA,
                'key', ['secret'])

    @property
    def secret(self):
        return self._secret

    @secret.getter
    def secret(self):
        return self._secret

    @secret.setter
    def secret(self, x):
        if not x:
            self._secret = x
        else:
            self._secret = base64.b64decode(x + '=' * (-len(x) % 4))

    def api_query(self, feature_requested, get_parameters=None, post_parameters=None):
        """ Performs a generic api request """
        time.sleep(1)
        if feature_requested in self.private:
            url = "https://www.cryptopia.co.nz/Api/" + feature_requested
            post_data = json.dumps(post_parameters)
            headers = self.secure_headers(url=url, post_data=post_data)
            req = requests.post(url, data=post_data, headers=headers)
            if req.status_code != 200:
                try:
                    req.raise_for_status()
                except requests.exceptions.RequestException as ex:
                    return None, "Status Code : " + str(ex)
            req = req.json()
            if req['Success'] is True:
                result = req['Data']
                error = None
            else:
                result = None
                if req['Message'] is None:
                    error = "Unknown response error"
                else:
                    error = req['Message']
            return (result, error)
        elif feature_requested in self.public:
            url = "https://www.cryptopia.co.nz/Api/" + feature_requested + "/" + \
                  ('/'.join(i for i in get_parameters.values()
                           ) if get_parameters is not None else "")
            req = requests.get(url, params=get_parameters)
            if req.status_code != 200:
                try:
                    req.raise_for_status()
                except requests.exceptions.RequestException as ex:
                    return None, "Status Code : " + str(ex)
            req = req.json()
            if req['Success'] is True:
                result = req['Data']
                error = None
            else:
                result = None
                if req['Message'] is None:
                    error = "Unknown response error"
                else:
                    error = req['Message']
            return (result, error)
        else:
            return None, "Unknown feature"

    def get_currencies(self):
        """ Gets all the currencies """
        return self.api_query(feature_requested='GetCurrencies')

    def get_tradepairs(self):
        """ GEts all the trade pairs """
        return self.api_query(feature_requested='GetTradePairs')

    def get_markets(self):
        """ Gets data for all markets """
        return self.api_query(feature_requested='GetMarkets')

    def get_market(self, market):
        """ Gets market data """
        return self.api_query(feature_requested='GetMarket',
                              get_parameters={'market': market})

    def get_history(self, market):
        """ Gets the full order history for the market (all users) """
        return self.api_query(feature_requested='GetMarketHistory',
                              get_parameters={'market': market})

    def get_orders(self, market):
        """ Gets the user history for the specified market """
        return self.api_query(feature_requested='GetMarketOrders',
                              get_parameters={'market': market})

    def get_ordergroups(self, markets):
        """ Gets the order groups for the specified market """
        return self.api_query(feature_requested='GetMarketOrderGroups',
                              get_parameters={'markets': markets})

    def get_balance(self, currency):
        """ Gets the balance of the user in the specified currency """
        result, error = self.api_query(feature_requested='GetBalance',
                                       post_parameters={'Currency': currency})
        if error is None:
            result = result[0]
        return (result, error)

    def get_openorders(self, market):
        """ Gets the open order for the user in the specified market """
        return self.api_query(feature_requested='GetOpenOrders',
                              post_parameters={'Market': market})

    def get_deposit_address(self, currency):
        """ Gets the deposit address for the specified currency """
        return self.api_query(feature_requested='GetDepositAddress',
                              post_parameters={'Currency': currency})

    def get_tradehistory(self, market):
        """ Gets the trade history for a market """
        return self.api_query(feature_requested='GetTradeHistory',
                              post_parameters={'Market': market})

    def get_transactions(self, transaction_type):
        """ Gets all transactions for a user """
        return self.api_query(feature_requested='GetTransactions',
                              post_parameters={'Type': transaction_type})

    def submit_trade(self, market, trade_type, rate, amount):
        """ Submits a trade """
        return self.api_query(feature_requested='SubmitTrade',
                              post_parameters={'Market': market,
                                               'Type': trade_type,
                                               'Rate': rate,
                                               'Amount': amount})

    def cancel_trade(self, trade_type, order_id, tradepair_id):
        """ Cancels an active trade """
        return self.api_query(feature_requested='CancelTrade',
                              post_parameters={'Type': trade_type,
                                               'OrderID': order_id,
                                               'TradePairID': tradepair_id})

    def submit_tip(self, currency, active_users, amount):
        """ Submits a tip """
        return self.api_query(feature_requested='SubmitTip',
                              post_parameters={'Currency': currency,
                                               'ActiveUsers': active_users,
                                               'Amount': amount})

    def submit_withdraw(self, currency, address, amount):
        """ Submits a withdraw request """
        return self.api_query(feature_requested='SubmitWithdraw',
                              post_parameters={'Currency': currency,
                                               'Address': address,
                                               'Amount': amount})

    def submit_transfer(self, currency, username, amount):
        """ Submits a transfer """
        return self.api_query(feature_requested='SubmitTransfer',
                              post_parameters={'Currency': currency,
                                               'Username': username,
                                               'Amount': amount})

    def secure_headers(self, url, post_data):
        """ Creates secure header for cryptopia private api. """
        nonce = str(int(time.time()))
        post_data = post_data.encode('utf8')
        md5 = hashlib.md5()
        md5.update(post_data)
        rcb64 = base64.b64encode(md5.digest()).decode('utf8')

        signature = self.key + "POST" + \
            urllib.parse.quote_plus(url).lower() + nonce + rcb64
        signature = signature.encode('utf8')
        sign = base64.b64encode(
            hmac.new(self.secret, signature, hashlib.sha256).digest())
        header_value = "amx " + self.key + ":" + sign.decode('utf8') + ":" + nonce
        return {'Authorization': header_value, 'Content-Type': 'application/json; charset=utf-8'}