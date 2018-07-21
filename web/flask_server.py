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
app = Flask(__name__)
app.secret_key = "hola guaripolas &##&$:__--_*[????=)&%==/%)=$%&?==fsBFgrd34Gevu98%( $%&#&/$Y#"


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


def partition(lst, n):
    return [lst[i::n] for i in range(n)]


# init
data_path = Path('/Users/mquezada/news-model/tweet_topics/')
files = list(data_path.glob('event_*-topic_*-tweet_ids_sorted_mmr.txt'))

topics_tweetids = defaultdict(list)

all_tweets = get_tweets()
all_tweets_d = dict()
for t in all_tweets:
    all_tweets_d[str(t['_id'])] = t
    
for f_0 in files:
    #print(f_0)
    _, ev, top, _, _, _ = f_0.name.split("_")
    event_id = ev.split("-")[0]
    topic_id = top.split("-")[0]
    #print(event_id, topic_id)
    
    with f_0.open() as f:
        for i, line in enumerate(f):
            r_id = line[:-1]
            topics_tweetids[topic_id].append(r_id)

labelers = dict()
events = get_events()
for e in events:
    event_id = str(e['_id'])
    all_topics, _ = get_topics(event_id)
    topics_tweets_this_event = {k: v for (k, v) in topics_tweetids.items() if k in [str(t['_id']) for t in all_topics]}
    labelers[event_id] = TopicLabeler(topics_tweets_this_event)


@app.route("/")
def root():
    events = get_events()
    return render_template('events.html', events=events)

@app.route("/init", methods=["POST"])
def init():
    user_name = request.form["nombre"]
    session['user_name'] = user_name
    event_id = request.form["eligeEvento"]
    return redirect(url_for('tweets', event_id=event_id))


@app.route("/event/<event_id>/tweets")
def tweets(event_id):
    all_topics, nrel = get_topics(event_id)

    topic_labeler = labelers[event_id]

    _info("querying a random tweet")
    topic, tweet_idx = topic_labeler.sample()
    tweet_id = topic_labeler.get_tweet(topic, tweet_idx)  # es un tweet_id
    
    tweet = db.tweets.find_one({'_id': ObjectId(tweet_id)})
    representative_id = str(tweet['representative'])

    return render_template('tweets.html',
                           tweet=tweet,
                           all_topics=all_topics,
                           non_rel = nrel,
                           event_id=event_id,
                           representative_id=representative_id,
                           tweet_idx=tweet_idx,
                           original_topic_id=topic)


def tweets1(event_id):
    path = Path('/home/mquezada/tweet_topics/')
    files = list(path.glob(f'event_{event_id}-topic_*-tweet_ids_sorted_mmr.txt'))
    if not files:
        return redirect(url_for('root'))

    topics = []
    for f in files:
        with f.open('r') as g:
            topics.append([line[:-1] for line in g.readlines()])

    print(topics)


@app.route("/event/label", methods=["GET", "POST"])
def label():
    representative_id = request.args.get('representative_id')
    event_id = request.args.get('event_id')
    tweet_idx = request.args.get('tweet_idx')
    original_topic_id = request.args.get('original_topic_id')
    topic_id = request.form.get('topic_id')
    user_name = session['user_name']
    topic_text = request.form.get('topic_text')

    if not (representative_id and topic_id and event_id and user_name):
        abort(400)

    _info(f"rep={representative_id}, event_id={event_id}, idx={tweet_idx}, orig_top={original_topic_id}, topic_id={topic_id}, topic_text={topic_text}, user={user_name}")
    
    db.representatives.update_one(
        {"_id": ObjectId(representative_id)},
        {
            "$push": {
                "topic": {
                    "topic_id": ObjectId(topic_id) if topic_id != "otro" else "otro",
                    "topic_text": topic_text,
                    "added_timestamp": datetime.utcnow(),
                    "user_name": user_name
                }
            }
        } 
    )

    labelers[event_id].label(original_topic_id, int(tweet_idx))
    return redirect(url_for('tweets', event_id=event_id))
