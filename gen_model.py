from pathlib import Path
import logging
import re
from unionfind import UnionFind

from paths import data_path
from load_urls import load_urls

from collections import namedtuple


# global functions and variables
logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)
_info = logging.info

url_re = re.compile(r'(https?://t.co/[a-zA-Z0-9]+)')
hashtag_re = re.compile(r'(#[a-zA-Z0-9]+)')
Tweet = namedtuple('Tweet', 'tweet_id retweet_id quote_id reply_id short_urls expanded_urls text created_at')

short_urls, expanded_urls = load_urls()

# dataset_name = 'libya_hotel_tweets.tsv'
# dataset_name = 'oscar_pistorius_tweets.tsv'
# dataset_name = 'nepal_earthquake_tweets.tsv'

# def sanity_check():
#     c = []
#     with (data_path / Path(dataset_name)).open('r') as g:
#         for l in g:
#             c.append(len(l.split('\t')) != 28)
#     for _, cc in enumerate(c):
#         if cc:
#             print(_ + 1)
# sanity_check()

# ORDER HEADER
# 0 id
# 1 tweet_id
# 2 text
# 3 created_at
# 4 when_added
# 5 source
# 6 source_url
# 7 entities
# 8 lang
# 9 truncated
# 10 possibly_sensitive
# 11 coordinates
# 12 in_reply_to_status_id
# 13 in_reply_to_screen_name
# 14 in_reply_to_user_id
# 15 favorite_count
# 16 retweet_count
# 17 is_headline
# 18 quoted_status_id
# 19 is_a_retweet
# 20 retweeted_status_id
# 21 user_id
# 22 is_filtered
# 23 url_expanded
# 24 id
# 25 tweet_id
# 26 event_id
# 27 when_added


##########

def load_data(dataset_name):
    _info(f'load and clean dataset: {dataset_name}')
    ignored_amount = 0
    missing_urls_amount = 0
    event_data = dict()
    with (data_path / Path(dataset_name)).open('r') as f:
        next(f)
        for line in f:
            tokens = line[:-1].split('\t')
            text = tokens[2]

            urls_in_tweet = url_re.findall(text)
            n_hashtags = hashtag_re.findall(text)

            expanded_map = dict()

            for i, short_url in enumerate(urls_in_tweet):
                expanded_id = short_urls.get(short_url)
                expanded_url = expanded_urls.get(expanded_id)

                expanded_map[i] = expanded_url

                if not expanded_url:
                    missing_urls_amount += 1

            if len(n_hashtags) >= 4 or len(urls_in_tweet) >= 3:
                ignored_amount += 1
                continue

            tweet_id = tokens[1]
            tweet = Tweet(
                tweet_id,   # tweet id
                tokens[20],  # retweet id
                tokens[18],  # quote id
                tokens[12],  # reply id
                urls_in_tweet,            # short_urls
                expanded_map,             # short_url index => expanded_url
                text,                     # text
                tokens[3]  # created_at
            )

            event_data[tweet_id] = tweet
    _info(f'tweets processed: {len(event_data)}, ignored: {ignored_amount}, missing urls: {missing_urls_amount}')
    return event_data, missing_urls_amount


def gen_model(dataset_name):
    event_data, missing_urls_amount = load_data(dataset_name)

    ##########

    _info("create pairs (t, u) or (t, t') for each tweet t and url u or replied/retweeted tweet t'")
    replies_amount = 0
    retweets_amount = 0
    quotes_amount = 0
    missing_replies_amount = 0
    pairs = []
    for tweet_id, tweet in event_data.items():
        [pairs.append((tweet_id, url)) for url in tweet.expanded_urls.values() if url]

        # retweets ARE considered, due to be exact text copies of the retweeted tweet
        if tweet.retweet_id != 'NULL':
            retweets_amount += 1
        if tweet.quote_id != 'NULL':
            quotes_amount += 1
        if tweet.reply_id != 'NULL':
            replies_amount += 1
            if tweet.reply_id in event_data:
                pairs.append((tweet_id, tweet.reply_id))
            else:
                missing_urls_amount += 1
    _info(f'total pairs: {len(pairs)}, retweets: {retweets_amount}, quotes: {quotes_amount}, replies: {replies_amount} '
          f'(missing: {missing_replies_amount})')

    ##########

    """
        all keys must be the same time (in this case, strings);
        unionfind will vectorize operations and will cast everything in the array to the same type,
        so if there are integers and strings, it will cast everything to string and comparisons will fail
        when calling uf.components().
    """

    _info('applying union-find')
    uf = UnionFind()
    for u, v in pairs:
        uf.union(u, v)
    _info(f'total components: {len(uf.components())}')

    return uf, event_data
