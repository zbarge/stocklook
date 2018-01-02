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
import re
import json
import logging as lg
from collections import Counter
from tweepy import Stream, OAuthHandler
from tweepy.streaming import StreamListener
from stocklook.config import (TWITTER_APP_KEY,
                              TWITTER_APP_SECRET,
                              TWITTER_CLIENT_KEY,
                              TWITTER_CLIENT_SECRET,
                              DATA_DIRECTORY,
                              config)
from stocklook.utils.database import (db_map_dict_to_alchemy_object,
                                      db_get_python_dtypes,
                                      db_describe_dict, AlchemyDatabase)
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (String, Boolean, DateTime, Float,
                        Integer, BigInteger, Column, ForeignKey, Table, Enum,
                        UniqueConstraint, TIMESTAMP, create_engine)
logger = lg.getLogger(__name__)

# Go to http://apps.twitter.com and create an app.
# The consumer key and secret will be generated for you after
consumer_key = config.get(TWITTER_APP_KEY, None)
consumer_secret = config.get(TWITTER_APP_SECRET, None)

# After the step above, you will be redirected to your app's page.
# Create an access token under the the "Your access token" section
access_token = config.get(TWITTER_CLIENT_KEY, None)
access_token_secret = config.get(TWITTER_CLIENT_SECRET, None)


# Global cache storing
# bits of tweets and counts.
# Used to identify spam.
SPAM_COUNTER = Counter()

# Compiled regex objects
# used to find stuff in tweets.
SPAM_RE = re.compile(
        r"(FREE|GIVEAWAY|SALE|"
        r"LUCKY|GIVING AWAY|"
        r"SIGN UP|TO WIN|TO PARTICIPATE|"
        r"LAST CHANCE|LIMITED TIME)",
        re.IGNORECASE)
TWEET_TARGET_RE = re.compile(
    r"(RT\s@|@)[A-Za-z0-9_\-]+(:\s|\s)", re.IGNORECASE)
TWITTER_HANDLE_RE = re.compile(
    r'@[A-Za-z0-9_]+(\W|$|\b)', re.IGNORECASE)


def twitter_message_is_spam(
        text, max_count=3,
        counter=SPAM_COUNTER,
        drop_handles=True,
        max_cache=10000,
        key_length=20):
    """
    Returns True when a message has been identified as spam.

    :param text: (str)
        The message to be checked

    :param max_count: (int, default 3)
        The max number of times the message
        key can show up before being considered spam.

    :param counter: (collections.Counter, default stocklook.apis.twitah.SPAM_COUNTER)
        Used to track the number of times
        a message key has passed through the function.

    :param drop_handles: (bool, default True)
        True scrubs twitter handles (starting with @)
        from text before generating the key. This helps
        to identify duplicate message content being spammed to
        different twitter handles.
    :param max_cache: (int, default 10,000)
        The max # of entries in the :param counter cache before it's cleared.
        Counter keys associated to counts greater than :param max_count
        will be kept as long as the total number of those entries is below :param max_cache.

    :param key_length: (int, default 20)
        The number of characters to trim the text down to when creating the key.
        20 characters is enough to identify most duplicate content.
    :return:
    """
    if drop_handles:
        text = twitter_drop_handles_from_txt(text)

    key = text[:key_length]
    counter[key] += 1

    if len(counter) > max_cache:
        # Not sure if this is even useful...
        # but i figure if this runs
        # long enough it could slow things down.
        print("Clearing counter...")
        spam = {k: v for k, v in counter.items()
                if v >= max_count}
        counter.clear()
        if len(spam) < max_cache:
            print("Loading spam keys "
                  "back into counter")
            counter.update(spam)

    return counter[key] >= max_count \
           or SPAM_RE.search(text) is not None


