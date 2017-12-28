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
import logging

DEFAULT_LOG_LVL = logging.DEBUG
# Environment variables to load
# into config dictionary.
env = os.environ
POLONIEX_KEY = 'POLONIEX_KEY'
GDAX_KEY = 'GDAX_KEY'
COINBASE_KEY = 'COINBASE_KEY'
STOCKLOOK_EMAIL = 'STOCKLOOK_EMAIL'
STOCKLOOK_NOTIFY_ADDRESS = 'STOCKLOOK_NOTIFY_ADDRESS'

# GDAX_FEED_URL_KWARGS
# Because SQLite couldn't hang.
db_type = 'mysql'
db_api = 'pymysql'
host = 'localhost'
port = '3306'
username = 'gdaxer'
database = 'gdax'


"""
Global config dictionary is imported and used by most classes that require an API or database
connection in the stocklook library.

The stocklook.utils.security.Credentials object uses this dictionary to
retrieve/store usernames and API Keys while securely storing API secrets/passphrases
and passwords in the encrypted facilities provided by the keyring package.
"""
config = dict(GMAIL_EMAIL=env.get(STOCKLOOK_EMAIL, None),
              STOCKLOOK_EMAIL=env.get(STOCKLOOK_EMAIL, None),
              STOCKLOOK_NOTIFY_ADDRESS=env.get(STOCKLOOK_NOTIFY_ADDRESS, None),
              DATA_DIRECTORY=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data'),
              POLONIEX_KEY=env.get(POLONIEX_KEY, None),
              COINBASE_KEY=env.get(COINBASE_KEY, None),
              GDAX_KEY=env.get(GDAX_KEY, None),
              GDAX_FEED_URL_KWARGS={
                                    'drivername': "{}+{}".format(db_type, db_api),
                                    'host': host or None,
                                    'port': port or None,
                                    'username': username or None,
                                    'password': None,
                                    'database': database or None
                                   },
              LOG_LEVEL=DEFAULT_LOG_LVL,
              PYTZ_TIMEZONE='US/Pacific',

              )


def update_config(config_dict):
    """
    Recommended to import this function
    and place at the beginning of any custom code
    to auto set usernames and API keys.

    API secrets/passphrases and passwords
    should not be hard-coded into files as keyring handles
    secure storage and these will be requested
    for input manually if not already found in secure storage.
    :param config_dict:
    :return:
    """
    config.update(config_dict)

    log_lvl = config.get('LOG_LEVEL', DEFAULT_LOG_LVL)
    logging.basicConfig(level=log_lvl)

    dirs = [v for k, v in config.items()
            if str(k).endswith('DIRECTORY')]
    for d in dirs:
        try:
            if not os.path.exists(d):
                os.makedirs(d)
        except:
            pass


# Default log level set here to INFO
# When update_config method is called and if LOG_LEVEL is available
# it will override this default.
# Also probably subsequent calls to logging.basicCOnfig would override
# this.
logging.basicConfig(level=config.get('LOG_LEVEL', DEFAULT_LOG_LVL))