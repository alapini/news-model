from pymongo import MongoClient
from bson.objectid import ObjectId
from random import choice
import random
import logging
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, session, request, abort
from functools import lru_cache
from pathlib import Path
from web.topic_labeler import TopicLabeler
from collections import defaultdict
from datetime import datetime

from multiprocessing import Value
import sys
from tqdm import tqdm


from collections import Counter
import random
import numpy as np


logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)
_info = logging.info

client = MongoClient('mongodb://localhost:27017')
db = client.twitter_news

# for rep in db.representatives.find():
#     to_remove = dict()
#     for field in rep:
#         if field in ('_id', 'event'):
#             continue
#         to_remove[field] = 1
    
#     if to_remove:
#         db.representatives.update_one({"_id": rep["_id"]}, {"$unset": to_remove})


total_events = 3

@lru_cache(maxsize=1)
def get_tweets(a=None):
    _info('getting all tweets')
    all_tweets = db.tweets.find()
    return list(all_tweets)


@lru_cache(maxsize=total_events)
def get_representatives(event_id):
    _info("getting representatives")
    representatives = db.representatives.find({'event': ObjectId(event_id)})
    return list(representatives)


@lru_cache(maxsize=total_events)
def get_topics(event_id):
    _info("getting topics")
    topics = list(db.topics.find({'event': ObjectId(event_id)}))
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

# init

### UNSET
def unset():
    for rep in tqdm(db.representatives.find()):
        to_remove = dict()
        for field in rep:
            if field in ('_id', 'event'):
                continue
            to_remove[field] = 1
        
        if to_remove:
            db.representatives.update_one({"_id": rep["_id"]}, {"$unset": to_remove})


def add_topics():
    data_path = Path('/home/mquezada/news-model-git/news-model/tweet_topics/')
    files = list(data_path.glob('event_*-topic_*-tweet_ids_sorted_mmr.txt'))

    topics_tweetids = defaultdict(list)

    all_tweets = get_tweets()
    all_tweets_d = dict()
    for t in all_tweets:
        all_tweets_d[str(t['_id'])] = t

    # add two fields to representatives: predef_topic, ranking    
    for f_0 in files:
        print(f_0)
        _, ev, top, _, _, _ = f_0.name.split("_")
        event_id = ev.split("-")[0]
        topic_id = top.split("-")[0]
        #print(event_id, topic_id)

        representatives = get_representatives(event_id)
        representatives_d = dict()
        for r in representatives:
            representatives_d[str(r['_id'])] = r
        
        with f_0.open() as f:
            for i, line in enumerate(f):
                tweet_id = line[:-1]
                # topic_id, event_id
                # topics_tweetids[topic_id].append(r_id)

                # tweet = db.tweets.find_one({"_id": ObjectId(tweet_id)})
                tweet = all_tweets_d[tweet_id]
                print(f"tweet {tweet['_id']}")

                # representative = db.representatives.find_one({"_id": tweet['representative']})
                representative = representatives_d[str(tweet['representative'])]
                print(f"repr {representative['_id']}")

                db.representatives.update_one(
                    {'_id': representative['_id']}, 
                    {'$set': {'predef_topic': topic_id, 'ranking': i}}
                )

                print(f"updated with topic_id {topic_id} and rank {i}")

#################################

def get_reps_user(user_name, event_id):
    reps = db.representatives.find(
        {
            'event': ObjectId(event_id),
            'topic': {
                '$elemMatch': {'user_name': user_name}
            }
        }
    )

    labeled = defaultdict(list)

    for r in reps:
        predef_topic = r['predef_topic']
        rep_id = r['_id']

        labeled[predef_topic].append(rep_id)

    return dict(labeled)


# def get_max_rank(event_id):
#     agg = db.representatives.aggregate([
#         {'$match': {'event': ObjectId(event_id), 'predef_topic': {'$exists': True}}},
#         {'$group': {
#             '_id': '$predef_topic',
#             'predef_topic': {'$addToSet': '$predef_topic'},
#             'ranking': {'$max': '$ranking'}
#             }
#         },
#         {'$project': {
#             '_id': 1,
#             'predef_topic': {'$arrayElemAt': ['$predef_topic', 0]},
#             'ranking': 1
#             }
#         }
#     ])

