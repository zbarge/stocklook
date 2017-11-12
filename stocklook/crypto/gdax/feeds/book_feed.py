#
# gdax/order_book.py
# David Caseria
#
# Live order book updated from the gdax Websocket Feed
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
import pickle
from bintrees import RBTree
from stocklook.crypto.gdax.feeds.websocket_client import GdaxWebsocketClient


class BookSnapshot:
    """
    Wraps a dictionary outputted by BookFeed
    with helper methods to access bids/asks/walls/etc.
    """
    def __init__(self, book_dict, book_feed):
        self.book_dict = book_dict
        self.book_feed = book_feed

    @property
    def d(self):
        return self.book_dict

    @property
    def bids(self):
        """
        Returns a list of lists containing bid info
        price, qty, order_id
        :return:
        """
        bids = self.book_dict['bids']
        if not bids:
            self.refresh()
        return self.book_dict['bids']

    @property
    def highest_bid(self):
        return self.bids[0]

    @property
    def lowest_ask(self):
        return self.asks[0]

    @property
    def asks(self):
        asks = self.book_dict['asks']
        if not asks:
            self.refresh()
        return self.book_dict['asks']

    def calculate_wall_size(self, walls=None, min_size=20, within_percent=0.01, measure_size=7):
        if measure_size >0:
            measure_size = -measure_size

        if walls is None:
            bid_walls, sell_walls = self.get_walls(min_size, within_percent=within_percent)
            walls = bid_walls + sell_walls
        elif len(walls) == 2:
            walls = walls[0] + walls[1]

        wall_sort = sorted(walls, key=lambda x: x[1], reverse=True)[measure_size:]
        return sum([w[1] for w in wall_sort]) / len(wall_sort)

    def calculate_bid_depth(self, to_price):
        depth = 0

        for price, size, o_id in self.bids:
            if price < to_price:
                break
            depth += size

        return depth

    def calculate_ask_depth(self, to_price):
        depth = 0

        for price, size, o_id in self.asks:
            if price > to_price:
                break
            depth += size

        return depth

    def refresh(self):
        self.book_dict = self.book_feed.get_current_book()
        self.bids.reverse()

    def get_spread_wall(self, wall_qty=50):
        pass

    def get_walls(self, size, within_percent=0.01):
        return self.get_bid_walls(size, within_percent), \
               self.get_ask_walls(size, within_percent)

    def get_bid_walls(self, size, within_percent=0.01):
        bids = self.bids
        price = float(bids[0][0])
        price -= (price*within_percent)

        return [b for b in bids
                if b[0] >= price
                and b[1] >= size]

    def get_ask_walls(self, size, within_percent=0.01):
        asks = self.asks
        price = float(asks[0][0])
        price += (price * within_percent)

        return [a for a in asks
                if a[0] >=price
                and a[1] >= size]

    def get_spread(self):
        return self.asks[0] - self.bids[0]


