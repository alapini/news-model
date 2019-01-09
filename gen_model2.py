from pathlib import Path
import logging
import re
from unionfind import UnionFind

from tqdm import tqdm
from paths import data_path
from load_urls import load_urls

import json

from collections import namedtuple, defaultdict


# global functions and variables
#logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)
_info = logging.info

url_re = re.compile(r'(https?://t.co/[a-zA-Z0-9]+)')
hashtag_re = re.compile(r'(#[a-zA-Z0-9]+)')
Tweet = namedtuple('Tweet', 'tweet_id retweet_id quote_id reply_id short_urls expanded_urls text created_at')

short_urls, expanded_urls = load_urls()


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



def url_graph(dataset_name):
    event_data, missing_urls_amount = load_data(dataset_name)

    adj_list = defaultdict(lambda: Counter())

    for tweet_id, tweet in tqdm(event_data.items(), total=len(event_data)):
        if not tweet.expanded_urls:
            continue
        for url_u in tweet.expanded_urls.values():
            for url_v in tweet.expanded_urls.values():
                if url_u != url_v:
                    adj_list[url_u][url_v] += 1

    return adj_list



def gen_model(dataset_name, ignore_wo_url=False, ignore_replies=False):   
    event_data, missing_urls_amount = load_data(dataset_name)

    ##########
    # create set of tweet_ids
    # for a given tweet t:
    # if t does not have urls: add a tweet_id {t.id}_0
    # for each url_i in t: add a tweet_id {t.id}_{i}
    # for each url_i in t: add a tweet_id {t.reply_id}_{i}
    ##########
    tweet_ids = set()
    logging.info("create list of tweet_ids")
    
    for tweet_id, tweet in tqdm(event_data.items(), total=len(event_data)):
        added = False
        if not tweet.expanded_urls:
            if not ignore_wo_url:
                tweet_ids.add(f'{tweet_id}_0')
                added = True
        else:       
            for i, url in enumerate(tweet.expanded_urls.values()):
                tweet_ids.add(f'{tweet_id}_{i}')
                added = True
                
        if added and tweet.reply_id != 'NULL':
            if tweet.reply_id in event_data and not ignore_replies:
                for i, url in enumerate(tweet.expanded_urls.values()):
                    tweet_ids.add(f'{tweet.reply_id}_{i}')
                    
    ##########
    # for each tweet_id in the set of tweet_ids
    # add a pair
    ##########
    logging.info("create pairs (t, u) or (t, t') for each tweet t and url u or replied/retweeted tweet t'")
    replies_amount = 0
    retweets_amount = 0
    quotes_amount = 0
    missing_replies_amount = 0
    pairs = []
    
    for tweet_id in tweet_ids:
        frags = tweet_id.split('_')
        o_tweet_id = frags[0]
        i = int(frags[1])
        
        tweet = event_data[o_tweet_id]
        
        url = tweet.expanded_urls.get(i)
        if url:
            pairs.append((tweet_id, url))
        
        # retweets ARE considered, due to be exact text copies of the retweeted tweet
        if tweet.retweet_id != 'NULL':
            retweets_amount += 1
        if tweet.quote_id != 'NULL':
            quotes_amount += 1
        if tweet.reply_id != 'NULL':
            replies_amount += 1

            if tweet.reply_id in event_data:
                if not ignore_replies:
                    ## TODO esto esta bien?
                    pairs.append((tweet_id, f'{tweet.reply_id}_{i}'))
            else:
                missing_replies_amount += 1
                
    logging.info(f'total pairs: {len(pairs)}, retweets: {retweets_amount}, quotes: {quotes_amount}, replies: {replies_amount} '
                 f'(missing: {missing_replies_amount}, missing urls: {missing_urls_amount})')

    ##########

    """
        all keys must be the same time (in this case, strings);
        unionfind will vectorize operations and will cast everything in the array to the same type,
        so if there are integers and strings, it will cast everything to string and comparisons will fail
        when calling uf.components().
    """

    logging.info('applying union-find')
    uf = UnionFind()
    for u, v in pairs:
        uf.union(u, v)
    logging.info(f'total components: {len(uf.components())}')
    logging.info('\n')

    return {
        'components': uf.components(), 
        'event_data': event_data
    }


# event_name: (uf, event_data)
"""
models = {
    'libya': gen_model('libya_hotel_tweets.tsv'),
    'pistorius': gen_model('oscar_pistorius_tweets.tsv'),
    'nepal': gen_model('nepal_tweets.tsv'),
    
    'libya_no_url': gen_model('libya_hotel_tweets.tsv', ignore_wo_url=True),
    'pistorius_no_url': gen_model('oscar_pistorius_tweets.tsv', ignore_wo_url=True),
    'nepal_no_url': gen_model('nepal_tweets.tsv', ignore_wo_url=True),
    
    'libya_no_rep': gen_model('libya_hotel_tweets.tsv', ignore_replies=True),
    'pistorius_no_rep': gen_model('oscar_pistorius_tweets.tsv', ignore_replies=True),
    'nepal_no_rep': gen_model('nepal_tweets.tsv', ignore_replies=True),
    
    'libya_no_url_no_rep': gen_model('libya_hotel_tweets.tsv', ignore_wo_url=True, ignore_replies=True),
    'pistorius_no_url_no_rep': gen_model('oscar_pistorius_tweets.tsv', ignore_wo_url=True, ignore_replies=True),
    'nepal_no_url_no_rep': gen_model('nepal_tweets.tsv', ignore_wo_url=True, ignore_replies=True)
}
"""