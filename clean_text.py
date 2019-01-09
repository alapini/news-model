import sys
from tqdm import tqdm

"""
import spacy
nlp = spacy.load('en', disable=["tagger", "parser", "ner", "textcat"])


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

# nlp.add_pipe(hashtag_pipe)
# nlp.tokenizer.infix_finditer = None

"""

fname = sys.argv[1]

with open(fname, 'r') as f:
    next(f)
    for line in tqdm(f, total=27714286):
        for token in line.split():
            word = token.lower()
            if not word.startswith("http://"):
                print(word, end=" ")
        print()




"""
for doc in tqdm(nlp.pipe(f), total=27714286):
        for token in doc:
            if not token.is_punct and not token.like_url:
                print(token.lower_, end=" ")



    for line in tqdm(f, total=27714286):
        tokens = nlp(line)
        for token in tokens:
            if not token.is_punct and not token.like_url:
                print(token.lower_, end=" ")

"""
"""
        for token in line.split():
            word = token.lower()
            if not word.startswith("http://"):
                print(word, end=" ")
"""     
       
 
# g.write(" ".join(token.lower_ for token in doc if not token.is_punct and not token.like_url))
