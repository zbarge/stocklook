import json
from stocklook.crypto.bittrex.api import Bittrex


def bittrex_make_positions_snapshot(bx_api=None, balances=None, output_path=None):
    """
    Creates a .json file with a snapshots
    of all positions in the bittrex account.

    :param bx_api:
    :param balances:
    :param output_path:
    :return:
    """
    if balances is None:
        if bx_api is None:
            bx_api = Bittrex()

        positions = bx_api.get_balances()

        if not positions['success']:
            raise Exception("Unable to retrieve position "
                            "balance: {}".format(positions))

        content = positions['message']
    else:
        content = balances

    if output_path is None:
        import os
        from stocklook.config import config, DATA_DIRECTORY
        output_path = os.path.join(config[DATA_DIRECTORY], 'bittrex_positions.json')

    with open(output_path, 'w') as fh:
        json.dump(content, fh)

    return output_path, content



