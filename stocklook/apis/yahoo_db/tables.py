from sqlalchemy import (String, Boolean, DateTime, Float,
                        Integer, BigInteger, Column, ForeignKey, Table)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime
from pandas import Timestamp


def now():
    return datetime.datetime.now()


Base = declarative_base()

{'Adj_Close': '22.889999', 'Date': '2017-03-20', 'Close': '22.889999', 'Low': '22.58',
 'Symbol': 'GDX', 'Volume': '36811900', 'High': '23.00', 'Open': '22.74'}


watchlists_stocks_association = Table('watchlists_stocks', Base.metadata,
    Column('stock_id', Integer, ForeignKey('stocks.id')),
    Column('watchlist_id', Integer, ForeignKey('watchlists.id'))
)


class Stock(Base):
    __tablename__ = 'stocks'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(30), unique=True)
    symbol_name = Column(String(255))
    stock_exchange = Column(String(30))
    trade_currency = Column(String(30))
    quotes = relationship('Quote', back_populates='stock')
    date_inserted = Column(DateTime, default=now)
    watchlists = relationship("WatchList",
                    secondary=watchlists_stocks_association,
                    back_populates="stocks")

    def __repr__(self):
        return """Stock(symbol='{}', symbol_name='{}', date_inserted='{}'""".format(self.symbol, self.symbol_name, self.date_inserted)


class Quote(Base):
    __tablename__ = 'quotes'
    id = Column(Integer, primary_key=True)

    stock_id = Column(ForeignKey('stocks.id'))
    stock = relationship('Stock', back_populates='quotes')
    symbol = Column(String(30))
    symbol_name = Column(String(255))
    stock_exchange = Column(String(30))
    trade_currency = Column(String(30))
    date_inserted = Column(DateTime, default=now)
    date_dividend_ex = Column(DateTime)
    dividend_pay_date = Column(DateTime)
    dividend_share = Column(Float())
    dividend_yield = Column(Float())
    date_last_traded = Column(DateTime)
    ebitda = Column(Float())
    eps_current = Column(Float())
    eps_current_year = Column(Float())
    eps_next_quarter = Column(Float())
    eps_next_year = Column(Float())
    eps_price_est_current_year = Column(Float())
    eps_price_est_next_year = Column(Float())
    errored_symbol = Column(Boolean(), default=False)
    limit_high = Column(Float())
    limit_low = Column(Float())
    market_cap = Column(BigInteger)
    pct_change_200_day_avg = Column(Float(precision=4))
    pct_change_50_day_avg = Column(Float(precision=4))
    pct_change_current = Column(Float(precision=4))
    pct_change_today = Column(Float(precision=4))
    pct_change_year_high = Column(Float(precision=4))
    pct_change_year_low = Column(Float(precision=4))
    pct_day_change = Column(Float(precision=4))
    pe_ratio = Column(Float(precision=4))
    peg_ratio = Column(Float(precision=4))
    price_200_day_moving_avg = Column(Float(precision=4))
    price_50_day_moving_avg = Column(Float(precision=4))
    price_ask = Column(Float(precision=4))
    price_bid = Column(Float(precision=4))
    price_book = Column(Float(precision=4))
    price_book_value = Column(Float(precision=4))
    price_change_200_day_avg = Column(Float(precision=4))
    price_change_50_day_avg = Column(Float(precision=4))
    price_change_year_high = Column(Float(precision=4))
    price_change_year_low = Column(Float(precision=4))
    price_day_change = Column(Float(precision=4))
    price_day_high = Column(Float(precision=4))
    price_day_low = Column(Float(precision=4))
    price_day_open = Column(Float(precision=4))
    price_last_close = Column(Float(precision=4))
    price_last_trade = Column(Float(precision=4))
    price_sales = Column(Float(precision=4))
    price_year_high = Column(Float(precision=4))
    price_year_low = Column(Float(precision=4))
    price_year_target = Column(Float(precision=4))
    range_day = Column(String(30))
    range_year = Column(String(30))
    short_ratio = Column(Float(precision=4))
    volume_day = Column(Integer)
    volume_day_avg = Column(Integer)

    def __repr__(self):
        return """Quote(symbol='{}', symbol_name='{}', date_last_traded='{}',
               price_last_trade='{}', price_last_close='{}', date_inserted='{}'""".format(self.symbol, self.symbol_name,
                                                                      self.date_last_traded, self.price_last_trade,
                                                                      self.price_last_close, self.date_inserted)


class WatchList(Base):
    __tablename__ = 'watchlists'

    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    stocks = relationship("Stock",
                    secondary=watchlists_stocks_association,
                    back_populates="watchlists")
    date_inserted = Column(DateTime, default=now)
    date_updated = Column(DateTime, default=now)

