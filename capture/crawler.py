"""Page discovery by following links, starting from one URL."""

import logging
import time
import urllib.robotparser
from collections import deque
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from capture.security import UnsafeURL, safe_get
from capture.sitemap import USER_AGENT
from capture.urls import is_same_domain, normalize_url, should_skip_url

logger = logging.getLogger(__name__)

IGNORED_HREF_PREFIXES = ('javascript:', 'mailto:', 'tel:', '#')


def get_robots_parser(base_url):
    """Fetch and parse robots.txt. Returns None when it cannot be fetched at all."""
    parsed = urlparse(base_url)
    robots_url = f'{parsed.scheme}://{parsed.netloc}/robots.txt'
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        response = safe_get(robots_url, headers={'User-Agent': USER_AGENT}, timeout=10)
    except Exception:
        return None
    if response.status_code in (401, 403):
        parser.disallow_all = True
    elif response.status_code >= 400:
        parser.allow_all = True
    else:
        parser.parse(response.text.splitlines())
    return parser


def _extract_links(html, page_url, base_domain):
    """Same-domain, normalized links found in an HTML page."""
    soup = BeautifulSoup(html, 'html.parser')
    for link in soup.find_all('a', href=True):
        href = link['href'].strip()
        if not href or href.startswith(IGNORED_HREF_PREFIXES):
            continue
        absolute = normalize_url(href, page_url)
        if absolute and is_same_domain(absolute, base_domain):
            yield absolute


def crawl_website(start_url, max_pages=200, delay=0.5, respect_robots=True, progress_callback=None):
    """Breadth-first crawl of one site. Returns the HTML pages found, at most max_pages.

    progress_callback(found, queued, current_url) is called before each page is fetched.
    """
    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc
    robots = get_robots_parser(f'{parsed_start.scheme}://{base_domain}') if respect_robots else None

    to_visit = deque([start_url])
    visited = set()
    discovered = []

    logger.info('Crawling %s (max %d pages, %.1fs delay)', base_domain, max_pages, delay)

    while to_visit and len(discovered) < max_pages:
        url = normalize_url(to_visit.popleft())
        if not url or url in visited:
            continue
        visited.add(url)

        if robots and not robots.can_fetch(USER_AGENT, url):
            logger.warning('Blocked by robots.txt: %s', url)
            continue
        if should_skip_url(url):
            continue

        try:
            if progress_callback:
                progress_callback(len(discovered), len(to_visit), url)
            logger.info('[%d/%d] Discovering %s', len(discovered) + 1, max_pages, url)

            response = safe_get(url, headers={'User-Agent': USER_AGENT}, timeout=15)
            if 'text/html' not in response.headers.get('Content-Type', '').lower():
                continue
            discovered.append(url)

            for link in _extract_links(response.text, url, base_domain):
                if link not in visited:
                    to_visit.append(link)

            if delay > 0:
                time.sleep(delay)

        except requests.exceptions.Timeout:
            logger.warning('Timeout: %s', url)
        except UnsafeURL as err:
            logger.warning('Not fetched (%s): %s', err, url)
        except requests.exceptions.RequestException as err:
            logger.error('Error fetching %s: %s', url, err)
        except Exception as err:
            logger.error('Unexpected error for %s: %s', url, err)

    logger.info('Crawl finished, %d pages found', len(discovered))
    return discovered
