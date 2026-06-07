"""
Sitemap XML parsing functionality.
"""

import xml.etree.ElementTree as ET
import requests
import logging
from config import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)


def parse_sitemap(sitemap_url, timeout=15):
    """
    Simple sitemap parser: fetches sitemap_url (expects a plain sitemap.xml)
    and returns a list of URLs found in <loc> tags.
    
    Args:
        sitemap_url: URL to the sitemap.xml file
        timeout: Request timeout in seconds
    
    Returns:
        List of URLs found in the sitemap
        
    Raises:
        HTTP errors if the request fails
        ET.ParseError if XML parsing fails
    """
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    resp = requests.get(sitemap_url, headers=headers, timeout=timeout)
    resp.raise_for_status()  # Throws an error if response code is not 200
    
    # Convert raw bytes to string
    text = resp.content.decode('utf-8-sig', errors='replace')

    try:
        root = ET.fromstring(text)  # Python's built-in XML parser
    except ET.ParseError:
        raise

    urls = []
    # Iterate all elements and pick the tags with 'loc'
    for elem in root.iter():
        if elem.tag.lower().endswith('loc') and elem.text and elem.text.strip():
            urls.append(elem.text.strip())

    # Deduplicate
    seen = set()
    unique_urls = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)
    
    return unique_urls
