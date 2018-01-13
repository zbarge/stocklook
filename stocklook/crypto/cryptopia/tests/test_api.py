from stocklook.crypto.cryptopia.api import Cryptopia
from stocklook.utils.database import db_describe_dict


def test_cryptopia_get_markets():
    c = Cryptopia()
    mkts = c.get_markets()

    for ticker in mkts[0]:
        ticker_fmt = {camel_case_to_under_score(k): v
                      for k, v in ticker.items()}
        db_describe_dict(ticker_fmt, table_name='ctopia_markets')
        break