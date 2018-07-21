import logging
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from numba import jit
import numpy as np

import spacy
from bson.objectid import ObjectId
from gensim.models import KeyedVectors
from nltk.corpus import stopwords
from pymongo import MongoClient
from tqdm import tqdm

logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)
_info = logging.info

client = MongoClient('mongodb://localhost:27017')
db = client.twitter_news
nlp = spacy.load('en_core_web_sm', tagger=False, entity=False, matcher=False)


def hashtag_pipe(doc):
    merged_hashtag = False
    while True:
        for token_index, token in enumerate(doc):
            if token.text == '#':
                if token.head is not None:
                    start_index = token.idx
                    end_index = start_index + len(token.head.text) + 1
                    if doc.merge(start_index, end_index) is not None:
                        merged_hashtag = True
                        break
        if not merged_hashtag:
            break
        merged_hashtag = False
    return doc


nlp.add_pipe(hashtag_pipe)


total_events = 3


@lru_cache(maxsize=total_events)
def get_representatives(event_id):
    _info("getting representatives")
    representatives = db.representatives.find({'event': ObjectId(event_id)})
    return list(representatives)


@lru_cache(maxsize=total_events)
def get_topics(event_id):
    _info("getting topics")
    topics = list(db.topics.find({'event': ObjectId(event_id)}))
    comodin = None
    for t in topics:
        if t['topic_name'] == "Non relevant":
            comodin = t
            topics.remove(t)
            break
    return topics, comodin


@lru_cache(maxsize=1)
def get_events():
    _info("getting events")
    events = db.events.find()
    return list(events)


@lru_cache(maxsize=1)
def get_tweets(a=None):
    _info('getting all tweets')
    all_tweets = db.tweets.find()
    return list(all_tweets)


@lru_cache(maxsize=3)
def get_vectors(path):
    _info(f"loading fasttext vectors from {path}")
    word_vectors = KeyedVectors.load_word2vec_format(path)
    return word_vectors


@lru_cache(maxsize=2**30)
def sim(tokens_a, tokens_b):
    return ft_comp.n_similarity(tokens_a, tokens_b)


def mmr(docs, query, l):
    def mmr_score(tweet):
        return l * sim(docs[tweet], query) - \
               (1 - l) * max([sim(docs[tweet], docs[y]) for y in set(selected) - {tweet}] or [0])

    L = np.array([[l, 0], [0, l - 1]])

    def score(tweet):
        s1 = sim(docs[tweet], query)
        s2 = np.max(np.array([sim(docs[tweet], docs[y]) for y in set(selected) - {tweet}] or [0]))

        return L.dot(np.array([s1, s2])).sum()

    selected = set()
    while selected != set(docs):
        remaining = list(set(docs) - selected)
        next_selected = max(remaining, key=mmr_score)
        # next_selected = remaining[np.argmax([score(t) for t in remaining])]

        # next_selected = None
        # max_score = 0
        #
        # for _t in remaining:
        #     score = l * sim(docs[_t], query) - \
        #             (1 - l) * max([sim(docs[_t], docs[y]) for y in set(selected) - {_t}] or [0])
        #     if score > max_score:
        #         max_score = score
        #         next_selected = _t

        selected.add(next_selected)
        yield next_selected, ' '.join(list(docs[next_selected]))


@lru_cache(maxsize=total_events)
def process_tweets(event_id):
    all_tweets = get_tweets()
    representatives = get_representatives(event_id)

    _info("processing tweets")

    # rep_tweet: repr_id => tweet
    rep_tweet = dict()
    for t in tqdm(all_tweets):
        rep_tweet[t['representative']] = t

    # repr_ids: {repr_id} // this event
    repr_ids = set([r['_id'] for r in representatives])

    # tweets_this_event: [tweet]
    tweets_this_event = [t for r, t in rep_tweet.items() if r in repr_ids]

    tweets_tokens = dict()
    all_tokens = set()
    for tweet, doc in tqdm(zip(tweets_this_event, nlp.pipe([_t['text'] for _t in tweets_this_event],
                                                           n_threads=8,
                                                           batch_size=1024)),
                           total=len(tweets_this_event)):

        tokens = frozenset([token.lower_
                            for token in doc
                            if token.lower_ not in stopwords.words('english') and token.lower_ in ft_comp])

        if tokens and tokens not in all_tokens:
            tweets_tokens[str(tweet['_id'])] = tokens
            all_tokens.add(tokens)

    return tweets_tokens


path = Path('/home/mquezada/anchor-text-twitter/data/ft_alltweets_model.vec')
ft_comp = get_vectors(path.as_posix())
events = get_events()

topics = list()
for event in events:
    topics.append([frozenset([t.lower()
                              for t in topic['topic_name'].split()])
                   for topic in get_topics(event['_id'])[0]])


def sample_1_tweet(event, query):
    tweets_tokens = process_tweets(event['_id'])
    yield from mmr(tweets_tokens, query, 0.6)


def test(j: int, topic: frozenset):
    event = events[j]
    for i, (id_, text) in enumerate(sample_1_tweet(event, topic)):
        print(id_, text)
        input()


export_dir = Path('/home/mquezada/tweet_topics/')
#for i, e in enumerate(events):

i = 2
e = events[2]
print(e['event_name'])
topics_this_event, _ = get_topics(e['_id'])

for topic in topics_this_event:
    print("\t", topic['topic_name'])

    f_name = f'event_{e["_id"]}-topic_{topic["_id"]}-tweet_ids_sorted_mmr.txt'
    topic_tokens = frozenset([t.lower() for t in topic['topic_name'].split()])

    with (export_dir / Path(f_name)).open('w') as f:
        for id_, text in tqdm(sample_1_tweet(e, topic_tokens)):
            f.write(f'{id_}\n')
