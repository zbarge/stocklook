

FILE = 'coinmc_stats.csv'

if __name__ == '__main__':
    import os
    from stocklook.crypto.coinmarketcap import \
        coinmc_report_on_snaps, CoinMCDatabase
    db = CoinMCDatabase()
    df = db.get_snapshots_frame()
    if not os.path.dirname(FILE):
        from stocklook.config import DATA_DIRECTORY, config
        FILE = os.path.join(config[DATA_DIRECTORY], FILE)
    coinmc_report_on_snaps(df, FILE)
