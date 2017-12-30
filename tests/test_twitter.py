from stocklook.apis.twitah import *


def test_twitter_handle_re_and_dropper():
    """
    Tests stocklook.apis.twitah.twitter_drop_handles_from_txt()
    Proves all twitter handles are removed
    from strings regardless of location.
    """
    handles = ['@moondog144', '@onetwo', '@bank_roll']
    texts = ['RT {} tag tag tag', '{} tag blah blah', 'RT {}: tag tag tag']

    for h in handles:
        for t in texts:
            txt1 = t.format(h)
            txt2 = h + ' ' + t.replace('{}', '') + ' ' + h
            t1 = twitter_drop_handles_from_txt(txt1)
            t2 = twitter_drop_handles_from_txt(txt2)
            assert '@' not in t1
            assert '@' not in t2


def test_twitter_message_is_spam():
    """
    Tests stocklook.apis.twitah.twitter_message_is_spam()
    Proves the spam counter works as expected.
    """
    msg = "Twitter bro yolo haha"

    # message is not spam if only seen once
    assert not twitter_message_is_spam(msg)

    # now we make the message spam
    for i in range(3):
        twitter_message_is_spam(msg)
    # and prove it
    assert twitter_message_is_spam(msg)

    # Message isnt spam again if we clear the counter.
    SPAM_COUNTER.clear()
    assert not twitter_message_is_spam(msg)
    SPAM_COUNTER.clear()

    # Pump 101 unique messages into this with a 100 max cache
    # to ensure the cache clears on the 101st.
    for i in range(101):
        m = str(i) + msg
        twitter_message_is_spam(m, max_cache=100)
    assert len(SPAM_COUNTER) == 0


