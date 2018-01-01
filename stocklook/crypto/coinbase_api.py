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

from warnings import warn
from stocklook.config import COINBASE_KEY, COINBASE_SECRET
from stocklook.utils.security import Credentials
from coinbase.wallet.client import Client as CBClient, Withdrawal
import json


class CoinbaseClient(CBClient):
    """
    Subclass coinbase.wallet.client with support for
    credentials from config + a few convenience methods.
    """
    Credentials.register_config_object_mapping(
        Credentials.COINBASE,
        {
            COINBASE_KEY: 'api_key',
            COINBASE_SECRET: 'api_secret',
        })

    def __init__(self,
                 api_key=None,
                 api_secret=None,
                 base_api_uri=None,
                 api_version=None):
        self.api_key = None
        self.api_secret = None
        if not all((api_key, api_secret)):
            from stocklook.utils.security import Credentials
            creds = Credentials(allow_input=True)
            creds.configure_object_vars(
                self, creds.COINBASE,
                'api_key', ['api_secret'])

        CBClient.__init__(self,
                          api_key=api_key,
                          api_secret=api_secret,
                          base_api_uri=base_api_uri,
                          api_version=api_version)

        self._pmt_methods = None
        self._accounts = None

    @property
    def pmt_methods(self):
        if self._pmt_methods is None:
            self._pmt_methods = self.get_payment_methods()\
                .response.json()['data']
        return self._pmt_methods

    @property
    def accounts(self):
        # dictionary of currency: account
        if self._accounts is None:
            res = self.get_accounts()\
                .response.json()['data']
            self._accounts = {
                a['currency']: a
                for a in res
            }

        return self._accounts

    def get_payment_method_by_last_4(self, last_four, name_key=None):
        # Convenient payment method via last 4
        last_four = str(last_four)
        if name_key:
            name_key = name_key.upper()
        try:
            return [m for m in self.pmt_methods
                    if m['name'].endswith(last_four)
                    and (name_key is None
                         or name_key in m['name'].upper())
                    ][0]
        except (IndexError, KeyError):
            return None








if __name__ == '__main__':
    from stocklook.crypto.gdax import Gdax, GdaxOrder
    from time import sleep

    c = CoinbaseClient()
    g = Gdax()
    last_4 = '5118'
    key = 'mastercard'
    #method = c.get_payment_method_by_last_4(last_4, key)
    #cusd_acc = g.coinbase_accounts['USD']
    # print(cusd_acc)
    gusd_acc = g.accounts['USD']
    gltc_acc = g.accounts['LTC']
    # Withdraw 1% of funds.
    amount = round(gusd_acc.balance * 0.01, 2)
    print("Funds amount: {}".format(amount))

    try:
        res = g.withdraw_to_coinbase('USD', amount)
        print(res)
        print(res.status_code)
        print(res.json())
    except Exception as e:
        print("Failed to withdraw...{}".format(e))
        raise

    try:
        res = g.deposit_from_coinbase('USD', amount)
        print(res.json())
    except Exception as e:
        print("Failed to deposit...{}".format(e))

    if gltc_acc.balance < 0.01:
        print("Ordering LTC")
        o = GdaxOrder(g, 'LTC-USD',
                      order_type='market',
                      size=0.01)
        o.post()
        sleep(10)
    try:
        g.withdraw_to_coinbase('LTC', 0.01)
    except Exception as e:
        print("Failed to withdraw LTC: {}".format(e))






