#
# gdax/GdaxWebsocketClient.py
# Daniel Paquin
#
# Template object to receive messages from the gdax Websocket Feed
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
from time import sleep, time
import json, base64, hmac, hashlib
from websocket import create_connection, WebSocketConnectionClosedException

# Channel types supported by GdaxWebsocketClient
HEARTBEAT = 'heartbeat'
TICKER = 'ticker'
LEVEL2 = 'level2'
USER = 'user'
MATCHES = 'matches'
FULL = 'full'



class GdaxWebsocketClient:
    HEARTBEAT = HEARTBEAT
    TICKER = TICKER
    FULL = FULL
    LEVEL2 = LEVEL2
    USER = USER
    MATCHES = MATCHES
    SUBSCRIBE = 'subscribe'
    CHANNELS = [HEARTBEAT, TICKER, FULL, LEVEL2, USER, MATCHES, SUBSCRIBE]
    SUBSCRIBE_TYPES = ['done', 'received', 'open', 'match']

    def __init__(self,
                 url="wss://ws-feed.gdax.com",
                 products=None,
                 message_type="subscribe",
                 auth=False,
                 api_key="",
                 api_secret="",
                 api_passphrase="",
                 channels=None,
                 ):

        if products is None:
            products = ['LTC-USD']
        elif hasattr(products, 'title'):
            products = [products]

        self.url = url
        self.products = products
        self.type = message_type
        self.channels = channels
        self.stop = False
        self.ws = None
        self.thread = None
        self.auth = auth
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase
        self.message_count = 0

    def start(self):
        self.stop = False
        if self.url[-1] == "/":
            self.url = self.url[:-1]

        def _go():
            self._connect()
            self._listen()

        self.on_open()
        self.ws = create_connection(self.url)
        self.thread = Thread(target=_go)
        self.thread.start()

    def _connect(self):

        sub_params = {'type': 'subscribe'}

        if self.channels:
            sub_params.update(dict(product_ids=self.products,
                                   channels=self.channels))

        elif self.type in [self.SUBSCRIBE, self.HEARTBEAT]:
            sub_params['product_ids'] = self.products

        else:
            sub_params['channels'] = [{'name': self.type,
                                       'product_ids': self.products}]

        if self.auth:
            timestamp = str(time())
            message = timestamp + 'GET' + '/users/self'
            hmac_key = base64.b64decode(self.api_secret)
            signature = hmac.new(hmac_key, bytes(str(message).encode('utf8')), hashlib.sha256)
            signature_b64 = base64.standard_b64encode(signature.digest())
            sub_params['signature'] = signature_b64.decode('utf8')
            sub_params['key'] = self.api_key
            sub_params['passphrase'] = self.api_passphrase
            sub_params['timestamp'] = timestamp

        self.ws = create_connection(self.url)
        self.ws.send(json.dumps(sub_params))

        if self.type == HEARTBEAT:
            sub_params = {"type": HEARTBEAT, "on": True}
            self.ws.send(json.dumps(sub_params))

    def _listen(self):
        decode_errs = 0

        while not self.stop:

            try:

                if int(time() % 30) == 0:
                    # Set a 30 second ping to keep connection alive
                    self.ws.ping("keepalive")

                if self.ws is None:
                    self._connect()

                res = self.ws.recv()
                msg = json.loads(res)
                decode_errs = 0

            except json.JSONDecodeError as e:
                # JSONDecodeErrors seem to occur every ~200K messages
                # We will fail it once we reach 3.
                print("Ignored decode error: {}"
                      " - trying again.".format(e))
                decode_errs += 1

                if decode_errs % 3 == 0:
                    decode_errs = 0
                    print("3 JSON decode errors in a "
                          "row = fail: {}".format(res))
                    self.on_error(e)

                continue

            except WebSocketConnectionClosedException:
                print("Websocket closed on us..."
                      "trying to re-open")
                sleep(2)
                self._connect()

            except Exception as e:
                self.on_error(e)

            else:
                self.message_count += 1
                self.on_message(msg)

    def close(self):
        if not self.stop:
            if self.type == HEARTBEAT:
                msg = {"type": HEARTBEAT, "on": False}
                msg_json = json.dumps(msg)
                self.ws.send(msg_json)

            self.on_close()
            self.stop = True

            sleep(1)

            try:

                self.thread.join(2)

            except Exception as e:
                print("Ignored error closing thread: {}({})".format(e, type(e)))

            try:

                if self.ws:
                    self.ws.close()

            except WebSocketConnectionClosedException as e:
                print("Ignored error closing WebSocket: {}".format(e))

            self.ws = None
            self.thread = None

    def on_open(self):
        print("-- Subscribed! --\n")

    def on_close(self):
        print("\n-- Socket Closed --")

    def on_message(self, msg):
        print(msg)

    def on_error(self, e):
        """
        Attempts to restart the feed when an error occurs.
        :param e:
        :return:
        """
        print("Initial Error: {} - attempting to recover.".format(e))
        sleep(1)

        try:
            self.close()
        except Exception as e:
            print("Closing error: {}".format(e))
            pass

        sleep(1)

        self.start()


