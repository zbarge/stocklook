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
from threading import Thread
from time import sleep
from stocklook.utils.timetools import timestamp_from_utc, now
from .tables import GdaxSQLOrder
import logging as lg
log = lg.getLogger(__name__)


class GdaxOrderCancellationError(Exception):
    pass


class GdaxOrderFillTimeout(Exception):
    pass


class GdaxInsufficientFundsError(Exception):
    """
    Raised when there isn't enough funds available to place an order.
    """
    pass


class GdaxDuplicateOrderError(Exception):
    """
    Raised when an order is being posted that already has an executed value.
    """
    pass


class GdaxMinOrderSizeError(Exception):
    """
    Raised when an order size is > 0 < 0.01
    """
    pass


class GdaxOrderTypes:
    """
    Stores available GDAX order types: limit, market, and stop
    """
    LIMIT = 'limit'
    MARKET = 'market'
    STOP = 'stop'
    LIST = [LIMIT, MARKET, STOP]


class GdaxOrderSides:
    """
    Stores available GDAX order sides: buy or sell
    """
    BUY = 'buy'
    SELL = 'sell'
    LIST = [BUY, SELL]


class GdaxOrder:
    """
    GdaxOrder is designed to encompass any order type and provide
    a dictionary with the appropriate parameters for posting to Gdax.
    Example:
        order = GdaxOrder('BTC-USD', order_type='limit', side='buy', price='4300', size='0.03')
        data = order.json()

    Order Statuses:
        1) open
        2) pending
        3) active

    ORDER STATUS AND SETTLEMENT
    ----------------------------
    Orders which are no longer resting on the order book,
    will be marked with the done status.
    There is a small window between an order being done and settled.
    An order is settled when all of the fills have settled and the
    remaining holds (if any) have been removed.

    """
    def __init__(self,
                 gdax,
                 product,
                 order_type='limit',
                 side='buy',
                 stp='dc',
                 price=None,
                 size=None,
                 funds=None,
                 time_in_force='GTC',
                 cancel_after=None,
                 client_oid=None,
                 status=None,
                 fill_fees=None,
                 id=None,
                 executed_value=None,
                 settled=None,
                 created_at=None,
                 post_only=None,
                 stop_price=None,
                 stop=None,
                 filled_size=None,
                 order_sys=None):
        """
        :param product: (str, ('BTC-USD', 'LTC-USD', 'ETH-USD'))
        :param order_type: (str, ('limit', 'market', 'stop'))
        :param side: (str, ('buy', 'sell'))
        :param stp: (str, ('dc'))
        :param price: (int, str)
        :param size: (int, str, default=None)
        :param funds: (int, str, default=None)
        :param time_in_force: (str, ('GTC', 'GTT', 'IOC', or 'FOK' (default is GTC))
        :param cancel_after: (str, int, (min, hour, day))
        :param client_oid: (str, int, default=None)
        """
        self.gdax = gdax
        self.product = product
        self.order_type = order_type
        self.side = side
        self.stp = stp
        self._price = price
        self.size = size
        self.funds = funds
        self.time_in_force = time_in_force
        self.cancel_after = cancel_after
        self.client_oid = client_oid
        self.status = status
        self.fill_fees = fill_fees
        self.id = id
        self.executed_value = executed_value
        self.settled = settled
        self.created_at = created_at
        self.post_only = post_only
        self.stop_price = stop_price
        self.stop = stop
        self.filled_size = filled_size
        self._json = None
        self._total_spend = None
        self.coin_currency, self.base_currency = product.split('-')
        self.order_sys = order_sys
        self._update_time = None

    @property
    def json(self):
        """
        Creates a JSON object based on order type
        of stop, market, or limit.
        :return:
        """
        self._validate_order_type(self.order_type)
        if self.order_type == GdaxOrderTypes.LIMIT:
            order = self._limit(self.price,
                                self.size,
                                self.time_in_force,
                                self.cancel_after)
        elif self.order_type == GdaxOrderTypes.MARKET:
            order = self._market(self.size,
                                 self.funds)
        elif self.order_type == GdaxOrderTypes.STOP:
            order = self._stop(self.price,
                               self.size,
                               self.funds)
        self._json = order
        return self._json

    @property
    def price(self):
        return self._price

    @price.setter
    def price(self, x):
        if x is not None:
            self._price = round(x, 2)
        else:
            self._price = x

    @price.getter
    def price(self):
        if self._price:
            return round(self._price, 2)

    def update(self, data=None):
        """
        Updates GdaxOrder class properties
        using data provided when calling the function
        or called automatically by the API.
        :param data: (dict)
            Should contain fields such as id, price, size,
            side, order_type, time_in_force, etc.
        :return: (None)
        """
        if data is None:
            if self.id is None:
                raise Exception("Order has no ID and "
                                "no data was provided to update.")
            data = self.gdax.get_orders(self.id)

        self.id = data.get('id')
        self.price = float(data.get('price', 0))
        self.size = float(data.get('size', 0))
        self.side = data.get('side')
        self.order_type = data.get('type')
        self.time_in_force = data.get('time_in_force')
        self.post_only = data.get('post_only')
        self.created_at = timestamp_from_utc(data.get('created_at'))
        self.funds = float(data.get('funds', 0))
        self.fill_fees = float(data.get('fill_fees', 0))
        self.filled_size = float(data.get('filled_size', 0))
        self.executed_value = float(data.get('executed_value', 0))
        self.status = data.get('status')
        self.settled = data.get('settled')
        self._update_time = now()

    @property
    def total_spend(self):
        """
        Calculates total spent on the order or makes an estimate
        on market orders that have not yet been placed.
        :return:
        """
        if self.executed_value is not None:
            self._total_spend = float(self.executed_value)
        else:

            size = (float(self.size) if self.size else 0)
            buy_price = (float(self.price) if self.price else 0)

            if self.order_type == GdaxOrderTypes.MARKET:
                if self.settled in (None, 'false') or not self.filled_size:
                    if not self.funds:
                        self.funds = 0
                    funds = float(self.funds)
                    prod = self.gdax.get_product(self.product)
                    mkt_price = prod.price
                    if size > 0:
                        spend = size * mkt_price
                        spend += spend * 0.03  # Taker fee
                        self._total_spend = spend
                    elif funds > 0:
                        self._total_spend =  funds
                        # Taker fee will be included just get less coin.

            elif self.order_type in [GdaxOrderTypes.LIMIT, GdaxOrderTypes.STOP]:
                self._total_spend = size * buy_price

        if self.side == GdaxOrderSides.SELL and self._total_spend > 0:
            # sell orders should be a negative
            # value to reflect an inflow
            # of funds rather than outflow.
            self._total_spend -= self._total_spend * 2

        return self._total_spend

    def _limit(self, price, size, time_in_force='GTC', cancel_after=None):
        data = dict(price=price, size=size)
        if time_in_force and time_in_force != 'GTC':
            data['time_in_force'] = time_in_force
        if cancel_after:
            data['cancel_after'] = cancel_after
        return self._finalize_data(data)

    def _market(self, size=None, funds=None):
        if all([size, funds]):
            raise AttributeError("size and funds cannot "
                                 "both contain data.")
        data = dict()
        if size:
            data['size'] = size
        if funds:
            data['funds'] = funds
        return self._finalize_data(data)

    def _stop(self, price, size=None, funds=None):
        if all([size, funds]):
            raise AttributeError("size and funds cannot "
                                 "both contain data.")
        data = dict(price=price)
        if size:
            data['size'] = size
        if funds:
            data['funds'] = funds

        return self._finalize_data(data)

    def _finalize_data(self, data):
        """
        Updates an order dictionary before dumping to JSON format
        with the following information:
            - side
            - product_id
            - client_oid (if present)

        This method is called by
        the following internal methods:
            GdaxOrder._market
            GdaxOrder._limit
            GdaxOrder._stop

        :param data: (dict)
            Data outputted by a market, limit, or stop order.
        :return:
        """

        # Add product/side
        self._validate_order_side(self.side)
        data.update({'product_id': self.product,
                     'side': self.side,
                     'type': self.order_type})

        # Round price to 2 decimal places
        price = data.get('price')
        if price:
            price = round(price, 2)
            data['price'] = price
            self.price = price

        # Round size to 7 decimal places
        size = data.get('size')
        if size:
            size = round(data['size'], 7)
            data['size'] = size
            self.size = size

        data.pop('client_oid', None)

        # Convert all values to string
        for key in data.keys():
            data[key] = str(data[key])

        return data

    def _validate_order_type(self, t):
        if t in GdaxOrderTypes.LIST:
            return True
        raise AttributeError("Order Type '{}' not "
                             "in GdaxOrderTypes"
                             "({})".format(t, GdaxOrderTypes.LIST))

    def _validate_order_side(self, t):
        if t in GdaxOrderSides.LIST:
            return True
        raise AttributeError("Order Side '{}' not "
                             "in GdaxOrderSides"
                             "({})".format(t, GdaxOrderSides.LIST))

    def is_posted(self) -> bool:
        """
        Returns True when status and id
        properties are not None.
        :return:
        """
        return self.status and self.id

    def is_cancelled(self):
        """
        Returns true when the GdaxOrder.status is canceled or rejected.
        :return:
        """
        return self.status in ['canceled', 'rejected']

    def is_filled(self, update=True) -> bool:
        """
        Returns True when GdaxOrder.status is 'done'.
        Calls order status from API if the order has
        been posted but is not in status 'done'.
        :return:
        """
        if self.is_cancelled() or not self.is_posted():
            return False
        elif self.status and self.status == 'done':
            return True

        if update:
            self.update()

        return self.status and self.status not in ['canceled', 'open']

    def wait_for_fill(self, interval=30, timeout=60*60, cancel=False):
        """
        Checks with the API on an interval to see if the order has been
        filled.

        :param interval: (int, default 30)
            Number of seconds to wait between checking for fills.

        :param timeout: (int, default 60*60)
            Number of seconds to wait before raising an error if no fill.

        :param cancel: (bool, default False)
            True will cancel the order before raising a timeout error.
            False will just raise the timeout error.

        :raises GdaxOrderFillTimeout
            When the wait period exceeds the timeout value.

        :raises GdaxOrderCancellationError
            When the order has been magically filled during cancellation.
            Only can occur if :param cancel=True.

        :return:
        """
        wait_time = 0
        while not self.is_filled():
            if self.is_cancelled():
                break
            # Check for timeout/need-to-cancel.
            if timeout and wait_time >= timeout:
                if cancel:
                    self.cancel()
                msg = 'Order(id={}, type={}, ' \
                      'size={}, price={})'.format(self.id, self.order_type,
                                                  self.size, self.price)
                raise GdaxOrderFillTimeout(msg)

            sleep(interval)
            wait_time += interval

    def cancel(self):
        """
        Cancels the order if it's open.
        If the API returns a fail reason a
        GdaxOrderCancellationError will be raised.
        :return:
        """
        if not self.is_posted() or self.is_cancelled():
            return False

        if self.order_sys is not None:
            return self.order_sys.cancel_order(self.id)

        ext = 'orders/{}'.format(self.id)
        res = self.gdax.delete(ext).json()
        if isinstance(res, dict):
            fail_reason = res.get('message', None)
        else:
            fail_reason = None

        if fail_reason:
            raise GdaxOrderCancellationError(fail_reason)

        self.status = 'canceled'
        return res

    def post(self, sql_obj=None, verify_balance=True):
        """
        Validates then places the order within Gdax via the Gdax.place_order method.

        :param sql_obj: (GdaxSQLOrder, default None)
            An optional GdaxSQLOrder to post a copy of results to.

        :raises GdaxDuplicateOrderError:
            When the GdaxOrder.status and GdaxOrder.id are already assigned. That means
            the order has already been placed with the API and a new one is needed.

        :raises GdaxInsufficientFundsError:
            GdaxOrderSides.BUY:
                must have enough base currency available to cover the
                transaction (or est. transaction in some market order cases)
            GdaxOrderSides.SELL:
                must have enough of the coin available to
                sell...not set up for margin trading. Fuck banks.

        :raises GdaxMinOrderSizeError:
            When GdaxOrder.size is present but smaller than 0.01

        :return:
        """

        # Make sure the order hasn't already been posted.
        if self.is_posted():
            raise GdaxDuplicateOrderError("Order {} has already "
                                          "posted with status {}.".format(self.id,
                                                                          self.status))

        # Size needs to be >= 0.01 if present.
        size = (0 if not self.size else self.size)
        if size < .01 and size > 0:
            raise GdaxMinOrderSizeError("Order size must be "
                                        "greater than 0.01, not {}".format(size))

        # Potentially verify balance
        # before placing the order.
        if verify_balance:
            self.gdax.sync_accounts()

            # Buy orders need to have enough funds
            # in the base currency account to cover the total.
            if self.side == GdaxOrderSides.BUY:
                acc = self.gdax.get_account(self.base_currency)
                val = acc.balance
                spend = self.total_spend

                if spend > val:
                    msg = "spend: {}, balance: {} coin: {}" \
                          "".format(spend, val, self.coin_currency)
                    raise GdaxInsufficientFundsError(msg)

            # Sell orders need to have enough coin
            # available to sell.
            elif self.side == GdaxOrderSides.SELL:
                size = float(self.size)
                acc = self.gdax.get_account(self.coin_currency)
                bal = float(acc.balance)

                if size > bal:
                    msg = "sell: {}, balance: {}, coin: {}" \
                          "".format(size, bal, self.coin_currency)
                    raise GdaxInsufficientFundsError(msg)

        # Call API - Green light if we made it here.
        res = self.gdax.post_order(self.json)
        self.update(res)

        # Update the SQL object if provided
        if sql_obj:
            self.update_sql_object(sql_obj)

    def post_after_block_height(self, block_num, check_interval=20, **order_post_kwargs):
        """
        Places an order after a given block number has passed.
        If the provided block number has passed the order is placed immediately.

        :param block_num:
        :param check_interval:
        :param order_post_kwargs:
        :return:
        """
        if 'BTC' in self.product.upper():
            from stocklook.crypto.bitcoin import btc_get_block_height as get_height
        else:
            raise NotImplementedError("This functionality is currently "
                                      "only supported for BTC.")

        while get_height() <= block_num:
            sleep(check_interval)

        return self.post(**order_post_kwargs)

    def to_sql_object(self):
        """
        Generates a GdaxSQLOrderObject
        and returns it after updating attributes.
        :return:
        """
        o = GdaxSQLOrder()
        self.update_sql_object(o)
        return o

    def update_sql_object(self, o):
        """
        Updates the attributes of a GdaxSQLOrderObject using
        class attributes.
        :param o:
        :return:
        """
        [setattr(o, k, v) for k, v in self.to_dict().items()]
        o.fake = False
        return o

    def to_dict(self):
        """
        Returns a dictionary with class attributes.
        :return:
        """
        return dict(id=self.id,
                    created_at=self.created_at,
                    executed_value=self.executed_value,
                    fill_fees=self.fill_fees,
                    filled_size=self.filled_size,
                    status=self.status,
                    funds=self.funds,
                    side=self.side,
                    stp=self.stp,
                    time_in_force=self.time_in_force,
                    post_only=self.post_only,
                    settled=self.settled,
                    type=self.order_type)

    def __repr__(self):
        return 'Product: {}\n' \
               'Order Type: {}\n' \
               'Order Side: {}\n'\
               'Price: ${}\n' \
               'Funds: ${}\n' \
               'Status: {}\n ' \
               'Size: {}\n' \
               'Settled: {}\n' \
               'Last Updated: {}\n'.format(
                                 self.product,
                                 self.order_type,
                                 self.side,
                                 self.price,
                                 self.funds,
                                 self.status,
                                 self.size,
                                 self.settled,
                                 self._update_time)


