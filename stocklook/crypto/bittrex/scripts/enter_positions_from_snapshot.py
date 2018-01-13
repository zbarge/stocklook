import os
import json
from stocklook.crypto.bittrex.api import Bittrex, ORDERTYPE_MARKET
import logging as lg
logger = lg.getLogger(__name__)
logger.setLevel(lg.DEBUG)

FILE_PATH = ""
BASE_CURRENCY = "USD"


def bittrex_enter_positions_from_snapshot(buy_method=None, source_json=None, base_currency='USD'):
    """
    Reads a dictionary balance snapshot outputted by Bittrex.get_balances() and market buys
    the balance for each coin to match the position.

    :param buy_method: (callable, default None)
        Defaults to Bittrex.trade_buy and requires
        the following keyword arguments (example values not required):
            - market = 'BTC-USD'
            - order_type = stocklook.crypyto.bittrex.api.ORDERTYPE_MARKET
            - quantity = 10.15
    :param source_json: (list)
        A list of dictionary objects like what's returned by
        Bittrex.get_balances()['message']

    :param base_currency: (str, default 'USD')
        The currency that will be used to enter these positions.

    :return:
    """
    if buy_method is None:
        bx_api = Bittrex()
        buy_method = bx_api.trade_buy

    if source_json is None:
        from stocklook.config import config, DATA_DIRECTORY
        source_path = os.path.join(
            config[DATA_DIRECTORY], 'bittrex_positions.json')

        if not os.path.exists(source_path):
            raise OSError("Unable to find positions snapshot: "
                          "{}".format(source_path))

        with open(source_path, 'r') as fh:
            source_json = json.load(fh)

    buys = list()
    for p in source_json:
        pair = p['Currency'] + '-' + base_currency
        qty = float(p['Balance'])
        logger.debug("Placing market buy order: {} {}".format(qty, pair))
        res = buy_method(
            market=pair,
            order_type=ORDERTYPE_MARKET,
            quantity=qty)
        buys.append(res)

    return buys


if __name__ == '__main__':
    with open(FILE_PATH, 'r') as fh:
        bittrex_enter_positions_from_snapshot(
            source_json=json.load(fh),
            base_currency=BASE_CURRENCY)
