import pandas as pd
import requests


ETHERIUM_SYMBOL = 'ETH'
ETHERIUM_PRICE_JSON_URL = 'https://etherchain.org/api/statistics/price'


def get_etherium_price_dataframe(begin_date=None, end_date=None):
    res = requests.get(ETHERIUM_PRICE_JSON_URL).json()['data']
    df = pd.DataFrame(data=res, index=range(len(res)))
    df.loc[:, 'time'] = pd.to_datetime(df.loc[:, 'time'], errors='coerce')

    if begin_date:
        df = df.loc[df['time'] > begin_date, :]

    if end_date:
        df = df.loc[df['time'] < end_date, :]

    return df


if __name__ == '__main__':
    df = get_etherium_price_dataframe()
    print(df.head(5))