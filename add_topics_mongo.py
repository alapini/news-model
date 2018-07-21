from collections import defaultdict
from datetime import datetime
import logging

from pymongo import MongoClient
from tqdm import tqdm


logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)
_info = logging.info

client = MongoClient('mongodb://localhost:27017')

db = client.twitter_news

event_names = ('libya_hotel_tweets.tsv',
               'oscar_pistorius_tweets.tsv',
               'nepal_tweets.tsv')

print("Event list")
print("==========")
for e in event_names:
    print(e)

e = ""
while e not in event_names:
    e = input("event? ")

print("add topics (Ctrl+C to exit)")
while True:
    topic_name = input("Topic name? ")
    event_obj = db.events.find_one({"event_name": e})
    topic_obj = {
        "topic_name": topic_name,
        "event": event_obj['_id']
    }

    res = db.topics.insert_one(topic_obj)
    print(f"Topic inserted with ID {res.inserted_id}")