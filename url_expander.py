import requests
import multiprocessing
import time
import datetime
import asyncio
import aiohttp
from typing import List
import logging

logger = logging.getLogger(__name__)

def resolve_url(short_url):
    try:
        response = requests.head(short_url, allow_redirects=True)
        logger.info('Done: {} ({})'.format(response.url, response.status_code))
        return short_url, response.url, response.status_code
    
    except Exception as e:
        logger.error(str(e))
    
    return short_url, None, None


async def get(url):
    logger.info(f'GET: {url}')
    async with aiohttp.ClientSession() as session:
        async with session.head(url, allow_redirects=True) as response:
            t = '{0:%H:%M:%S}'.format(datetime.datetime.now())
            logger.info('Done: {}, {} ({})'.format(t, response.url, response.status))
            return response.url


def get_urls(urls: List[str]):
    loop = asyncio.get_event_loop()
    tasks = [asyncio.ensure_future(get(u)) for u in urls]
    loop.run_until_complete(asyncio.wait(tasks))
    return tasks


if __name__ == '__main__':
    from pathlib import Path
    import pickle

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', level=logging.INFO)
    #urls_path = Path('/home/mquezada/news-model-git/news-model/data_crisismmd')
    urls_path = Path('/home/mquezada/news-model-git/news-model/data_ccmr/urls.txt')

    urls = []
    #for fn in urls_path.glob('*_urls.txt'):
    #   with fn.open() as f:
    #       urls.extend([u[:-1] for u in f.readlines()])
    with urls_path.open() as f:
        for line in f:
            urls.append(line[:-1])

    p = multiprocessing.Pool(processes=20)
    result = p.map(resolve_url, urls)
    