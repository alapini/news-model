from tqdm import tqdm
import pandas as pd
from pathlib import Path
import logging
import spacy
import re
from unionfind import UnionFind
import numpy as np
import pickle

from gensim.models import KeyedVectors
from collections import defaultdict, Counter

from auxiliary_functions import convert_tid, tokenize

# options
pd.options.display.max_colwidth = 0
tqdm_min_interval = 60

# global functions and variables
logging.basicConfig(format='%(asctime)s | %(name)s | %(levelname)s : %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
_info = logger.info

path = Path('/home/mquezada/anchor-text-twitter/data')


# process
# _info("loading spacy")
# nlp = spacy.load('en_core_web_sm', parser=False, tagger=False, entity=False, matcher=False)

url_re = re.compile(r'(https?://t.co/[a-zA-Z0-9]+)')
hashtag_re = re.compile(r'(#[a-zA-Z0-9]+)')


# URLS

_info("loading short urls")
# short urls
# all_short_urls: List<List<short_url_id<str>, url<str>, expanded_url_id<str>>>
with (path / Path('short_urls.tsv')).open() as f:
    next(f)
    all_short_urls = [line.split() for line in f.readlines()]

short_urls = dict()
# short_urls: url<str> => expanded_url_id<int>
for _, url, e_id in all_short_urls:
    if e_id == "NULL":
        continue
    short_urls[url] = int(e_id)


_info("loading expanded urls")
# all_exp_urls: List<List<expanded_url_id<str>, expanded_url<str>, title<str>, expanded_clean<str>>>
with (path / Path('expanded_urls.tsv')).open(encoding='utf-8') as f:
    next(f)
    all_exp_urls = [line.split('\t') for line in f.readlines()]

expanded_urls = dict()
# X expanded_urls: expanded_url_id<int> => Tuple<expanded_url<str>, expanded_clean<str>, title<str>>

# expanded_urls: expanded_url_id<int> => expanded_clean<str>
for _id, exp, title, exp_clean in all_exp_urls:
    # expanded_urls[int(_id)] = (exp, exp_clean.replace('\n', '').replace('\\n', ''), title)
    expanded_urls[int(_id)] = exp_clean.replace('\n', '').replace('\\n', '')

_info("cleaning url residual info")
del all_exp_urls
del all_short_urls


# DATASET

usecols = ['tweet_id',
           'text',
           'created_at',
           'in_reply_to_status_id',
           'favorite_count',
           'retweet_count',
           'quoted_status_id',
           'is_a_retweet',
           'retweeted_status_id',
           'user_id']

converters = {'tweet_id': convert_tid,
              'in_reply_to_status_id': convert_tid,
              'quoted_status_id': convert_tid,
              'retweeted_status_id': convert_tid}

dtypes = {'text': np.str}

dataset_name = 'libya_hotel_tweets.tsv'
_info("loading dataset " + dataset_name)

f_libya = path / Path(dataset_name)
df_0 = pd.read_table(f_libya,
                     usecols=usecols,
                     converters=converters,
                     dtype=dtypes)

_info("filtering tweets with 4 or more hashtags or 3 or more urls")
to_remove = set()
event_short_urls = dict()

# event_short_urls: tweet_id<int> => List<short_url<str>>

for index, row in tqdm(df_0.iterrows(), total=len(df_0), mininterval=tqdm_min_interval):
    removed = False

    tweet_text = row['text']
    tweet_id = row['tweet_id']

    if type(tweet_text) != str:
        continue

    urls_in_tweet = url_re.findall(tweet_text)
    n_hashtags = hashtag_re.findall(tweet_text)

    if len(n_hashtags) >= 4 or len(urls_in_tweet) >= 3:
        to_remove.add(index)
        removed = True

    if not removed:
        event_short_urls[tweet_id] = urls_in_tweet

_info(f"to be removed: {len(to_remove)}")
df_1 = df_0.drop(df_0.index[list(to_remove)]).set_index('tweet_id')
df_1 = df_1[~df_1.index.duplicated(keep='first')]
_info(f"tweets after filtering: {len(df_1)}")


# DOCUMENTS

miss_short = []
total_short = 0
total_replies_rts = 0
tweet_info = defaultdict(list)

# tweet_info: 'i<N>_<tweet_id>' => List<expanded_url_clean<str>>

"""
for tweet_id, short_urls in event_short_urls:
    tweet_info[tweet_id] <= expanded_url for each short_url that was expanded
"""

for tweet_id, _short_urls in tqdm(event_short_urls.items(), total=len(event_short_urls), mininterval=tqdm_min_interval):
    if pd.isnull(tweet_id):
        continue

    key = str(int(tweet_id))

    effective_urls = 0
    for i, _short_url in enumerate(_short_urls):
        total_short += 1

        _expanded_id = short_urls.get(_short_url)
        _expanded_url = expanded_urls.get(_expanded_id)

        # if _short_url in short_urls and short_urls[_short_url] in expanded_urls:
        if _expanded_url:
            # tweet_info[f'i{i}_' + key].append(expanded_urls[short_urls[_short_url]])
            # tweet_info[f'i{i}_' + key].append(_expanded_url)
            tweet_info[key].append(_expanded_url)
            effective_urls += 1
        else:
            miss_short.append(_short_url)

    _tweet = df_1.loc[tweet_id]
    _reply = _tweet['in_reply_to_status_id']
    if not pd.isnull(_reply) and _reply in df_1.index:
        _replied_tweet_id = str(int(_reply))
        total_replies_rts += 1
        tweet_info[key].append(_replied_tweet_id)

    """
    for field in ['in_reply_to_status_id', 'retweeted_status_id', 'quoted_status_id']:
        if not np.isnan(tweet[field]) and tweet[field] in df_1.index:
            _field = 'i0_' + str(int(tweet[field]))

            total_replies_rts += 1
            for i in range(effective_urls):
                tweet_info[f'i{i}_' + key].append(_field)
    """

_info(f"total short urls in event: {total_short}")
_info(f"total tweets w/rt or reply: {total_replies_rts}")
_info(f"missed short urls (unavailable): {len(miss_short)}")


_info("creating union-find components")
"""
this creates a list of sets of tweets and urls
using tweet_info

tweet_info :: tweet_id => URL | tweet_id'

so it's possible to have sets of tweets without any URL (e.g. only retweets or conversations)
"""

uf = UnionFind()
for tweet_id, parents in tqdm(tweet_info.items(), total=len(tweet_info), mininterval=tqdm_min_interval):
    for p in parents:
        uf.union(tweet_id, p)


"""generates pandas with documents based on unionfind"""
# _data = list()
# for component in tqdm(uf.components(), mininterval=tqdm_min_interval):
#     elements = sorted(component)
#     url = elements[0]
#
#     # gets tweets from data frame using real IDs (non "i<k>_id")
#     tweets = map(lambda t: df_1.loc[int(t.split('_')[1])]['text'], elements[1:])
#     tweet_counts = Counter(tweets)
#     token_tweet_counts = list()
#
#     for tweet, count in tweet_counts.items():
#         tokens = list(tokenize(nlp, tweet))
#         token_tweet_counts.append((tokens, count))
#
#     norm_tweet_counts = defaultdict(int)
#     for tokens, count in token_tweet_counts:
#         tokens_set = frozenset(tokens)
#         norm_tweet_counts[tokens_set] += count
#
#     row = {'url': elements[0],
#            'tweets': list(norm_tweet_counts.items())}
#     _data.append(row)
#

for cc in c:
    t = df_1.loc[int(cc)]
    a = str(int(t.name))
    b = t['retweeted_status_id']
    d = t['in_reply_to_status_id']

    if not pd.isnull(b):
        b = str(int(b))
    if not pd.isnull(d):
        d = str(int(d))

    print(a,b,d)
