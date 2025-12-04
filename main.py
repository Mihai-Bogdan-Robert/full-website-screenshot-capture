#!/usr/bin/env python3
"""
crawl_screenshots.py

Usage:
    python crawl_screenshots.py https://example.com output_folder --max 200 --delay 1.0

This script crawls the given starting URL's domain, respects robots.txt,
takes full-page screenshots with Playwright, and saves them to output_folder.
"""

import sys
import os
import time
import queue
import logging
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup
import urllib.robotparser
from playwright.sync_api import sync_playwright
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Default user agent for crawling
DEFAULT_USER_AGENT = "FullWebsiteCaptures/1.0 (+https://github.com/Mihai-Bogdan-Robert/Full-Website-Captures)"

# Device viewport configurations
DEVICE_CONFIGS = {
    'desktop': {
        'viewport': {'width': 1920, 'height': 1080},
        'user_agent': None,  # Use default
        'is_mobile': False,
        'has_touch': False,
    },
    'mobile': {
        'viewport': {'width': 390, 'height': 844},
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'is_mobile': True,
        'has_touch': True,
        'device_scale_factor': 3,
    }
}

#-----------------------SCREENSHOT FUNCTIONALITY-------------------------------

def screenshot_urls(urls, folder, start_index=0, max_pages=None, headless=True, user_agent=None, device='desktop', progress_callback=None):
    """
    Takes screenshots of the given URLs using Playwright.

    Filenames are created from the page <title>, sanitized for filesystem safety.
    Returns a dict with counts, failed URLs and saved file paths.
    """
    os.makedirs(folder, exist_ok=True)
    # total: number of successful screenshots saved
    total = 0
    failed = 0
    failed_urls = []
    saved_files = []

    if max_pages is None:
        max_pages = len(urls)
    
    # Get device configuration
    device_config = DEVICE_CONFIGS.get(device, DEVICE_CONFIGS['desktop'])

    def sanitize(s):
        # Convert None to empty string and trim whitespace
        s = (s or '').strip()
        # Replace forward slashes (path separators) with a dash so we never create nested paths
        s = s.replace('/', '-')
        # Replace spaces and underscores with a single dash to meet your requirement
        s = s.replace(' ', '-').replace('_', '-')
        # Keep only ASCII letters, digits and dash
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
        out = ''.join(ch for ch in s if ch in allowed)
        # collapse multiple consecutive dashes into a single dash
        while '--' in out:
            out = out.replace('--', '-')
        # strip leading/trailing dashes
        out = out.strip('-')
        # limit filename length to 120 characters
        return out[:120]

    used = set()

    # 'used' keeps track of generated filenames during this run so we can avoid collisions when two pages produce the same title.

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        
        # Create context with device-specific settings
        context_options = {
            'viewport': device_config['viewport'],
            'is_mobile': device_config.get('is_mobile', False),
            'has_touch': device_config.get('has_touch', False),
        }
        
        # Add device scale factor for mobile (retina display)
        if 'device_scale_factor' in device_config:
            context_options['device_scale_factor'] = device_config['device_scale_factor']
        
        # Use custom user agent if provided, otherwise use device default
        if user_agent:
            context_options['user_agent'] = user_agent
        elif device_config.get('user_agent'):
            context_options['user_agent'] = device_config['user_agent']
        
        context = browser.new_context(**context_options)
        page = context.new_page()
        
        logger.info(f"📐 Using {device} viewport: {device_config['viewport']['width']}x{device_config['viewport']['height']}")
        
        total_urls = min(len(urls[start_index:]), max_pages)

        for idx, url in enumerate(urls[start_index:], start=start_index):
            if total >= max_pages:
                break
            try:
                # Calculate progress: 50% to 95% for screenshots
                if progress_callback and total_urls > 0:
                    screenshot_progress = 50 + int((total / total_urls) * 45)
                    progress_callback(f'Capturing page {total+1}/{total_urls}...', screenshot_progress)
                
                logger.info(f"🌐 [{total+1}/{max_pages}] Visiting: {url}")
                # We wait for network to be idle and use a generous timeout (20s) for slower pages
                page.goto(url, timeout=20000)

                page.wait_for_load_state('networkidle', timeout=5000)
                
                # Initial wait after page load for JavaScript to initialize
                time.sleep(1.5)

                # Try to trigger lazy-loaded images by scrolling the page slowly
                # and then wait until all <img> elements report they are complete
                # (naturalWidth > 0) to reduce partially-loaded images in screenshots.
                try:
                    # Scroll the page in small steps so that lazy-load handlers trigger.
                    page.evaluate("""
                    async () => {
                        const distance = 400;
                        const delay = 150; // ms - slightly longer delay for content to load
                        const el = document.scrollingElement || document.documentElement;
                        while (el.scrollTop + window.innerHeight < el.scrollHeight) {
                            el.scrollBy(0, distance);
                            await new Promise(r => setTimeout(r, delay));
                        }
                        // one final scroll to bottom
                        el.scrollTop = el.scrollHeight;
                        // pause at bottom to let lazy-load handlers run
                        await new Promise(r => setTimeout(r, 500));
                        // return to top
                        window.scrollTo(0, 0);
                        return true;
                    }
                    """)

                    # Wait until all images are either complete or there are no images.
                    # This avoids taking screenshots while images are mid-download.
                    page.wait_for_function(
                        "() => { const imgs = Array.from(document.images); if (!imgs.length) return true; return imgs.every(i => i.complete && (i.naturalWidth > 0 || !i.src)); }",
                        timeout=10000,
                    )
                except Exception as e:
                    # Non-fatal: if scrolling or the wait fails, proceed to screenshot anyway.
                    logger.warning(f"   ⚠️  Image-ready wait failed (continuing anyway): {e}")

                # Final wait after scrolling to ensure all animations/transitions complete
                time.sleep(1.0)

                # read <title> from the page, if Playwright fails to get it fall back to empty string
                try:
                    title = page.title() or ''
                except Exception:
                    title = ''

                name = sanitize(title)
                # join index and name with a dash (e.g., 007-Optik)
                base = f"{idx:03d}-{name}"
                filename = base + ".png"
                n = 1

                # Filename conflicts
                while filename in used or os.path.exists(os.path.join(folder, filename)):
                    filename = f"{base}_{n}.png"
                    n += 1

                fullpath = os.path.join(folder, filename)

                # capture and save the screenshot with full_page=True
                try:
                    page.screenshot(path=fullpath, full_page=True)
                    logger.info(f"   📸 Screenshot saved: {filename}")
                    total += 1
                    saved_files.append(fullpath)
                    used.add(filename)
                except Exception as e:
                    logger.error(f"   ❌ Screenshot failed: {e}")
                    failed += 1
                    failed_urls.append(url)

            except Exception as e:
                logger.error(f"   ❌ Error visiting page: {e}")
                failed += 1
                failed_urls.append(url)

        try:
            context.close()
            browser.close()
        except:
            pass

    return { 'screenshots': total, 'failed': failed, 'failed_urls': failed_urls, 'saved': saved_files, 'out_dir': folder }

