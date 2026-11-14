"""The whole capture: find the pages, then screenshot them."""

import logging

from capture.crawler import crawl_website
from capture.screenshots import screenshot_urls
from capture.sitemap import parse_sitemap, sitemap_url_for

logger = logging.getLogger(__name__)

# Progress bar layout: discovery runs from 20 to 50, screenshots from 50 to 95.
DISCOVERY_START = 20
DISCOVERY_END = 50


def _discover_crawl(url, max_pages, delay, on_progress):
    def crawl_progress(found, queued, current_url):
        percent = DISCOVERY_START + int(found / max_pages * (DISCOVERY_END - DISCOVERY_START))
        on_progress(f'Crawling pages... ({found}/{max_pages} found)', min(percent, DISCOVERY_END - 1))

    on_progress('Crawling website to discover pages...', DISCOVERY_START)
    urls = crawl_website(url, max_pages=max_pages, delay=delay, progress_callback=crawl_progress)
    on_progress(f'Crawled {len(urls)} pages, starting screenshots...', DISCOVERY_END)
    return urls


def _discover_sitemap(url, on_progress):
    on_progress('Parsing sitemap...', DISCOVERY_START)
    urls = parse_sitemap(sitemap_url_for(url))
    on_progress(f'Found {len(urls)} pages in sitemap, starting screenshots...', DISCOVERY_END)
    return urls


def capture_site(url, on_screenshot, max_pages=200, mode='sitemap', device='desktop',
                 delay=0.5, on_progress=None, should_cancel=None):
    """Capture the pages of a website.

    Args:
        url: an absolute http(s) address (the site, or a sitemap .xml in sitemap mode)
        on_screenshot: called as on_screenshot(filename, png_bytes) for every screenshot
        max_pages: how many pages to capture at most
        mode: 'sitemap' reads sitemap.xml, 'crawl' follows links
        device: 'desktop' or 'mobile'
        delay: seconds between requests while crawling
        on_progress: optional on_progress(message, percent)
        should_cancel: optional callable that returns True when the capture should stop

    Returns {'screenshots': n, 'failed': n, 'urls_found': n}.
    """
    notify = on_progress or (lambda message, percent: None)

    if mode == 'crawl':
        urls = _discover_crawl(url, max_pages, delay, notify)
    else:
        urls = _discover_sitemap(url, notify)

    result = screenshot_urls(urls[:max_pages], on_screenshot, device=device,
                             on_progress=on_progress, should_cancel=should_cancel)
    result['urls_found'] = len(urls)
    return result
