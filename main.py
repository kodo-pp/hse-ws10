#!/usr/bin/env python

import json
import re
import sys
import time
from argparse import ArgumentParser
from queue import Queue

import requests as rq
from bs4 import BeautifulSoup
from loguru import logger


def parse_arguments():
    ap = ArgumentParser(
        description = 'Download an HTML page, find HTTPS links in it and save them into a JSON file',
    )
    ap.add_argument(
        '--url',
        '-u',
        type = str,
        help = 'The URL from which to download the HTML page',
        required = True,
    )
    ap.add_argument(
        '--output',
        '-o',
        type = str,
        help = 'The name of the output file',
        required = True,
    )
    ap.add_argument(
        '--delay',
        '-d',
        type = float,
        help = 'Delay before downloads (real number; defaults to 0)',
        default = 0.0,
    )
    ap.add_argument(
        '--max-iterations',
        '-m',
        type = int,
        help = 'Max iterations',
        default = 1000,
    )

    return ap.parse_args()


def download_html_page(url):
    try:
        response = rq.get(url)
    except Exception as e:
        # Error message provided by requests is too long and technical, so we'll just use a general message
        #raise Exception(f'Unable to download the page: {e}') from e
        raise Exception(f'Unable to download the web page') from e
    if response.status_code != 200:
        raise Exception(f'Server returned {response.status_code}')
    return response.content


def find_text(element):
    if isinstance(element, str):
        return [element]
    else:
        return element.find_all(text=True)


def concat_lists(list_of_lists):
    return sum(list_of_lists, [])


def find_links(html):
    try:
        bs = BeautifulSoup(markup=html, features='html.parser')
    except Exception as e:
        raise Exception(f'Unable to parse HTML: {e}') from e

    for element in bs.find_all('a'):
        try:
            href = element['href']
        except KeyError as e:
            # Skip the link if it doesn't have a `href` attribute
            continue

        children = list(element.children)
        text_elements = concat_lists(find_text(child) for child in children)
        text = ' '.join(text_elements)
        yield (text, href)


def is_internal(url):
    return url.startswith('/wiki/')


def write_json(data, filename):
    try:
        with open(filename, 'w') as file:
            json.dump(data, file)
    except Exception as e:
        raise Exception(f'Failed to write file: {e}') from e


def make_absolute(url, lang):
    return f'https://{lang}.wikipedia.org' + url


def recursive_download_and_parse(url, lang, iteration_limit=1000, delay=0):
    # Not actually recursive because downloading is DFS (Depth First Search) manner with the limit on
    # the number on iterations instead of the recursion depth doesn't make much sense. Instead, the BFS-like
    # algorithm is used
    #
    # Yields:
    #     Pairs of (text, href) of internal links

    task_queue = Queue(iteration_limit + 10)
    task_queue.put(url)

    iterations = 0
    while not task_queue.empty() and iterations < iteration_limit:
        current_url = task_queue.get_nowait()
        iterations += 1
        logger.info('Iteration {}: get {}', iterations, current_url)
        try:
            html = download_html_page(current_url)
            internal_links = (
                (text, make_absolute(href, lang=lang))
                for text, href in find_links(html)
                if is_internal(href)
            )
            for text, href in internal_links:
                yield text, href
                if not task_queue.full():
                    task_queue.put_nowait(href)
            time.sleep(delay)
        except Exception as e:
            logger.error(e)
            continue


def parse_url(url):
    return re.match(r'https?://([a-z]+)[.]wikipedia.org/', url)


def main():
    try:
        config = parse_arguments()
        parsed_url = parse_url(config.url)
        if parsed_url is None:
            raise Exception('The program can only work with wikipedia urls: http(s)://<lang>.wikipedia.org')
        lang = parsed_url.group(1)

        result = dict(
            recursive_download_and_parse(
                config.url,
                iteration_limit = config.max_iterations,
                delay = config.delay,
                lang = lang,
            )
        )
        write_json(result, config.output)

    except Exception as e:
        logger.error('Error: {}', e)
        sys.exit(1)


if __name__ == '__main__':
    main()
