
BTC_LOW = None
BTC_HIGH = None

LTC_LOW = None
LTC_HIGH = None

ETH_LOW = None
ETH_HIGH = None


if __name__ == '__main__':
    from time import sleep
    from threading import Thread
    from stocklook.utils.emailsender import send_message
    from stocklook.crypto.gdax import Gdax, scan_price, GdaxProducts as G

    gdax = Gdax()
    print("total account value: {} ".format(gdax.get_total_value()))
    btc, ltc, eth = G.BTC_USD, G.LTC_USD, G.ETH_USD
    #btc_args = (gdax, btc, send_message, BTC_LOW, BTC_HIGH)
    ltc_args = (gdax, ltc, send_message, LTC_LOW, LTC_HIGH)
    eth_args = (gdax, eth, send_message, ETH_LOW, ETH_HIGH)

    #btc_thread = Thread(target=scan_price, args=btc_args)
    ltc_thread = Thread(target=scan_price, args=ltc_args)
    eth_thread = Thread(target=scan_price, args=eth_args)
    #threads = [btc_thread, ltc_thread, eth_thread]
    threads = [ltc_thread, eth_thread]

    for i, t in enumerate(threads):
        print("starting thread {}".format(i))
        t.start()
        sleep(2)

