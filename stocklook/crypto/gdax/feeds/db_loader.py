from stocklook.utils.database import DatabaseLoadingThread


class GdaxDatabaseLoader(DatabaseLoadingThread):
    SIZE_MAP = {'gdax_ticks': 200,
                'gdax_changes': 200,
                'gdax_heartbeats': 120,
                'gdax_feed': 1000,
                }


