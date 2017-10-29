from warnings import warn
from coinbase.wallet.client import Client as CBClient, Withdrawal
import json


class CoinbaseClient(CBClient):
    """
    Subclass coinbase.wallet.client with support for
    credentials from config + a few convenience methods.
    """
    def __init__(self,
                 api_key=None,
                 api_secret=None,
                 base_api_uri=None,
                 api_version=None):

        if not all((api_key, api_secret)):
            from stocklook.utils.security import Credentials
            creds = Credentials(allow_input=True)
            if api_key is None:
                try:
                    api_key = creds.data['COINBASE_KEY']
                except KeyError:
                    warn("Set dict(stocklook.config.config) with "
                         "COINBASE_KEY to avoid inputting it manually.")

            # This will be input manually if not available.
            api_secret = creds.get(creds.COINBASE, username=api_key, api=False)
            if api_key is None:
                api_key = creds.data[creds.COINBASE]

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






