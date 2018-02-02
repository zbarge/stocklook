from stocklook.crypto.cryptopia.api import Cryptopia
from stocklook.utils.database import db_describe_dict
from stocklook.utils.formatters import camel_case_to_under_score, camel_case_to_under_score_dict

api = Cryptopia()


def test_ctopia_get_markets():

    mkts = api.get_markets()

    for ticker in mkts[0]:
        ticker_fmt = {camel_case_to_under_score(k): v
                      for k, v in ticker.items()}
        db_describe_dict(ticker_fmt, table_name='ctopia_markets')
        ticker['ask_price']
        ticker['base_volume']
        ticker['bid_price']
        ticker['buy_base_volume']
        ticker['buy_volume']
        ticker['change']
        ticker['close']
        ticker['high']
        ticker['label']
        ticker['last_price']
        ticker['low']
        ticker['open']
        ticker['sell_base_volume']
        ticker['sell_volume']
        ticker['trade_pair_id']
        ticker['volume']
        break


def test_ctopia_get_balance():
    currencies = ['BTC', 'LTC', 'ETH', 'NEO']
    for currency in currencies:
        entries = api.get_balance(currency)
        print(entries)
        break


def test_ctopia_get_currencies():
    currencies = api.get_currencies()[0]

    for c_data in currencies:
        c_data = camel_case_to_under_score_dict(c_data)
        for k, v in sorted(c_data.items()):
            print("{}: {}".format(k, v))
        print("\n\n")

        c_data['deposit_confirmations']
        c_data['id']
        c_data['is_tip_enabled']
        c_data['min_base_trade']
        c_data['name']
        c_data['status']
        c_data['symbol']
        c_data['withdraw_fee']

        db_describe_dict(c_data, 'ctopia_currencies')
        break

def test_ctopia_get_market_history():

    history = api.get_market_history