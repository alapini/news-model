from collections import defaultdict
from datetime import datetime
import logging

from gen_model import load_data

from pymongo import MongoClient
from tqdm import tqdm


logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)
_info = logging.info

client = MongoClient('mongodb://localhost:27017')

db = client.twitter_news

event_names = ('libya_hotel_tweets.tsv',
               'oscar_pistorius_tweets.tsv',
               'nepal_tweets.tsv')

# insert events
db_events = db.events
event_id = dict()

for e in event_names:
    db_event = {
        'event_name': e
    }
    result = db_events.insert_one(db_event)
    event_id[e] = result.inserted_id
    print(f"Event {e} with ID {result.inserted_id}")
print(event_id)


# create_representatives
# event_name = 'libya_hotel_tweets.tsv'

for event_name in event_names:
    _info(event_name)
    event_data, _ = load_data(event_name)

    text_ids = defaultdict(list)
    for tweet_id_str, tweet in tqdm(event_data.items(), total=len(event_data), desc="creating reprs"):
        text_ids[tweet.text].append(tweet_id_str)

    # insert representatives
    db_repr = db.representatives
    db_tweets = db.tweets

    representatives = list()
    for tweet_id_str_list in tqdm(text_ids.values(), total=len(text_ids), desc="saving reprs and tweets"):
        rep = {
            'event': event_id[event_name]
        }
        res = db_repr.insert_one(rep)
        _id = res.inserted_id

        tweets_to_insert = list()
        for tweet_id_str in tweet_id_str_list:
            tweet = event_data[tweet_id_str]

            expanded_urls = [tweet.expanded_urls.get(i)
                             for i, _ in enumerate(tweet.short_urls)]

            twt = {
                'tweet_id': int(tweet_id_str),
                'text': tweet.text,
                'created_at': datetime.strptime(tweet.created_at, '%Y-%m-%d %H:%M:%S'),
                'retweet_id': None if tweet.retweet_id == "NULL" else int(tweet.retweet_id),
                'reply_id': None if tweet.reply_id == "NULL" else int(tweet.reply_id),
                'short_urls': tweet.short_urls,
                'expanded_urls': expanded_urls,
                'representative': _id
            }
            tweets_to_insert.append(twt)
        res2 = db_tweets.insert_many(tweets_to_insert)

        if len(tweet_id_str_list) != len(res2.inserted_ids):
            _info(f"Saved {len(res2)} tweets of {len(tweet_id_str_list)} in Repr")

