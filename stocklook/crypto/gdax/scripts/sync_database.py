



if __name__ == '__main__':
    from stocklook.crypto.gdax import sync_database, Gdax, GdaxDatabase
    interval = 60
    gdax = Gdax()
    sync_database(gdax, interval=interval)