class GdaxTrailingStop(Thread):
    """
    A thread that scans price and sells
    using a trailing stop by percent or by amount.

    The default price-checking protocol is for the thread to use the gdax.product.GdaxProduct.price
    which will sync via the API based on the GdaxTrailingStop.interval.


    Side Note:
    ----------
    It would be ideal to subclass and override the GdaxTrailingStop.get_current_price method with a call
    to a database that's attached to the gdax.feeds.GdaxDatabaseFeed 'ticker' websocket feed.
    In this scenario it is critical that the database feed stay ALWAYS ON to keep current prices up-to-date.
    This scenario would eliminate an API call from the GdaxTrailingStop to get the price on each interval
    but we're talking milliseconds of difference between a database call v.s. API call. This would be the
    #1 way to maximize performance and accuracy in my opinion.
    """

    def __init__(self, pair, size, stop_pct=None, stop_amt=None,
                 target=None, notify=None, interval=10, gdax=None,
                 product=None):
        """
        :param pair: (str)
            LTC-USD, BTC-USD, or ETH-USD

        :param size: (int, float)
            The size of coin(s) to sell. If this size is not available in the Gdax account
            they'll be immediately market bought as long as :param buy_needed is True.

        :param stop_pct: (float, default None)
            The decimal (percentage) amount the currency must fall to trigger the sell order.
            Note: You can't use both :param stop_pct and :param stop_amt, just one or the other.

        :param stop_amt: (float, default None)
            The $ amount that the currency must fall to trigger the sell order.
            Note: You can't use both :param stop_pct and :param stop_amt, just one or the other.

        :param notify: (str, default None)
            An email address to notify when the stop has been triggered.

        :param interval (int, default 10)
            The number of seconds to wait between price-checks & stop calculations.

        :param gdax: (gdax.api.Gdax, default None)
            None will generate a default Gdax API object within the GdaxTrailingStop.
            This is used to check account balance and get the current price by default.

        """
        assert interval >= 5
        fail = all([stop_pct, stop_amt])
        if fail:
            msg = "stop_pct and stop_amt " \
                  "cannot both contain values."
            log.error(msg)
            raise AttributeError(msg)

        Thread.__init__(self)

        if gdax is None:
            from stocklook.crypto.gdax import Gdax
            gdax = Gdax()
        if product is None:
            product = gdax.get_product(pair)
            product.sync_interval = interval - 1

        self.gdax = gdax
        self.pair = pair
        self.product = product
        self.size = size
        self.stop_pct = stop_pct
        self.stop_amt = stop_amt
        self.notify = notify
        self.sell_mark = None
        self.sell_order = None
        self.down_diff = None
        self.up_diff = None
        self.first_price = None
        self.price = None
        self.target = target
        self.interval = interval

    def notify_user(self, update):
        """
        Sends a notification email as long as
        GdaxTrailingStop.notify contains a destination.

        :param update: (str)
            The message to send.
            By default the only message sent is a notification
            that the stop order has been triggered.
        :return: (None)
        :raises (None)
            All errors are ignored and only printed when encountered
        """
        if not self.notify:
            return

        try:
            from stocklook.utils.emailsender import send_message
            send_message(self.notify, update)
        except Exception as e:
            log.info("ERROR: Failed to send notification "
                     "to {} - {}".format(self.notify, e))

    @property
    def pnl(self):
        p = self.price
        fp = self.first_price
        if all((p, fp)):
            return round((p - fp) * self.size, 2)

    def get_current_price(self):
        """
        Returns gdax.product.GdaxProduct.price
        This is set to sync with the API on an interval 1 second less
        than GdaxTrailingStop.interval so it should be always up-to-date.
        :return:
        """
        return self.product.price

    def get_sell_mark(self, price):
        """
        Returns the price at which the currency should be sold
        based on the GdaxTrailingStop.stop_pct or GdaxTrailingStop.stop_amt
        whichever is provided.
        :param price: (float, int)
            The current price to use for calculating the stop price.

        :return: (float, int)
            The stop price based on the given price.
        """
        if self.target and price >= self.target:
            m = price
        elif self.stop_pct:
            m = price - (price * self.stop_pct)
        elif self.stop_amt:
            m = price - self.stop_amt
        else:
            m = None
        return m

    def sell(self):
        """
        Executes a market sell order
        liquidating the entire position.
        :return: (GdaxOrder)
            The posted GdaxOrder object reflecting the sell order.
        """
        if self.sell_order is not None:
            raise Exception("Existing sell order - "
                            "cannot re-sell: "
                            "{}".format(self.sell_order))

        o = GdaxOrder(self.gdax,
                      self.pair,
                      order_type='market',
                      side='sell',
                      size=self.size)
        o.post()
        # Wait a few moments
        # and update the order with fill info.
        sleep(5)
        o.update()

        msg = '{} Trailing stop order @ price {} ' \
              'executed - {}'.format(now(), self.price, o)
        self.notify_user(msg)
        self.sell_order = o

        return o

    def run(self):
        """
        Scans price on an interval via GdaxTrailingStop.get_current_price.
        Updates GdaxTrailingStop.sell_mark as the price moves up
        Executes GdaxTrailingStop.sell and GdaxTrailingStop.notify when the price
        hits the sell_mark.

        :return: (GdaxOrder)
            Reflecting the triggered sale.
            This is also assigned to GdaxTrailingStop.sell_order.
        """
        price = self.first_price = self.get_current_price()
        mark = new_mark = self.sell_mark = self.get_sell_mark(price)

        while True:
            # We move the sell_mark up
            # as price moves higher.
            if (mark and new_mark and new_mark > mark) or \
                    (new_mark is not None and mark is None):

                if mark and new_mark:
                    m_diff = round(new_mark - mark, 2)
                    log.debug("mark bump ${} to "
                              "{}".format(m_diff, new_mark))

                self.sell_mark = new_mark

            mark = self.sell_mark

            if price <= mark:
                o = self.sell()
                break

            self.down_diff = round(price - mark, 2)
            self.up_diff = (round(self.target - price, 2)
                            if self.target else None)
            price = self.price = self.next_price(price)
            new_mark = self.get_sell_mark(price)

        return o

    def next_price(self, p):
        while p == self.price:
            sleep(self.interval)
            p = self.get_current_price()
            log.debug("price: {}".format(p))
        return p


