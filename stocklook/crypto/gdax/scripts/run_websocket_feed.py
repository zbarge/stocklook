"""
MIT License

Copyright (c) 2017 Zeke Barge

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
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
