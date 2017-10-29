from threading import Thread
from stocklook.utils.timetools import timestamp_to_local
from queue import Empty
from time import sleep
import logging as lg
logger = lg.getLogger(__name__)

def get_python_dtypes(sql_table, date_type=None, include_str=False):

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
        # Convert dtypes
        for c, tp in self.dtype_items:
            try:
                d[c] = tp(d[c])
            except KeyError:
                pass
            except (ValueError, TypeError):
                d[c] = None

        # Set attributes
        e = self.obj()
        for k, v in d.items():
            try:
                setattr(e, k, v)
            except AttributeError as e:
                msg = "SQL object {} missing: {}".format(self.obj, k)
                if self.raise_on_error:
                    raise KeyError(msg)
                logger.error(msg)

        return e

    def _run(self):
        """
        Retrieves a message (dict) from the DatabaseLoadingThread.queue
        Parses message into SQLAlchemy object
        Loads SQLAlchemy object into database
        Commits updates based on DatabaseLoadingThread.commit_interval

        :return:
        """
        sess = self.get_session()
        get_msg = self.queue.get
        get_rec = self.get_sql_record
        stop = self.STOP_SIGNAL
        done = self.queue.task_done
        raise_errs = self.raise_on_error

        while not self.stop:

            try:
                msg = get_msg(timeout=300)
            except Empty:
                logger.info("No item(s) available in "
                      "'{}' queue. Sleeping."
                      "".format(self.type))
                sleep(30)
                continue

            if msg == stop:
                sess.commit()
                sess.close()
                break

            sess.add(get_rec(msg))

            self.count += 1
            sess = self.handle_session(sess)

            done()

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
        #start_no = self.count

        while True:
            try:

                msg = self.queue.get(timeout=1)
                if isinstance(msg, str) and msg == self.STOP_SIGNAL:
                    break

                rec = self.get_sql_record(msg)
                
                session.add(rec)
                self.count += 1
                done = self.count % self.commit_interval == 0
                if done: break
            except Empty:
                break

        #stop_no = self.count - start_no
        #if stop_no > 0:
        #    logger.info("'{}' loaded {} records".format(self.type, stop_no))

        session.commit()
        session.close()

        return msg