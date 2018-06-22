from stocklook.crypto import Gdax, CoinbaseClient, BitMEX, Poloniex, Bittrex
from stocklook.utils.security import Credentials
import logging as lg
logger = lg.getLogger(__name__)

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

    @property
    def accounts(self):
        return self._accounts

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
            kws = build_kwargs.get(t, dict())
            try:
                obj_c = obj(**kws)
                data[t] = obj_c
                if t == c.GDAX:
                    obj_c.ws.start()
            except Exception as e:
                errs.append((t, e))

        if errs and raise_on_error:
            raise Exception("An error has occured when building "
                            "the following accounts: {}".format(errs))

        return {'data': data, 'errors': errs}

    def get_balances(self):
        data, errs = dict(), list()
        p = self.poloniex
        if p is not None:
            try:
                data[c.POLONIEX] = p.return_balances(hide_zero=True)
            except Exception as e:
                errs.append((c.POLONIEX, e))

        p = self.gdax
        if p is not None:
            # TODO: Add method
            try:
                data[c.GDAX] = p.get_balances(hide_zero=True)
            except Exception as e:
                errs.append((c.GDAX, e))
                raise

        p = self.bittrex
        if p is not None:
            try:
                data[c.BITTREX] = p.get_balances()
            except Exception as e:
                errs.append((c.BITTREX, e))

        p = self.coinbase
        if isinstance(p, CoinbaseClient):
            # TODO: Add method
            try:
                data[c.COINBASE] = p.get_balances(hide_zero=True)
            except Exception as e:
                errs.append((c.COINBASE, e))

        p = self.bitmex
        if isinstance(p, BitMEX):
            try:
                data[c.BITMEX] = p.funds()
            except Exception as e:
                errs.append((c.BITMEX, e))
        if errs:
            logger.error(errs)
        return {'data': data, 'errors': errs}

    def __getattr__(self, x):
            try:
                return self._accounts[x]
            except KeyError:
                return None










