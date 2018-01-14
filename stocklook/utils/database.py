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
import os
from threading import Thread
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from stocklook.utils.timetools import timestamp_to_local
from queue import Empty
import logging as lg
logger = lg.getLogger(__name__)

PY_TYPE_TO_SQL_ALCHEMY_LABEL_MAP = {
    str: "String(255)",
    bool: 'Boolean',
    int: 'Integer',
    float: 'Float',
    None: 'String(255)',
}


def db_describe_dict(data, table_name=None):
    """
    Helper function prints sqlalchemy table definitions
    using dictionary key and value pairs.
    :param data:
    :return:
    """
    if table_name is None:
        table_name = "Table1"

    m = PY_TYPE_TO_SQL_ALCHEMY_LABEL_MAP
    others = list()

    print("__tablename__ = '{}'".format(table_name))
    for k, v in sorted(data.items()):
        if isinstance(v, dict):
            others.append((k, v))
        else:
            print("{} = Column({})".format(k, m.get(type(v), 'String')))

    for k, v in others:
        print("\n\n__tablename__ = '{}'\n".format(k))
        db_describe_dict(v)
    print("\n\n")


def db_get_python_dtypes(sql_table, date_type=None, include_str=False):
    """
    Returns a dictionary of {column_name: python_dtype} after extracting
    information from :param sql_table.

    :param sql_table: (declarative_base object)
        A Sqlalchemy Table object.

    :param date_type: (object, callable, default None)
        None defaults to function stocklook.utils.timetools.timestamp_to_local

    :param include_str: (bool, default False)
        True includes columns in string format in the returned dictionary.
        Usually the data being parsed is in string format so it's not often needed.

    :return: (dict)
    """
    d = dict()
    cols = sql_table.__table__.columns

    if date_type is None:
        date_type = timestamp_to_local

    if not include_str:
        cols = [c for c in cols
                if c.type.python_type != str]

    for c in cols:
        py_type = c.type.python_type
        col = c.name

        if 'date' in str(py_type).lower():
            d[col] = date_type

        else:
            d[col] = py_type

    return d


def db_map_dict_to_alchemy_object(d, sql_object, dtype_items=None, raise_on_error=False):
    """
    Converts a dictionary object
    into a SQLAlchemy object. The dictionary
    keys should exactly match the attribute names
    of the SQLAlchemy object or a warning will be printed
    and missing attributes will be skipped.

    :param d:
    :param sql_object:
    :param dtype_items:
    :param raise_on_error:
    :return:
    """

    # Convert dtypes
    if dtype_items is not None:
        for c, tp in dtype_items:
            try:
                d[c] = tp(d[c])
            except KeyError:
                pass
            except (ValueError, TypeError):
                d[c] = None

    # Set attributes
    obj = sql_object()
    for k, v in d.items():
        try:
            setattr(obj, k, v)
        except AttributeError:
            msg = "SQL object {} missing: " \
                  "{}".format(sql_object, k)
            if raise_on_error:
                raise KeyError(msg)

    return obj


class DatabaseLoadingThread(Thread):
    """
    A thread class that handles the loading of dict objects
    from a Queue to a SQLAlchemy table.

    Useful for consuming large amounts of data without bottle-necks.


    """
    STOP_SIGNAL = '--stop--'

    # str(table_name): int(max_queue_size)
    SIZE_MAP = dict()

    def __init__(self,
                 threadsafe_session_maker,
                 queue,
                 sql_object,
                 raise_on_error=True,
                 commit_interval=10,
                 **kwargs):
        self.session_maker = threadsafe_session_maker
        self.queue = queue
        self.obj = sql_object
        self.dtypes = dict()
        self.dtype_items = None
        self.count = 0
        self.raise_on_error = raise_on_error
        self.commit_interval = commit_interval
        self._setup()
        self.stop = False

        kwargs.pop('target', None)
        kwargs.pop('args', None)

        super(DatabaseLoadingThread, self).__init__(**kwargs)

    def get_session(self):
        return self.session_maker()

    @property
    def type(self):
        return self.obj.__tablename__

    @property
    def max_qsize(self):
        return self.SIZE_MAP.get(self.type, 500)

    def _setup(self):
        """
        Loads DatabaseLoadingThread.dtypes & DatabaseLoadingThread.dtype_items
        using python data types from the SQLAlchemy table.
        :return:
        """
        d = self.dtypes
        cols = self.obj.__table__.columns

        for c in cols:
            py_type = c.type.python_type
            col = c.name

            if py_type == str:
                continue

            elif 'date' in str(py_type).lower():
                d[col] = timestamp_to_local

            else:
                d[col] = py_type

        self.dtype_items = d.items()

    def get_sql_record(self, d):
        """
        Converts a dictionary object
        into a SQLAlchemy object. The dictionary
        keys should exactly match the attribute names
        of the SQLAlchemy object or a warning will be printed
        and missing attributes will be skipped.
        :param d:
        :return:
        """
        return db_map_dict_to_alchemy_object(
            d, self.obj,
            dtype_items=self.dtype_items,
            raise_on_error=self.raise_on_error)

    def run(self):
        while True:
            msg = self.load_messages()
            if isinstance(msg, str) and msg == self.STOP_SIGNAL:
                logger.info("Stop signal received on "
                            "'{}'.".format(self.type))
                break

    def load_messages(self):
        """
        Retrieves a message (dict) from the DatabaseLoadingThread.queue
        Parses message into SQLAlchemy object
        Loads SQLAlchemy object into database
        Commits updates based on DatabaseLoadingThread.commit_interval
        Closes session and returns the last message processed
        :return:
        """
        session = self.get_session()
        msg = None

        while True:
            try:

                msg = self.queue.get(timeout=1)
                if not hasattr(msg, 'items'):
                    if msg == self.STOP_SIGNAL:
                        break
                    else:
                        err_msg = "Got unexpected message: '{}'.\n "\
                                  "Expecting dictionary-like "\
                                  "messages that have .items()".format(msg)
                        if self.raise_on_error:
                            raise AttributeError(err_msg)
                        else:
                            # Wont be able to process
                            # this message so move along.
                            logger.error(err_msg)
                            continue

                rec = self.get_sql_record(msg)
                
                session.add(rec)
                self.count += 1
                done = self.count % self.commit_interval == 0
                if done: break
            except Empty:
                break

        session.commit()
        session.close()

        return msg


class AlchemyDatabase:
    """
    Base class for databases holds the
    engine, sessionmaker, and declarative base.
    """
    def __init__(self, engine=None, session_maker=None, base=None):
        self._engine = engine
        self._session_maker = session_maker
        self._declarative_base = base

    @property
    def engine(self):
        """
        SQLAlchemy engine defaults to classname.sqlite3
        in the directory found in stocklook.config.config['DATA_DIRECTORY']
        :return:
        """
        if self._engine is None:
            from stocklook.config import config, DATA_DIRECTORY
            db_name = '{}.sqlite3'.format(self.__class__.__name__.lower())
            db_path = 'sqlite:///' + os.path.join(
                config[DATA_DIRECTORY], db_name)
            self._engine = create_engine(db_path)
            if self._declarative_base is not None:
                self._declarative_base.metadata.create_all(bind=self._engine)
        return self._engine

    @property
    def meta(self):
        return self._declarative_base.metadata

    @property
    def tables(self):
        return self.meta.tables

    def get_session(self):
        if self._session_maker is None:
            self._session_maker = sessionmaker(bind=self.engine)
        return self._session_maker()
