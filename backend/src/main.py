"""
Main orchestration module for logik.

Coordinates crawling/sitemap parsing with screenshot capture.

Usage:
    import logik
    result = logik.main('https://example.com', folder='output')
    result = logik.main('https://example.com', mode='crawl')
    result = logik.main('https://example.com', device='mobile')
"""

import logging
from sitemap import parse_sitemap
from crawler import crawl_website
from screenshot import screenshot_urls
from utils import build_url

logger = logging.getLogger(__name__)


def main(url, folder=None, max_pages=200, delay=1.0, headless=True, user_agent=None, mode='sitemap', device='desktop', progress_callback=None, screenshot_callback=None, cancel_check=None):
    """
    Main entry point for logik - coordinates URL discovery and screenshot capture.
    
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

    Returns a dict: { 'screenshots': int, 'failed': int, 'failed_urls': list, 'saved': list, 'out_dir': str, 'urls_found': int }
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