def twitter_split_handle_from_txt(tweet):
    """
    Looks for RT @twitterhandle: or just @twitterhandle in the beginning of the tweet.

    The handle is split off and returned as two separate strings.

    :param tweet: (str)
        The tweet text to split.

    :return: (str, str)
        twitter_handle, rest_of_tweet
    """
    match = TWEET_TARGET_RE.search(tweet)

    if match is not None:
        match = match.group()
        tweet = tweet.replace(match, '')

    return match, tweet


def twitter_drop_handles_from_txt(tweet):
    """
    Strips out any @twitter_handle from a message
    exposing the root content Used to identify duplicate
    content.
    :param tweet:
    :return:
    """
    while True:
        m = TWITTER_HANDLE_RE.search(tweet)
        if m is None:
            break
        tweet = tweet.replace(m.group(), '')
    return tweet


# SQLAlchemy declarations begin here
SQLTwitterBase = declarative_base()


class SQLTwitterUser(SQLTwitterBase):
    """
    Stores data about a twitter user.
    """
    __tablename__ = 'twitter_users'

    user_id = Column(Integer, primary_key=True)
    tweets = relationship('SQLTweet', back_populates='user')

    contributors_enabled = Column(Boolean)
    created_at = Column(String(255))
    default_profile = Column(Boolean)
    default_profile_image = Column(Boolean)
    description = Column(String(255))
    favourites_count = Column(Integer)
    follow_request_sent = Column(String)
    followers_count = Column(Integer)
    following = Column(String)
    friends_count = Column(Integer)
    geo_enabled = Column(Boolean)
    id = Column(Integer)
    id_str = Column(String(255))
    is_translator = Column(Boolean)
    lang = Column(String(255))
    listed_count = Column(Integer)
    location = Column(String(255))
    name = Column(String(255))
    notifications = Column(String)
    profile_background_color = Column(String(255))
    profile_background_image_url = Column(String(255))
    profile_background_image_url_https = Column(String(255))
    profile_background_tile = Column(Boolean)
    profile_banner_url = Column(String(255))
    profile_image_url = Column(String(255))
    profile_image_url_https = Column(String(255))
    profile_link_color = Column(String(255))
    profile_sidebar_border_color = Column(String(255))
    profile_sidebar_fill_color = Column(String(255))
    profile_text_color = Column(String(255))
    profile_use_background_image = Column(Boolean)
    protected = Column(Boolean)
    screen_name = Column(String(255))
    statuses_count = Column(Integer)
    time_zone = Column(String(255))
    translator_type = Column(String(255))
    url = Column(String)
    utc_offset = Column(Integer)
    verified = Column(Boolean)



class SQLTweet(SQLTwitterBase):
    """
    Stores data about an individual tweet.
    """
    __tablename__ = 'twitter_tweets'

    tweet_id = Column(Integer, primary_key=True)
    user = relationship('SQLTwitterUser', back_populates='tweets')
    user_id = Column(Integer, ForeignKey('twitter_users.user_id'))

    # Generated via describe_json_object
    contributors = Column(String)
    coordinates = Column(String)
    created_at = Column(String(255))
    display_text_range = Column(String)
    favorite_count = Column(Integer)
    favorited = Column(Boolean)
    filter_level = Column(String(255))
    geo = Column(String)
    id = Column(Integer)
    id_str = Column(String(255))
    in_reply_to_screen_name = Column(String(255))
    in_reply_to_status_id = Column(Integer)
    in_reply_to_status_id_str = Column(String(255))
    in_reply_to_user_id = Column(Integer)
    in_reply_to_user_id_str = Column(String(255))
    is_quote_status = Column(Boolean)
    lang = Column(String(255))
    place = Column(String)
    possibly_sensitive = Column(Boolean)
    quote_count = Column(Integer)
    reply_count = Column(Integer)
    retweet_count = Column(Integer)
    retweeted = Column(Boolean)
    source = Column(String(255))
    text = Column(String(255))
    timestamp_ms = Column(String(255))
    truncated = Column(Boolean)


