from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
import json
import re
from stocklook.config import (TWITTER_APP_KEY,
                              TWITTER_APP_SECRET,
                              TWITTER_CLIENT_KEY,
                              TWITTER_CLIENT_SECRET,
                              config)

# Go to http://apps.twitter.com and create an app.
# The consumer key and secret will be generated for you after
consumer_key = config.get(TWITTER_APP_KEY, None)
consumer_secret = config.get(TWITTER_APP_SECRET, None)

# After the step above, you will be redirected to your app's page.
# Create an access token under the the "Your access token" section
access_token = config.get(TWITTER_CLIENT_KEY, None)
access_token_secret = config.get(TWITTER_CLIENT_SECRET, None)


class TwitterDatabaseListener(StreamListener):
    """
    Streams tweets to a SQLite3 database.
    """
    SPAM_RE = re.compile(
        r"(FREE|GIVEAWAY|SALE|"
        r"LUCKY|GIVING AWAY|"
        r"SIGN UP|TO WIN|TO PARTICIPATE|LAST CHANCE|LIMITED TIME)",
        re.IGNORECASE)

    def __init__(self, api=None, stream_options=None):
        if stream_options is None:
            stream_options = dict()

        StreamListener.__init__(self, api=api)
        self._auth = None
        self._stream = None
        self._stream_options = stream_options

    @property
    def auth(self):
        if self._auth is None:
            tokens = (consumer_key, consumer_secret,
                      access_token, access_token_secret)
            if not all(tokens):
                raise KeyError("Unable to authorize twitter "
                               "as there is a missing token. "
                               "Please make sure the following "
                               "environmental variables are set:\n\t"
                               "1) {}: {}\n\t"
                               "2) {}: {}\n\t"
                               "3) {}: {}\n\t"
                               "4) {}: {}\n\t".format(
                                TWITTER_APP_KEY, consumer_key,
                                TWITTER_APP_SECRET, consumer_secret,
                                TWITTER_CLIENT_KEY, access_token,
                                TWITTER_CLIENT_SECRET, access_token_secret))
            self._auth = OAuthHandler(consumer_key, consumer_secret)
            self._auth.set_access_token(access_token, access_token_secret)
        return self._auth

    @property
    def stream(self):
        if self._stream is None:
            self._stream = Stream(
                self.auth, self,
                **self._stream_options)
        return self._stream

    def on_data(self, data):
        data = json.loads(data)
        txt = data['text']
        if not self.SPAM_RE.search(txt):
            print("{}\n{}\n\n".format(
                data['created_at'], data['text']))
        return True

    def on_error(self, status):
        print(status)

if __name__ == '__main__':
    tdb = TwitterDatabaseListener()
    tdb.stream.filter(track=['BTC'])