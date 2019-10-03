#!/usr/bin/env python

import json
import sys
from argparse import ArgumentParser

import requests as rq
from bs4 import BeautifulSoup


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


def is_https(url):
    return url.startswith('https://')


def write_json(data, filename):
    try:
        with open(filename, 'w') as file:
            json.dump(data, file)
    except Exception as e:
        raise Exception(f'Failed to write file: {e}') from e


def main():
    try:
        config = parse_arguments()
        html = download_html_page(config.url)
        https_links = [(text, url) for text, url in find_links(html) if is_https(url)]
        write_json(data=https_links, filename=config.output)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
