DOMAIN = {
    'tweets': {
        'schema': {
            'tweet_id': {},
            'text': {},
            'created_at': {},
            'retweet_id': {},
            'reply_id': {},
            'short_urls': {},
            'expanded_urls': {},
            'representative_id': {}
        }
    },
    'events': {
        'schema': {
            'event_name': {}
        }
    },
    'representatives': {
        'schema': {
            'event_id': {}
        }
    }
}

MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_USERNAME = ''
MONGO_PASSWORD = ''
MONGO_DBNAME = 'twitter_news'
RESOURCE_METHODS = ['GET']
ITEM_METHODS = ['GET']