#     reps = []
#     for a in agg:
#         r = db.representatives.find_one({'predef_topic': a['predef_topic'], 'ranking': a['ranking']})
#         reps.append(r)

#     return reps


@lru_cache(maxsize=3)
def get_totals(event_id):
    reps = db.representatives.find({
        'event': ObjectId(event_id),
        'predef_topic': {'$exists': True}
    })
    totals = Counter()
    for r in reps:
        predef_topic = r['predef_topic']
        totals[predef_topic] += 1
    return dict(totals)


# def get_min_rank(event_id):
#     agg = db.representatives.aggregate([
#         {'$match': {'event': ObjectId(event_id), 'predef_topic': {'$exists': True}}},
#         {'$group': {
#             '_id': '$predef_topic',
#             'predef_topic': {'$addToSet': '$predef_topic'},
#             'ranking': {'$min': '$ranking'}
#             }
#         },
#         {'$project': {
#             '_id': 0,
#             'predef_topic': {'$arrayElemAt': ['$predef_topic', 0]},
#             'ranking': 1
#             }
#         }
#     ])

#     reps = {}
#     for a in agg:
#         reps[a['predef_topic']] = a['ranking']

#     return reps

# def get_next_rank(event_id, predef_topic, prev_rank):
#     agg = db.representatives.aggregate([
#         {'$match': {'event': ObjectId(event_id), 'predef_topic': predef_topic, 'ranking': {'$gt': prev_rank}}},
#         {'$group': {
#             '_id': {},
#             'ranking': {'$min': '$ranking'}
#         }}
#     ])

#     res = list(agg)
#     if res:
#         rep = db.representatives.find_one({
#             'event': ObjectId(event_id),
#             'predef_topic': predef_topic,
#             'ranking': res[0]['ranking']
#         })
#         return rep


def get_tweet(event_id, predef_topic, already_labeled_ids):
    event = ObjectId(event_id)

    # get min ranking
    query = db.representatives.aggregate([
        {'$match': {
            '_id': {'$nin': already_labeled_ids},
            'event': event, 
            'predef_topic': predef_topic, 
            'topic.user_name': {
                '$nin': [user_name]
            }
        }},
        {'$project': {
            'no_labels': {'$size': {'$ifNull': ['$topic', []]}},
            'ranking': True
        }},
        {'$match': { 'no_labels': {'$lt': 3} }},
        {'$group': {
            '_id': {},
            'ranking': {'$min': '$ranking'}
        }}
    ])
    
    if query:
        rank = list(query)[0]['ranking']
        rep = db.representatives.find_one({
            'event': event,
            'predef_topic': predef_topic,
            'ranking': rank
        })
        return rep
    return None


@lru_cache(maxsize=3)
def get_predef_topics(event_id):
    return db.representatives.distinct('predef_topic', {'event': ObjectId(event_id)})


DEBUG = True
from pprint import pprint

def get_next_tweet(user_name, event_id):
    # total tweets per predef topic:
    totals = get_totals(event_id)

    # topics
    topics = get_predef_topics(event_id)

    if DEBUG:
        print("topics")
        pprint(topics)
        print()

        print("totals")
        pprint(totals)
        print()

    # reps labeled by this user: dict of ids
    reps_labeled = get_reps_user(user_name, event_id)
    
    if DEBUG:
        print("labeled by this user")
        for k, v in reps_labeled.items():
            print(k, len(v))
        print()

    probas = dict()
    for topic in topics:
        labeled = len(reps_labeled.get(topic, []))
        total = totals[topic]
        probas[topic] = 1 - labeled / total

    if DEBUG:
        print("probas")
        pprint(probas)
        print()

    if sum(probas.values()) > 0:
        x = 1 / sum(probas.values())
    else:
        x = 1 / len(probas)

    if DEBUG:
        print("x = ", x)
    chosen = None
    rnd = random.random()

    if DEBUG:
        print("random = ", rnd)
        print()

    p0 = 0
    for topic in topics:
        p = probas[topic] * x
        if DEBUG: print(f"topic: {topic}", "choice:", f"{p0} <= {rnd} < {p0 + p}", end=" ", sep="\t")
        if p0 <= rnd < p0 + p:
            chosen = topic
            if DEBUG: print("\tCHOSEN\n")
            break
        p0 += p
        if DEBUG: print()

    already_labeled_ids = list(reps_labeled.values())
    rep = get_tweet(event_id, chosen, already_labeled_ids)

    if DEBUG:
        print("rep chosen")
        pprint(rep)
        print()
    return rep


