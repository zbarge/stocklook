from .db_feed import GdaxDatabaseFeed
from .book_feed import GdaxBookFeed
from .websocket_client import GdaxWebsocketClient
from stocklook.utils.timetools import timestamp_to_local
from .db_loader import GdaxDatabaseLoader


class GdaxTickerFeed(GdaxDatabaseFeed):
    """
    {
        "type": "ticker",
        "trade_id": 20153558,
        "sequence": 3262786978,
        "time": "2017-09-02T17:05:49.250000Z",
        "product_id": "BTC-USD",
        "price": "4388.01000000",
        "side": "buy", // Taker side
        "last_size": "0.03000000",
        "best_bid": "4388",
        "best_ask": "4388.01"
    }
    """
    _dtypes = {'trade_id': int,
           'sequence': int,
           'time': timestamp_to_local,
           'price': float,
           'last_size': float,
           'best_bid': float,
           'best_ask': float}

    def __init__(self, **kwargs):
        from stocklook.crypto.gdax.tables import GdaxSQLTickerFeedEntry
        super(GdaxTickerFeed, self).__init__(GdaxSQLTickerFeedEntry, **kwargs)
        self.type = self.TICKER


class GdaxHeartbeatFeed(GdaxDatabaseFeed):
    """
    {
        "type": "heartbeat",
        "sequence": 90,
        "last_trade_id": 20,
        "product_id": "BTC-USD",
        "time": "2014-11-07T08:19:28.464459Z"
    }
    """
    _dtypes = {'sequence': int,
               'time': timestamp_to_local,
               'last_trade_id': int,}

    def __init__(self, **kwargs):
        from stocklook.crypto.gdax.tables import GdaxSQLHeartbeatFeedEntry
        super(GdaxTickerFeed, self).__init__(GdaxSQLHeartbeatFeedEntry, **kwargs)
        self.type = self.HEARTBEAT


class GdaxTradeFeed(GdaxDatabaseFeed):
    _dtypes = dict(time=timestamp_to_local,
                   remaining_size=float,
                   size=float,
                   sequence=int,
                   price=float)

    def __init__(self, **kwargs):
        """
        Subscribes to real-time trades logging them to a SQL database.

        :param gdax: (gdax.api.Gdax)
            The Gdax object

        :param gdax_db: (gdax.db.GdaxDatabase)
            Recommended to configure with a MySQL/Postgres backend rather than SQLite.
            SQLite databases can return Disk I/O errors pretty easily due to the speed
            of data being received over the web socket.

        :param products: (list)
            LTC-USD, BTC-USD, ETH-USD

        """
        from stocklook.crypto.gdax.tables import GdaxSQLFeedEntry
        super(GdaxTradeFeed, self).__init__(GdaxSQLFeedEntry, **kwargs)
