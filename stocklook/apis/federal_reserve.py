#!/usr/bin/env python
""" fred.py
https://github.com/hamiltonkibbe/stocks/blob/master/sources/fred.py
Python interface to the St.Louis Fed's Federal Reserve Economic Data
"""

from .config import FRED_API_KEY
import urllib
from xml.etree import ElementTree
from datetime import date
from time import mktime, strptime

indicators = {'bank_prime_loan_rate': 'DPRIME',
              'primary_credit_rate': 'DPCREDIT',
              'consumer_price_index': 'CPIAUCSL',
              'real_gdp': 'GDPC1',
              'civilian_unemployment_rate': 'UNRATE',
              'm2_money_stock': 'M2',
              'dow_jones_industrial': 'DJIA',
              'dow_jones_composite': 'DJCA',
              'dow_jones_utility': 'DJUA',
              'dow_jones_transportation': 'DJTA',
              'sp_500': 'SP500',
              'libor_12mo': 'USD12MD156N',
              'libor_6mo': 'USD6MTD156N',
              'libor_3mo': 'USD3MTD156N',
              'libor_1mo': 'USD1MTD156N',
              'libor_1wk': 'USD1WKD156N',
              'libor_overnight': 'USDONTD156N',
              'wilshire_2500_pi': 'WILL2500PR',
              'wilshire_2500_tmi': 'WILL2500IND',
              'wilshire_4500_pi': 'WILL4500PR',
              'wilshire_4500_tmi': 'WILL4500IND',
              'wilshire_5000_pi': 'WILL5000PR',
              'wilshire_5000_tmi': 'WILL5000IND',
              'wilshire_5000_full_cap_pi': 'WILL5000PRFC',
              'wilshire_5000_full_cap_tmi': 'WILL5000INDFC',
              'wilshire_internet_tmi': 'WILLWWW',
              'wilshire_small_cap_250_pi': 'WILLSMLCAP250PR',
              'wilshire_small_cap_250_tmi': 'WILLSMLCAP250',
              'wilshire_us_micro_cap_pi': 'WILLMICROCAPPR',
              'wilshire_us_micro_cap_tmi': 'WILLMICROCAP',
              'wilshire_us_small_cap_pi': 'WILLSMLCAPPR',
              'wilshire_us_small_cap_tmi': 'WILLSMLCAP',
              'wilshire_us_small_cap_growth_pi': 'WILLSMLCAPGRPR',
              'wilshire_us_small_cap_growth_tmi': 'WILLSMLCAPGR',
              'wilshire_us_small_cap_value_pi': 'WILLSMLCAPVALPR',
              'wilshire_us_small_cap_value_tmi': 'WILLSMLCAPVAL',
              'wilshire_us_mid_cap_pi': 'WILLMIDCAPPR',
              'wilshire_us_mid_cap_tmi': 'WILLMIDCAP',
              'wilshire_us_mid_cap_growth_pi': 'WILLMIDCAPGRPR',
              'wilshire_us_mid_cap_growth_tmi': 'WILLMIDCAPGR',
              'wilshire_us_mid_cap_value_pi': 'WILLMIDCAPVALPR',
              'wilshire_us_mid_cap_value_tmi': 'WILLMIDCAPVAL',
              'wilshire_us_large_cap_pi': 'WILLLRGCAPPR',
              'wilshire_us_large_cap_tmi': 'WILLLRGCAP',
              'wilshire_us_large_cap_growth_pi': 'WILLLRGCAPGRPR',
              'wilshire_us_large_cap_growth_tmi': 'WILLLRGCAPGR',
              'wilshire_us_large_cap_value_pi': 'WILLLRGCAPVALPR',
              'wilshire_us_large_cap_value_tmi': 'WILLLRGCAPVAL',
              'wilshire_us_reit_pi': 'WILLREITPR',
              'wilshire_us_reit_tmi': 'WILLREITIND',
              'wilshire_us_resi_pi': 'WILLRESIPR',
              'wilshire_us_resi_tmi': 'WILLRESIND'
              }


def _get_url(fname):
    return 'http://api.stlouisfed.org/fred/series/observations?series_id=' + fname + '&api_key=' + FRED_API_KEY


def _get_raw(fname):
    tree = ElementTree.fromstring(urllib.urlopen(_get_url(fname)).read())
    observations = tree.iter('observation')
    # Get dates
    dates = [date.fromtimestamp(mktime(strptime(obs.get('date'), '%Y-%m-%d'))) for obs in tree.iter('observation')]
    # Get values
    values = [obs.get('value') for obs in tree.iter('observation')]
    # FRED uses a "." to indicate that there is no data for a given date,
    # so we just do a zero-order interpolation here
    for i in range(len(values)):
        if values[i] == '.':
            values[i] = values[i-1]

    # Return dates and values in a nested list
    data = []
    for i in range(len(dates)):
        data.append[dates[i], float(values[i])]

    return data

def get(indicator):
    return _get_raw(indicators[indicator])