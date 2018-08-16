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
from pprint import pprint
import os

from web.mongo_password import user, password


random.seed = os.urandom(1024)


DEBUG = False
logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)
_info = logging.info

if user:
    login = f'{user}:{password}@'
else:
    login = ''

client = MongoClient(f'mongodb://{login}localhost:27017')
db = client.twitter_news


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


def get_tweet(event_id, predef_topic, already_labeled_ids, user_name):
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
    total_labeled = sum(len(v) for v in reps_labeled.values())
    
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
    rep = get_tweet(event_id, chosen, already_labeled_ids, user_name)

    if DEBUG:
        print("rep chosen")
        pprint(rep)
        print()

    return rep, total_labeled


def label_tweet(user_name=None, 
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