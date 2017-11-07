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
import time
from time import strptime, mktime
from pandas import Timestamp, DateOffset, to_datetime, Series, NaT, isnull
import calendar
from calendar import timegm
from datetime import datetime, timedelta
import pytz
from pytz import timezone
from stocklook.config import config
import logging as lg
log = lg.getLogger(__name__)

# Time-related helper methods
TZ = 'PYTZ_TIMEZONE'
GLOBAL_TIMEOUT_MAP = dict()

def timestamp_to_local(dt):
    """
    Convert nearly any time object to local time.

    :param dt:
        The following objects are tested:
        - utc integer/float/numeric string
        - datetime.datetime
        - pandas.Timestamp
        - date or datetime string coercible by pandas.Timestamp algos
            -
    :return:
    """
    try:
        return localize_utc_int(dt)
    except:
        if not dt:
            return None

        if isinstance(dt, str):
            # convert a string-ish object to a
            # pandas.Timestamp (way smarter than datetime)
            utc_dt = Timestamp(dt)

        # Get rid of existing timezones
        dt = de_localize_datetime(dt)

        if hasattr(dt, 'utctimetuple'):
            dt = timegm(dt.utctimetuple())

    return localize_utc_int(dt)


def localize_utc_int(utc_int):
    tz = timezone(config[TZ])
    utc_dt = datetime.fromtimestamp(int(float(utc_int)), pytz.utc)
    return utc_dt.astimezone(tz)


def de_localize_datetime(dt):
    tz_info = getattr(dt, 'tzinfo', None)
    if tz_info and tz_info != pytz.utc:
        if hasattr(dt, 'astimezone'):
            dt = dt.astimezone(pytz.utc)
        return dt.replace(tzinfo=None)
    return dt


def timestamp_trim_to_min(time_stamp):
    t = Timestamp(time_stamp)
    s = DateOffset(seconds=t.second)
    return t - s


def timestamp_trim_to_hour(time_stamp):
    t = Timestamp(time_stamp)
    s = DateOffset(seconds=t.second, minutes=t.minute)
    return t - s


def timestamp_trim_to_date(time_stamp):
    t = Timestamp(time_stamp)
    return t.date


def timestamp_from_utc(utc_time):
    try:
        utc = datetime.utcfromtimestamp(utc_time)
        utc_form = utc.strftime('%Y-%m-%d %H:%M:%S')
    except (TypeError, OSError):
        utc_form = utc_time
    return Timestamp(utc_form)


def timestamp_to_utc_int(ts):
    if isnull(ts):
        return ts

    t = getattr(ts, 'utctimetuple', None)

    if t:
        ts = de_localize_datetime(ts)

    elif isinstance(ts, (int, float)):
        # assume already UTC time
        return ts

    elif isinstance(ts, str):
        try:
            return int(float(ts))
        except:
            ts = de_localize_datetime(Timestamp(ts))

    t = getattr(ts, 'utctimetuple', None)
    if t:
        return timegm(t())

    return 0


def timestamp_to_iso8601(ts, de_localize=True):
    if hasattr(ts, 'title'):
        ts = Timestamp(ts)
    if de_localize:
        ts = de_localize_datetime(ts)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def timestamp_to_path(time_stamp, trim=10):
    t = str(time_stamp)
    t = t.replace(':', '_').replace(' ', '_')

    if '.' in t:
        t = t.split('.')[0]

    if trim:
        t = t[:trim]

    return t


def create_timestamp(datestr, format="%Y-%m-%d %H:%M:%S"):
    return mktime(strptime(datestr, format))


def three_days_ago():
    return datetime.now() - DateOffset(days=3)


def today():
    return datetime.now() - DateOffset(hours=datetime.now().hour, minutes=datetime.now().minute)


def this_month():
    return datetime.now() - DateOffset(days=datetime.now().day)


def five_minutes_ago():
    return datetime.now() - DateOffset(minutes=5)


def one_hour_ago():
    return datetime.now() - DateOffset(hours=1)


def four_hours_ago():
    return datetime.now() - DateOffset(hours=4)


def one_week_ago():
    return datetime.now() - DateOffset(weeks=1)


def now_minus(**kwargs):
    return datetime.now() - DateOffset(**kwargs)


def now_plus(**kwargs):
    return datetime.now() + DateOffset(**kwargs)


def now():
    return Timestamp(datetime.now())


def now_local():
    t = datetime.utcnow().utctimetuple()
    return localize_utc_int(timegm(t))


def timeout_check(key, t_data=None, seconds=30):
    """
    A way to check if a key has timed out. Useful for calling API
    on an interval rather than calling every time the method is calling.

    :param key: (str)
        A unique key that one method calls on to check for timeouts.

    :param t_data: (dict, default stocklook.utils.timetools.GLOBAL_TIMEOUT_MAP)
        A dictionary containing key/values like
            {'unique_key_for_caller': datetime.datetime}
        If the key is not in the dict it will be added with
        the current time.


    :param seconds: (int, default 30)
        The number of seconds

    :return: (bool)
        True when a timeout has reached.
        False when a timeout has not been reached.
    """
    if t_data is None:
        t_data = GLOBAL_TIMEOUT_MAP

    n = now()
    t_out = t_data.get(key, None)

    if t_out is None or n >= t_out + timedelta(seconds=seconds):
        t_data[key] = n
        return False if t_out is None else True

    return False




if __name__ == '__main__':
    print(pytz.all_timezones)