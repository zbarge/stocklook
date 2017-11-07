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
import pytest
import pandas as pd
from random import randint
from stocklook.config import config
from sqlalchemy import create_engine
from stocklook.utils.timetools import now
from stocklook.crypto.gdax import GdaxDatabase, Gdax, GdaxOrderSystem, GdaxOrder
from stocklook.crypto.gdax.order import GdaxTrailingStop, execute_trailing_stop


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
TEST_DB_PATH = os.path.join(FIXTURES_DIR, 'gdax_test.sqlite3')
TEST_ENGINE = create_engine('sqlite:///' + TEST_DB_PATH)


gdax = Gdax()
db = GdaxDatabase(gdax, engine=TEST_ENGINE)
sys = GdaxOrderSystem(gdax, db)

class FakeProduct:
    def __init__(self, start_price, increment=0.01):
        self.start_price = start_price
        self.increment = increment
        self._price = start_price

    @property
    def price(self):
        """
        May return same price
        may return price incremented
        may return price decremented
        that's the point...
        :return:
        """
        r = randint(2, 500)
        r2 = randint(2, 500)
        val = self._price * self.increment
        if r2 % 2 == 0:
            if r % 2 == 0:
                self._price += val
            else:
                self._price -= val
        return self._price

fake_prod = FakeProduct(57.50)


def test_order_trailing_stop():
    """
    Verifies the trailing stop method executes...
    checks and balances inside the method make sure
    the coin gets bought and sold.
    :return:
    """
    pytest.skip()

    pair = 'LTC-USD'
    size = 0.01
    stop_amt = 0.02

    order = execute_trailing_stop(pair, size, stop_amt=stop_amt)

    assert isinstance(order, GdaxTrailingStop)

def test_get_fills():

    product = 'LTC-USD'
    p_fmt = product.lower().replace('-', '_')
    fill_path = os.path.join(config['DATA_DIRECTORY'], '{}_fills_analysis.csv'.format(p_fmt))
    fill_path2 = os.path.splitext(fill_path)[0] + '.txt'
    dtypes = {'size': float, 'price': float, 'fee': float, 'trade_id': int,}

    if not os.path.exists(fill_path):
        fills = gdax.get_fills(product_id=product, paginate=True)
        df = pd.DataFrame(fills)
        df.to_csv(fill_path, index=False)
    else:
        df = pd.read_csv(fill_path, dtype=dtypes)
        params = {'after': df['trade_id'].max()}
        fills = gdax.get_fills(product_id=product, paginate=True, params=params)


    float_cols = ['size', 'price', 'fee']
    for c in float_cols:
        df.loc[:, c] = pd.to_numeric(df.loc[:, c], errors='coerce')

    df.loc[:, 'total'] = (df['size'] * df['price']) + df['fee']
    buys = df.loc[df['side'] == 'buy', :]
    sells = df.loc[df['side'] == 'sell', :]
    pnl = sells['total'].sum() - buys['total'].sum()
    fees = df['fee'].sum()

    text = "Product: {}\n" \
           "PNL: ${}\n" \
           "Total Fees: ${}\n" \
           "Total Bought: {}\n" \
           "Total Sold: {}".format(product, pnl, fees,
                                   buys['size'].sum(),
                                   sells['size'].sum())

    with open(fill_path2, 'w') as fh:
        fh.write(text)

# Comment out the parametrize decorator to speed this test up x3
#@pytest.mark.parametrize('coin', ['BTC-USD', 'LTC-USD', 'ETH-USD'])
def test_order_create_and_cancel(coin=None):
    """
    Ensures the order system will
    create, post, retrieve, and cancel an order.

    Although the orders are real - the quantity is miniscule
    and price is set to half of coin price to ensure the order
    is not executed.

    :param coin: (all three coins are tested)
    :return:
    """
    pytest.skip()
    if coin is None:
        coin = 'BTC-USD'

    # Check account balance because pointless test with 0 balance
    bal = gdax.get_account('USD').usd_value
    if bal < 3:
        pytest.skip("Skipping order test because 0 USD balance.")

    session = db.get_session()
    prod = gdax.get_product(coin)
    price = prod.price - (prod.price * 0.5)
    size = 0.01
    order = GdaxOrder(gdax,
                      coin,
                      order_type='limit',
                      side='buy',
                      price=price,
                      size=size)

    # Place order, retrieve it from Gdax, delete from Gdax
    res = sys.place_order(session, order)
    cres = gdax.get_orders(order_id=res.id)
    deleted = sys.cancel_order(session, res.id, commit=True)

    assert cres['id'] == order.id
    assert float(cres['price']) == float(order.price)
    assert float(cres['size']) == float(cres['size'])
    assert deleted[0] == order.id

    session.close()


if __name__ == '__main__':
    pytest.main()