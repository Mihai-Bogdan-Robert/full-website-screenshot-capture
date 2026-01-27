#!/usr/bin/env python3
"""
crawl_screenshots.py

Usage:
    python crawl_screenshots.py https://example.com output_folder --max 200 --delay 1.0

This script crawls the given starting URL's domain, respects robots.txt,
takes full-page screenshots with Playwright, and saves them to output_folder.
Supports streaming screenshots via callback for browser-side storage.
"""

import sys
import os
import time
import queue
import logging
import requests
import base64
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

#-----------------------COOKIE BANNER HANDLING---------------------------------

# Common cookie consent button selectors
COOKIE_SELECTORS = [
    # Generic accept buttons (text-based)
    "button:has-text('Accept')",
    "button:has-text('Accept all')",
    "button:has-text('Accept All')",
    "button:has-text('Accept cookies')",
    "button:has-text('Accept Cookies')",
    "button:has-text('I Accept')",
    "button:has-text('I agree')",
    "button:has-text('I Agree')",
    "button:has-text('Agree')",
    "button:has-text('OK')",
    "button:has-text('Got it')",
    "button:has-text('Allow')",
    "button:has-text('Allow all')",
    "button:has-text('Allow All')",
    "button:has-text('Continue')",
    "button:has-text('Consent')",
    
    # Romanian cookie banners
    "button:has-text('Acceptă')",
    "button:has-text('Accepta')",
    "button:has-text('Accept toate')",
    "button:has-text('Acceptă tot')",
    "button:has-text('Sunt de acord')",
    "button:has-text('De acord')",
    "button:has-text('Înțeleg')",
    "button:has-text('Inteleg')",
    
    # German
    "button:has-text('Akzeptieren')",
    "button:has-text('Alle akzeptieren')",
    "button:has-text('Zustimmen')",
    
    # French
    "button:has-text('Accepter')",
    "button:has-text('Tout accepter')",
    "button:has-text('J'accepte')",
    
    # Spanish
    "button:has-text('Aceptar')",
    "button:has-text('Aceptar todo')",
    
    # Common ID/class selectors
    "#onetrust-accept-btn-handler",
    "#accept-cookies",
    "#accept-all-cookies",
    "#cookie-accept",
    "#cookies-accept",
    "#cookieAccept",
    "#acceptCookies",
    "#gdpr-accept",
    "#consent-accept",
    ".cookie-accept",
    ".accept-cookies",
    ".cookie-consent-accept",
    "[data-action='accept']",
    "[data-consent='accept']",
    "[data-cookie-accept]",
    
    # CookieBot
    "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
    "#CybotCookiebotDialogBodyButtonAccept",
    
    # Quantcast
    ".qc-cmp2-summary-buttons button:first-child",
    
    # Generic link-based accept
    "a:has-text('Accept')",
    "a:has-text('Accept all')",
    "a:has-text('I agree')",
    
    # Close/dismiss buttons
    ".cookie-close",
    ".cookie-dismiss",
    "[aria-label='Close cookie banner']",
    "[aria-label='Accept cookies']",
]

def dismiss_cookie_banners(page, timeout=3000):
    """
    Attempts to dismiss cookie consent banners by clicking accept buttons.
    """
    for selector in COOKIE_SELECTORS:
        try:
            element = page.locator(selector).first
            if element.is_visible(timeout=200):
                element.click(timeout=1000)
                logger.info(f"   🍪 Dismissed cookie banner with: {selector}")
                # Wait a bit for the banner to disappear
                time.sleep(0.5)
                return True
        except Exception:
            continue
    
    # Also try to remove common overlay elements via JavaScript
    try:
        page.evaluate("""
            () => {
                // Common cookie banner container selectors
                const bannerSelectors = [
                    '#onetrust-consent-sdk',
                    '#cookie-banner',
                    '#cookie-notice',
                    '#gdpr-banner',
                    '.cookie-banner',
                    '.cookie-notice',
                    '.gdpr-banner',
                    '.consent-banner',
                    '[class*="cookie-consent"]',
                    '[class*="cookie-banner"]',
                    '[id*="cookie-consent"]',
                    '[id*="cookie-banner"]',
                ];
                
                bannerSelectors.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {
                        if (el) el.style.display = 'none';
                    });
                });
                
                // Remove any overlay/backdrop
                const overlays = document.querySelectorAll('[class*="overlay"], [class*="backdrop"]');
                overlays.forEach(el => {
                    const style = window.getComputedStyle(el);
                    if (style.position === 'fixed' && parseFloat(style.opacity) > 0.3) {
                        el.style.display = 'none';
                    }
                });
                
                // Re-enable scrolling on body
                document.body.style.overflow = 'auto';
                document.documentElement.style.overflow = 'auto';
            }
        """)
    except Exception:
        pass
    
    return False

