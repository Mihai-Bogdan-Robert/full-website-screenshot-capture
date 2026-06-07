"""
Web crawler functionality for discovering internal links.
"""

import requests
import logging
from collections import deque
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from config import DEFAULT_USER_AGENT
from utils import normalize_url, is_same_domain, should_skip_url, get_robots_parser

logger = logging.getLogger(__name__)


def crawl_website(start_url, max_pages=200, delay=0.5, respect_robots=True, progress_callback=None):
    """
    Crawl a website starting from start_url, discovering all internal links.
    
    Args:
        start_url: The URL to start crawling from
        max_pages: Maximum number of pages to discover
        delay: Delay between requests in seconds
        respect_robots: Whether to respect robots.txt
        progress_callback: Optional callback function(discovered, queued, current_url)
    
    Returns:
        List of discovered URLs
    """
    import time
    
    # Normalize start URL
    if not start_url.startswith(('http://', 'https://')):
        start_url = 'https://' + start_url
    
    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc
    base_url = f"{parsed_start.scheme}://{parsed_start.netloc}"
    
    # Initialize robots.txt parser
    robots = None
    if respect_robots:
        robots = get_robots_parser(base_url)
    
    # BFS queue and visited set
    to_visit = deque([start_url])
    visited = set()
    discovered = []
    
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    
    logger.info(f"🕷️  Starting crawl of {base_domain}")
    logger.info(f"⚙️  Max pages: {max_pages}, Delay: {delay}s")
    
    while to_visit and len(discovered) < max_pages:
        current_url = to_visit.popleft()
        
        # Skip if already visited
        normalized = normalize_url(current_url)
        if not normalized or normalized in visited:
            continue
        
        visited.add(normalized)
        
        # Check robots.txt
        if robots and not robots.can_fetch(DEFAULT_USER_AGENT, normalized):
            logger.warning(f"   🚫 Blocked by robots.txt: {normalized}")
            continue
        
        # Skip non-page resources
        if should_skip_url(normalized):
            continue
        
        try:
            if progress_callback:
                progress_callback(len(discovered), len(to_visit), normalized)
            
            logger.info(f"🔍 [{len(discovered)+1}/{max_pages}] Discovering: {normalized}")
            
            # Fetch the page
            resp = requests.get(
                normalized, 
                headers=headers, 
                timeout=15,
                allow_redirects=True
            )
            
            # Only process HTML pages
            content_type = resp.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type:
                continue
            
            # Add to discovered list
            discovered.append(normalized)
            
            # Parse HTML and extract links
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            for link in soup.find_all('a', href=True):
                href = link['href'].strip()
                
                # Skip empty, javascript, mailto, tel links
                if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                    continue
                
                # Normalize the URL
                full_url = normalize_url(href, normalized)
                if not full_url:
                    continue
                
                # Only follow links on the same domain
                if not is_same_domain(full_url, base_domain):
                    continue
                
                # Add to queue if not visited
                if full_url not in visited:
                    to_visit.append(full_url)
            
            # Respect delay between requests
            if delay > 0:
                time.sleep(delay)
                
        except requests.exceptions.Timeout:
            logger.warning(f"   ⏱️  Timeout: {normalized}")
        except requests.exceptions.RequestException as e:
            logger.error(f"   ❌ Error fetching {normalized}: {e}")
        except Exception as e:
            logger.error(f"   ❌ Unexpected error for {normalized}: {e}")
    
    logger.info(f"✅ Crawl finished! Discovered {len(discovered)} pages")
    return discovered