def execute_trailing_stop(pair,
                          size,
                          stop_amt=None,
                          stop_pct=None,
                          target=None,
                          notify=None,
                          buy_needed=True,
                          gdax=None,
                          stop_obj=None):
    """
    A trailing stop sell order function.

    Takes over the main thread until the order has been executed so this is a standalone function
    meant to be run by a trader alone as is...anything custom just make your own method using the
    GdaxTrailingStop object.

    :param pair: (str)
        LTC-USD, BTC-USD, or ETH-USD

    :param size: (int, float)
        The size of coin(s) to sell. If this size is not available in the Gdax account
        they'll be immediately market bought as long as :param buy_needed is True.

    :param stop_amt: (float, default None)
        The $ amount that the currency must fall to trigger the sell order.
        Note: You can't use both :param stop_pct and :param stop_amt, just one or the other.

    :param stop_pct: (float, default None)
        The decimal (percentage) amount the currency must fall to trigger the sell order.
        Note: You can't use both :param stop_pct and :param stop_amt, just one or the other.

    :param notify: (str, default None)
        An email address to notify when the stop has been triggered.

    :param buy_needed: (bool, default True)
        True will market buy needed coins based on the exact
        difference between the account balance and the :param size.
        If there are enough coins in the account already none will need to be purchased.

    :param gdax: (gdax.api.Gdax, default None)
        None will generate a default Gdax API object within the GdaxTrailingStop.
        This is used to check account balance and get the current price by default.

    :return: (GdaxTrailingStop)
        Object will be returned and the actual stop order can be accessed
        via the GdaxTrailingStop.sell_order property.
    """
    currency, denomination = pair.split('-')
    if stop_obj is None:
        stop_obj = GdaxTrailingStop

    order = stop_obj(pair,
                     size,
                     stop_amt=stop_amt,
                     stop_pct=stop_pct,
                     target=target,
                     notify=notify,
                     gdax=gdax)

    if gdax is None:
        gdax = order.gdax

    account = gdax.get_account(currency)
    bal = account.balance

    if bal < size:
        if not buy_needed:
            raise Exception("Only {} {} available but "
                            "order size is {} and buy_needed "
                            "is False".format(bal, currency, size))
        need = size - bal

        # Buy some coin
        o = GdaxOrder(gdax,
                      pair,
                      order_type='market',
                      size=need)
        o.post()
        sleep(5)
        account.update()
        # Proves the coin was bought.
        assert account.balance >= size
        log.info("Purchased {} {}".format(need, pair))
        log.info(o)

    order.start()
    sleep(15)

    while not order.sell_order:
        # Check and output price/away information about the order
        # Every 30 seconds.
        log.info("{}: price: ${}, "
                 "mark: ${}, "
                 "to target: ${}"
                 "from stop: ${}"
                 "pnl: ${}".format(order.pair,
                                   order.price,
                                   order.sell_mark,
                                   order.up_diff,
                                   order.down_diff,
                                   order.pnl))
        sleep(30)

    bal = account.balance
    account.update()

    # Proves the balance was decreased now that the stop has triggered.
    assert account.balance == (bal - size)
    log.info(order.sell_order)
    return order


