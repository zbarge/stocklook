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
from pandas import Timestamp, DateOffset
from datetime import datetime
from time import sleep
import requests


BTC_HISTORICAL_URL = 'http://api.coindesk.com/v1/bpi/historical/close.json'
BTC_BLOCK_HEIGHT_URL = 'https://blockchain.info/q/getblockcount'
BTC_NEXT_BLOCK_ETA_URL = 'https://blockchain.info/q/eta'
BTC_UNCONFIRMED_TX_CT_URL = 'https://blockchain.info/q/unconfirmedcount'
BTC_AVG_BLOCK_TIME_URL = 'https://blockchain.info/q/interval'

BITCOIN_INFO = [None, None]


def btc_get_price_usd():
    """
    Returns a float of the current
    BTC-USD price via the coindesk.com API.
    :return: (float)
    """
    b = BITCOIN_INFO
    if b[0] is None:

        res = requests.get(BTC_HISTORICAL_URL).json()
        i = sorted(res['bpi'].items())

        for date, price in reversed(i):
            b[0] = float(price)
            b[1] = Timestamp(date)
            break

    elif b[1] < datetime.now() - DateOffset(days=2):
        b[0] = None
        btc_get_price_usd()

    return b[0]


def btc_to_usd(btc_val):
    """
    Returns the USD value of a BTC denomination
    multiplying it by the current BTC-USD
    price using the coindesk.com API.
    :param btc_val: (float, int)
    :return: (float)
    """
    return btc_val * btc_get_price_usd()


def btc_get_block_height():
    """
    Returns an integer of the current
    BTC block height of the longest chain.
    :return: (int)
    """
    return int(requests.get(BTC_BLOCK_HEIGHT_URL).json())


def btc_get_secs_to_next_block():
    """
    Returns the estimated number of
    seconds until the next block is due.
    If the next block is later than
    expected a negative number may be returned.
    :return: (int)
    """
    return int(requests.get(BTC_NEXT_BLOCK_ETA_URL).json())


def btc_get_unconfirmed_tx_count():
    """
    Returns the number of currently
    unconfirmed transactions on the BTC network.
    :return:
    """
    return int(requests.get(BTC_UNCONFIRMED_TX_CT_URL).json())


def btc_get_avg_block_time():
    return int(requests.get(BTC_AVG_BLOCK_TIME_URL).json())


def btc_notify_on_block_height(block_no, to_address=None, times_to_ping=1):
    """
    Sends an alert once a BTC
    block height has been reached.

    :param block_no: (int)
        The desired block height to receive an alert for.
        The alert will send as soon as the block
        height has been reached or passed.

    :param to_address: (str, default None)
        None will default to stocklook.config[STOCKLOOK_NOTIFY_ADDRESS]
        :raises: KeyError when the address is None
                 and the default is not found in config.

    :param times_to_ping (int, default 1)
        The number of times the alert will be sent out (5 seconds between).
        Set this to a high number if it's really important to know when the block
        height is reached... (like to avoid a fork dump or something).

    :return: (None)
    """
    from stocklook.utils.emailsender import send_message

    if to_address is None:
        from stocklook.config import config, STOCKLOOK_NOTIFY_ADDRESS
        to_address = config.get(STOCKLOOK_NOTIFY_ADDRESS, None)
        if to_address is None:
            raise KeyError("to_address was not provided and "
                           "STOCKLOOK_NOTIFY_ADDRESS config "
                           "variable not found.")
        action = "{} will be notified at block number " \
                 "{}.".format(to_address, block_no)
        print(action)
        # This would force the user to input
        # send_message credentials on first use rather
        # than when the alert is supposed to happen.
        send_message(to_address, action)

    # Loop and check the block height.
    while True:
        block_height = btc_get_block_height()

        if block_height >= block_no:
            break

        secs_left = abs(btc_get_secs_to_next_block())
        block_diff = block_no - block_height

        # Calculate the interval to
        # wait until the next check.
        if block_diff > 10:
            interval = secs_left * 10
        elif block_diff < 2:
            interval = secs_left / 3
        else:
            interval = secs_left * (block_diff * .8)

        hours_till = round(btc_get_avg_block_time()*block_diff/60/60,2)

        print("{}: "
              "Block Height: {}\n"
              "Blocks to target: {}\n"
              "Seconds/Minutes/Hours to next block: {}/{}/{}\n"
              "Estimated hours to target: {}\n"
              "Next check in {} seconds.".format(
               datetime.now(), block_height,
               block_diff, secs_left,
               round((secs_left / 60), 1),
               round(secs_left / 60 / 60, 1),
               hours_till,
               interval))
        sleep(interval)

    # If we've made it out of the above
    # loop we're at the desired block height.
    msg = "ALERT: The current BTC block height is: " \
          "{}!".format(block_height)

    for i in range(times_to_ping):
        send_message(to_address, msg)
        sleep(5)


if __name__ == '__main__':
    print(btc_get_secs_to_next_block())
    exit()
    for i in range(50):
        print(btc_get_price_usd())

