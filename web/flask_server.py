from pymongo import MongoClient
from bson.objectid import ObjectId
from random import choice
import random
import logging
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, session, request, abort
from functools import lru_cache
from pathlib import Path
from collections import defaultdict

from web.topic_labeler2 import get_next_tweet, label_tweet


logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)
_info = logging.info

client = MongoClient('mongodb://localhost:27017')
db = client.twitter_news
app = Flask(__name__)
app.secret_key = "hola guaripolas &##&$:__--_*[????=)&%==/%)=$%&?==fsBFgrd34Gevu98%( $%&#&/$Y#"

# FLASK_APP=flask_server.py FLASK_ENV=development flask run --host=0.0.0.0

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


@app.route("/")
def root():
    events = get_events()
    message = session.get('message')
    session['message'] = None
    return render_template('events.html', events=events, message=message)

@app.route("/init", methods=["POST"])
def init():
    user_name = request.form["nombre"]
    password = request.form["password"]

    u = db.users.find_one({'username': user_name, 'password': password})
    if u:
        session['user_name'] = user_name
        event_id = request.form["eligeEvento"]
        return redirect(url_for('tweets', event_id=event_id))
    else:
        session['message'] = "Usuario/contraseña incorrectos"
        return redirect(url_for('root'))


@app.route("/event/<event_id>/tweets")
def tweets(event_id):
    all_topics, nrel = get_topics(event_id)
    user_name = session['user_name']
    representative, count = get_next_tweet(user_name, event_id)
    
    tweet = db.tweets.find_one({'representative': representative['_id']})
    representative_id = str(tweet['representative'])

    return render_template('tweets.html',
                           tweet=tweet,
                           all_topics=all_topics,
                           non_rel = nrel,
                           event_id=event_id,
                           count=count,
                           representative_id=representative_id)


@app.route("/event/label", methods=["GET", "POST"])
def label():
    representative_id = request.args.get('representative_id')
    event_id = request.args.get('event_id')
    
    user_name = session['user_name']

    if not (representative_id and event_id and user_name):
        abort(400)

    topic_ids = request.form.getlist('topic_id')
    topic_text = request.form.get('topic_text')

    non_relevant = request.form.get('non_relevant')
    skip = request.form.get('skip')

    res = label_tweet(user_name=user_name,
                      topic_ids=topic_ids,
                      topic_text=topic_text,
                      non_relevant=non_relevant,
                      skip=skip,
                      representative_id=representative_id)

    _info(f"updated: {representative_id}. User: {user_name}")
    return redirect(url_for('tweets', event_id=event_id))
