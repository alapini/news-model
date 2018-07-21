from pathlib import Path
import logging
from paths import data_path
from functools import lru_cache


# global functions and variables
_info = logging.info


@lru_cache(maxsize=1)
def load_urls():
    _info("loading short urls")
    # short urls
    # all_short_urls: List<List<short_url_id<str>, url<str>, expanded_url_id<str>>>
    with (data_path / Path('short_urls.tsv')).open() as f:
        next(f)
        all_short_urls = [line.split() for line in f.readlines()]

    short_urls = dict()
    # short_urls: url<str> => expanded_url_id<int>
    for _, url, e_id in all_short_urls:
        if e_id == "NULL":
            continue
        short_urls[url] = int(e_id)
    _info(f'loaded {len(short_urls)} urls')

    _info("loading expanded urls")
    # all_exp_urls: List<List<expanded_url_id<str>, expanded_url<str>, title<str>, expanded_clean<str>>>
    with (data_path / Path('expanded_urls.tsv')).open(encoding='utf-8') as f:
        next(f)
        all_exp_urls = [line.split('\t') for line in f.readlines()]

    expanded_urls = dict()
    # X expanded_urls: expanded_url_id<int> => Tuple<expanded_url<str>, expanded_clean<str>, title<str>>

    # expanded_urls: expanded_url_id<int> => expanded_clean<str>
    for _id, exp, title, exp_clean in all_exp_urls:
        # expanded_urls[int(_id)] = (exp, exp_clean.replace('\n', '').replace('\\n', ''), title)
        expanded_urls[int(_id)] = exp_clean.replace('\n', '').replace('\\n', '')
    _info(f'loaded {len(expanded_urls)} urls')

    _info("cleaning url residual info")

    return short_urls, expanded_urls