#-----------------------URL EXTRACTION FROM SITEMAP XML-----------------------

def parse_sitemap(sitemap_url, timeout=15):
    """
    Simple sitemap parser: fetches sitemap_url (expects a plain sitemap.xml)
    and returns a list of URLs found in <loc> tags.
    """
    headers = {"User-Agent": "FullWebsiteCaptures/1.0 (+https://github.com/Mihai-Bogdan-Robert/Full-Website-Captures)"}
    resp = requests.get(sitemap_url, headers=headers, timeout=timeout)
    resp.raise_for_status() # Throws an error for HTTP errors if code if not 200
    
    # Convert raw bytes to string
    text = resp.content.decode('utf-8-sig', errors='replace')

    try:
        root = ET.fromstring(text) #Python’s built-in XML parser: xml.etree.ElementTree (aliased as ET).
    except ET.ParseError:
        raise

    urls = []
    # iterate all elements and pick the tags with 'loc'
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


#-----------------------WEB CRAWLER - DISCOVER LINKS--------------------------

def normalize_url(url, base_url=None):
    """
    Normalize a URL by removing fragments, trailing slashes, and ensuring consistent format.
    """
    # Handle relative URLs
    if base_url and not url.startswith(('http://', 'https://', '//')):
        url = urljoin(base_url, url)
    elif url.startswith('//'):
        url = 'https:' + url
    
    # Remove fragment
    url, _ = urldefrag(url)
    
    # Parse and reconstruct
    parsed = urlparse(url)
    
    # Skip non-http(s) URLs
    if parsed.scheme not in ('http', 'https'):
        return None
    
    # Normalize path - remove trailing slash except for root
    path = parsed.path
    if path != '/' and path.endswith('/'):
        path = path.rstrip('/')
    if not path:
        path = '/'
    
    # Reconstruct URL without fragment, with normalized path
    normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    
    return normalized


