"""Page discovery from a sitemap.xml."""

import logging
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

from capture.security import safe_get

logger = logging.getLogger(__name__)

USER_AGENT = 'FullWebsiteCaptures/1.0 (+https://github.com/Mihai-Bogdan-Robert/full-website-screenshot-capture)'
MAX_URLS = 5000
MAX_CHILD_SITEMAPS = 20


def sitemap_url_for(url):
    """The sitemap address for a site: the URL itself if it already points to an .xml file,
    otherwise /sitemap.xml on the same host."""
    parsed = urlparse(url)
    if parsed.path.lower().endswith('.xml'):
        return url
    return urljoin(f'{parsed.scheme}://{parsed.netloc}', '/sitemap.xml')


def parse_sitemap(sitemap_url, timeout=15, _depth=0):
    """Return the de-duplicated page URLs listed in a sitemap.

    A sitemap index (a sitemap that lists other sitemaps) is followed one level deep, up to
    MAX_CHILD_SITEMAPS children. A child that cannot be read is skipped.
    """
    response = safe_get(sitemap_url, headers={'User-Agent': USER_AGENT}, timeout=timeout)
    response.raise_for_status()

    root = ET.fromstring(response.content.decode('utf-8-sig', errors='replace'))
    locs = [e.text.strip() for e in root.iter()
            if e.tag.lower().endswith('loc') and e.text and e.text.strip()]

    if root.tag.lower().endswith('sitemapindex'):
        if _depth >= 1:
            return []
        urls = []
        for child in locs[:MAX_CHILD_SITEMAPS]:
            try:
                urls.extend(parse_sitemap(child, timeout=timeout, _depth=_depth + 1))
            except Exception as err:
                logger.warning('Could not read child sitemap %s: %s', child, err)
            if len(urls) >= MAX_URLS:
                break
        locs = urls

    return list(dict.fromkeys(locs))[:MAX_URLS]
