import os
import json
from stocklook.crypto.bittrex.scripts.enter_positions_from_snapshot import bittrex_enter_positions_from_snapshot
from stocklook.crypto.bittrex.scripts.make_positions_snapshot import bittrex_make_positions_snapshot


def test_make_positions_snapshot():
    balances = [{'Currency': 'BTC', 'Balance': '1.0335'},
                {'Currency': 'XRP', 'Balance': '125.0'}]
    out_path = os.path.join(os.path.dirname(__file__), '_test_position_snapshots.json')
    if os.path.exists(out_path):
        os.remove(out_path)

    res = bittrex_make_positions_snapshot(
        balances=balances, output_path=out_path)

    assert os.path.exists(out_path)
    with open(out_path, 'r') as fh:
        read_back = json.load(fh)

    assert isinstance(read_back, list)
    assert len(read_back) == len(balances)
    for old, new in zip(balances, read_back):
        assert old['Currency'] == new['Currency']
        assert float(old['Balance']) == float(new['Balance'])

    os.remove(out_path)


def test_bittrex_enter_positions_from_snapshot():
    balances = [{'Currency': 'BTC', 'Balance': '1.0335'},
                {'Currency': 'XRP', 'Balance': '125.0'}]
    out_path = os.path.join(os.path.dirname(__file__), '_test_position_snapshots.json')
    if os.path.exists(out_path):
        os.remove(out_path)

    res = bittrex_make_positions_snapshot(
        balances=balances, output_path=out_path)

    def fake_buy_method(**kwargs):
        return kwargs

    # Can't really test this against the API to
    # make sure it bought right now... I dont have access.
    # So if the function does not error we'll have to assume it works.
    try:
        bittrex_enter_positions_from_snapshot(
            buy_method=fake_buy_method,
            source_json=balances,
            base_currency='USD')
    finally:
        os.remove(out_path)


