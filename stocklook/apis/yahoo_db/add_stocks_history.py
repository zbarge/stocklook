from stocklook.apis.yahoo_db.database import StockDatabase
symbols = ['MJNA', 'MRPHF', 'AMMJ',
               'TRTC', 'GRSO','CIIX', 'CANN',
               'PRMCF', 'MSRT', 'AERO', 'ACAN', 'AGTK', 'PRRE',
               'BTFL', 'CVSI', 'CBDS', 'CBIS', 'CGRW', 'CNAB', 'DEWM', 'DIDG', 'ERBB', 'GRNH',
               'HEMP', 'CRBP', 'INSY']

from stocklook.apis.yahoo_db.symbols import TD_AMERITRADE_ALL_LIST as SYMBOLS
START_DATE = '2015-01-01'
END_DATE = '2017-01-01'


def add_symbols(symbols, start_date, end_date):
    db = StockDatabase()
    session = db.get_session()
    for s in symbols:
        stock = db.get_stock(session, s)
        hist = db.update_historical(session, stock, start_date, end_date)
        if hist is not None:
            [print(h) for h in hist]
    session.commit()
    session.close()


if __name__ == '__main__':
    add_symbols(SYMBOLS, START_DATE, END_DATE)