def is_same_domain(url, base_domain):
    """
    Check if a URL belongs to the same domain (including subdomains).
    """
    parsed = urlparse(url)
    url_domain = parsed.netloc.lower()
    base_domain = base_domain.lower()
    
    # Exact match or subdomain match
    return url_domain == base_domain or url_domain.endswith('.' + base_domain)


def should_skip_url(url):
    """
    Check if a URL should be skipped (non-page resources).
    """
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    # Skip common non-page extensions
    skip_extensions = (
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico', '.bmp',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.rar', '.tar', '.gz', '.7z',
        '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
        '.css', '.js', '.json', '.xml', '.rss', '.atom',
        '.woff', '.woff2', '.ttf', '.eot', '.otf',
        '.exe', '.dmg', '.apk', '.msi'
    )
    
    if any(path.endswith(ext) for ext in skip_extensions):
        return True
    
    # Skip common non-content paths
    skip_paths = (
        '/wp-admin', '/wp-includes', '/wp-content/plugins',
        '/admin', '/login', '/logout', '/register', '/signup',
        '/cart', '/checkout', '/account',
        '/api/', '/feed/', '/rss',
        '/.well-known/', '/cdn-cgi/'
    )
    
    if any(skip in path for skip in skip_paths):
        return True
    
    return False


def get_robots_parser(base_url):
    """
    Fetch and parse robots.txt for the given base URL.
    Returns a RobotFileParser or None if robots.txt is not available.
    """
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url)
    
    try:
        rp.read()
        return rp
    except Exception:
        return None


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
            
            logger.info(f"🔍 [{len(discovered)+1}/{max_pages}] Crawling: {normalized}")
            
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


#------------------------------------------------------------------------------

def build_url(unparsed_url):
    parsed_url = urlparse(unparsed_url)
    if not parsed_url.scheme:
        # assume https when scheme is missing
        unparsed_url = 'https://' + unparsed_url.lstrip('/')
        parsed_url = urlparse(unparsed_url)
    
    # if path already contains a sitemap file, use as-is
    if parsed_url.path and parsed_url.path.lower().endswith('.xml'):
        return unparsed_url
    
    # otherwise, append /sitemap.xml to the origin
    origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
    return urljoin(origin, '/sitemap.xml')

#------------------------------------------------------------------------------

def main(folder, url, max_pages=200, delay=1.0, headless=True, user_agent=None, mode='sitemap', device='desktop', progress_callback=None):
    """
    Usage:
        import main
        result = main.main(folder, url)
        result = main.main(folder, url, mode='crawl')  # Use crawler instead of sitemap
        result = main.main(folder, url, device='mobile')  # Mobile viewport

    Args:
        folder: Output folder for screenshots
        url: Website URL or sitemap URL
        max_pages: Maximum number of pages to capture
        delay: Delay between requests
        headless: Run browser in headless mode
        user_agent: Custom user agent string
        mode: 'sitemap' (default) or 'crawl'
        device: 'desktop' (default) or 'mobile'
        progress_callback: Optional callback(message, percent) for progress updates

    Returns a dict: { 'screenshots': int, 'out_dir': str, 'urls_found': int }
    """
    
    urls = []
    
    if mode == 'crawl':
        #-----------------------CRAWL MODE: Discover URLs by crawling--------------
        logger.info("🕷️ Using CRAWL mode to discover pages")
        if progress_callback:
            progress_callback('Crawling website to discover pages...', 20)
        urls = crawl_website(url, max_pages=max_pages, delay=0.5)
        if progress_callback:
            progress_callback(f'Found {len(urls)} pages, starting screenshots...', 50)
    else:
        #-----------------------SITEMAP MODE: Parse sitemap XML--------------------
        logger.info("📋 Using SITEMAP mode to parse sitemap")
        if progress_callback:
            progress_callback('Parsing sitemap...', 20)
        sitemap_url = build_url(url)
        
        try:
            urls = parse_sitemap(sitemap_url)
            if progress_callback:
                progress_callback(f'Found {len(urls)} pages, starting screenshots...', 50)
        except Exception as e:
            logger.error(f"❌ Sitemap parsing failed: {e}")
            raise

    urls_found = len(urls)
    
    # Limit to max_pages number of pages
    if max_pages is not None:
        urls = urls[:max_pages]

    #-------------------------SCREENSHOT URLs--------------------------------------
    result = screenshot_urls(urls, folder, start_index=0, max_pages=max_pages, headless=headless, user_agent=user_agent, device=device, progress_callback=progress_callback)
    
    # Add urls_found to result
    result['urls_found'] = urls_found
    
    return result
