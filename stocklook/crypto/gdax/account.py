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


class GdaxAccount:
    """
    Represents a user's Gdax Account related to one
    of the products: LTC, BTC, ETH, or USD.
    The account
    """
    LTC = 'LTC'
    BTC = 'BTC'
    ETH = 'ETH'
    USD = 'USD'
    CURRENCIES = [LTC, BTC, ETH, USD]

    def __init__(self, data, gdax, price=None):
        """
        :param data: (dict)
            This data should be taken from the response
            returned by gdax.api.Gdax.get_accounts(). The following fields
            are assigned to GdaxAccount properties (same names):
                - available
                - profile_id
                - balance
                - id
                - currency
                - hold

        :param gdax: (gdax.api.Gdax)
            A reference to the API object is stored and used if/when needed.

        :param price:
        """
        self._data = data
        self._gdax = gdax
        self._price = price
        self.available = None
        self.profile_id = None
        self.balance = None
        self.id = None
        self.currency = None
        self.hold = None
        self.pair = None
        self._product = None
        self.update(data)

    @property
    def price(self):
        """
        Returns the USD price of the currency
        associated to the account.
        :return:
        """
        if self.currency == self.USD:
            self._price = 1
        else:
            # Price gets updated on a sync interval
            self._price = self.product.price

        return self._price

    @property
    def product(self):
        """
        Returns a gdax.product.GdaxProduct
        based on GdaxAccount.currency.
        :return:
        """
        p = self._product
        c = self.pair

        if p is None or p.currency != c:
            new_p = self._gdax.get_product(c)
            self._product = new_p

        return self._product

    @property
    def usd_value(self):
        """
        Returns the value in USD of the account.
        If the account is USD already then the balance
        is returned.
        :return:
        """
        if self.currency == self.USD:
            return self.balance
        elif not self.balance:
            return 0
        return round(self.price * self.balance, 2)

    def update(self, data=None):
        """
        Updates the GdaxAccount with data from the API.
        The following fields are assigned to
        GdaxAccount properties (same names):
            - available
            - profile_id
            - balance
            - id
            - currency
            - hold
        :param data: (dict)
        :return:
        """
        if data is None:
            data = self._gdax.get_accounts(account_id=self.id)
        [setattr(self, attr, val)
         for attr, val in data.items()]
        self.balance = float(self.balance)

        if self.currency == self.USD:
            self.balance = round(self.balance, 2)
            self.pair = self.USD
        else:
            self.pair = '{}-{}'.format(self.currency, self.USD)

    def get_history(self, paginate=True):
        """
        If an entry is the result of a trade (match, fee),
        the details field will contain additional information about the trade.

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

        :param paginate (bool, default True)
            True will paginate through all historical items using multiple API calls
            collecting data into one list.
            False will only return the first page of data returned by the API.

        :return:
        """
        ext = 'accounts/{}/ledger'.format(self.id)
        res = self._gdax.get(ext)

        if not paginate:
            return res.json()

        data = list(res.json())
        while 'cb-after' in res.headers:
            p = {'after': res.headers['cb-after']}
            res = self._gdax.get(ext, params=p)
            data.extend(res.json())

        return data

    def get_holds(self):
        """
        Returns a list of orders that are on hold for the GdaxAccount.
        Canceled orders get their hold (if there is one) removed.
        [
            {
                "id": "82dcd140-c3c7-4507-8de4-2c529cd1a28f",
                "account_id": "e0b3f39a-183d-453e-b754-0c13e5bab0b3",
                "created_at": "2014-11-06T10:34:47.123456Z",
                "updated_at": "2014-11-06T10:40:47.123456Z",
                "amount": "4.23",
                "type": "order",
                "ref": "0a205de4-dd35-4370-a285-fe8fc375a273",
            }
        ]
        :return:
        """
        ext = '/accounts/{}/holds'.format(self.id)
        return self._gdax.get(ext).json()

    def __repr__(self):
        return 'Currency: {}\n' \
               'Balance: {}\n' \
               'Price Per: ${}\n' \
               'Total Value: ${}'.format(self.currency,
                                         self.balance,
                                         self.price,
                                         self.usd_value)