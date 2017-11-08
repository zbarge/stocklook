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
import pandas as pd
import logging as lg
from queue import Queue
from .product import GdaxProducts
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import scoped_session
from sqlalchemy.exc import IntegrityError
from stocklook.utils.database import DatabaseLoadingThread
from .tables import (GdaxSQLQuote,
                     GdaxSQLProduct,
                     GdaxSQLTickerFeedEntry,
                     GdaxOHLC5)
from stocklook.utils.timetools import (timestamp_to_local,
                                       timestamp_to_utc_int,
                                       now_local)
from pandas import (DataFrame,
                    DatetimeIndex,
                    infer_freq,
                    DateOffset,
                    Timestamp,
                    read_sql)

logger = lg.getLogger(__name__)


class GdaxDatabase:
    def __init__(self, gdax=None, base=None, engine=None, session_maker=None):
        if gdax is None:
            from . import Gdax
            gdax = Gdax()
        self.gdax = gdax
        self._base = None
        self._engine = None
        self._session_maker = None
        self._stock_ids = dict()
        self.setup(base, engine, session_maker)

    @property
    def stock_ids(self):
        if not self._stock_ids:
            session = self.get_session()
            self.load_stocks(session)
            session.close()
        return self._stock_ids

    def get_stock_id(self, pair):
        return self.stock_ids[pair]

    def get_loading_thread(self, obj, queue=None, commit_interval=10, raise_on_error=True, **kwargs):
        if queue is None:
            queue = Queue()
        return DatabaseLoadingThread(self._session_maker,
                                     queue,
                                     obj,
                                     raise_on_error=raise_on_error,
                                     commit_interval=commit_interval,
                                     **kwargs)

    def setup(self, base=None, engine=None, session_maker=None):
        """
        Configures SQLAlchemy connection.

        Assigns configured objects to
            GdaxDatabase._base
            GdaxDatabase._engine
            GdaxDatabase._session_maker

        :param base:
        :param engine:
        :param session_maker:
        :return:
        """
        if base is None:
            from .tables import GdaxBase
            base = GdaxBase

        if engine is None:
            from sqlalchemy import create_engine
            from ...config import config
            from ...utils.security import Credentials
            from sqlalchemy.engine.url import URL
            # Look for a postgres or mysql database first
            url_kwargs = config.get('GDAX_FEED_URL_KWARGS', dict()).copy()
            # Popping off a copy
            d = url_kwargs.pop('drivername', '')
            if url_kwargs and d:

                if d.startswith('mysql') \
                        or d.startswith('postgres') \
                        or d.startswith('sqlite'):
                    pw = url_kwargs.get('password', None)

                    if not pw and not d.startswith('sqlite'):
                        # Make the user input the password securely.
                        # if it's not stored in the KeyRing
                        user = url_kwargs['username']
                        c = Credentials(data=config, allow_input=True)
                        svc_name = '{}_{}'.format(c.GDAX_DB, d)
                        pw = c.get(svc_name, username=user, api=False)
                        url_kwargs['password'] = pw

                    url = URL(d, **url_kwargs)
                    engine = create_engine(url)

                else:
                    # Don't feel like supporting databases other
                    # than mysql, pgsql, sqlite...other dbs are lame anyways.
                    raise NotImplementedError("Unsupported drivername: "
                                              "{}".format(d))
            else:
                # Go for a sqlite engine as a backup.
                try:
                    db_path = config['GDAX_DB_PATH']
                except KeyError:
                    import os
                    db_dir = config['DATA_DIRECTORY']
                    db_path = os.path.join(db_dir, 'gdax.sqlite3')

                db_path = db_path.replace("\\", "/")
                pfx = 'sqlite:///'

                if not db_path.startswith(pfx):
                    db_path = pfx + db_path

                engine = create_engine(db_path)

        if session_maker is None:
            from sqlalchemy.orm import sessionmaker
            session_maker = sessionmaker(bind=engine)

        try:
            session_maker = scoped_session(session_maker)
        except Exception as e:
            print("Error creating scoped session maker: {}".format(e))

        base.metadata.create_all(bind=engine, checkfirst=True)

        for p in self.gdax.products.values():
            # We dont want prices cached more
            # Than 30 seconds at a time
            p.sync_interval = 30

        self._base = base
        self._engine = engine
        self._session_maker = session_maker

    def get_session(self):
        return self._session_maker()

    def load_stocks(self, session):
        qry = session.query(GdaxSQLProduct)
        res = qry.all()
        prods = self.gdax.products.values()
        stocks = list()

        if len(prods) == len(res):
            stocks = res

        elif not res:
            for p in prods:
                i = GdaxSQLProduct(name=p.name,
                                   currency=p.currency)
                session.add(i)
                stocks.append(i)
            session.commit()

        elif res:
            for p in prods:
                v = [r for r in res
                     if r.name == p.name]

                if v:
                    continue

                i = GdaxSQLProduct(name=p.name,
                                   currency=p.currency)
                stocks.append(i)
                session.add(i)
            session.commit()

        for s in stocks:
            self._stock_ids[s.name] = s.stock_id

    def get_stock(self, session, name):
        qry = session.query(GdaxSQLProduct)
        res = qry.filter(GdaxSQLProduct.name == name).first()
        if not res:
            if name not in GdaxProducts.LIST:
                raise Exception("Invalid gdax "
                                "product name {}".format(name))
            self.load_stocks(session)
            return self.get_stock(session, name)
        return res

    def sync_quotes(self, session=None):

        if session is None:
            session = self.get_session()
            close = True
        else:
            close = False

        for stock_name, stock_id in self.stock_ids.items():
            p = self.gdax.get_product(stock_name)
            q = GdaxSQLQuote(stock_id=stock_id,
                             close=p.price,
                             volume=p.volume24hr,
                             quote_date=now_local())
            print(q)
            session.add(q)

        session.commit()

        if close:
            session.close()

    def register_quote(self,
                       session,
                       stock_id,
                       open=None,
                       high=None,
                       low=None,
                       close=None,
                       volume=None,
                       quote_date=None):

        if quote_date is None:
            quote_date = now_local()

        try:
            int(stock_id)
        except:
            # Convert string to numeric stock id
            stock_id = self._stock_ids[stock_id]

        q = GdaxSQLQuote(stock_id=stock_id,
                         open=open,
                         high=high,
                         low=low,
                         close=close,
                         volume=volume,
                         quote_date=quote_date)

        session.add(q)
        return q

    def get_quotes(self, stock_id):
        int(stock_id)
        from pandas import read_sql

        tbl = GdaxSQLQuote.__tablename__
        sql = "SELECT * FROM {}" \
              "WHERE {}={}".format(tbl,
                                   GdaxSQLQuote.stock_id.name,
                                   stock_id)
        parse_dates = [GdaxSQLQuote.date_added.name,
                       GdaxSQLQuote.quote_date.name]

        return read_sql(sql, self._engine, parse_dates=parse_dates)

    def to_frame(self, query_set, cols):

        data = [(getattr(rec, c) for c in cols)
                for rec in query_set]

        return DataFrame(data=data,
                         columns=cols,
                         index=range(len(data)))

    def get_prices(self, session, from_date, to_date, products):
        """
        Returns price data available between from_date and to_date
        from the GdaxSQLTickerFeedEntry.__tablename__.

        This method would be useful if you're maintaining this table
        in the database by subscribing to the 'ticker' websocket channel.

        :param session:
        :param from_date:
        :param to_date:
        :param products:
        :return:
        """
        t = GdaxSQLTickerFeedEntry
        crit = and_(t.time >= from_date,
                    t.time <= to_date,
                    t.product_id.in_(products))

        res = session.query(t).filter(crit).all()

        cols = [t.best_ask.name,
                t.best_bid.name,
                t.last_size.name,
                t.side.name,
                t.time.name,
                t.product_id.name,
                t.price.name]

        return self.to_frame(res, cols)


