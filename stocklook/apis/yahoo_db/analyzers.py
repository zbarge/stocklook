from stocklook.apis.yahoo_db.database import engine, StockDatabase
import pandas as pd
from collections import Counter, defaultdict
import enum
PCC200 = 'pct_change_200_day_avg'
PCC50 = 'pct_change_50_day_avg'


class ZekeRating(enum.Enum):
    buy_strong = 4
    buy = 3
    hold = 2
    sell = 1
    sell_strong = 0

class BuyType(enum.Enum):
    growth = 0
    value = 1
    income = 2


class StockAnalyzer:
    def __init__(self, stock):
        self._stock = stock
        self.analyze(stock)

    def analyze(self, quote):
        scores = []

    def score_on_values(self, x, min=-1000):
        if not x:
            return ZekeRating.sell_strong
        if x < -100000:
            return ZekeRating.sell_strong
        elif x < 0:
            return ZekeRating.sell
        elif x < 250000:
            return ZekeRating.hold
        else:
            return ZekeRating.buy


def analyze_stocks(score_path, data_path, df=None):
    if df is None:
        df = pd.read_sql("SELECT * FROM quotes ORDER BY date_inserted DESC", engine, parse_dates=['date_inserted'])
    df.sort_values(['date_last_traded', 'date_inserted'], ascending=[False, False], inplace=True)
    df.drop_duplicates('symbol', inplace=True)
    ranks = {}
    gathers = (
        ('ebitda', False, ((df.loc[:, 'ebitda'] != 0) & (df.loc[:, 'ebitda'] > -100000))),
        ('eps_current', False, (df.loc[:, 'eps_current'] != 0)),
        ('eps_current_year', False, (df.loc[:, 'eps_current_year'] != 0)),
        ('eps_next_year', False, (df.loc[:, 'eps_next_year'] != 0)),
        #('market_cap', False, (df.loc[:, 'market_cap'] != 0)),
        ('price_sales', True, (df.loc[:, 'price_sales'] != 0)),
        ('price_book', True, ((df.loc[:, 'price_book'] > -5) & (df.loc[:, 'price_book'] != 0))),
        ('price_book_value', True, (df.loc[:, 'price_book_value'] != 0)),
        (PCC200, False, (df.loc[:, PCC200] > -60)),
        (PCC50, False, (df.loc[:, PCC50] != 0)),
        ('pe_ratio', True, (df.loc[:, 'pe_ratio'] != 0)),
        ('peg_ratio', True, (df.loc[:, 'peg_ratio'] != 0)),
        ('volume_day_avg', True, (df.loc[:, 'volume_day_avg'] > 100000)),
    )
    for field, asc, mask in gathers:
        ranks[field] = df.sort_values(field, ascending=asc)\
                         .dropna(subset=[field])\
                         .loc[mask, 'symbol']\
                         .tolist()
    scores = Counter()
    stats = defaultdict(list)
    df.set_index(df.loc[:, 'symbol'], inplace=True)

    for field, rank_set in ranks.items():
        if not rank_set:
            continue
        rank_set.reverse()
        adds = 100 / len(rank_set)
        for score, symbol in enumerate(rank_set):
            scores[symbol] += int(adds * (score + 1))
            stats[symbol].append((field, score))
        rank_set.reverse()

    print(scores)
    print(stats)

    finals = []
    for symbol, total_score in scores.items():
        row = {'symbol': symbol,
               'total_score': total_score}
        for field, score in stats[symbol]:
            row[field + "_score"] = score
            row[field] = df.loc[symbol, field]
        finals.append(row)
    score_df = pd.DataFrame(finals, index=range(len(finals)))
    score_df.to_csv(score_path, index=False)
    df.to_csv(data_path, index=False)



if __name__ == '__main__':
    from stocklook.apis.yahoo_db.symbols import NORTH_AMERICAN_MARIJUANA_INDEX as symbols
    sql = "SELECT * FROM quotes WHERE symbol IN ({});".format(','.join(["'{}'".format(s) for s in symbols]))
    df = pd.read_sql(sql, engine, parse_dates=['date_inserted'])
    score_path = "C:/Users/Zeke/Desktop/stock_scores.csv"
    data_path = "C:/Users/Zeke/Desktop/stock_scores_data.csv"
    print(df)

    analyze_stocks(df)