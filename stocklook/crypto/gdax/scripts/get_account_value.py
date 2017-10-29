if __name__ == '__main__':
    from stocklook.crypto.gdax import Gdax
    gdax = Gdax()
    value = gdax.get_total_value()
    msg = "Account value is: ${}".format(value)
    print(msg)
