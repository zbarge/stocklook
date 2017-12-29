from stocklook.apis.twitah import *




def test_twitter_handle_re_and_dropper():
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


