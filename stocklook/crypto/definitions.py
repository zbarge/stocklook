BTC_USD = 'BTC_USD'
ETH_USD = 'ETH_USD'
LTC_USD = 'LTC_USD'
ETH_BTC = 'ETH_BTC'
BCH_BTC = 'BCH_BTC'
LTC_BTC = 'LTC_BTC'
OPEN = 'open'
O = 'open'
HIGH = 'high'
H = 'high'
LOW = 'low'
L = 'low'
CLOSE = 'close'
C = 'close'
PRICE = 'price'
P = 'price'
TIME = 'time'
T = 'time'
INTERVAL = 'interval'
I = 'interval'


def fix_symbol(s):
    return s.upper().replace('/', '-').replace('-', '_')



