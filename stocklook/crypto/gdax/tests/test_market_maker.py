


if __name__ == '__main__':
    from stocklook.crypto.gdax.api import Gdax

    fill_map = dict()
    g = Gdax()
    fills = g.get_fills(product_id='ETH-USD', paginate=False)
    for f in fills:
        fill_map[f['order_id']] = f
        f['price'] = float(f['price'])
        f['fee'] = float(f['fee'])
        f['size'] = float(f['size'])

    for o_id, data in fill_map.items():
        print(data)
        print("\n\n")
    num1 = 5
    num2 = -5
    print(num1 - num2)