# def next_tweet(user_name, event_id):
#     # representatives already labeled by current user:
#     reps = get_reps_user(user_name, event_id)
#     topics = get_predef_topics(event_id)
#     min_ranks = get_min_rank(event_id)

#     if not reps:  # initial state
#         return random.choice(min_ranks)

#     labeled_topics = defaultdict(int)
#     totals = get_totals(event_id)
#     rankings = dict()

#     for r in min_ranks:
#         rankings[r['predef_topic']] = r['ranking']

#     for rep in reps:
#         predef_topic = rep['predef_topic']
#         labeled_topics[predef_topic] += 1
#         # minimum rank in already labeled reps
#         if rankings[predef_topic] < rep['ranking']:
#             rankings[predef_topic] = rep['ranking']
        
#     fr = np.array([labeled_topics[k] / totals[k] for k in topics])
#     probas = 1 - fr

#     x = 1 / sum(probas)
#     rnd = random.random()
#     p0 = 0

#     choice = topics[0]  # topic
#     for i, p1 in enumerate(x * p for p in probas):
#         if p0 <= rnd <= p0 + p1:
#             choice = topics[i]
#             break
#         p0 += p1

#     topic = choice
#     rank = rankings[choice]
#     rep = get_next_rank(event_id, topic, rank)
#     return rep


def label(user_name=None, 
          topic_ids=None, 
          topic_text=None, 
          non_relevant=None, 
          skip=None,
          representative_id=None):

    if not user_name:
        raise Exception("user name")
    
    if not representative_id:
        raise Exception("repr id")

    if not any([topic_ids, topic_text, non_relevant, skip]):
        raise Exception("any topic")

    topic_save = defaultdict(list)

    if topic_ids:
        for topic_id in topic_ids:   
            topic_save['topics'].append(ObjectId(topic_id))
    
    if topic_text:
        topic_save['custom_topic'] = topic_text

    if skip:
        topic_save['skipped'] = True
    
    if non_relevant:
        topic_save['non_relevant'] = True
        topic_save.pop('topics', None)
        topic_save.pop('custom_topic', None)

    to_save = {
            "$push": {
                "topic": {
                    "info": dict(topic_save),
                    "added_timestamp": datetime.utcnow(),
                    "user_name": user_name
                }
            }
        }

    rep_id = {"_id": ObjectId(representative_id)}
    res = db.representatives.update_one(rep_id, to_save)
    #_info(f"updated: {representative_id}. User: {user_name}. Topics: {dict(topic_save)}")
    return res


##### test


%%time 
user_name1 = 'wax'
user_name2 = 'qwe'
event_id = "5b171725da870923dcb0478f"
ITS = 100
predef_topic = '5b184131da870950572be268'

# label
reps = db.representatives.find({'predef_topic': predef_topic}).limit(362)
for r in reps:
    label(user_name=user_name1 if random.random > 0.5 else user_name2,
          topic_ids=['5b184131da870950572be268'],
          topic_text=None,
          non_relevant=None,
          skip=None,
          representative_id=str(r['_id']))

t = Counter()
for _ in range(ITS):
    rep = get_next_tweet(user_name1, event_id)
    t[rep['predef_topic']] += 1


# CPU times: user 132 ms, sys: 26.4 ms, total: 158 ms
# Wall time: 36.6 s
