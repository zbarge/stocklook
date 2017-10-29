import plotly
from plotly.tools import FigureFactory as FF
from datetime import datetime
import pandas.io.data as web
import os
from stocklook.apis.yahoo_db.database import StockDatabase, Stock

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
CHARTS_DIR = os.path.join(DATA_DIR, 'charts')

if not os.path.exists(CHARTS_DIR):
    os.mkdir(CHARTS_DIR)
db = StockDatabase()
symbols = ['URA', 'GDX']


START_DATE = [2016, 10, 1]
END_DATE = [2017, 3, 22]


def create_plotly_candlestick(symbol, start_date, end_date, filename=None):
    if filename is None:
        filename = os.path.join(CHARTS_DIR, '{}-{}-{}.html'.format(
            symbol, start_date.date(), end_date.date()))
    df = web.DataReader(symbol, 'yahoo', start_date, end_date)
    fig = FF.create_candlestick(df.Open, df.High, df.Low, df.Close, dates=df.index)
    plotly.offline.plot(fig, filename=filename)
    return filename


def create_main_file(filename, dirname=None):
    if dirname is None:
        dirname = CHARTS_DIR
    paths = []
    for dirname, subdirs, files in os.walk(dirname):
        for f in files:
            name, ext = os.path.splitext(f)
            if ext.lower() == '.html':
                paths.append(os.path.join(dirname, f))
    rows = ''.join(["<tr><td><a href='{}' target='blank'>{}</a></td></tr>".format(
                    f, os.path.basename(f))
                    for f in sorted(paths)])
    table = '<table><head>Stock Charts:</head><tr>{}</tr></table>'.format(rows)

    with open(filename, 'w') as outfile:
        outfile.write(table)

    return filename


def update_charts(symbols, start_date, end_date):

    for sym in symbols:
        create_plotly_candlestick(sym, start_date, end_date)


def update_all_charts():
    session = db.get_session()
    stocks = session.query(Stock).group_by(Stock.symbol).all()
    symbols = [s.symbol for s in stocks]
    update_charts(symbols, datetime(*START_DATE), datetime(*END_DATE))
    f = os.path.join(DATA_DIR, 'charts.html')
    create_main_file(f, CHARTS_DIR)

if __name__ == '__main__':
    #update_charts(symbols, datetime(*START_DATE), datetime(*END_DATE))
    update_all_charts()
