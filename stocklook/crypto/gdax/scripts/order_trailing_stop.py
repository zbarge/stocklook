import os

PAIR = 'ETH-USD'
SIZE = 2.89
STOP_AMOUNT = 8.50
STOP_PERCENT = None
TARGET_SELL_PRICE = 314.87
NOTIFY_ADDRESS = os.environ['CELL_NOTIFY_ADDRESS']
BUY_NEEDED_COIN = False


if __name__ == '__main__':
    from stocklook.crypto.gdax.order import execute_trailing_stop
    execute_trailing_stop(PAIR,
                          SIZE,
                          stop_amt=STOP_AMOUNT,
                          stop_pct=STOP_PERCENT,
                          target=TARGET_SELL_PRICE,
                          notify=NOTIFY_ADDRESS,
                          buy_needed=BUY_NEEDED_COIN)

