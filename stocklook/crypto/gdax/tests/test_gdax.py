from stocklook.crypto.gdax import Gdax
import pytest
import os


class TestGdax:
    @pytest.fixture
    def gdax(self):
        return Gdax()

    def test_get_account_history(self, gdax: Gdax):
        pytest.skip("Skipping obnoxiously expensive calls to API.")
        history = gdax.get_account_ledger_history()
        fp = os.path.join(os.path.dirname('__file__'), 'fixtures', 'sample_history.csv')
        history.to_csv(fp, index=False)
        print(history)
