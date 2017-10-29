import datetime
import logging
import os

import pandas as pd
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from yahoo_finance import Share, YQLResponseMalformedError

from stocklook.utils.formatters import get_stock_data, field_map, get_stock_data_historical
from .tables import Quote, Stock, Base, WatchList

logger = logging.getLogger()
logger.setLevel(logging.INFO)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)
DEFAULT_DATABASE_PATH = os.path.join(DATA_DIR, 'db.sqlite3')
engine = create_engine('sqlite:///' + DEFAULT_DATABASE_PATH)
Session = sessionmaker(bind=engine)
stock_keys = Stock.__dict__.keys()
quote_keys = Quote.__dict__.keys()


class StockDatabase:
    STOCK_TIMES = [[5, 30], [13, 30]]

    def __init__(self, symbols=None):
        Base.metadata.create_all(bind=engine, checkfirst=True)
        self._symbols = symbols

    def _add_stock(self, session, name, data=None):
        if data is None:
            try:
                data = get_stock_data(Share(name), field_map)
            except:
                return None

        stock = Stock(**{k: v for k, v in data.items() if k in stock_keys})
        try:
            session.add(stock)
        except:
            pass
        return data

    def seconds_until_market_open(self):
        open, close = self.STOCK_TIMES
        ohour, omin = open
        chour, cmin = close
        osec = (ohour*60*60) + (omin*60)
        csec = (chour*60*60) + (cmin*60)
        today = datetime.datetime.now()
        tsec = (today.hour*60*60) + (today.minute*60)
        weekday = today.weekday()

        if weekday < 5:
            add = 0
        elif weekday == 5:
            add = (48*60*60)-tsec
        elif weekday == 6:
            add = (24*60*60)-tsec

        if tsec > csec:
            sec = (24*60*60)-tsec+osec+add
            #logger.info("STMO1: Stock market opens in {} hours".format(round(sec/60/60),2))
        elif tsec < osec:
            sec = osec-tsec+add
            #logger.info("STMO2: Stock market opens in {} hours".format(round(sec / 60 / 60), 2))
        else:
            #logger.info("STMO3: Stock market is currently open")
            sec = 0 + add

        return sec

    def get_quote_latest(self, session, stock):
        return session.query(Quote)\
                      .filter(Quote.stock_id == stock.id)\
                      .order_by(Quote.date_inserted.desc())\
                      .limit(1)\
                      .one_or_none()

    def get_quote(self, session, stock, data=None):
        update_time = pd.Timestamp(datetime.datetime.now()) - pd.DateOffset(minutes=15)
        if stock is None or not hasattr(stock, 'quotes') or not hasattr(stock, 'symbol'):
            return None
        seconds = self.seconds_until_market_open()
        quote = self.get_quote_latest(session, stock)

        market_closed = (seconds > 15*60)
        if quote is None \
                or (not market_closed and quote.date_inserted <= update_time)\
                or (market_closed and quote.date_inserted.minute < 30 and quote.date_inserted.hour == 13):
            if data is None:
                data = get_stock_data(Share(stock.symbol), field_map)
            quote = Quote(**{k: v
                             for k, v in data.items()
                             if k in quote_keys})
            logger.info("UPDATED QUOTE: {}".format(quote))
            stock.quotes.append(quote)

        else:
            logging.info("EXISTING QUOTE: {}".format(quote))

        return quote

    def get_quotes(self, session, stocks):
        return [self.get_quote(session, s) for s in stocks]

    def get_stock(self, session, symbol):
        symbol = symbol.upper()
        query = session.query(Stock).filter(Stock.symbol == symbol)
        stock = query.one_or_none()
        if stock is None:
            self._add_stock(session, symbol)
        else:
            return stock
        return query.one_or_none()

    def get_stocks(self, session, symbols):
        return [self.get_stock(session, s) for s in symbols]

    def get_session(self):
        return Session()

    def update_stocks(self, session, stocks=None):
        if not stocks:
            stocks = session.query(Stock).all()
        try:
            return self.get_quotes(session, stocks)
        except Exception as e:
            logger.error("Error getting quotes: {}".format(e))
            session.rollback()

    def update_historical(self, session, stock, start_date, end_date):
        share = Share(stock.symbol)
        try:
            data = get_stock_data_historical(share, start_date, end_date)
        except YQLResponseMalformedError as e:
            logger.error(e)
            return None
        matching_quotes = session.query(Quote).filter(and_(Quote.stock_id == stock.id,
                                                           Quote.date_last_traded >= pd.Timestamp(start_date),
                                                           Quote.date_last_traded <= pd.Timestamp(end_date)))\
                                 .order_by(Quote.date_inserted.asc())
        dates = [pd.Timestamp(q.date_last_traded).date() for q in matching_quotes.all()
                 if pd.Timestamp(q.date_last_traded).hour > 13]

        quotes = []
        for record in data:
            try:
                if record[Quote.date_last_traded.name].date() not in dates:
                    quote = Quote(**{k: v
                                     for k, v in record.items()
                                     if k in quote_keys})
                    quote.symbol_name = stock.symbol_name
                    quote.stock_exchange = stock.stock_exchange
                    quote.trade_currency = stock.trade_currency
                    quotes.append(quote)
                    stock.quotes.append(quote)
            except (KeyError, ValueError) as e:
                logger.error("Error parsing historical quote - {} - {}".format(e, record))
        [session.add(q) for q in quotes]
        return quotes

    def update_historicals(self, session, stocks=None, start_date=None, end_date=None):
        now = pd.Timestamp(datetime.datetime.now())
        if start_date is None:
            start_date = now - pd.DateOffset(years=1)
        if end_date is None:
            end_date = now
        return [self.update_historical(session, s, start_date, end_date) for s in stocks]

    def get_watchlist(self, session, name):
        return session.query(WatchList).filter(WatchList.name == name).one_or_none()

    def add_watchlist(self, session, name, tickers=None):
        exists = self.get_watchlist(session, name)
        if exists is None:
            w = WatchList(name=name)
            session.add(w)
        else:
            w = exists

        if tickers is not None:
            stocks = self.get_stocks(session, tickers)
            for s in stocks:
                if s in w.stocks:
                    continue
                w.stocks.append(s)
        return w

    def delete_watchlist(self, session, name):
        session.query(WatchList).filter(WatchList.name == name).delete()

    def add_watchlist_stocks(self, session, watchlist, tickers):
        stocks = self.get_stocks(session, tickers)
        for s in stocks:
            if s in watchlist.stocks:
                continue
            watchlist.stocks.append(s)

    def delete_watchlist_stocks(self, session, watchlist, tickers):
        for stock in watchlist.stocks:
            if stock.symbol in tickers:
                session.delete(stock)
        return watchlist
















