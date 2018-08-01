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

from multiprocessing import Value


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
data_path = Path('/home/mquezada/news-model-git/news-model/tweet_topics/')
files = list(data_path.glob('event_*-topic_*-tweet_ids_sorted_mmr.txt'))

topics_tweetids = defaultdict(list)

all_tweets = get_tweets()
all_tweets_d = dict()
for t in all_tweets:
    all_tweets_d[str(t['_id'])] = t

# add two fields to representatives: predef_topic, ranking    
for f_0 in files:
    #print(f_0)
    _, ev, top, _, _, _ = f_0.name.split("_")
    event_id = ev.split("-")[0]
    topic_id = top.split("-")[0]
    #print(event_id, topic_id)
    
    with f_0.open() as f:
        for i, line in enumerate(f):
            tweet_id = line[:-1]
            # topic_id, event_id
            # topics_tweetids[topic_id].append(r_id)
            tweet = db.tweets.find_one({"_id": ObjectId(tweet_id)})
            representative = db.representatives.find_one({"_id": tweet['representative']})
            db.representatives.update_one(
                {'_id': representative['_id']}, 
                {'$set': {'predef_topic': topic_id, 'ranking': i}}
            )


#################################

def next_tweet(user_name, event_id):
    # representatives already labeled by current user:
    reps = db.representatives.find(
        {
            'event': ObjectId(event_id),
            'topic': {
                'user_name': user_name
            }
        }
    )

    labeled_topics = defaultdict(int)
    rankings = defaultdict(int)
    for rep in reps:
        predef_topic = rep['predef_topic']
        labeled_topics[predef_topic] += 1

        if rankings[predef_topic] < rep['ranking']:
            empanada = ...



labelers = dict()
events = get_events()
for e in events:
    event_id = str(e['_id'])
    all_topics, _ = get_topics(event_id)
    topics_tweets_this_event = {k: v for (k, v) in topics_tweetids.items() if k in [str(t['_id']) for t in all_topics]}
    labelers[event_id] = TopicLabeler(topics_tweets_this_event)