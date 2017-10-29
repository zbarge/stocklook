from stocklook.apis.yahoo_db.database import StockDatabase
symbols = ['MJNA', 'MRPHF', 'AMMJ',
               'TRTC', 'GRSO','CIIX', 'CANN',
               'PRMCF', 'MSRT', 'AERO', 'ACAN', 'AGTK', 'PRRE',
               'BTFL', 'CVSI', 'CBDS', 'CBIS', 'CGRW', 'CNAB', 'DEWM', 'DIDG', 'ERBB', 'GRNH',
               'HEMP', 'CRBP', 'INSY']

from stocklook.apis.yahoo_db.symbols import TD_AMERITRADE_OIL_LIST as SYMBOLS


def add_symbols(symbols):
    db = StockDatabase()
    session = db.get_session()
    for s in symbols:
        stock = db.get_stock(session, s)
        quote = db.get_quote(session, stock)
        print(quote)
    session.commit()
    session.close()


if __name__ == '__main__':
    add_symbols(SYMBOLS)

