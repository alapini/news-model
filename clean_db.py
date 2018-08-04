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
from tqdm import tqdm
for rep in tqdm(db.representatives.find()):
    to_remove = dict()
    for field in rep:
        if field in ('_id', 'event'):
            continue
        to_remove[field] = 1
    
    if to_remove:
        db.representatives.update_one({"_id": rep["_id"]}, {"$unset": to_remove})

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

sys.exit(0)



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
    return list(reps)


def get_max_rank(event_id):
    agg = db.representatives.aggregate([
        {'$match': {'event': ObjectId(event_id), 'predef_topic': {'$exists': True}}},
        {'$group': {
            '_id': '$predef_topic',
            'predef_topic': {'$addToSet': '$predef_topic'},
            'ranking': {'$max': '$ranking'}
            }
        },
        {'$project': {
            '_id': 1,
            'predef_topic': {'$arrayElemAt': ['$predef_topic', 0]},
            'ranking': 1
            }
        }
    ])

    reps = []
    for a in agg:
        r = db.representatives.find_one({'predef_topic': a['predef_topic'], 'ranking': a['ranking']})
        reps.append(r)

    return reps


@lru_cache(maxsize=3)
def get_totals(event_id):
    reps = get_max_rank(event_id)
    totals = dict()
    for r in reps:
        predef_topic = str(r['predef_topic'])
        totals[predef_topic] = r['ranking'] + 1
    return totals


def get_min_rank(event_id):
    agg = db.representatives.aggregate([
        {'$match': {'event': ObjectId(event_id), 'predef_topic': {'$exists': True}}},
        {'$group': {
            '_id': '$predef_topic',
            'predef_topic': {'$addToSet': '$predef_topic'},
            'ranking': {'$min': '$ranking'}
            }
        },
        {'$project': {
            '_id': 1,
            'predef_topic': {'$arrayElemAt': ['$predef_topic', 0]},
            'ranking': 1
            }
        }
    ])

    reps = []
    for a in agg:
        r = db.representatives.find_one({'predef_topic': a['predef_topic'], 'ranking': a['ranking']})
        reps.append(r)

    return reps

def get_next_rank(event_id, predef_topic, prev_rank):
    agg = db.representatives.aggregate([
        {'$match': {'event': ObjectId(event_id), 'predef_topic': predef_topic, 'ranking': {'$gt': prev_rank}}},
        {'$group': {
            '_id': {},
            'ranking': {'$min': '$ranking'}
        }}
    ])

    res = list(agg)
    if res:
        rep = db.representatives.find_one({
            'event': ObjectId(event_id),
            'predef_topic': predef_topic,
            'ranking': res[0]['ranking']
        })
        return rep


@lru_cache(maxsize=3)
def get_predef_topics(event_id):
    return db.representatives.distinct('predef_topic', {'event': ObjectId(event_id)})


def next_tweet(user_name, event_id):
    # representatives already labeled by current user:
    reps = get_reps_user(user_name, event_id)
    topics = get_predef_topics(event_id)
    min_ranks = get_min_rank(event_id)

    if not reps:  # initial state
        return random.choice(min_ranks)

    labeled_topics = defaultdict(int)
    totals = get_totals(event_id)
    rankings = dict()

    for r in min_ranks:
        rankings[r['predef_topic']] = r['ranking']

    for rep in reps:
        predef_topic = rep['predef_topic']
        labeled_topics[predef_topic] += 1
        # minimum rank in already labeled reps
        if rankings[predef_topic] < rep['ranking']:
            rankings[predef_topic] = rep['ranking']
        
    fr = np.array([labeled_topics[k] / totals[k] for k in topics])
    probas = 1 - fr

    x = 1 / sum(probas)
    rnd = random.random()
    p0 = 0

    choice = topics[0]  # topic
    for i, p1 in enumerate(x * p for p in probas):
        if p0 <= rnd <= p0 + p1:
            choice = topics[i]
            break
        p0 += p1

    topic = choice
    rank = rankings[choice]
    rep = get_next_rank(event_id, topic, rank)
    return rep


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
user_name = 'wax'
event_id = "5b171725da870923dcb0478f"

%%time
t = Counter()
for i, r in enumerate(list(db.representatives.find({'predef_topic': '5b184122da870950572be266'}).limit(1000))):
    try:
        label(user_name, ['5b18413eda870950572be269'], None, None, None, str(r['_id']))
    except:
        print(i)

for _ in range(500):
    r = next_tweet(user_name, event_id)
    if r:
        t[str(r['predef_topic'])] += 1