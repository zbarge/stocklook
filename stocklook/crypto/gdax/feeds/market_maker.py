import asyncio
import logging
from time import sleep
from datetime import datetime, timedelta
from stocklook.config import config
from stocklook.crypto.gdax.api import Gdax
from stocklook.crypto.gdax.order import GdaxOrder, GdaxOrderCancellationError
from stocklook.crypto.gdax.feeds.book_feed import GdaxBookFeed, BookSnapshot

logger = logging.getLogger(__name__)
logger.setLevel(config.get('LOG_LEVEL', logging.DEBUG))


class GdaxMarketMaker:

    def __init__(self, book_feed=None, product_id=None,
                 gdax=None, auth=True,
                 max_spread=0.10, min_spread=0.05,
                 stop_pct=0.05, interval=2,
                 wall_size=None, spend_pct=0.01):
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
        self.stop = False
        self._book_snapshot = None
        self._wall_size = wall_size
        self.interval = interval
        self._t_time = datetime.now()

    def place_order(self, price, size, side='buy', adjust_vs_open=True, adjust_vs_wall=True):

        if adjust_vs_open:
            o_order = self.lowest_open_order
            if o_order is not None:
                o_price = o_order.price
                if side == 'buy':
                    if price >= o_price:
                        price -= (self.min_spread*.25)
                else:
                    if price <= o_price:
                        price += (self.min_spread*.25)
        if adjust_vs_wall:
            o_order = self.lowest_open_order
            if o_order is not None:
                o_price = o_order.price
                if side == 'buy':
                    pass
                # TODO: Finish this and adjust price against the wall



        order = GdaxOrder(self.gdax,
                          self.product_id,
                          order_type='limit',
                          side=side,
                          price=price,
                          size=size)
        order.post()
        assert order.id is not None
        self._orders[order.id] = order
        logger.debug("new: {} {} {} @ {}".format(side, size, self.product_id, price))
        return order

    @property
    def orders(self):
        filled = list()
        updates = self.gdax.get_orders(status='open')
        open_ids = [o['id'] for o in updates]
        logger.debug("Open order ids: {}".format(open_ids))
        for o_id, order in self._orders.items():
            if o_id not in open_ids:
                order.update()
            if order.is_filled(update=False):
                filled.append(o_id)
        # Handle fills like this because
        # The order is going to be popped off
        # MarketMaker._orders
        [self.handle_fill(o) for o in filled]

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
        out = self._t_time + timedelta(seconds=10)
        if n > out:
            self._t_time = n
            return True
        return False

    def shift_orders(self, snap: BookSnapshot, exclude=None, spread=None):
        orders = self.orders
        if not orders:
            return None

        spread = (self.max_spread if not spread else spread)
        exclude = ([] if not exclude else exclude)
        cancels = list()

        bid = float(snap.highest_bid[0])
        ask = float(snap.lowest_ask[0])

        for order_id, order in orders.items():
            # Check if order needs a shift
            # keeping acceptable profit margin.
            if order_id in exclude:
                continue
            price = order.price
            if order.side == 'buy':
                allowed = ask - (spread * 1.2)
                if price < allowed:
                    cancels.append((order.id, allowed))

            else:
                allowed = bid + (spread * 1.2)
                if price > allowed:
                    cancels.append((order.id, allowed))

        for o_id, price in cancels:
            order = self.cancel_order(o_id)
            self.place_order(price, order.size, side=order.side)

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
                new_side = 'sell'
                new_price = order.price + self.max_spread
            else:
                new_side = 'buy'
                new_price = order.price - self.max_spread

            new_order = self.place_order(new_price, order.size, side=new_side)
            new_order.__op_order = order
        else:
            new_order = None
        return new_order

    def cancel_order(self, order_id):
        order = self._orders.pop(order_id, None)
        logger.debug("Cancelling order: {}".format(order))
        try:
            check = order.cancel()
            assert check['id'] == order_id
        except (GdaxOrderCancellationError,
                AttributeError,
                AssertionError,
                KeyError) as e:
            logger.error("Error cancelling order '{}': {}\n"
                         "Order: {}".format(order_id, e, order))
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
            orders_open = len(self._orders)
            logger.debug("Spend available: {}\n"
                         "Size Available: {}\n".format(
                          spend_avail, size_avail))

            if size_avail > 0.01 and orders_open < 5:
                # We can place a spread order.
                bid_idx = None
                for idx, data in enumerate(snap.bids):
                    price, size, o_id = data
                    if size >= wall_size:
                        bid_idx = idx-1
                        break
                    else:
                        logger.debug("Passing bid ${} & {}".format(price, size))

                if bid_idx:
                    min_order = self.lowest_open_order
                    b_price, b_size, b_id = snap.bids[bid_idx]
                    if min_order is not None:
                        p = min_order.price
                        if p >= b_price:
                            b_price -= self.min_spread

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
    MAX_SPREAD = .45
    MIN_SPREAD = 0.15
    STOP_PCT = 0.05
    INTERVAL = 5
    SPEND_PERCENT=0.0075

    g = Gdax()
    m = GdaxMarketMaker(product_id='ETH-USD', gdax=g,
                        max_spread=MAX_SPREAD,
                        min_spread=MIN_SPREAD,
                        stop_pct=STOP_PCT,
                        interval=INTERVAL,
                        spend_pct=SPEND_PERCENT)
    m.run()

