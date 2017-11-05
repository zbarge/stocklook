import asyncio
import logging
from time import sleep
from datetime import datetime, timedelta
from stocklook.config import config
from stocklook.crypto.gdax.api import Gdax, GdaxAPIError
from stocklook.crypto.gdax.order import GdaxOrder, GdaxOrderCancellationError
from stocklook.crypto.gdax.feeds.book_feed import GdaxBookFeed, BookSnapshot

logger = logging.getLogger(__name__)
logger.setLevel(config.get('LOG_LEVEL', logging.DEBUG))


class GdaxMarketMaker:

    def __init__(self,
                 book_feed=None,
                 product_id=None,
                 gdax=None,
                 auth=True,
                 max_spread=0.10,
                 min_spread=0.05,
                 stop_pct=0.05,
                 interval=2,
                 wall_size=None,
                 spend_pct=0.01,
                 max_positions=6):
        if book_feed is None:
            book_feed = GdaxBookFeed(product_id=product_id,
                                     gdax=gdax,
                                     auth=auth)
        if gdax is None:
            gdax = book_feed.gdax

        if product_id is None:
            product_id = book_feed.product_id

        self.book_feed = book_feed
        self.product_id = product_id
        self.gdax = gdax
        self.auth = auth
        self._orders = dict()
        self._fills = dict()

        self.spend_pct = spend_pct
        self.max_spread = max_spread
        self.min_spread = min_spread
        self.stop_pct = stop_pct
        self.max_positions = max_positions
        self.stop = False
        self._book_snapshot = None
        self._wall_size = wall_size
        self.interval = interval
        self._t_time = datetime.now()
        self._last_ticker = dict()

    def place_order(self, price, size, side='buy', op_order=None, adjust_vs_open=True,
                    adjust_vs_wall=True, check_size=True, check_ticker=True):

        if adjust_vs_open:
            o_orders = [o for o in self._orders.values() if o.side == side]
            o_prices = [round(o.price, 2) for o in o_orders]

            if o_orders:
                if side == 'buy':

                    o_order = min(o_orders, key=lambda o: o.price)
                    o_price = o_order.price
                    if price >= o_price:
                        # Adjust buy price down to next lowest
                        # Price that doesnt already have an order
                        price = o_price
                        price -= (self.min_spread * .75)
                        price = round(price, 2)
                        while price in o_prices:
                            price -= (self.min_spread*.75)
                            price = round(price, 2)
                else:
                    o_order = max(o_orders, key=lambda o: o.price)
                    o_price = o_order.price
                    if price <= o_price:
                        # Adjust sell price up to next highest
                        # price that doesnt already have an order
                        price = o_price
                        price += (self.min_spread * .75)
                        price = round(price, 2)
                        while price in o_prices:
                            price += (self.min_spread*.75)
                            price = round(price, 2)

        if adjust_vs_wall:
            o_order = self.lowest_open_order
            if o_order is not None:
                o_price = o_order.price
                if side == 'buy':
                    pass
                # TODO: Finish this and adjust price against the wall

        # Adjust price against ticker if needed
        # As we don't want a market order.
        if check_ticker:
            ticker = self.book_feed.get_current_ticker()
            if ticker:
                ticker_price = float(ticker['price'])

                if side == 'buy':
                    if price > ticker_price:
                        price = ticker_price - self.min_spread
                elif side == 'sell':
                    if price < ticker_price:
                        price = ticker_price + self.min_spread
        if check_size and side == 'buy':
            pos_size = self.position_size
            if size > pos_size:
                size = pos_size
        order = GdaxOrder(self.gdax,
                          self.product_id,
                          order_type='limit',
                          side=side,
                          price=price,
                          size=size)
        logger.debug("new: {} {} {} @ {}".format(side, size, self.product_id, price))
        order.post()
        assert order.id is not None
        self._orders[order.id] = order


        if op_order is not None:
            order.__op_order = op_order
        return order

    @property
    def orders(self):
        open_orders = [o for o in self.gdax.get_orders(status='open',
                                                          paginate=False   #
                                                          )]
        open_ids = [o['id'] for o in open_orders]
        existing_keys = self._orders.keys()
        new_keys = [o['id'] for o in open_orders if o['id'] not in existing_keys]
        logger.debug("Open order ids: {}".format(open_ids))

        filled = [o_id for o_id in existing_keys
                  if o_id not in open_ids]
        [self.handle_fill(o) for o in filled]

        # Cache new orders placed on the account.
        for o_data in open_orders:
            if o_data['id'] not in new_keys:
                continue
            o = GdaxOrder(self.gdax, self.product_id)
            o.update(data=o_data)
            self._orders[o.id] = o

        return self._orders

    @property
    def wall_size(self):
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
        usd_acc = self.gdax.accounts['USD']
        snap = self.get_book_snapshot()
        balance = usd_acc.balance
        bid = float(snap.lowest_ask[0])
        spend_avail = balance * self.spend_pct
        size_avail = spend_avail / bid
        return size_avail

    @property
    def position_spend(self):
        usd_acc = self.gdax.accounts['USD']
        balance = usd_acc.balance
        spend_avail = balance * self.spend_pct
        return spend_avail

    def shift_orders(self, snap: BookSnapshot, exclude=None, spread=None):
        orders = self.orders
        if not orders:
            return None

        spread = (self.max_spread if not spread else spread)
        exclude = ([] if not exclude else exclude)
        cancels = list()

        bid = float(snap.highest_bid[0])
        ask = float(snap.lowest_ask[0])

        order_objs = list(sorted(orders.values(), key=lambda o: o.price, reverse=True))
        o_prices = [o.price for o in order_objs]
        logger.debug("Order prices: {}".format([o.price for o in order_objs]))
        last_buy = None
        last_sell = None

        # Prevent stacking bids
        # we want to keep a decent spread
        # between positions
        for o in order_objs:
            if o.id in exclude:
                continue
            if last_sell:
                last_sell = round(last_sell, 2)
            if last_buy:
                last_buy = round(last_buy, 2)
            o_price = round(o.price, 2)

            if o.side == 'buy':
                if last_buy is None:
                    last_buy = o_price

                elif last_buy == o_price:

                    new_price = round(last_buy - self.min_spread, 2)
                    while new_price in o_prices:
                        new_price -= self.min_spread
                    logger.debug("Shifting buy price from {} to "
                                 "{}".format(o_price, new_price))
                    self.cancel_order(o.id)
                    new_order = self.place_order(new_price,
                                                 o.size,
                                                 side=o.side,
                                                 adjust_vs_open=False,
                                                 op_order=getattr(o, '__op_order', None))
                    exclude.extend([o.id, new_order.id])
                    last_buy = new_order.price
                    o_prices.append(last_buy)
                else:
                    last_buy = o_price

            elif o.side == 'sell':
                if last_sell is None:
                    last_sell = o_price

                elif last_sell == o_price:
                    new_price = round(last_sell + self.min_spread, 2)
                    while new_price in o_prices:
                        new_price += (self.min_spread*0.25)
                        new_price = round(new_price, 2)

                    logger.debug("Shifting buy price from {} to "
                                 "{}".format(o_price, new_price))
                    self.cancel_order(o.id)
                    try:
                        new_order = self.place_order(new_price,
                                                     o.size,
                                                     side=o.side,
                                                     adjust_vs_open=False,
                                                     op_order=getattr(o, '__op_order', None))
                        exclude.extend([o.id, new_order.id])
                        last_sell = new_order.price
                        o_prices.append(last_sell)
                    except GdaxAPIError as e:
                        logger.debug("Error shifting order {}, {}".format(o, e))
                else:
                    last_sell = o_price

        ticker = self.book_feed.get_current_ticker()
        if ticker:
            p = float(ticker['price'])
        else:
            p = 0

        if not self._last_ticker and p > 0:
            self._last_ticker = p
        elif self._last_ticker == p:
            pass
            # dont do anything
        else:
            for order_id, order in orders.items():
                # Check if order needs a shift
                # keeping acceptable profit margin.
                if order_id in exclude:
                    continue
                price = order.price
                if order.side == 'buy':
                    allowed = ask - (self.max_spread*1.5)
                    if price < allowed:
                        logger.debug("Shifting buy order within range from "
                                     "{} to {}".format(price, allowed))
                        cancels.append((order.id, ask - self.max_spread))

                elif order.side == 'sell':

                    targ_price = bid + spread

                    if price > targ_price:
                        # Consider decreasing price
                        # Dont sell an order under min spread
                        # unless the position is stopped out

                        op_order = getattr(order, '__op_order', None)
                        if op_order is not None:
                            buy_price = op_order.price
                            stop_price = buy_price * (1-self.stop_pct)
                            min_price = buy_price + self.min_spread
                        else:
                            buy_price, stop_price = None, None
                            min_price = None

                        if stop_price and bid < stop_price:
                            # Allow targ_price as the position is stopped
                            pass
                        elif min_price and targ_price < min_price:
                            # Take min acceptable spread until stopped.
                            targ_price = min_price

                        cancels.append((order.id, targ_price))

        o_prices = [round(o.price,2) for o in self._orders.values()]
        new_orders = list()
        for o_id, price in cancels:
            order = self.cancel_order(o_id)
            price = round(price, 2)
            if order.side == 'buy':
                while price in o_prices:
                    price -= self.min_spread
                    price = round(price, 2)
            else:
                while price in o_prices:
                    price += self.min_spread
                    price = round(price, 2)
            new_order = self.place_order(price,
                                         order.size,
                                         side=order.side,
                                         op_order=getattr(order, '__op_order', None),
                                         adjust_vs_open=False)
            new_orders.append(new_order)
            o_prices.append(new_order.price)

        return new_orders

    @property
    def buy_orders(self):
        return {o_id: o for o_id, o in self._orders.items()
                if o.side == 'buy'}

    @property
    def sell_orders(self):
        return {o_id: o for o_id, o in self._orders.items()
                if o.side == 'sell'}

    def handle_fill(self, order_id, replace=True):
        order = self._orders.pop(order_id)
        if not order.is_filled():
            raise Exception("Order {} is not "
                            "filled.".format(order))
        self._fills[order_id] = order

        # Log PNL if possible.
        op_order = getattr(order, '__op_order', None)
        if op_order is not None:
            if op_order.side == 'buy':
                pnl = order.total_spend - op_order.total_spend
            else:
                pnl = op_order.total_spend - order.total_spend
            logger.info("Closed two-sided {} order, pnl: "
                        "${}".format(self.product_id, round(pnl, 2)))

        # Place the opposite order immediately
        if replace:
            if order.side == 'buy':
                maxed = None
                new_side = 'sell'
                new_price = order.price + self.max_spread
            else:
                maxed = len(self.buy_orders) > self.max_positions
                new_side = 'buy'
                new_price = order.price - self.max_spread

            if not maxed:
                new_order = self.place_order(new_price, order.size,
                                             side=new_side, op_order=order)
            else:
                new_order = None
                logger.debug("Not replacing order {} due "
                             "to maxed position size of {}".format(order_id, self.max_positions))
        else:
            new_order = None
        return new_order

    def cancel_order(self, order_id):
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
        except GdaxAPIError as e:
            if 'done' in str(e):
                self._orders[order_id] = order
                self.handle_fill(order_id, replace=True)
            elif 'not found' in str(e):
                pass
            else:
                raise

        return order

    def get_book_snapshot(self):
        if self._book_snapshot is None:
            book = self.book_feed.get_current_book()
            book['bids'].reverse()
            self._book_snapshot = BookSnapshot(book, self.book_feed)
        elif self._timeout():
            self._book_snapshot.refresh()
        return self._book_snapshot

    def run(self):
        self.book_feed.start()
        sleep(15)

        while not self.stop:
            usd_acc = self.gdax.accounts['USD']
            snap = self.get_book_snapshot()
            balance = usd_acc.balance
            wall_size = self.wall_size
            bid = float(snap.lowest_ask[0])
            spend_avail = balance * self.spend_pct
            size_avail = spend_avail / bid
            new_orders = list()
            orders_open = len(self.buy_orders)
            logger.debug("Spend available: {}\n"
                         "Size Available: {}\n".format(
                          spend_avail, size_avail))

            if size_avail > 0.01 and orders_open < self.max_positions:
                # We can place a spread order.
                bid_idx = None
                for idx, data in enumerate(snap.bids):
                    price, size, o_id = data
                    if size >= wall_size:
                        bid_idx = idx-1
                        break
                    else:
                        #logger.debug("Passing bid ${} & {}".format(price, size))
                        pass
                if bid_idx:
                    min_order = self.lowest_open_order
                    b_price, b_size, b_id = snap.bids[bid_idx]
                    if min_order is not None:
                        p = min_order.price
                        if p >= b_price:
                            b_price -= self.min_spread
                    if b_price < bid * .9:
                        b_price = bid - self.max_spread

                    o = self.place_order(b_price, size_avail, side='buy')
                    new_orders.append(o.id)
                else:
                    logger.debug("No bid index found so no buy.")
            else:
                logger.debug("{} open orders & {} funds available".format(orders_open, balance))

            self.shift_orders(snap, exclude=new_orders)
            sleep(self.interval)

        self.book_feed.close()


if __name__ == '__main__':
    MAX_SPREAD = .35
    MIN_SPREAD = 0.15
    STOP_PCT = 0.05
    INTERVAL = 10
    SPEND_PERCENT=0.02
    MAX_POSITIONS = 10

    g = Gdax()
    m = GdaxMarketMaker(product_id='ETH-USD', gdax=g,
                        max_spread=MAX_SPREAD,
                        min_spread=MIN_SPREAD,
                        stop_pct=STOP_PCT,
                        interval=INTERVAL,
                        spend_pct=SPEND_PERCENT,
                        max_positions=MAX_POSITIONS)
    m.run()

