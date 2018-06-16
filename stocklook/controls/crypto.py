from stocklook.crypto import Gdax, CoinbaseClient, BitMEX, Poloniex, Bittrex
from stocklook.utils.security import Credentials
c = Credentials
CRYPTO_OBJ_MAP = {
    c.GDAX: Gdax,
    c.COINBASE: CoinbaseClient,
    c.BITMEX: BitMEX,
    c.POLONIEX: Poloniex,
    c.BITTREX: Bittrex,
}


class CryptoController:
    def __init__(self):
        self._accounts = dict()

    def build_accounts(self, build_kwargs=None, acc_types=None, raise_on_error=False):
        errs, data = list(), self._accounts
        data_keys = list(data.keys())
        if acc_types is None:
            acc_types = [c.GDAX, c.BITMEX, c.BITTREX, c.COINBASE, c.POLONIEX]
        build_kwargs = (build_kwargs if build_kwargs is not None else dict())
        for t in acc_types:
            if t in data_keys:
                continue
            obj = CRYPTO_OBJ_MAP[t]
            try:
                build_kwargs[t]
            except KeyError:
                build_kwargs[t] = dict()

            try:
                data[t] = obj(**build_kwargs[t])
            except Exception as e:
                errs.append((t, e))

        if errs and raise_on_error:
            raise Exception("An error has occured when building "
                            "the following accounts: {}".format(errs))

        return data, errs







