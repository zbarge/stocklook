from datetime import datetime
from simplejson.errors import JSONDecodeError
from time import sleep
import pandas as pd
import requests


ETH = 'ETH'
ETH_PRICE_URL = 'https://etherchain.org/api/statistics/price'
ETH_CHAIN_STATS_URL = 'https://api.blockcypher.com/v1/eth/main'


def eth_get_price_frame(begin_date=None, end_date=None):
    res = requests.get(ETH_PRICE_URL).json()['data']
    df = pd.DataFrame(data=res, index=range(len(res)))
    df.loc[:, 'time'] = pd.to_datetime(df.loc[:, 'time'], errors='coerce')

    if begin_date:
        df = df.loc[df['time'] > begin_date, :]

    if end_date:
        df = df.loc[df['time'] < end_date, :]

    return df


def eth_get_chain_stats():
    """
    Returns a dict snapshot of info about the ETH blockchain.

    Example:

    {'previous_url': 'https://api.blockcypher.com/v1/eth/main/blocks/004cc9d90eea8c9a8a55a58a7bdea9bd57bdf25daffb24c8302ac50a452e5743',
    'low_gas_price': 5000000000,
    'peer_count': 144,
    'high_gas_price': 21320232122,
    'latest_url': 'https://api.blockcypher.com/v1/eth/main/blocks/2c6e2e3ea3a59147fdbdaab2400a511955b89fb451611fa7af659804ab4da127',
    'unconfirmed_count': 4234, 'name': 'ETH.main', 'height': 4825457,
    'last_fork_hash': '5a78fdcd8376fdd01d514fbec113de641b1b9d993bdf660e91965e201f9b7fe5',
    'hash': '2c6e2e3ea3a59147fdbdaab2400a511955b89fb451611fa7af659804ab4da127',
    'time': '2017-12-30T18:40:02.147746029Z',
    'previous_hash': '004cc9d90eea8c9a8a55a58a7bdea9bd57bdf25daffb24c8302ac50a452e5743',
    'last_fork_height': 4825453,
    'medium_gas_price': 20000000000}
    """
    try:
        return requests.get(ETH_CHAIN_STATS_URL).json()
    except (requests.exceptions.ConnectionError, JSONDecodeError):
        sleep(1)
        return eth_get_chain_stats()


def eth_notify_on_block_height(block_no, to_address=None, times_to_ping=1):
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

    # Variables keep track of
    # time between seen blocks.
    time_diffs = list()
    last_height = 0
    last_time = None

    def avg_time_diff():
        if len(time_diffs) >= 2:
            return sum(time_diffs)/len(time_diffs)
        return 0

    # Loop and check the block height.
    while True:
        stats = eth_get_chain_stats()
        block_height = stats['height']

        # Reasons to break/continue
        if block_height >= block_no:
            break
        if last_height and last_height == block_height:
            sleep(avg_time_diff() or 45)
            continue

        # Tracking time difference
        t = datetime.now()
        if last_time is not None:
            last_diff = block_height - last_height
            t_diff = (t-last_time).total_seconds()/last_diff
            time_diffs.append(t_diff)
        else:
            # Time difference vars set the first time.
            last_height = block_height
            last_time = t

        secs_left = avg_time_diff() or 45
        block_diff = block_no - block_height

        # Calculate time to next check
        if block_diff > 30:
            interval = secs_left * 30
        elif block_diff < 2:
            interval = secs_left / 3
        else:
            interval = secs_left * (block_diff * .8)

        hours_till = round(secs_left * block_diff / 60 / 60, 2)

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
    msg = "ALERT: The current ETH block height is: " \
          "{}!".format(block_height)

    for i in range(times_to_ping):
        send_message(to_address, msg)
        sleep(5)

if __name__ == '__main__':
    #df = eth_get_price_frame()
    #print(df.head(5))
    eth_notify_on_block_height(4936270)