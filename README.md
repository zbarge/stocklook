stocklook
=========

A Python based cryptocurrency and stock exchange analysis toolset that I'm working on for personal use.
One end-goal is to algo-trade gdax with limit orders on 5-15 minute timeframes.
Another end-goal is to aggregate/analyze longer-term price movements in crypto/stock markets.

Many crypto python libraries have limited functionality and documentation in the code so I figured it would be better to
design a multi-exchange library from scratch.
I will lean on pre-built libraries if they're well-maintained and/or solve a significant problem.


APIs:
---------

Coinbase: light wrapper around coinbase client
Gdax: custom API/database wrapper for managing account/trading and price history
Poloniex: custom API/wrapper for getting price history.
Yahoo Finance (broken)


Configuration:
--------------
Configuration variables are stored in global variable stocklook.config.config(dict). User input may be required
on Object initialization to figure out credentials unless they've been previously cached or added to this dictionary.
Passwords & secrets are always cached safely using the keyring library.

Update os.environ with the following credentials to have them auto-update config:

coinbase: COINBASE_KEY
poloniex: POLONIEX_KEY
GDAX: GDAX_KEY
GMAIL: STOCKLOOK_EMAIL

You can update global configuration like so:

    from stocklook.config import update_config, config
    my_config = {
        'DATA_DIRECTORY': 'C:/Users/me/stocklook_data'
        'COINBASE_KEY': 'mycoinbasekey',
        'COINBASE_SECRET': 'mycoinbasesecret',
        'GDAX_KEY': 'mygdaxkey',
        'GDAX_SECRET': 'mygdaxsecret',
        'GDAX_PASSPHRASE': 'mygdaxpassphrase',
        'GMAIL_EMAIL': 'mygmailemail@gmail.com',
        'GMAIL_PASSWORD': 'mygmailpassword',
        'LOG_LEVEL': logging.DEBUG,
        'PYTZ_TIMEZONE': 'US/Pacific',

        # SQLAlchemy URL kwargs
        'GDAX_FEED_URL_KWARGS': {
                                'drivername': 'mysql+pymysql',
                                'host': 'localhost',
                                'port': None,
                                'username': 'dbuser',
                                'password': 'dbpass',
                                'database': 'dbname'
                               },
    }

    # method 1
    update_config()

    # method 2 (same as method 1)
    config.update(my_config)


Examples
--------

Accessing Coinbase to view accounts:

    from stocklook.crypto.coinbase_api import CoinbaseClient

    c = CoinbaseClient()

    # method 1 - access accounts via coinbase library
    obj = c.get_accounts()
    accounts = obj.response.json['data']
    for account in accounts:
        print("{}: {}".format(account['currency']: account['id'])

    # method 2 - parses accounts into dictionary upon access.
    usd_account = c.accounts['USD']


Accessing Gdax to buy some coin:

    from stocklook.crypto.gdax import Gdax, GdaxOrder

    g = Gdax()
    g.deposit_from_coinbase('USD', 100)

    o = GdaxOrder('LTC-USD', order_type='market', amount=100)
    o.post()


Accessing Poloniex chart data:
    # In progress



To-do List:
-----------

    [] Add tests for gdax, coinbase
    [] fix yahoo api
    [] add Poloniex account management code






