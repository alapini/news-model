from collections import Counter
import random
import numpy as np
from typing import Any, Tuple


class TopicLabeler:
    def __init__(self, topics_tweetids):
        self.topics_tweetids = topics_tweetids
        self.labeled = Counter()
        self.to_label = {topic: list(range(len(tweets))) for topic, tweets in self.topics_tweetids.items()}
        
    def sample(self) -> Tuple[Any, Any]:
        """
        sample tweet con proba inv. prop. a la fraccion de tweets etiquetados del mismo topico
        """
        keys = list(self.topics_tweetids.keys())
        
        totals = [len(self.topics_tweetids[k]) for k in keys]
        labeleds = [self.labeled[k] for k in keys]
        
        fr = np.array([labeled / total for total, labeled in zip(totals, labeleds)])  # in [0, 1]
        probas = 1 - fr  # higher for topics with less labels
        
        x = 1 / sum(probas)
        rnd = random.random()
        p0 = 0
        
        #print([x * p for p in probas])
        
        choice = 0
        #print(rnd)
        for i, p1 in enumerate([x * p for p in probas]):
            #print(p0, p0 + p1)
            if p0 <= rnd < p0 + p1:
                choice = i
                break
            p0 += p1
        
        topic = list(self.topics_tweetids.keys())[choice]
        if not self.to_label[topic]:
            return None  # done!
        
        #tweet = random.choice(self.to_label[topic])
        tweet = self.to_label[topic][0]
        return topic, tweet

    def get_tweet(self, topic, tweet_idx):
        return self.topics_tweetids[topic][tweet_idx]
    
    def label(self, topic_id, tweet_idx):
        self.to_label[topic_id].remove(tweet_idx)
        self.labeled.update({topic_id: 1})
