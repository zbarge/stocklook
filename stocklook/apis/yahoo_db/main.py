import logging
import sys
from datetime import datetime
from time import sleep

from stocklook.database import StockDatabase
from stocklook.utils.emailsender import EmailSender

logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def sync_database():
    """
    This method is designed to run perpetually - it will
    hit the Yahoo API for new quotes on all stocks every 15 minutes.

    :return:
    """
    db = StockDatabase()
    notifier = EmailSender()
    errors = 0
    while True:
        session = db.get_session()
        try:

            db.update_stocks(session)
            session.commit()
            session.close()
            logging.info("Stock Updater: Completed updates at {}".format(datetime.now()))
        except Exception as e:
            session.rollback()
            errors += 1
            logging.error("Stock Updater: Error # {}".format(e))
            if errors < 5:
                notifier.smtp.send(subject="Stock Updater Error", contents=str(e))
            else:
                raise
        else:
            open_seconds = db.seconds_until_market_open()
            if open_seconds == 0:
                logging.info("Stock Updater: sleeping for 15 minutes.")
                sleep(15 * 60)
            else:
                logging.info("Stock Updater: sleeping for {} hours".format(
                    round(open_seconds / 60 / 60), 2))
                sleep(open_seconds)


if __name__ == '__main__':
    sync_database()

        

