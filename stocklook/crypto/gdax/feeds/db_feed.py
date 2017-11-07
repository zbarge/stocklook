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
from time import sleep
from stocklook.utils.timetools import now_minus
from stocklook.crypto.gdax.feeds.db_loader import GdaxDatabaseLoader
from stocklook.crypto.gdax.feeds.websocket_client import GdaxWebsocketClient
from stocklook.crypto.gdax.tables import GDAX_FEED_CLASS_MAP
from queue import Queue


def get_default_gdax_feed_database(gdax=None):
    """
    This was relevant until GdaxDatabase
    got configured to look for GDAX_URL_FEED_KWARGS
    first and use that database for all transactions if
    available. sqlite is a last resort.
    """
    from stocklook.crypto.gdax import GdaxDatabase
    return GdaxDatabase(gdax=gdax)


class GdaxDatabaseFeed(GdaxWebsocketClient):
    """
    https://docs.gdax.com/#websocket-feed
    Adds a threaded database layer to the GdaxWebsocketClient.
    Simultaneously supports subscriptions (say that 3 times fast) to multiple
    channels (and products) of the Gdax websocket feed service.

    A localhost MySQL database can handle subscriptions to the full and ticker feeds
    for ETH-USD, BTC-USD, LTC-USD (millions of records daily) without bottle necks.
    SQLite...probably not.


    Recommended Channels
    ------------------
    1) heartbeat
    2) full
    3) ticker


    Thread Workflow
    ---------------
    Thread 1: Receive JSON messages from subscribed channels and identify them.
    Thread 1: Spawn/store up to 1 thread(GdaxDatabaseFeed) for each message type
    Thread 1: Insert the message into the appropriate GdaxDatabaseFeed.queue
    Thread 2, 3, 4: Retrieve messages from Queue, parse data types,
    Thread 2, 3, 4: Insert data into database and commit changes.


    Thread Shutdown Process
    -----------------------
    1) Stop Thread 1
    2) Insert GdaxDatabaseFeed.STOP_SIGNAL value into queues.
    3) Join queues - database sessions are committed and closed.
    4) Join Threads 2, 3, 4 - ensuring all have completed their work.
    5) Close down the websocket connection


    Once these processes are complete - it starts over again.
    Crypto never sleeps.
    """
    _dtypes = dict()
    _class_map = GDAX_FEED_CLASS_MAP

    def __init__(self, gdax=None, gdax_db=None, products=None, channels=None):
        """

        :param gdax: (gdax.api.Gdax)
            The Gdax API object.
            None will attempt to create a default Gdax object.
            If an error happens it will continue without authentication.

        :param gdax_db: (gdax.db.GdaxDatabase)
            Recommended to configure with a MySQL/Postgres backend rather than SQLite.
            SQLite databases can return Disk I/O errors pretty easily due to the speed
            of data being received over the web socket.

        :param products: (list, default  ['LTC-USD', 'BTC-USD', 'ETH-USD'])
            A list of currency pairs to subscribe to.

        :param channels (list, default ['ticker', 'full'])
            A list of websocket channels to subscribe to.
        """

        if products is None:
            products = ['LTC-USD', 'BTC-USD', 'ETH-USD']

        if channels is None:
            channels = ['ticker', 'full']

        if gdax is None:
            # Try to authenticate using Gdax
            try:
                from stocklook.crypto.gdax import Gdax
                gdax = Gdax()
                key = gdax.api_key
                secret = gdax.api_secret
                phrase = gdax.api_passphrase
                auth = False # figure out why auth is broke
            except Exception as e:
                print("Ignored error configuring "
                      "default Gdax object. "
                      "Using public API.\n{}".format(e))
                key, secret, phrase = None, None, None
                auth = False

        super(GdaxDatabaseFeed, self).__init__(products=products,
                                               api_key=key,
                                               api_secret=secret,
                                               api_passphrase=phrase,
                                               channels=channels,
                                               auth=auth)
        self.session = None
        self.db = gdax_db
        self.gdax = gdax
        self.url = "wss://ws-feed.gdax.com/"

        self.queues = dict()
        self._loaders = dict()

    def on_open(self):
        """
        Ensures GdaxDatabase and session objects are ready.

        :return:
        """

        if self.db is None:
            self.db = get_default_gdax_feed_database(self.gdax)

    @property
    def loaders(self):
        """
        A dictionary containing GdaxDatabaseLoader
        objects with keys to the channel.
        :return:
        """
        return self._loaders

    def get_loader(self, channel):
        """
        Retrieves a GdaxDatabaseLoader from
        the GdaxDatabaseFeed._loader dictionary using
        the channel value as a key. If a loader is not found,
        a queue and loader will be initialized, cached, and returned.

        :param channel: (str)
            Channel name must exist in the GdaxDatabaseFeed._class_map
            keys and have a SQLAlchemy table class associated to it.

        :raises KeyError:
            When a channel doesn't exist in the GdaxDatabaseFeed._class_map

        :raises AttributeError:
            When something that is not a  SQLAlchemy table object is stored
            in the GdaxDatabaseFeed._class_map. Because the GdaxDatabaseLoader
            will parse the SQLAlchemy table for python data types to use when
            parsing messages from the queue.

        :return:
        """


        try:
            loader = self._loaders[channel]
        except KeyError:

            try:
                q = self.queues[channel]
            except KeyError:
                q = Queue()
                self.queues[channel] = q

            cls = self._class_map[channel]
            maker = self.db._session_maker

            if channel == self.TICKER:
                c = 5

            elif channel == self.SUBSCRIBE:
                c = 1000

            else:
                c = 20

            loader = GdaxDatabaseLoader(maker, q, cls,
                                        raise_on_error=True,
                                        commit_interval=c)
            self._loaders[channel] = loader
            loader.start()

        return loader

    def stop_loaders(self):
        """
        puts a stop signal in each loader's Queue.
        joins each queue, blocking new items.
        joins each loader (thread).
        Halting all database update operations.
        :return:
        """
        loaders = self._loaders.values()

        for loader in loaders:
            loader.queue.put(loader.STOP_SIGNAL)

        for loader in loaders:
            loader.queue.join()

        for loader in loaders:
            loader.join()

    def on_message(self, msg):
        """
        Parses msg['type'] and places the message
        in the appropriate GdaxDatabaseLoader.queue. The message
        will be processed as soon as the loader can allowing the next
        message to be received and placed in the appropriate queue without
        delay.

        :param msg:
        :return:
        """
        msg_type = msg['type']

        if msg_type in self.SUBSCRIBE_TYPES:
            msg_type = self.SUBSCRIBE

        elif msg_type == 'subscriptions':
            return print(msg)

        try:
            loader = self.get_loader(msg_type)
            loader.queue.put(msg)
        except KeyError as e:
            print("Error('{}') retrieving loader for "
                  "message type: {} - {}".format(e, msg_type, msg))

    def on_close(self):
        """
        Attempts to commit and close the session to the database.
        :return:
        """
        try:
            self.stop_loaders()
        except Exception as e:
            print("Session commit/close error: {}".format(e))
            pass

    def on_error(self, e):
        """
        Attempts to restart the feed when an error occurs.
        :param e:
        :return:
        """

        print("Initial Error: {}\n Cause: {}\nContext: {}\n"
              "- attempting to recover.".format(e, e.__cause__, e.__context__))

        try:
            self.close()
        except Exception as e:
            print("Ignored closing error: {}".format(e))
            pass

        sleep(0.5)

        self.start()
