from stocklook.crypto.gdax.feeds import GdaxDatabaseFeed
from time import sleep


def run_websocket_feed():
    feed = GdaxDatabaseFeed(products=['LTC-USD', 'BTC-USD', 'ETH-USD'],
                            channels=['full', 'ticker'])
    feed.start()
    last_id = 0
    same_id = 0

    while True:
        msg_id = feed.message_count
        if msg_id == last_id:
            same_id += 1
        else:
            same_id = 0
            last_id = msg_id

        if same_id >= 3:
            print("Same ID 3 times - we've lost our feed.")

            try:
                feed.close()
            except:
                pass
            finally:
                break

        msg = "ID: {}".format(feed.message_count)

        for feed_type, q in feed.queues.items():
            size = q.qsize()
            if size > 5:
                msg += "\n{} queue #: {}".format(feed_type, size)

        print(msg)
        sleep(30)

    run_websocket_feed()


if __name__ == '__main__':
    run_websocket_feed()