class GdaxBookFeed(GdaxWebsocketClient):
    def __init__(self, product_id='LTC-USD', log_to=None, gdax=None, auth=True):

        if gdax is None:
            from stocklook.crypto.gdax.api import Gdax
            gdax = Gdax()

        super(GdaxBookFeed, self).__init__(products=product_id,
                                           auth=auth,
                                           api_key=gdax.api_key,
                                           api_secret=gdax.api_secret,
                                           api_passphrase=gdax.api_passphrase)
        self._asks = None
        self._bids = None
        self._client = gdax
        self._sequence = -1
        self._log_to = log_to
        if self._log_to:
            assert hasattr(self._log_to, 'write')
        self._current_ticker = None
        self._key_errs = 0
        self._errs = 0
        self.message_count = 0

    @property
    def product_id(self):
        '''
        Currently OrderBook only supports a single product even
        though it is stored as a list of products.
        '''
        return self.products[0]

    def on_message(self, message):
        self.message_count += 1
        if self._log_to:
            pickle.dump(message, self._log_to)

        try:
            sequence = message['sequence']
        except KeyError:
            print("Error: {}".format(message))
            self._key_errs += 1
            if self._key_errs >= 3:
                print("3 errors retrieving sequence. Restarting....")
                self.close()
                self._key_errs = 0
                self.start()
            return

        if self._sequence == -1:
            self._asks = RBTree()
            self._bids = RBTree()
            res = self._client.get_book(self.product_id, level=3)
            for bid in res['bids']:
                self.add({
                    'id': bid[2],
                    'side': 'buy',
                    'price': float(bid[0]),
                    'size': float(bid[1])
                })
            for ask in res['asks']:
                self.add({
                    'id': ask[2],
                    'side': 'sell',
                    'price': float(ask[0]),
                    'size': float(ask[1])
                })
            self._sequence = res['sequence']

        if sequence <= self._sequence:
            # ignore older messages (e.g. before order book
            # initialization from getProductOrderBook)
            return
        elif sequence > self._sequence + 1:
            print('Error: messages missing ({} - {}). '
                  'Re-initializing websocket.'.format(sequence, self._sequence))
            self.close()
            self.start()
            return

        msg_type = message['type']
        if msg_type == 'open':
            self.add(message)
        elif msg_type == 'done' and 'price' in message:
            self.remove(message)
        elif msg_type == 'match':
            self.match(message)
            self._current_ticker = message
        elif msg_type == 'change':
            self.change(message)

        self._sequence = sequence

        # bid = self.get_bid()
        # bids = self.get_bids(bid)
        # bid_depth = sum([b['size'] for b in bids])
        # ask = self.get_ask()
        # asks = self.get_asks(ask)
        # ask_depth = sum([a['size'] for a in asks])
        # print('bid: %f @ %f - ask: %f @ %f' % (bid_depth, bid, ask_depth, ask))

    def on_error(self, e):
        self._sequence = -1
        self._errs += 1
        self.close()
        if self._errs >= 3:
            raise Exception(e)
        self.start()

    def add(self, order):
        order = {
            'id': order.get('order_id') or order['id'],
            'side': order['side'],
            'price': float(order['price']),
            'size': float(order.get('size') or order['remaining_size'])
        }
        if order['side'] == 'buy':
            bids = self.get_bids(order['price'])
            if bids is None:
                bids = [order]
            else:
                bids.append(order)
            self.set_bids(order['price'], bids)
        else:
            asks = self.get_asks(order['price'])
            if asks is None:
                asks = [order]
            else:
                asks.append(order)
            self.set_asks(order['price'], asks)

    def remove(self, order):
        price = float(order['price'])
        if order['side'] == 'buy':
            bids = self.get_bids(price)
            if bids is not None:
                bids = [o for o in bids if o['id'] != order['order_id']]
                if len(bids) > 0:
                    self.set_bids(price, bids)
                else:
                    self.remove_bids(price)
        else:
            asks = self.get_asks(price)
            if asks is not None:
                asks = [o for o in asks if o['id'] != order['order_id']]
                if len(asks) > 0:
                    self.set_asks(price, asks)
                else:
                    self.remove_asks(price)

    def match(self, order):
        size = float(order['size'])
        price = float(order['price'])

        if order['side'] == 'buy':
            bids = self.get_bids(price)
            if not bids:
                return
            assert bids[0]['id'] == order['maker_order_id']
            if bids[0]['size'] == size:
                self.set_bids(price, bids[1:])
            else:
                bids[0]['size'] -= size
                self.set_bids(price, bids)
        else:
            asks = self.get_asks(price)
            if not asks:
                return
            assert asks[0]['id'] == order['maker_order_id']
            if asks[0]['size'] == size:
                self.set_asks(price, asks[1:])
            else:
                asks[0]['size'] -= size
                self.set_asks(price, asks)

    def change(self, order):
        try:
            new_size = float(order['new_size'])
        except KeyError:
            return

        price = float(order['price'])

        if order['side'] == 'buy':
            bids = self.get_bids(price)
            if bids is None or not any(o['id'] == order['order_id'] for o in bids):
                return
            index = [b['id'] for b in bids].index(order['order_id'])
            bids[index]['size'] = new_size
            self.set_bids(price, bids)
        else:
            asks = self.get_asks(price)
            if asks is None or not any(o['id'] == order['order_id'] for o in asks):
                return
            index = [a['id'] for a in asks].index(order['order_id'])
            asks[index]['size'] = new_size
            self.set_asks(price, asks)

        tree = self._asks if order['side'] == 'sell' else self._bids
        node = tree.get(price)

        if node is None or not any(o['id'] == order['order_id'] for o in node):
            return

    def get_current_ticker(self):
        return self._current_ticker

    def get_current_book(self):
        result = {
            'sequence': self._sequence,
            'asks': [],
            'bids': [],
        }
        for ask in self._asks:
            try:
                # There can be a race condition here,
                # where a price point is removed
                # between these two ops.
                this_ask = self._asks[ask]
            except KeyError:
                continue
            for order in this_ask:
                bit = [order['price'],
                       order['size'],
                       order['id']]
                result['asks'].append(bit)
        for bid in self._bids:
            try:
                # There can be a race condition here,
                # where a price point is removed
                # between these two ops.
                this_bid = self._bids[bid]
            except KeyError:
                continue

            for order in this_bid:
                result['bids'].append([order['price'], order['size'], order['id']])
        return result

    def get_orders_matching_ids(self, order_ids):
        return [a for a in self._asks
                if a['id'] in order_ids] +\
               [b for b in self._bids
                if b['id'] in order_ids
        ]

    def get_ask(self):
        return self._asks.min_key()

    def get_asks(self, price):
        return self._asks.get(price)

    def remove_asks(self, price):
        self._asks.remove(price)

    def set_asks(self, price, asks):
        self._asks.insert(price, asks)

    def get_bid(self):
        return self._bids.max_key()

    def get_bids(self, price):
        return self._bids.get(price)

    def remove_bids(self, price):
        self._bids.remove(price)

    def set_bids(self, price, bids):
        self._bids.insert(price, bids)


if __name__ == '__main__':
    import time
    import datetime as dt


    class OrderBookConsole(GdaxBookFeed):
        ''' Logs real-time changes to the bid-ask spread to the console '''

        def __init__(self, product_id=None):
            super(OrderBookConsole, self).__init__(product_id=product_id)

            # latest values of bid-ask spread
            self._bid = None
            self._ask = None
            self._bid_depth = None
            self._ask_depth = None

        def on_message(self, message):
            super(OrderBookConsole, self).on_message(message)

            # Calculate newest bid-ask spread
            bid = self.get_bid()
            bids = self.get_bids(bid)
            bid_depth = sum([b['size'] for b in bids])
            ask = self.get_ask()
            asks = self.get_asks(ask)
            ask_depth = sum([a['size'] for a in asks])

            if self._bid == bid \
                    and self._ask == ask \
                    and self._bid_depth == bid_depth \
                    and self._ask_depth == ask_depth:
                # If there are no changes to the bid-ask spread
                # since the last update, no need to print
                pass
            else:
                # If there are differences, update the cache
                self._bid = bid
                self._ask = ask
                self._bid_depth = bid_depth
                self._ask_depth = ask_depth
                print('{}\tbid: {:.3f} @ {:.2f}\t'
                      'ask: {:.3f} @ {:.2f}'.format(dt.datetime.now(),
                                                    bid_depth,
                                                    bid,
                                                    ask_depth,
                                                    ask))


    order_book = OrderBookConsole(product_id='LTC-USD')
    order_book.start()