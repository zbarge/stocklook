from stocklook.crypto.poloniex.api import Poloniex, polo_return_chart_data
from stocklook.utils.database import AlchemyDatabase, declarative_base


SQLPoloBase = declarative_base()


class PoloDatabase(AlchemyDatabase):
    def __init__(self, api=None, engine=None, session_maker=None):
        self.api = api
        AlchemyDatabase.__init__(
            self, engine=engine,
            session_maker=session_maker,
            declarative_base=SQLPoloBase)

