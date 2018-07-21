import spacy

nlp = spacy.load('en_core_web_sm', tagger=False, entity=False, matcher=False)

def hashtag_pipe(doc):
    merged_hashtag = False
    while True:
        for token_index, token in enumerate(doc):
            if token.text == '#':
                if token.head is not None:
                    start_index = token.idx
                    end_index = start_index + len(token.head.text) + 1
                    if doc.merge(start_index, end_index) is not None:
                        merged_hashtag = True
                        break
        if not merged_hashtag:
            break
        merged_hashtag = False
    return doc

nlp.add_pipe(hashtag_pipe)

all_tweets = '/home/mquezada/anchor-text-twitter/data/all_tweets.txt'

with open(all_tweets, 'r') as f:
	for doc in nlp.pipe(f, batch_size=512, n_threads=8):
		print(doc)
		break