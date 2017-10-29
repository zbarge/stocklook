import os
from yahoo_finance import Share
from stocklook.utils.formatters import DictParser, format_dollar_letter_conversions
from pandas import DataFrame, Timestamp, read_excel

field_map = {
'ExDividendDate': 'date_dividend_ex',
'LastTradeDate': 'date_last_traded',
'DividendPayDate': 'dividend_pay_date',
'DividendShare': 'dividend_share',
'DividendYield': 'dividend_yield',
'ChangeFromTwoHundreddayMovingAverage': 'price_change_200_day_avg',
'ChangeFromFiftydayMovingAverage': 'price_change_50_day_avg',
'ChangeFromYearHigh': 'price_change_year_high',
'ChangeFromYearLow': 'price_change_year_low',
'EBITDA': 'ebitda',
'EarningsShare': 'eps_current', # higher current eps means better value
'EPSEstimateCurrentYear': 'eps_current_year', #higher eps means better value
'EPSEstimateNextQuarter': 'eps_next_quarter',
'EPSEstimateNextYear': 'eps_next_year',
'PriceEPSEstimateCurrentYear': 'eps_price_est_current_year',
'PriceEPSEstimateNextYear': 'eps_price_est_next_year',
'ErrorIndicationreturnedforsymbolchangedinvalid': 'errored_symbol',
'HighLimit': 'limit_high',
'LowLimit': 'limit_low',
'MarketCapitalization': 'market_cap',
'PercentChangeFromTwoHundreddayMovingAverage': 'pct_change_200_day_avg',
'PercentChangeFromFiftydayMovingAverage': 'pct_change_50_day_avg',
'PercentChange': 'pct_change_current',
'Change_PercentChange': 'pct_change_today',
'PercebtChangeFromYearHigh': 'pct_change_year_high',
'PercentChangeFromYearLow': 'pct_change_year_low',
'ChangeinPercent': 'pct_day_change',
'PERatio': 'pe_ratio',
'PEGRatio': 'peg_ratio',
'TwoHundreddayMovingAverage': 'price_200_day_moving_avg',
'FiftydayMovingAverage': 'price_50_day_moving_avg',
'Ask': 'price_ask',
'Bid': 'price_bid',
'PriceBook': 'price_book',
'BookValue': 'price_book_value',
'Change': 'price_day_change',
'DaysHigh': 'price_day_high',
'DaysLow': 'price_day_low',
'Open': 'price_day_open',
'PreviousClose': 'price_last_close',
'LastTradePriceOnly': 'price_last_trade',
'PriceSales': 'price_sales', # lower ratio means better invest
'YearHigh': 'price_year_high',
'YearLow': 'price_year_low',
'OneyrTargetPrice': 'price_year_target',
'DaysRange': 'range_day',
'YearRange': 'range_year',
'ShortRatio': 'short_ratio', # higher short ratio gives a squeeze when shorts have to cover = strong rally
'StockExchange': 'stock_exchange',
'Symbol': 'symbol',
'Name': 'symbol_name',
'Currency': 'trade_currency',
'Volume': 'volume_day',
'AverageDailyVolume': 'volume_day_avg',
}
yahoo_historical_map = {
    'Date': 'date_last_traded',
    'Close': 'price_day_close',
    'Symbol': 'symbol',
    'Volume': 'volume_day',
    'High': 'price_day_high',
    'Low': 'price_day_low',
}
yahoo_dtype_map = {
'date_dividend_ex': Timestamp,
'date_last_traded': Timestamp,
'dividend_pay_date': Timestamp,
'dividend_share': float,
'dividend_yield': float,
'ebitda': float,
'eps_current': float,
'eps_current_year': float,
'eps_next_quarter': float,
'eps_next_year': float,
'eps_price_est_current_year': float,
'eps_price_est_next_year': float,
'errored_symbol': bool,
'limit_high': float,
'limit_low': float,
'market_cap': float,
'pct_change_200_day_avg': float,
'pct_change_50_day_avg': float,
'pct_change_current': float,
'pct_change_today': float,
'pct_change_year_high': float,
'pct_change_year_low': float,
'pct_day_change': float,
'pe_ratio': float,
'peg_ratio': float,
'price_200_day_moving_avg': float,
'price_50_day_moving_avg': float,
'price_ask': float,
'price_bid': float,
'price_book': float,
'price_book_value': float,
'price_change_200_day_avg': float,
'price_change_50_day_avg': float,
'price_change_year_high': float,
'price_change_year_low': float,
'price_day_change': float,
'price_day_high': float,
'price_day_low': float,
'price_day_open': float,
'price_last_close': float,
'price_last_trade': float,
'price_sales': float,
'price_year_high': float,
'price_year_low': float,
'price_year_target': float,
'range_day': str,
'range_year': str,
'short_ratio': float,
'stock_exchange': str,
'symbol': str,
'symbol_name': str,
'trade_currency': str,
'volume_day': int,
'volume_day_avg': int,
}
format_dollars_fields = ['ebitda', 'market_cap']


def get_stock_data(share, map_of_fields):
    share_map = share.__dict__['data_set']
    return DictParser.parse_dtypes({value: share_map.get(key, None)
                                    for key, value in
                                    map_of_fields.items()},
                                   yahoo_dtype_map,
                                   default=str,
                                   raise_on_error=False)


def get_stock_data_historical(share, start_date, end_date):
    share_list = share.get_historical(start_date, end_date)
    return [DictParser.parse_dtypes({value: s.get(key, None)
                                     for key, value in
                                     yahoo_historical_map.items()},
                                    yahoo_dtype_map,
                                    default=str,
                                    raise_on_error=False)
            for s in share_list]


def generate_stock_updates(file_path=None):
    if file_path is None:
        file_path = 'C:/Users/Zeke/Google Drive/Documents/Financial/td_ameritrade/'\
                    'Watchlist_Uranium_2017-02-18.xlsx'
    df = read_excel(file_path)

    new_data = []
    for i in range(df.index.size):
        row = df.iloc[i]
        share = Share(row['Symbol'])
        new_data.append(share.__dict__.get('data_set', {}))

    path_out = os.path.splitext(file_path)[0] + '-updated.csv'
    new_df = DataFrame(new_data, index=range(len(new_data)))
    new_df.to_csv(path_out)


def format_stock_dataframe(df):
    for f in format_dollars_fields:
        if f in df.columns:
            df.loc[:, f] = df.loc[:, f].apply(format_dollar_letter_conversions)
