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
import logging
from time import sleep
from stocklook.config import config
from datetime import datetime, timedelta
from stocklook.crypto.gdax.api import Gdax, GdaxAPIError
from stocklook.utils.timetools import now, now_minus, timeout_check, now_plus
from stocklook.crypto.gdax.feeds.book_feed import GdaxBookFeed, BookSnapshot
from stocklook.crypto.gdax.order_mm import GdaxMMOrder, GdaxOrderCancellationError, OrderLockError

logger = logging.getLogger(__name__)
logger.setLevel(config.get('LOG_LEVEL', logging.DEBUG))


def tick_change_check(t_price, t_dict, t_key, min_change=0.01):
    if t_price is None:
        return False

    last_tick = t_dict.get(t_key, None)

    if not last_tick:
        t_dict[t_key] = t_price
        return True

    t_change = last_tick + min_change
    abs_change = abs(t_price - t_change)

    if abs_change >= min_change:
        t_dict[t_key] = t_price
        return True

    return False


class GdaxMarketMaker:
    _5M = '5M'
    _15M = '15M'
    _1H = '1H'
    _4H = '4H'
    _1D = '1D'
    TIME_FRAMES = [_5M, _15M, _1H, _4H, _1D]
    TIMEFRAME_MAP = {
        # time frame: (granularity, hours back, refresh seconds)
        _5M: (60*5, 24, 60*30),
        _15M: (60*15, 36, 60*60),
        _1H: (60*60, 48, 60*60*2),
        _4H: (60*60*4, 24*14, 60*60*8),
        _1D: (60*60*24, 24*28, 60*60*24),
    }

    def __init__(self,
                 book_feed=None,
                 product_id=None,
                 gdax=None,
                 max_spread=0.10,
                 min_spread=0.05,
                 stop_pct=0.05,
                 interval=2,
                 wall_size=None,
                 spend_pct=0.01,
                 max_open_buys=6,
                 max_open_sells=12,
                 manage_existing_orders=True,
                 aggressive=True):
        """
        Gdax market maker bot automatically trades the spreads.

        :param book_feed: (stocklook.crypto.gdax.feeds.book_feed.GdaxBookFeed, default None)
            None creates a new object.

        :param product_id: (str, ('ETH-USD', 'BTC-USD'))
            Can be any currency pair supported by Gdax.

        :param gdax: (stocklook.crypto.gdax.api.Gdax)
            None creates a new default object relying on stocklook.config.

        :param max_spread: (float, default 0.10)
            The maximum amount of currency desired on each position trade.
            Aggressive trades have lower maximums.

        :param min_spread: (float, default 0.05)
            The minimum amount of currency desired on each position trade.
            Aggressive trades have lower minimums.

        :param stop_pct: (float, default 0.05)
            Defaults a stop out at 5% decrease in asset price from purchase price.
            places limit orders near spread until the order is filled during stop out.

        :param interval: (int, default 2)
            Number of seconds to wait between order cycles.
            An order cycle is one loop during GdaxMarketMaker.run method.

        :param wall_size: (int, float, default None)
            The number of coins on a bid or ask that should be considered a "wall".
            None will calculate wall size measuring largest bids or asks on the book.

        :param spend_pct: (float, default 0.01)
            By default, 1% of available currency will be spent on each position.

        :param max_open_buys: (int, default 6)
            The maximum number of open buy orders to maintain spreads for.

        :param max_open_sells: (int, default 12)
            The maximum number of open sell orders to maintain spreads for.

        :param manage_existing_orders: (bool, default True)
            Allow management of existing open buy or sell orders... With no previous history
            The bot may decide to change prices/sell the positions for a loss.

        :param aggressive: (bool, default True)
            The aggressive parameter is used to determine how tight or loose to manage order prices.
            An aggressive bot trades more frequently for tighter spreads/margins.
        """
        if book_feed is None:
            book_feed = GdaxBookFeed(product_id=product_id,
                                     gdax=gdax,
                                     auth=True)
        if gdax is None:
            gdax = book_feed.gdax

        if product_id is None:
            product_id = book_feed.product_id

        self.book_feed = book_feed
        self.product_id = product_id
        self.gdax = gdax
        self.auth = True
        self._wall_size = wall_size
        self.interval = interval
        self._t_time = datetime.now()
        self.spend_pct = spend_pct
        self.max_spread = max_spread
        self.min_spread = min_spread
        self.stop_pct = stop_pct
        self.max_open_buys = max_open_buys
        self.max_open_sells = max_open_sells
        self.manage_existing_orders = manage_existing_orders
        self.aggressive = aggressive
        self.currency = product_id.split('-')[1]
        self._currency_balance = 0
        self._coin_balance = 0
        self._high_frequency = False

        self.stop = False
        self._book_snapshot = None
        self._last_ticker = dict()
        self._orders = dict()
        self._fills = dict()
        self._t_data = dict()
        self._tick_prices = dict()
        self._charts = dict()
        self._fill_queue = dict()

    def allow_high_frequency_trading(self):
        self._high_frequency = True

    def place_order(self, price=None, size=None, side='buy', order=None, op_order=None, adjust_vs_open=True,
                    adjust_vs_wall=True, check_size=True, check_ticker=True, aggressive=True):
        """
        Places new buy and sell orders.

        :param price: (float)
            The desired price to place the order on.
            This price may be altered depending on settings.

        :param size: (float)
            The desired quantity to buy or sell.
            This quantiy may be altered depending on settings.

        :param side: (str, ('buy', 'sell), default 'buy')
            buying or selling

        :param op_order: (GdaxMMOrder, default None)
            The opposite order (or previous canceled order)
            Gets registered to the GdaxMMOrder if not None.

        :param adjust_vs_open: (bool, default True)
            True sets price to GdaxMMOrder.get_price_adjusted_to_other_prices

        :param adjust_vs_wall: (bool, default True)
            -- IN PROGRESS --
            True adjusts buy orders to be just above the next bid wall
            False adjusts sell orders just beneath the next ask wall
        :param check_size: (bool, default True)
            True adjusts the size of buy orders to match GdaxMMOrder.position_size

        :param check_ticker: (bool, default
        :param aggressive:
        :return:
        """
        if order is not None:
            price = order.price
            size = order.size
            side = order.side

        if adjust_vs_wall:
            o_order = self.lowest_open_order
            if o_order is not None:
                o_price = o_order.price
                if side == 'buy':
                    pass
                # TODO: Finish this and adjust price against the wall

        # Adjust position size on buy orders
        # based on total value of account
        if check_size and side == 'buy':
            pos_size = self.position_size
            if pos_size <= 0.01:
                # allowed position size
                # is below minimum
                return None
            if size != pos_size:
                size = pos_size

        if order is None:
            order = GdaxMMOrder(self,
                                self.gdax,
                                self.product_id,
                                op_order=op_order,
                                order_type='limit',
                                side=side,
                                price=price,
                                size=size)
        else:
            if price:
                order.price = price
            if size:
                order.size = size


        if adjust_vs_open:
            open_price = order.get_price_adjusted_to_other_prices(
                step=self.min_spread, min_profit=self.min_spread, aggressive=aggressive
            )
            if open_price:
                order.price = open_price

        # Adjust price against ticker if needed
        # As we don't want a market order.
        if check_ticker:
            tick_price = order.get_price_adjusted_to_ticker(
                aggressive=aggressive)
            if tick_price:
                order.price = tick_price

        logger.debug("new: {} {} {} @ {}".format(
            side, size, self.product_id, price))

        order.post()

        assert order.id is not None
        self._orders[order.id] = order

        return order

    def ticker_changed(self, ticker_key, min_change=0.01):
        return tick_change_check(self.ticker_price,
                                 self._tick_prices,
                                 ticker_key,
                                 min_change=min_change)

    def get_chart(self, time_frame='5M'):
        """
        Access to GdaxChartData objects that are automatically created,
        cached, and/or refreshed on an interval.
        :param time_frame (str, default '5M')
            The timeframe interval of chart data to get.
            5M: 5 minutes
            15M: 15 minutes
            1H: 1 hour
            4H: 4 hours
            1D: daily
        :return: (stocklook.crypto.gdax.chartdata.GdaxChartData)
        """
        assert time_frame in self.TIME_FRAMES

        key = 'chart_data_{}'.format(time_frame)
        chart = self._charts.get(key, None)
        granularity, hours_back, seconds = self.TIMEFRAME_MAP[time_frame]
        timed_out = timeout_check(key,
                                  t_data=self._t_data,
                                  seconds=seconds)
        start = now_minus(hours=hours_back)
        end = now_plus(days=1)

        if chart is None:
            from stocklook.crypto.gdax.chartdata import GdaxChartData

            chart = GdaxChartData(
                self.gdax, self.product_id,
                start, end, granularity=granularity
            )
            chart.get_candles()

            self._charts[key] = chart
        elif timed_out:
            chart.start = start
            chart.end = end
            chart.get_candles()

        return chart

    @property
    def orders(self):
        """
        Public orders accessor calls open orders from API
        removing already filled orders before returning
        the dictionary of open buy and sell orders.
        :return: {GdaxMMOrder.id: GdaxMMOrder}
        """
        self.handle_fill_queue()
        if not self.ticker_changed('orders', min_change=0.01):
            return self._orders

        open_orders = self.gdax.get_orders(paginate=False)
        open_ids = [o['id'] for o in open_orders if o['status'] != 'done']
        existing_keys = list(self._orders.keys())

        for key in existing_keys:
            if key not in open_ids:
                self.handle_fill(key)

        if self.manage_existing_orders:
            # Cache any orders placed on the account.
            new_keys = [o['id'] for o in open_orders
                        if o['id'] not in existing_keys]
            for o_data in open_orders:
                if o_data['id'] not in new_keys:
                    continue
                o = GdaxMMOrder(self, self.gdax, self.product_id)
                o.update(data=o_data)
                self._orders[o.id] = o

        return self._orders

    @property
    def order_list(self):
        """
        Returns a list of open buy/sell orders
        Preferred method to get orders without
        calling the API.
        :return:
        """
        return list(self._orders.values())

    @property
    def buy_orders(self):
        """
        Returns dictionary of GdaxMMOrder.id: GdaxMMOrder
        on the buy side.
        :return:
        """
        return {o_id: o for o_id, o in self._orders.items()
                if o.side == 'buy'}

    @property
    def sell_orders(self):
        """
        Returns dictionary of GdaxMMOrder.id: GdaxMMOrder
        on the sell side.
        :return:
        """
        return {o_id: o for o_id, o in self._orders.items()
                if o.side == 'sell'}

    @property
    def wall_size(self):
        """
        Calculates bid/ask wall size if one wasn't provided on
        init.
        :return:
        """
        if self._wall_size is None or self._timeout():
            snap = self.get_book_snapshot()
            self._wall_size = snap.calculate_wall_size()
        return self._wall_size

    @property
    def lowest_open_order(self):
        if self._orders:
            orders = list(self._orders.values())
            return min(orders, key=lambda o: o.price)
        return None

    def _timeout(self):
        n = datetime.now()
        out = self._t_time + timedelta(seconds=5)
        if n > out:
            self._t_time = n
            return True
        return False

    @property
    def position_size(self):
        """
        Returns the position size that should be ordered
        taking into consideration
            - open sell orders v.s. GdaxMarketMaker.max_open_sells
            - open buy orders v.s GdaxMarketMaker.max_open_buys
            - currency balance.
        :return:
        """
        usd_acc = self.gdax.accounts[self.currency]
        snap = self.get_book_snapshot()
        balance = usd_acc.balance
        bid = float(snap.lowest_ask[0])
        spend_avail = balance * self.spend_pct
        size_avail = spend_avail / bid
        buy_orders = len(self.buy_orders)
        sells_open = len(self.sell_orders)
        if size_avail > 0.01 \
                and buy_orders < self.max_open_buys \
                and sells_open < self.max_open_sells:
            return size_avail
        return 0

    @property
    def position_spend(self):
        """
        Returns the amount of curency that should
        be spent on entering a new buy position based on
        GdaxMarketMaker.spend_pct value.
        :return:
        """
        usd_acc = self.gdax.accounts['USD']
        balance = usd_acc.balance
        spend_avail = balance * self.spend_pct
        return spend_avail

    def shift_orders(self, exclude=None):
        """
        Algorithm for shifting buy and sell orders up and down. Called once every
        interval and cancels/replaces many orders.

        Roughly follows these steps:
            - Compare buy and sell orders to ensure they aren't stacked on the same bid/asks
                - If stacked, shift the price down a fraction on bids, up a fraction on asks
            - Roughly evaluate MarketMaker.min_spread/max_spread on all positions
                - If a buy position is at a loss, do not sell
                  under MarketMaker.min_spread until MarketMaker.stop_pct has been reached.
                  Move sell order to min_spread at a minimum.
                - If a bid is too far under MarketMaker.max_spread - shift it up a few points
                  to encourage a taker to fill.

        Note: With tight stops or serious downward momentum i expect this algorithm to lose...
              we need bullish or choppy market conditions in order for this to stay profitable.
              I guess that should be a given with the commitment to market making...

        :param snap: (stocklook.crypto.gdax.feeds.boook_feed.BookSnapshot)
        :param exclude: (list, default None)
            A list of GdaxMMOrder.id to exclude.
        :return:
        """
        # TODO: Adjust spread based on market volatility/price action.
        orders = self.orders
        if not orders:
            return None

        exclude = ([] if not exclude else exclude)
        new_orders = list()

        p = self.ticker_price or 0
        tick_change = self.ticker_changed('shift_orders',
                                          min_change=self.min_spread/4)

        if not tick_change:
            return new_orders

        snap = self.get_book_snapshot()
        spread = (self.min_spread if self.aggressive else self.max_spread)

        for order_id, order in self._orders.copy().items():
            if order_id in exclude:
                logger.debug("Excluding {} order at price "
                             "{}".format(order.side, order.price))
                continue

            if order.locked:
                logger.debug("Ignoring locked {} order at price "
                             "{}".format(order.side, order.price))
                continue

            min_price = order.get_price_adjusted_to_spread(
                aggressive=True, min_profit=spread)
            max_price = order.get_price_adjusted_to_spread(
                aggressive=False, min_profit=spread)

            min_diff = round(order.price - min_price, 2)
            max_diff = round(max_price - order.price, 2)
            logger.debug("Evaluating {} order:\n"
                         "price {}\n"
                         "min {}\n"
                         "max {}\n"
                         "ticker {}\n"
                         "min diff {}\n"
                         "max diff {}".format(order.side, order.price, min_price,
                                              max_price, p, min_diff, max_diff))

            check_price = order.get_price_adjusted_to_other_prices(
                aggressive=self.aggressive, step=spread, )

            if order.side == 'buy':
                vol_2_price = snap.calculate_bid_depth(order.price)
                vol_2_cprice = snap.calculate_bid_depth(check_price)
                # min_diff = max buy
                # max_diff = min buy
                if max_diff > spread:
                    # go for minimum spread
                    if check_price > order.price:
                        self.cancel_order(order.id)
                        new_order = self.place_order(check_price,
                                                     order.size,
                                                     side=order.side,
                                                     op_order=order,
                                                     adjust_vs_open=True)
                        new_orders.append(new_order)

            elif order.side == 'sell':
                # First priority is checking stops
                stop = order.stop_amount
                stop_sell = round(p+(spread/2), 2)
                if stop and stop >= p and order.price > stop_sell:
                    logger.debug("shift_prices: order stopped. price: {}, "
                                 "stop: {}, ticker: {}".format(
                        order.price, stop, p))
                    self.cancel_order(order.id)
                    new_order = self.place_order(stop_sell,
                                                 order.size,
                                                 side=order.side,
                                                 op_order=order,
                                                 adjust_vs_open=False,
                                                 check_size=False)
                    new_orders.append(new_order)

                else:
                    vol_2_price = snap.calculate_ask_depth(order.price)
                    vol_2_cprice = snap.calculate_ask_depth(check_price)
                    if order.price > min_price:
                        # go for minimum spread
                        # first check against others
                        if order.price > check_price:
                            # clear for min spread
                            self.cancel_order(order.id)
                            new_order = self.place_order(check_price,
                                                         order.size,
                                                         side=order.side,
                                                         op_order=order,
                                                         adjust_vs_open=False)
                            new_orders.append(new_order)

        return new_orders

    def adjust_currency_balance(self, amount, side='buy', filled=False):
        if side == 'buy':
            self._currency_balance -= amount
        elif side == 'sell' and filled:
            self._currency_balance += amount

    def handle_fill(self, order_id, replace=True):
        """
        Handles a buy or sell order that has been filled.
        An opposite order can be placed immediately if replace is True.
        An unfilled order raises an AttributeError.
        A filled order is removed from GdaxMarketMaker.orders.

        :param order_id:
        :param replace:
        :return:
        """
        order = self._orders.pop(
            order_id, self._fill_queue.pop(order_id, None))

        if order is None:
            assert order_id in self._fills.keys()

        if not order.is_filled():
            if order.selling:
                self._fill_queue[order.id] = order
                logger.debug("Queueing delayed order "
                             "{}".format(order))
                return None
            raise Exception("Order {} is not "
                            "filled.".format(order))
        self._fills[order_id] = order

        # Log PNL if possible.
        pnl = getattr(order, 'pnl', None)
        if pnl is not None:
            logger.info("Closed two-sided {} order, pnl: "
                        "${}".format(self.product_id, round(pnl, 2)))

        # adjust currency balance
        o_amt = order.price * order.size
        if order.side == 'buy':
            self._currency_balance -= o_amt
        elif order.side == 'sell':
            self._currency_balance += o_amt

        # Place the opposite order immediately
        if replace:
            buy_orders = self.buy_orders
            sell_orders = self.sell_orders
            spread = (self.min_spread if self.aggressive
                      else self.max_spread)
            if order.buying:
                maxed = None
                new_side = 'sell'
                new_price = order.price + spread

            else:  # order selling
                maxed = (len(buy_orders) > self.max_open_buys or
                         len(sell_orders) > self.max_open_sells)
                new_side = 'buy'
                new_price = order.price - spread

            # priority 1: place target order
            targ_order = getattr(order, 'targ_order', None)
            if targ_order is not None:
                # We expect price to be adjusted here
                # if necessary, no other adjustments
                # allowed.
                targ_order.prepare_for_post()
                new_order = self.place_order(
                                 order=targ_order,
                                 op_order=order,
                                 adjust_vs_open=False,
                                 check_size=False,
                                 check_ticker=False,
                                 aggressive=self.aggressive)
                # price is irrelevant here as were expecting
                # the new target order price to be
                # adjusted just before placement.
                new_order.register_target_order(
                    price=new_price, lock=True, override=True)

            # priority 2: place opposite order if not maxed.
            elif not maxed:
                new_order = self.place_order(new_price,
                                             order.size,
                                             side=new_side,
                                             op_order=order,
                                             adjust_vs_open=True,
                                             check_size=True,
                                             check_ticker=True,
                                             aggressive=self.aggressive)

            # priority 3: do nothing, we're maxed without a target order.
            else:
                new_order = None
                logger.debug("Not replacing order {} as we're maxed.\n"
                             "Buys {}/{}\n"
                             "Sells {}/{}".format(
                    order_id, len(buy_orders), self.max_open_buys,
                    len(sell_orders), self.max_open_sells))
        else:
            new_order = None
        return new_order

    def handle_fill_queue(self):
        keys = list(self._fill_queue.keys())
        return [self.handle_fill(i) for i in keys]

    def handle_high_freq_orders(self):
        if not self._high_frequency:
            return False

        o_vals = list(self._orders.values())
        hf_orders = [o for o in o_vals
                     if o.target_type == o.HIGH_FREQ]
        hf_buys = [o for o in hf_orders if o.side == 'buy']
        hf_sells = [o for o in hf_orders if o.side == 'sell']

        try:
            first_o = [o for o in o_vals
                       if not o.locked][0]
        except IndexError:
            return False

        if len(hf_orders) < 2:
            pos = self.position_size
            if pos <= 0.01:
                pos = 0.8
            else:
                pos*= 3

            order = first_o.get_clone()
            order.side = 'buy'
            order.target_type = order.HIGH_FREQ
            order.min_profit = 0.05
            order.min_step = 0.05
            order.size = pos

            order.prepare_for_post()


            self.place_order(order=order,
                             adjust_vs_open=False,
                             adjust_vs_wall=False,
                             check_size=False,
                             check_ticker=False)

            # set the target order
            t_price = order.get_price_adjusted_to_wall_and_target_type(side='sell')
            order.register_target_order(price=t_price, lock=True, override=True )

        for o in hf_buys:
            check_p = o.get_price_adjusted_to_wall_and_target_type()
            if check_p - o.price > o.min_step*2:
                o.unlock()
                self.cancel_order(o.id)
                break

    def cancel_order(self, order_id):
        """
        Cancels an open buy or sell order. If the order has been filled
        it will be handled via GdaxMarketMaker.handle_fill.
        :param order_id:
        :return:
        """
        order = self._orders.pop(order_id, None)
        logger.debug("Cancelling order: {}".format(order))
        try:
            check = order.cancel()
            logger.debug("Order cancel return: {}".format(check))
            assert check[0] in (order_id, None)
        except (GdaxOrderCancellationError,
                AttributeError,
                AssertionError,
                KeyError) as e:
            logger.error("Error cancelling order '{}': {}\n"
                         "Order: {}".format(order_id, e, order))
            raise
        except OrderLockError:
            logger.error("Order {} is locked.".format(order.id))
            self._orders[order_id] = order

        except GdaxAPIError as e:
            if 'done' in str(e):
                self._orders[order_id] = order
                self.handle_fill(order_id, replace=True)
            elif 'not found' in str(e):
                pass
            else:
                raise

        return order

    def get_book_snapshot(self, refresh=False):
        """
        Returns a new BookSnapshot or refreshes the
        existing BookSnapshot on an interval.
        :return:
        """
        t_out = self.ticker_changed('get_book_snapshot')

        if self._book_snapshot is None:
            book = self.book_feed.get_current_book()
            book['bids'].reverse()
            self._book_snapshot = BookSnapshot(book, self.book_feed)

        elif t_out or refresh is True:
            self._book_snapshot.refresh()

        return self._book_snapshot

    def map_open_orders_to_fills(self):
        """
        Scans recent fills mapping them to buy orders. If a successful fill & buy order can be
        matched they'll be managed during order cycles, otherwise existing orders are ignored
        as long as GdaxMarketMaker.manage_existing_orders is False.
        :return:
        """
        fills = self.gdax.get_fills(product_id=self.product_id, paginate=False)
        open_orders = self.gdax.get_orders(status='open',
                                           paginate=False  #
                                           )
        existing_keys = [k for k, o in self._orders.items()
                         if o._op_order is not None and o.side == 'sell']
        added = list()

        for f in fills:
            f['price'] = round(float(f['price']), 2)
            f['fee'] = float(f['fee'])
            f['size'] = float(f['size'])

        for o_data in open_orders:
            if o_data['id'] in existing_keys:
                continue
            if o_data['side'] == 'buy':
                continue

            try:
                o = self._orders[o_data['id']]
            except KeyError:
                o = GdaxMMOrder(self, self.gdax, self.product_id)
                o.update(data=o_data)

            for f in fills:
                if f['side'] == 'sell':
                    continue
                if f['order_id'] in added:
                    continue
                if f['size'] == o.size:
                    op_order = GdaxMMOrder(self, self.gdax, self.product_id,
                                           size=f['size'],
                                           price=f['price'],
                                           id=f['order_id'],)
                    o.register_op_order(op_order)
                    self._orders[o.id] = o
                    added.append(o.id)
                    break

        if added:
            logger.debug("Mapped {} open orders to fills: "
                         "{}".format(len(added), added))

    @property
    def ticker_price(self):
        """
        Returns the current ticker price or None.
        """
        try:
            return float(self.book_feed.get_current_ticker()['price'])
        except TypeError:
            return None

    def run(self):
        """
        Main method runs in main thread managing the order book on a separate thread.
        does a refresh every GdaxMarketMaker.interval seconds evaluating open buy and
        sell orders against each other and the bids/asks.
        :return:
        """
        self.book_feed.start()
        sleep(10)

        while not self.stop:

            snap = self.get_book_snapshot()
            wall_size = self.wall_size
            bid = float(snap.lowest_ask[0])
            bids = snap.bids
            size_avail = self.position_size
            tick_price = self.ticker_price
            new_orders = list()
            tick_change = self.ticker_changed('run', min_change=0.01)

            if size_avail > 0.01 and bids and tick_change:
                spend_avail = size_avail * tick_price
                size_avail = spend_avail / bid
                logger.debug("Spend available: {}\n"
                             "Size Available: {}\n".format(
                    spend_avail, size_avail))

                bid_idx = None
                for idx, data in enumerate(snap.bids):
                    price, size, o_id = data
                    if size >= wall_size and idx >= 3:
                        bid_idx = idx-1
                        break

                if bid_idx:
                    b_price, b_size, b_id = bids[bid_idx]
                    while not b_price:
                        bid_idx += 1
                        try:
                            b_price, b_size, b_id = bids[bid_idx]
                        except IndexError:
                            continue

                    o = self.place_order(b_price,
                                         size_avail,
                                         side='buy',
                                         aggressive=False,
                                         adjust_vs_open=True,
                                         check_ticker=True)
                    new_orders.append(o.id)


                else:
                    logger.debug("No bid index found so no buy.")

                self.register_order_cycle()

            else:
                logger.debug("{} open buy orders\n"
                             "{} open sell orders\n"
                             "ticker ${}\n"
                             "allowed positiion size: {}".format(
                              len(self.buy_orders), len(self.sell_orders),
                              tick_price, size_avail))

            self.shift_orders(exclude=new_orders)
            self.handle_high_freq_orders()
            sleep(self.interval)

        self.book_feed.close()

    def close_open_buy_orders(self, raise_errs=True):
        """
        Cancels any open buy orders.
        :param raise_errs:
        :return:
        """
        for o_id, order in self.buy_orders.items():
            try:
                self.cancel_order(o_id)
            except Exception as e:
                logger.error("Error canceling buy order {}: "
                             "{}".format(o_id, e))
                if raise_errs:
                    raise

    def adjust_to_market_conditions(self):
        """
        analyze market conditions to change
        spreads/spend_pct/max_buys/etc.
        :return:
        """
        t_change = self.ticker_changed(
            'adjust_to_market_conditions', min_change=0.10)
        t = self.ticker_price
        if t is None or not t_change:
            return None

        # 5 minute candles
        c5 = self.get_chart(time_frame=self._5M)
        df5 = c5.df
        c5_r1 = df5.iloc[0]
        c5o, c5h, c5l, c5c = c5_r1['open'], c5_r1['high'], c5_r1['low'], c5_r1['close']
        avg_rsi5 = c5.avg_rsi
        avg_rng5 = c5.avg_range
        avg_vol5 = c5.avg_vol
        ibars5 = c5.get_inside_bars()

        # 15 minute candles
        c15 = self.get_chart(time_frame=self._15M)
        df15 = c15.df
        c15_r1 = df15.iloc[0]
        c15o, c15h, c15l, c15c = c15_r1['open'], c15_r1['high'], c15_r1['low'], c15_r1['close']
        avg_rsi15 = c15.avg_rsi
        avg_rng15 = c15.avg_range
        avg_vol15 = c15.avg_vol
        ibars15 = c15.get_inside_bars()

        # Hourly candles
        c1h = self.get_chart(time_frame=self._1H)
        df1h = c1h.df
        c1h_r1 = df1h.iloc[0]
        c1ho, c1hh, c1hl, c1hc = c1h_r1['open'], c1h_r1['high'], c1h_r1['low'], c1h_r1['close']
        avg_rsi1h = c1h.avg_rsi
        avg_rng1h = c1h.avg_range
        avg_vol1h = c1h.avg_vol
        ibars1h = c1h.get_inside_bars()

        # 4 hour candles
        c4h = self.get_chart(time_frame=self._4H)
        df4h = c4h.df
        c4h_r1 = df4h.iloc[0]
        c4ho, c4hh, c4hl, c4hc = c4h_r1['open'], c4h_r1['high'], c4h_r1['low'], c4h_r1['close']
        avg_rsi4h = c4h.avg_rsi
        avg_rng4h = c4h.avg_range
        avg_vol4h = c4h.avg_vol
        ibars4h = c4h.get_inside_bars()

        avg_rsi_avg = sum([avg_rsi5, avg_rsi1h, avg_rsi4h, avg_rsi15]) / 4
        avg_rng_avg = sum([avg_rng5, avg_rng1h, avg_rng4h, avg_rng15]) / 4
        avg_vol_avg = sum([avg_vol5, avg_vol1h, avg_vol4h, avg_vol15]) / 4
        avg_o = sum([c1ho, c4ho, c5o, c15o]) / 4
        avg_h = sum([c1hh, c4hh, c5h, c15h]) / 4
        avg_l = sum([c1hl, c4hl, c5l, c15l]) / 4
        avg_c = sum([c1hc, c4hc, c5c, c15c]) / 4
        ibars = [ibars5, ibars15, ibars1h, ibars4h]

        logger.debug("Averages:\n\n"
                     "5 Minute:\nrsi: {}\nrng: {}\nvol: {}\n\n"
                     "1 Hour:\nrsi: {}\nrng: {}\nvol: {}\n\n"
                     "4 Hour:\nrsi: {}\nrng: {}\nvol: {}\n\n"
                     "Median:\nrsi: {}\nrng: {}\nvol: {}\n\n".format(
                      avg_rsi5, avg_rng5, avg_vol5,
                      avg_rsi1h, avg_rng1h, avg_vol1h,
                      avg_rsi4h, avg_rng4h, avg_vol4h,
                      avg_rsi_avg, avg_rng_avg, avg_vol_avg,
        ))

        logger.debug("Prices:\n\n"
                     "5 Minute:\no: {}\nh: {}\nl: {}\nc: {}\n\n"
                     "1 Hour:\no: {}\nh: {}\nl: {}\nc: {}\n\n"
                     "4 Hour:\no: {}\nh: {}\nl: {}\nc: {}\n\n"
                     "Median:\no: {}\nh: {}\nl: {}\nc: {}".format(
                      c5o, c5h, c5l, c5c,
                      c1ho, c1hh, c1hl, c1hc,
                      c4ho, c4hh, c4hl, c4hc,
                      avg_o, avg_h, avg_l, avg_c
        ))

        for ibar in ibars:
            if not ibar:
                continue
            logger.debug(ibar)

    def register_order_cycle(self):
        """
        increments GdaxMMOrder.cycle_number.
        Called on every loop in
        GdaxMarketMaker.run.
        :return:
        """
        [o.register_order_cycle()
         for o in self._orders.values()]

    def __del__(self):
        """
        Not sure this works but its worth trying...
        If we get an error/shut down we should cancel buy orders since
        we'll no longer be able to manage them.
        :return:
        """
        self.close_open_buy_orders(raise_errs=False)


if __name__ == '__main__':
    PRODUCT_ID = 'ETH-USD'
    MAX_SPREAD = .50
    MIN_SPREAD = 0.20
    STOP_PCT = 0.05
    INTERVAL = 5
    SPEND_PERCENT = 0.005
    MAX_OPEN_BUYS = 10
    MAX_OPEN_SELLS = 27
    MANAGE_OUTSIDE_ORDERS = False

    m = GdaxMarketMaker(product_id=PRODUCT_ID,
                        gdax=Gdax(),
                        max_spread=MAX_SPREAD,
                        min_spread=MIN_SPREAD,
                        stop_pct=STOP_PCT,
                        interval=INTERVAL,
                        spend_pct=SPEND_PERCENT,
                        max_open_buys=MAX_OPEN_BUYS,
                        max_open_sells=MAX_OPEN_SELLS,
                        manage_existing_orders=MANAGE_OUTSIDE_ORDERS)

    m.map_open_orders_to_fills()
    m.allow_high_frequency_trading()
    m.run()


