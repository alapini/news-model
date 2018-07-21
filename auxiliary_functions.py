import re
from stopwords import stopwords

HASHTAG_PLACEHOLDER = 'ZZZPLACEHOLDERZZZ'


def tokenize(nlp,
             text,
             allow_urls=False,
             allow_stop=False,
             allow_hashtags=False,
             allow_mentions=False):
    text_ht = re.sub(r'#(\w+)', rf'{HASHTAG_PLACEHOLDER}\1', text)

    doc = nlp(text_ht)
    for token in doc:
        if (not allow_stop and (token.is_stop or token.lower_ in stopwords)) \
                or (not allow_urls and token.like_url) \
                or (not allow_mentions and token.text.startswith('@')) \
                or (not allow_hashtags and token.text.startswith(HASHTAG_PLACEHOLDER)) \
                or token.pos_ == 'PUNCT' \
                or token.is_punct \
                or token.is_space \
                or token.is_quote \
                or token.is_bracket:
            continue
        else:
            if token.text.startswith(HASHTAG_PLACEHOLDER):
                yield token
            else:
                yield token.lower_