DB_TWEET_DTYPES = db_get_python_dtypes(SQLTweet, include_str=True)
DB_TWEET_DTYPES_ITEMS = DB_TWEET_DTYPES.items()

DB_TWITTER_USER_DTYPES = db_get_python_dtypes(SQLTwitterUser, include_str=True)
DB_TWITTER_USER_DTYPES_ITEMS = DB_TWITTER_USER_DTYPES.items()
DB_TWITTER_USER_CACHE = dict()


class TwitterDatabaseListener(StreamListener, AlchemyDatabase):
    """
    Streams tweets to a SQLAlchemy database.
    """
    def __init__(self, api=None, stream_options=None, engine=None, session_maker=None):
        if stream_options is None:
            stream_options = dict()

        StreamListener.__init__(self, api=api)
        AlchemyDatabase.__init__(
            self, engine=engine,
            session_maker=session_maker,
            declarative_base=SQLTwitterBase)
        self._auth = None
        self._stream = None
        self._stream_options = stream_options
        self.session = self.get_session()

    @property
    def auth(self):
        """
        tweepy.OAuthHandler generated on demand using environment (or user injected)
        variables that have been loaded into global dictionary stocklook.config.config
        :return:
        """
        if self._auth is None:
            tokens = (consumer_key, consumer_secret,
                      access_token, access_token_secret)
            if not all(tokens):
                raise KeyError("Unable to authorize twitter "
                               "as there is a missing token. "
                               "Please make sure the following "
                               "environment variables are set:\n\t"
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

    def get_user_sql_object(self, user_data):
        """
        Checks memory cache for user object.
        Then checks database for user object.
        Then creates user object as last resort
        adding to database & memory cache.

        :param user_data: (dict)
        :return: SQLTwitterUser
        """
        try:
            # Return cached user object
            return DB_TWITTER_USER_CACHE[user_data['id_str']]
        except KeyError:

            # Find user in database
            user = self.session \
                .query(SQLTwitterUser) \
                .filter(SQLTwitterUser.id == user_data['id']).first()

            if user is None:
                # Make user and add to database
                user = db_map_dict_to_alchemy_object(
                    user_data, SQLTwitterUser,
                    dtype_items=DB_TWITTER_USER_DTYPES_ITEMS)
                self.session.add(user)

            # Cache user
            DB_TWITTER_USER_CACHE[user.id_str] = user

        # Keep the cache clean
        if len(DB_TWITTER_USER_CACHE) > 10000:
            DB_TWITTER_USER_CACHE.clear()

        return user

    def stream_data_to_sql(self, data):
        """
        Parses JSON data into SQLAlchemy object data.
        Creates or retrieves twitter user.
        :param data: (str, dict)
            The JSON data to be converted.
        """
        if isinstance(data, str):
            data = json.loads(data)

        user = self.get_user_sql_object(data['user'])
        tweet = db_map_dict_to_alchemy_object(
            data, SQLTweet,
            dtype_items=DB_TWEET_DTYPES_ITEMS)

        try:
            user.tweets.append(tweet)
        except AttributeError as e:
            logger.error(e)
            self.session.rollback()
        else:
            self.session.commit()

        return user, tweet

    @property
    def stream(self):
        """
        tweepy.Stream object.
        :return:
        """
        if self._stream is None:
            self._stream = Stream(
                self.auth, self,
                **self._stream_options)
        return self._stream

    def on_data(self, data):
        """
        Checks for spam before loading
        tweet/user data into database.
        :param data: (str)
            JSON data from twitter API.
        """
        data = json.loads(data)
        text = data['text']

        # Uncomment line below to print sqlalchemy columns.
        # db_describe_dict(data)
        if not twitter_message_is_spam(text):
            self.stream_data_to_sql(data)
            print("{}\n{}\n\n".format(
                data['created_at'], text))

        return True

    def on_error(self, status):
        print(status)

if __name__ == '__main__':
    tdb = TwitterDatabaseListener()
    tdb.stream.filter(track=['BTC'])
