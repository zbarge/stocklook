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
DEFAULT_PYTZ_TIMEZONE = 'US/Pacific'
DEFAULT_DATA_DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

# Environment variables below will be loaded into the config dictionary.
# The stocklook library uses this config dictionary to access private information
# like keys and secrets. The values of these variables should be used as the
# key name and added to the OS environment.

# Alternatively, a program can inject these variable names into the config dictionary here
# If there is some other method of storing private information.
env = os.environ
BITMEX_KEY = 'BITMEX_KEY'
BITMEX_SECRET = 'BITMEX_SECRET'
BITTREX_KEY = 'BITTREX_KEY'
BITTREX_SECRET = 'BITTREX_SECRET'
COINBASE_KEY = 'COINBASE_KEY'
COINBASE_SECRET = 'COINBASE_SECRET'
CRYPTOPIA_KEY = 'CRYPTOPIA_KEY'
CRYPTOPIA_SECRET = 'CRYPTOPIA_SECRET'
DATA_DIRECTORY = 'DATA_DIRECTORY'
GDAX_KEY = 'GDAX_KEY'
GDAX_PASSPHRASE = 'GDAX_PASSPHRASE'
GDAX_SECRET = 'GDAX_SECRET'
GMAIL_EMAIL = 'GMAIL_EMAIL'                                # Synonymous with STOCKLOOK_EMAIL
GMAIL_PASSWORD = 'GMAIL_PASSWORD'
LOG_LEVEL = 'LOG_LEVEL'                                    # Not env variable. uses DEFAULT_LOG_LVL.
POLONIEX_KEY = 'POLONIEX_KEY'
POLONIEX_SECRET = 'POLONIEX_SECRET'
PYTZ_TIMEZONE = 'PYTZ_TIMEZONE'                            # Not env variable. uses DEFAULT_PYTZ_TIMEZONE.
STOCKLOOK_EMAIL = 'STOCKLOOK_EMAIL'                        # Synonymous with GMAIL_EMAIL
STOCKLOOK_NOTIFY_ADDRESS = 'STOCKLOOK_NOTIFY_ADDRESS'
TWITTER_APP_KEY = 'STOCKLOOK_TWITTER_APP_KEY'
TWITTER_APP_SECRET = 'STOCKLOOK_TWITTER_APP_SECRET'
TWITTER_CLIENT_KEY = 'STOCKLOOK_TWITTER_CLIENT_KEY'
TWITTER_CLIENT_SECRET = 'STOCKLOOK_TWITTER_CLIENT_SECRET'


ENVIRONMENT_VARIABLES = [
    BITMEX_KEY, BITMEX_SECRET,
    BITTREX_KEY, BITTREX_SECRET,
    COINBASE_SECRET, COINBASE_KEY,
    CRYPTOPIA_KEY, CRYPTOPIA_SECRET,
    GDAX_SECRET, GDAX_KEY, GDAX_PASSPHRASE,
    GMAIL_EMAIL, GMAIL_PASSWORD,
    POLONIEX_KEY, POLONIEX_SECRET,
    STOCKLOOK_NOTIFY_ADDRESS, STOCKLOOK_EMAIL,
    TWITTER_CLIENT_SECRET, TWITTER_CLIENT_KEY,
    TWITTER_APP_SECRET, TWITTER_APP_KEY
]
# Variables in this list will be searched
# for in the os.environment and added to config.

VAR_SYNONYMS = {
    STOCKLOOK_EMAIL: GMAIL_EMAIL,
}
BITMEX_SETTINGS_DIR = 'BITMEX_SETTINGS_DIR'

db_type = 'mysql'
db_api = 'pymysql'
host = 'localhost'
port = '3306'
username = 'gdaxer'
database = 'gdax'
# GDAX_FEED_URL_KWARGS
# Because SQLite couldn't hang.


config = {
              'GDAX_FEED_URL_KWARGS': {
                    'drivername':  "{}+{}".format(db_type, db_api),
                    'host':  host or None,
                    'port':  port or None,
                    'username':  username or None,
                    'password':  None,
                    'database':  database or None
                                   },
              DATA_DIRECTORY: DEFAULT_DATA_DIRECTORY,
              LOG_LEVEL: DEFAULT_LOG_LVL,
              PYTZ_TIMEZONE: DEFAULT_PYTZ_TIMEZONE,
}
"""
Global config dictionary is imported and used by most classes that require an API or database
connection in the stocklook library.

The stocklook.utils.security.Credentials object uses this dictionary to
retrieve/store usernames and API Keys while securely storing API secrets/passphrases
and passwords in the encrypted facilities provided by the keyring package.
"""
config.update({var: env.get(var, None)
               for var in ENVIRONMENT_VARIABLES})
config[GMAIL_EMAIL] = config[STOCKLOOK_EMAIL]


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


logging.basicConfig(level=config.get('LOG_LEVEL', DEFAULT_LOG_LVL))
# When update_config method is called and if LOG_LEVEL is available
# it will override this default.
# Also probably subsequent calls to logging.basicCOnfig would override this.