class GdaxOHLCViewer:
    FREQ = '5T'
    GRANULARITY = 60*5
    MAX_SPAN = 1

    def __init__(self, pair=None, db=None, obj=None):
        if db is None:
            db = GdaxDatabase()
        if obj is None:
            obj = GdaxOHLC5
        self.pair = None
        self.stock_id = None
        self.db = db
        self.gdax = db.gdax
        self._loading_threads = list()
        self.obj = obj
        self.span_secs = self.MAX_SPAN * 24 * 60 * 60
        if pair is not None:
            self.set_pair(pair)

    def load_df(self, df, thread=True, raise_on_error=True):
        id_label = self.obj.stock_id.name
        if id_label not in df.columns or df[id_label].dropna().index.size != df.index.size:
            df.loc[:, id_label] = self.stock_id
        missing = self.get_missing_columns(df.columns)
        if missing:
            raise KeyError("Data missing columns: "
                           "{}".format(missing))

        # Ensure UTC time
        t = self.obj.time.name
        dtype = str(df[t].dtype)
        logger.info("time column data type: {}".format(dtype))
        if 'int' not in dtype and 'float' not in dtype:
            logger.debug("Converting time to UTC")
            logger.info(df[t].head(5))
            df.loc[:, t] = df.loc[:, t].apply(timestamp_to_utc_int).astype(int)
            logger.info(df[t].head(5))
        else:
            logger.debug("Confirmed UTC time dtype: {}".format(dtype))

        # load database (thread vs non-thread)
        if thread is True:
            t = self.db.get_loading_thread(self.obj,
                                           queue=None,
                                           commit_interval=df.index.size)
            t.start()
            q = t.queue
            for idx, rec in df.iterrows():
                q.put(rec)
            q.put(t.STOP_SIGNAL)
            self._loading_threads.append(t)
        else:
            session = self.db.get_session()
            cols = [c.name for c in self.obj.__table__.columns]
            recs = list()

            for idx, rec in df.iterrows():
                o = self.obj()
                [setattr(o, k, str(v))
                 for k, v in rec.items()
                 if k in cols]
                recs.append(o)

            try:
                # Attempt to load all at once
                session.add_all(recs)
                session.commit()

            except (IntegrityError, Exception) as e:
                session.rollback()
                # Attempt individual load
                # Since adding all at once didn't work.
                e = str(e).upper()
                if raise_on_error or 'UNIQUE' not in e:
                    logger.error(e.lower())
                    raise
                logger.error("Attempting individual insert/commits"
                             "as a solution to: {}".format(e))
                errs = 0
                for rec in recs:
                    try:
                        session.add(rec)
                        session.commit()
                    except:
                        session.rollback()
                        errs += 1
                c = len(recs)
                logger.info("{}/{} records successfully "
                            "imported.".format(c - errs/c))
            else:
                session.close()

            session.close()

    def set_pair(self, pair):
        self.stock_id = self.db.get_stock_id(pair)
        self.pair = pair

    def get_missing_columns(self, df_cols):
        cols = [c.name for c in self.obj.__table__.columns]
        cols = [c for c in cols if (not c.endswith('_id') or c == 'stock_id')]
        return [c for c in cols if c not in df_cols]

    def get_min_max_times(self, session):
        crit = self.obj.stock_id == self.stock_id
        max_sel = func.max(self.obj.time)
        min_sel = func.min(self.obj.time)
        max_date = session.query(max_sel).filter(crit).one()[0]
        min_date = session.query(min_sel).filter(crit).one()[0]
        try:
            return timestamp_to_local(min_date), timestamp_to_local(max_date)
        except ValueError:
            return None, None

    def slice_frame(self, df):
        if df.empty:
            return df

        t = self.obj.time.name
        t_ser = df[t]
        min_t, max_t = t_ser.min(), t_ser.max()

        try:
            min_t + 3
        except:
            raise ValueError("Expected integer (UTC) min/max "
                             "time to slice data, not {}".format(type(min_t)))

        bump = self.GRANULARITY
        osize = df.index.size
        kwargs = {'time': t,
                  'id_label': self.obj.stock_id.name,
                  'id': self.stock_id,
                  'table': self.obj.__tablename__,
                  'start': min_t + bump,
                  'end': max_t + bump,
                  }
        sql = "select {time} " \
              "from {table} " \
              "where {id_label} = {id} " \
              "and {time} between {start} and {end};".format(**kwargs)

        s = self.read_sql(sql, convert_dates=False)

        if not s.empty:
            if s[t].dtype != df[t].dtype:
                t_temp = '__{}'.format(t)
                logger.debug("Using temp column '{}' "
                             "to slice data.".format(t_temp))
                for frame in (df, s):
                    frame.loc[t_temp, :] = pd.to_numeric(frame.loc[:, t],
                                                         errors='coerce',
                                                         downcast='integer').astype(int)
                label = t_temp
            else:
                t_temp = None
                label = t

            df = df.loc[~df[label].isin(s[label]), :]

            if t_temp:
                df.drop([t_temp], axis=1, errors='raise', inplace=True)

            diff = df.index.size - osize
            if diff > 0:
                logger.debug("slice_frame: Removed {} records from "
                             "data, was {}.".format(osize, diff))

        return df

    def request_ohlc(self, start, end, convert_dates=False):
        df = self.gdax.get_candles(self.pair,
                                   start,
                                   end,
                                   self.GRANULARITY,
                                   convert_dates=convert_dates,
                                   to_frame=True)
        if not df.empty:
            df.sort_values(['time'], ascending=[False], inplace=True)
            df.loc[:, self.obj.stock_id.name] = self.stock_id
        return df

    def read_sql(self, sql, convert_dates=False, **kwargs):
        kwargs['coerce_float'] = kwargs.get('coerce_float', False)
        df = read_sql(sql, self.db._engine, **kwargs)

        if not df.empty:
            t = self.obj.time.name
            if t in df.columns and convert_dates:
                logger.debug("pre-converted time: {}".format(df[t].head(5)))
                df.loc[:, t] = df[t].apply(timestamp_to_local)
                df.loc[:, t] = pd.to_datetime(df.loc[:, t], errors='coerce')
                logger.debug("converted time: {}".format(df[t].head(5)))
                df = df.loc[df[t] > Timestamp('2015-01-01'), :]

        return df

    def get_time_gaps(self, df=None, time_label=None):
        """
        Analyzes the time columns identifying gaps in the data.
        A list is returned of gaps in data.
            list([start, end], [start, end])
        :param df:
        :param time_label:
        :return:
        """
        if time_label is None:
            time_label = self.obj.time.name
        if df is None:

            kwargs = {'table': self.obj.__tablename__,
                      'id_label': self.obj.stock_id.name,
                      'id': self.stock_id,
                      'time': time_label}
            sql = "select {time}, {id_label} from {table} " \
                  "where {id_label} = {id}".format(**kwargs)
            df = self.read_sql(sql, convert_dates=True)

            logger.info(df[time_label].head(10))

        # Sort by times old to new
        df.sort_values(time_label, ascending=True, inplace=True)
        df.reset_index(drop=True, inplace=True)
        logger.info(df[time_label].head(10).tolist())

        gaps = []
        last_time = None
        bump = DateOffset(seconds=self.GRANULARITY)
        n = now_local()

        def maybe_extend_gaps(start, end):
            # Determines whether to extend an
            # existing gap or add a new list
            try:
                last_start, last_end = gaps[-1]
            except IndexError:
                gaps.append([start, end])
                return

            if start == last_end:
                # Swap end date in existing list
                gaps[-1][1] = end
                logger.info("Extending existing gap: "
                            "{} {}".format(last_start, end))
            else:
                # Add new gap
                gaps.append([start, end])
                logger.info("Adding new gap: "
                            "{} {}".format(start, end))

        # Run through all of the data
        # looking for gaps
        for idx, row in df.iterrows():
            t = row[time_label]
            if last_time is None:
                last_time = t
            else:
                expect = last_time + bump
                if expect > n:
                    logger.info("Got out of range time {} on "
                                "index {}/{}.".format(t, idx,
                                                      df.index.size))
                    break
                elif t > expect:
                    # Got time greater than expected
                    maybe_extend_gaps(expect, t)
                    last_time = t
                elif t < expect:
                    # Got time less than expected
                    maybe_extend_gaps(t, expect)
                    last_time = expect
                else:
                    # Got expected time.
                    last_time = t
        return gaps

    def sync_time_gaps(self, gaps=None):
        """
        Uses a list([start, end], [start, end])
        to request/load OHLC data from the API to the database.
        :param gaps:
        :return:
        """
        if gaps is None:
            gaps = self.get_time_gaps()

        for start, end in gaps:
            _, max = self.get_time_bump(start, end, bump_start=False)
            if max < end:
                df = DataFrame()
                while max < end:
                    df = df.append(self.request_ohlc(start, max))
                    start, max = self.get_time_bump(start, end)
            else:
                df = self.request_ohlc(start, end)

            if df.empty:
                logger.info("Failed 2nd time on gap {}: "
                            "{} {}".format(self.pair, start, end))
                continue
            self.load_df(df, thread=False,)

    def sync_ohlc(self, months=6, thread=True, raise_on_error=True):
        """
        Gets OHLC data current by using the
        :param months:
        :param thread:
        :param raise_on_error:
        :return:
        """
        sess = self.db.get_session()
        min_time, max_time = self.get_min_max_times(sess)
        n = now_local()

        if not all((min_time, max_time)):

            logger.info("OHLC database contains "
                        "no data for {} "
                        "pair.".format(self.pair))
            start = n - DateOffset(months=months)
            end = start + DateOffset(days=self.MAX_SPAN)
        else:
            # Existing database/table/dates
            start = Timestamp(max_time) + DateOffset(seconds=self.GRANULARITY)

            end = start + DateOffset(days=self.MAX_SPAN)
            if end > n:
                end = n
            logger.info("Existing OHLC start: {} "
                        "end: {}".format(start, end))

        total, n = 0, now_local()
        empties = 0

        while end < n:

            df = self.request_ohlc(start, end, convert_dates=False)
            df = self.slice_frame(df)

            if df.empty:
                logger.info("Got empty data set for "
                            "start: {} and end: "
                            "{}".format(start, end))
                empties += 1

            else:
                total += df.index.size
                self.load_df(df,
                             thread=thread,
                             raise_on_error=raise_on_error)
            '''
            # Bump start/end times by the difference
            # between now and the end time or by the
            # max span allowed for the granularity.
            diff = n - end
            secs = diff.total_seconds()
            if secs < span_secs:
                bump = DateOffset(seconds=secs)
            else:
                bump = DateOffset(days=self.MAX_SPAN)

            start += bump
            end += bump
            '''

            start, end = self.get_time_bump(start, end,
                                            now_time=n,
                                            bump_start=True)

            logger.info('{}: {} - '
                        '{}'.format(self.pair,
                                    start, end))
        sess.commit()
        sess.close()
        logger.info("OHLC sync complete for "
                    "{}, {} records added.".format(self.pair, total))

    def get_time_bump(self, start, end, now_time=None, bump_start=True):
        #logger.info("Time bump - before: {} {}".format(start, end))
        if now_time is None:
            diff = end - start
        else:
            diff = now_time - end
        secs = diff.total_seconds()

        if secs <= self.span_secs:
            bump = DateOffset(seconds=secs)
        else:
            bump = DateOffset(days=self.MAX_SPAN)
        if bump_start:
            start += bump
        end = start + bump
        #logger.info("Time bump - after: {} {}".format(start, end))
        return start, end
































