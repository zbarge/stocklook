import logging
from .websocket_client import GdaxWebsocketClient
from collections import defaultdict, deque
from time import sleep

log = logging.getLogger(__name__)


class GdaxMemoryWebSocketClient(GdaxWebsocketClient):
    def __init__(self, max_size=5000*5000, **kwargs):
        kwargs['products'] = kwargs.get('products', ['ETH-USD', 'BTC-USD', 'LTC-USD', 'BCH-USD'])
        GdaxWebsocketClient.__init__(self, **kwargs)
        self._data = {p: deque(maxlen=max_size)
                      for p in self.products}
        self._types = ['match']
        self.max_size = max_size

    @property
    def data(self):
        return self._data

    def on_message(self, msg):
        _type, _id = None, None
        try:
            _type = msg['type']
            _id = msg['product_id']
        except KeyError as e:
            log.error("GdaxMemoryWebSocketClient.KeyError: {}".format(e))
        except AttributeError as e:
            log.error("GdaxMemoryWebSocketClient.AttributeError: {}".format(e))
        if _type not in self._types:
            return
        self._data[_id].appendleft(msg)

    def get_price(self, product, wait=True):
        try:
            return float(self._data[product][0]['price'])
        except IndexError:
            if wait:
                sleep(10)
                log.debug("Halting 5sec for {} price".format(product))
                return self.get_price(product, wait=False)
            raise



