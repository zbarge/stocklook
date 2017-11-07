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
from sqlalchemy import (String, Boolean, DateTime, Float,
                        Integer, BigInteger, Column, ForeignKey, Table, Enum,
                        UniqueConstraint, TIMESTAMP)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

GdaxBase = declarative_base()


class GdaxSQLProduct(GdaxBase):
    __tablename__ = 'gdax_stocks'
    stock_id = Column(Integer, primary_key=True)
    name = Column(String(20))
    currency = Column(String(20))
    quotes = relationship('GdaxSQLQuote', back_populates='stock')
    date_added = Column(DateTime, default=datetime.now)


class GdaxSQLQuote(GdaxBase):
    __tablename__ = 'gdax_quotes'

    quote_id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('gdax_stocks.stock_id'))
    stock = relationship('GdaxSQLProduct')
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    quote_date = Column(String(50))
    date_added = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return 'GdaxSQLQuote(open={}, high={}, low={}, ' \
               'close={}, volume={}, ' \
               'quote_date={}'.format(self.open,
                                      self.high,
                                      self.low,
                                      self.close,
                                      self.volume,
                                      self.quote_date)


class GdaxOHLC5(GdaxBase):
    __tablename__ = 'gdax_ohlc5'

    ohlc_id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('gdax_stocks.stock_id'))
    stock = relationship('GdaxSQLProduct')
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    time = Column(Integer)

    __table_args__ = (UniqueConstraint('stock_id', 'time', name='_stock_id_time_unique'),
                      )
    def __repr__(self):
        return 'GdaxSQLQuote(open={}, high={}, low={}, ' \
               'close={}, volume={}, ' \
               'quote_date={}'.format(self.open,
                                      self.high,
                                      self.low,
                                      self.close,
                                      self.volume)


class GdaxSQLOrder(GdaxBase):
    """
        {
        "id": "d0c5340b-6d6c-49d9-b567-48c4bfca13d2",
        "price": "0.10000000",
        "size": "0.01000000",
        "product_id": "BTC-USD",
        "side": "buy",
        "stp": "dc",
        "type": "limit",
        "time_in_force": "GTC",
        "post_only": false,
        "created_at": "2016-12-08T20:02:28.53864Z",
        "fill_fees": "0.0000000000000000",
        "filled_size": "0.00000000",
        "executed_value": "0.0000000000000000",
        "status": "pending",
        "settled": false
    }
    """
    __tablename__ = 'gdax_orders'

    order_id = Column(Integer, primary_key=True)
    id = Column(String(100))
    price = Column(Float)
    size = Column(Float)
    side = Column(String(10))
    stp = Column(String(10))
    type = Column(String(10))
    time_in_force = Column(String(10))
    post_only = Column(String(10))
    created_at = Column(DateTime)
    fill_fees = Column(Float)
    filled_size = Column(Float)
    executed_value = Column(Float)
    status = Column(String(30))
    settled = Column(String(10))

    fake = Column(Boolean, default=False)
    date_added = Column(DateTime, default=datetime.now)
    date_updated = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return "GdaxOrder(order_id={}, price={}, size={}, " \
               "created_at={}, filled_size={}, " \
               "status={}, settled={})".format(self.order_id, self.price, self.size,
                                               self.created_at, self.filled_size,
                                               self.status, self.settled)


class GdaxSQLHistory(GdaxBase):
    """
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
    """
    __tablename__ = 'gdax_history'

    history_id = Column(Integer, primary_key=True)
    id = Column(Integer)
    created_at = Column(DateTime)
    amount = Column(Float)
    balance = Column(Float)
    type = Column(String(10))
    order_id = Column(String(30))
    trade_id = Column(Integer)
    product_id = Column(String(10))

class GdaxSQLFeedEntry(GdaxBase):
    """
    {'side': 'sell', 'product_id': 'BTC-USD', 'time': '2017-09-12T23:48:12.444000Z',
    'taker_order_id': '8b14f701-79ea-4ea0-835f-4e0ba60e0fcc', 'price': '4171.51000000',
    'sequence': 4009106178, 'trade_id': 20687644, 'type': 'match',
    'maker_order_id': '5fe7813c-2c43-463a-bc92-fce95a90164a', 'size': '0.00000239'}
    """
    __tablename__ = 'gdax_feed'
    feed_id = Column(Integer, primary_key=True)

    time = Column(DateTime)
    type = Column(String(15))
    product_id = Column(String(10))
    sequence = Column(Integer)
    order_id = Column(String(100))
    side = Column(String(10))
    remaining_size = Column(Float)
    reason = Column(String(30))
    size = Column(Float)
    price = Column(Float)
    client_oid = Column(String(100))
    date_added = Column(DateTime, default=datetime.now)

    trade_id = Column(Integer)
    maker_order_id = Column(String(150))
    taker_order_id = Column(String(150))


class GdaxSQLTickerFeedEntry(GdaxBase):
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
    __tablename__ = 'gdax_ticks'

    ticker_id = Column(Integer, primary_key=True)
    type = Column(String(20))
    trade_id = Column(Integer)
    sequence = Column(Integer)
    time = Column(String(50))
    product_id = Column(String(10))
    price = Column(Float)
    side = Column(String(10))
    last_size = Column(Float)
    best_bid = Column(Float)
    best_ask = Column(Float)


class GdaxSQLHeartbeatFeedEntry(GdaxBase):
    """
    {
    "type": "heartbeat",
    "sequence": 90,
    "last_trade_id": 20,
    "product_id": "BTC-USD",
    "time": "2014-11-07T08:19:28.464459Z"
}
    """
    __tablename__ = 'gdax_heartbeats'

    beat_id = Column(Integer, primary_key=True)
    type = Column(String(10))
    sequence = Column(Integer)
    last_trade_id = Column(Integer)
    product_id = Column(String(10))
    time = Column(String(50))


class GdaxSQLOrderChange(GdaxBase):
    """
    {'new_size': '2.22860000', 'sequence': 1148368608,
    'time': '2017-09-15T02:45:21.246000Z', 'type': 'change',
    'side': 'sell', 'price': '239.00000000', 'old_size': '2.42860000',
    'product_id': 'ETH-USD', 'order_id': '213f3f85-9653-43f6-b54f-5c6063e06902'}
    """
    __tablename__ = 'gdax_changes'
    change_id = Column(Integer, primary_key=True)
    sequence = Column(Integer)
    time = Column(String(50))
    type = Column(String(10))
    side = Column(String(10))
    price = Column(Float)
    new_size = Column(Float)
    old_size = Column(Float)
    product_id = Column(String(10))
    order_id = Column(String(150))


GDAX_FEED_CLASS_MAP = {'ticker': GdaxSQLTickerFeedEntry,
                       'heartbeat': GdaxSQLHeartbeatFeedEntry,
                       'subscribe': GdaxSQLFeedEntry,
                       'full': GdaxSQLFeedEntry,
                       'change': GdaxSQLOrderChange}