#-----------------------SCREENSHOT FUNCTIONALITY-------------------------------

def screenshot_urls(urls, folder=None, start_index=0, max_pages=None, headless=True, user_agent=None, device='desktop', progress_callback=None, screenshot_callback=None, cancel_check=None):
    """
    Takes screenshots of the given URLs using Playwright.

    Filenames are created from the page <title>, sanitized for filesystem safety.
    
    Args:
        urls: List of URLs to capture
        folder: Output folder for screenshots (optional if screenshot_callback is provided)
        start_index: Starting index
        max_pages: Maximum number of pages to capture
        headless: Run browser headless
        user_agent: Custom user agent
        device: 'desktop' or 'mobile'
        progress_callback: Callback for progress updates
        screenshot_callback: If provided, sends (filename, base64_data) instead of saving to disk
        cancel_check: Optional callback() that returns True if job should be cancelled
    
    Returns a dict with counts, failed URLs and saved file paths.
    """
    # Only create folder if we're saving to disk
    if folder and not screenshot_callback:
        os.makedirs(folder, exist_ok=True)
    
    # total: number of successful screenshots
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

    # Manually manage playwright to avoid blocking on context manager exit
    from playwright.sync_api import sync_playwright
    playwright_instance = sync_playwright().start()
    
    try:
        browser = playwright_instance.chromium.launch(headless=headless)
        
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
            # Check for cancellation
            if cancel_check and cancel_check():
                logger.info("⚠️ Job cancelled by user")
                break
            
            if total >= max_pages:
                break
            try:
                # Calculate progress: 50% to 95% for screenshots
                if progress_callback and total_urls > 0:
                    screenshot_progress = 50 + int ((total / total_urls) * 45)
                    progress_callback(f'📸 Capturing screenshot {total+1}/{total_urls}...', screenshot_progress)
                
                logger.info(f"🌐 [{total+1}/{max_pages}] Visiting: {url}")
                
                # Navigate with aggressive timeout - use 'commit' which is fastest
                # This waits only for navigation to commit, not for page to fully load
                try:
                    page.goto(url, timeout=20000, wait_until='commit')
                    # Give more time for initial page elements to load
                    time.sleep(1.5)
                except Exception as nav_error:
                    logger.warning(f"   ⚠️  Navigation error, trying fallback: {nav_error}")
                    # Try one more time with even more aggressive settings
                    try:
                        page.goto(url, timeout=10000, wait_until='commit')
                    except Exception:
                        logger.error(f"   ❌ Failed to load page, skipping")
                        failed += 1
                        failed_urls.append(url)
                        continue
                
                # Don't wait for network idle - it often never happens
                # Wait longer for the page to render and images to load
                time.sleep(3.0)
                
                # Try to dismiss cookie banners and popups
                try:
                    dismiss_cookie_banners(page)
                except Exception as cookie_error:
                    logger.debug(f"   Cookie banner dismissal: {cookie_error}")

                # Try to trigger lazy-loaded images by scrolling the page slowly
                # and then wait until all <img> elements report they are complete
                # (naturalWidth > 0) to reduce partially-loaded images in screenshots.
                try:
                    # Scroll the page in small steps so that lazy-load handlers trigger.
                    page.evaluate("""
                    async () => {
                        const distance = 400;
                        const delay = 300; // ms - increased for slower animations
                        const el = document.scrollingElement || document.documentElement;
                        const maxScrolls = 20; // limit scrolling to prevent hanging
                        let scrollCount = 0;
                        while (el.scrollTop + window.innerHeight < el.scrollHeight && scrollCount < maxScrolls) {
                            el.scrollBy(0, distance);
                            await new Promise(r => setTimeout(r, delay));
                            scrollCount++;
                        }
                        // one final scroll to bottom
                        el.scrollTop = el.scrollHeight;
                        // longer pause at bottom for animations
                        await new Promise(r => setTimeout(r, 1000));
                        // return to top
                        window.scrollTo(0, 0);
                        return true;
                    }
                    """)

                    # Wait for images to fully load
                    page.wait_for_function(
                        "() => { const imgs = Array.from(document.images); if (!imgs.length) return true; return imgs.every(i => i.complete && (i.naturalWidth > 0 || !i.src)); }",
                        timeout=5000,  # Increased to 5s for better image loading
                    )
                except Exception as e:
                    # Non-fatal: if scrolling or the wait fails, proceed to screenshot anyway.
                    logger.debug(f"   ⚠️  Image-ready wait failed (continuing): {str(e)[:50]}")

                # Ensure we're at the top of the page before screenshot
                page.evaluate("window.scrollTo(0, 0)")
                # Wait longer for scroll and animations to complete
                time.sleep(2.0)

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
                while filename in used:
                    filename = f"{base}_{n}.png"
                    n += 1

                # capture the screenshot with full_page=True
                try:
                    if screenshot_callback:
                        # Stream screenshot as base64 to browser
                        screenshot_bytes = page.screenshot(full_page=True)
                        screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                        screenshot_callback(filename, screenshot_base64)
                        logger.info(f"   📸 Screenshot streamed: {filename}")
                    else:
                        # Save to disk
                        fullpath = os.path.join(folder, filename)
                        page.screenshot(path=fullpath, full_page=True)
                        logger.info(f"   📸 Screenshot saved: {filename}")
                        saved_files.append(fullpath)
                    
                    total += 1
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
            logger.info(f"🧹 Cleaning up browser resources...")
            context.close()
            browser.close()
            logger.info(f"✅ Browser closed successfully")
        except Exception as e:
            logger.warning(f"⚠️  Browser cleanup error (non-fatal): {e}")
    
    finally:
        # Note: We skip calling playwright_instance.stop() because it hangs indefinitely
        # The Playwright instance will be cleaned up when the process exits.
        # This was causing 10+ second delays in job completion.
        logger.info(f"✅ Job completed: {total} screenshots, {failed} failed")
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