class GdaxOrderSystem:
    """
    The GdaxOrderSystem is responsible for
    placing, canceling, and retrieving orders keeping
    track within a SQL database.
    """
    def __init__(self, gdax, db, currency='USD', fake=False):
        """

        :param gdax: (gdax.api.Gdax)
            The Gdax API object.

        :param db: (gdax.db.GdaxDatabase)
        :param fake:
        """
        self.gdax = gdax
        self.db = db
        self.fake = fake
        self.currency = currency

    def sync_history(self):
        pass

    def place_order(self, session, gdax_order: GdaxOrder, commit=True):
        """
        Places an order to Gdax and records it within the database
        as well.

        :param session:
        :param gdax_order:
        :param commit:
        :return:
        """

        try:

            gdax_order.post()

        except Exception:
            raise

        else:
            # Finalize updates
            # Generate a new order
            o = GdaxSQLOrder()
            gdax_order.update_sql_object(o)
            session.add(o)
            if commit:
                session.commit()

        return o

    def cancel_order(self, session, order_id, commit=True):
        """
        Cancels an order on gdax and deletes it from the database
        as well.

        :param session:
            GdaxOrderSystem.get_session()
        :param order_id: (str)
            GdaxSQLOrder.id
            GdaxOrder.id
        :param commit: (bool, default True)
            True will commit the data to the database.
            False is good for canceling many orders trying to
            optimize i guess. Might as well use GdaxOrderSystem.cancel_all()
            at that point.
        :return:
        """
        qry = session.query(GdaxSQLOrder)\
                     .filter(GdaxSQLOrder.id == order_id)

        ext = 'orders/{}'.format(order_id)
        res = self.gdax.delete(ext).json()

        qry.delete()

        if commit:
            session.commit()

        return res

    def cancel_all(self, session, commit=True):
        """
        Cancels all open orders on Gdax and
        removes them from the database.

        :param session:
        :param commit:
        :return:
        """
        res = self.gdax.delete('orders').json()

        if res:
            qry = session.query(GdaxSQLOrder)\
                         .filter(GdaxSQLOrder.id.in_(res))
            qry.delete()

            if commit:
                session.commit()

        return res

    def list_orders(self):
        """
        Wraps Gdax.get_orders method
        for convenience.
        :return:
        """
        return self.gdax.get_orders()

    def get_orders(self, order_id=None, paginate=True):
        """
        Wraps Gdax.get_orders
        :param order_id: (str, default None)
            An order_id provides only information about that order.

        :param paginate: (bool, default True)
            True collects all orders.
        :return:
        """
        return self.gdax.get_orders(order_id=order_id, paginate=paginate)




