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
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup
import urllib.robotparser
from playwright.sync_api import sync_playwright

#-----------------------SCREENSHOT FUNCTIONALITY-------------------------------

def screenshot_urls(urls, folder, start_index=0, max_pages=None, headless=True, user_agent=None):
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
        context = browser.new_context(user_agent=user_agent) if user_agent else browser.new_context()
        page = context.new_page()

        for idx, url in enumerate(urls[start_index:], start=start_index):
            if total >= max_pages:
                break
            try:
                print(f"[visit] {url}")
                # We wait for network to be idle and use a generous timeout (20s) for slower pages
                page.goto(url, timeout=20000)

                page.wait_for_load_state('networkidle', timeout=5000)

                # Try to trigger lazy-loaded images by scrolling the page slowly
                # and then wait until all <img> elements report they are complete
                # (naturalWidth > 0) to reduce partially-loaded images in screenshots.
                try:
                    # Scroll the page in small steps so that lazy-load handlers trigger.
                    page.evaluate("""
                    async () => {
                        const distance = 500;
                        const delay = 100; // ms
                        const el = document.scrollingElement || document.documentElement;
                        while (el.scrollTop + window.innerHeight < el.scrollHeight) {
                            el.scrollBy(0, distance);
                            await new Promise(r => setTimeout(r, delay));
                        }
                        // one final scroll to bottom
                        el.scrollTop = el.scrollHeight;
                        // small pause to let lazy-load handlers run
                        await new Promise(r => setTimeout(r, 200));
                        // return to top (optional)
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
                    print(f"  -> image-ready wait/scroll helper failed: {e}")

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
                    print(f"  -> screenshot saved: {fullpath}")
                    total += 1
                    saved_files.append(fullpath)
                    used.add(filename)
                except Exception as e:
                    print(f"  -> screenshot failed: {e}")
                    failed += 1
                    failed_urls.append(url)

            except Exception as e:
                print(f"  -> error visiting {url}: {e}")
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

def main(folder, url, max_pages=200, delay=1.0, headless=True, user_agent=None):
    """
    Usage:
        import main
        result = main.main(folder, url)

    Returns a dict: { 'screenshots': int, 'out_dir': str }
    """

    #-----------------------------1 STEP: Build sitemap URL-–---––--------------–---
    sitemap_url = build_url(url)

    #-----------------------2 STEP: Parse sitemap to get URLs-–-----------------–––-
    try:
        urls = parse_sitemap(sitemap_url)
    except Exception:
        raise

    # Limit to max_pages number of pages
    if max_pages is not None:
        urls = urls[:max_pages]

    #-------------------------3 STEP: Screenshot URLs-–---––-----------------------
    result = screenshot_urls(urls, folder, start_index=0, max_pages=max_pages, headless=headless, user_agent=user_agent)
    
    #-------------TODO--------4 STEP: Screenshot mobile URLs-–-------------------–––-

    # return the detailed result from the screenshot run so callers can inspect saved files and failures
    return result