def main(url, folder=None, max_pages=200, delay=1.0, headless=True, user_agent=None, mode='sitemap', device='desktop', progress_callback=None, screenshot_callback=None, cancel_check=None):
    """
    Usage:
        import main
        result = main.main(url, folder=folder)
        result = main.main(url, mode='crawl')  # Use crawler instead of sitemap
        result = main.main(url, device='mobile')  # Mobile viewport
        result = main.main(url, screenshot_callback=my_callback)  # Stream to browser

    Args:
        url: Website URL or sitemap URL
        folder: Output folder for screenshots (optional if screenshot_callback is provided)
        max_pages: Maximum number of pages to capture
        delay: Delay between requests
        headless: Run browser in headless mode
        user_agent: Custom user agent string
        mode: 'sitemap' (default) or 'crawl'
        device: 'desktop' (default) or 'mobile'
        progress_callback: Optional callback(message, percent) for progress updates
        screenshot_callback: Optional callback(filename, base64_data) to stream screenshots
        cancel_check: Optional callback() that returns True if job should be cancelled

    Returns a dict: { 'screenshots': int, 'urls_found': int }
    """
    
    urls = []
    
    if mode == 'crawl':
        #-----------------------CRAWL MODE: Discover URLs by crawling--------------
        logger.info("🕷️ Using CRAWL mode to discover pages")
        if progress_callback:
            progress_callback('Crawling website to discover pages...', 20)
        
        # Create a crawl progress callback that updates the main progress
        def crawl_progress(discovered_count, queued_count, current_url):
            if progress_callback:
                # Calculate progress: 20% to 50% during crawl phase
                pct = 20 + int((discovered_count / max_pages) * 30) if max_pages > 0 else 20
                progress_callback(f'🕷️ Crawling pages... ({discovered_count}/{max_pages} found)', min(pct, 49))
        
        urls = crawl_website(url, max_pages=max_pages, delay=0.5, progress_callback=crawl_progress)
        if progress_callback:
            progress_callback(f'✅ Crawled {len(urls)} pages, starting screenshots...', 50)
    else:
        #-----------------------SITEMAP MODE: Parse sitemap XML--------------------
        logger.info("📋 Using SITEMAP mode to parse sitemap")
        if progress_callback:
            progress_callback('Parsing sitemap...', 20)
        sitemap_url = build_url(url)
        
        try:
            urls = parse_sitemap(sitemap_url)
            if progress_callback:
                progress_callback(f'📋 Found {len(urls)} pages in sitemap, starting screenshots...', 50)
        except Exception as e:
            logger.error(f"❌ Sitemap parsing failed: {e}")
            raise

    urls_found = len(urls)
    
    # Limit to max_pages number of pages
    if max_pages is not None:
        urls = urls[:max_pages]

    #-------------------------SCREENSHOT URLs--------------------------------------
    result = screenshot_urls(
        urls, 
        folder=folder, 
        start_index=0, 
        max_pages=max_pages, 
        headless=headless, 
        user_agent=user_agent, 
        device=device, 
        progress_callback=progress_callback,
        screenshot_callback=screenshot_callback,
        cancel_check=cancel_check
    )
    
    # Add urls_found to result
    result['urls_found'] = urls_found
    
    return result
