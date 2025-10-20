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

# ---- Helpers ----
def same_domain(base_netloc, url):
    try:
        p = urlparse(url)
        return p.netloc == base_netloc
    except:
        return False

def normalize_url(base, link):
    # Remove fragments and normalize relative URLs
    joined = urljoin(base, link)
    nofrag, _ = urldefrag(joined)
    return nofrag

def extract_links(html, base_url):
    links = set()
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if href:
            links.add(normalize_url(base_url, href))
    return links

def crawl_and_screenshot(start_url, out_dir, max_pages=200, delay=1.0, headless=True, user_agent=None):
    os.makedirs(out_dir, exist_ok=True)
    parsed = urlparse(start_url)
    base_netloc = parsed.netloc
    base_scheme = parsed.scheme
    base_origin = f"{base_scheme}://{base_netloc}"

    # robots.txt
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(urljoin(base_origin, "/robots.txt"))
    try:
        rp.read()
    except:
        # If robots.txt cannot be read, continue but be conservative
        pass

    # BFS queue
    q = queue.Queue()
    q.put(start_url)
    seen = set([start_url])
    page_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(user_agent=user_agent) if user_agent else browser.new_context()
        page = context.new_page()

        while not q.empty() and page_count < max_pages:
            url = q.get()

            # robots check
            path = urlparse(url).path or "/"
            if rp.can_fetch("*", url) is False:
                print(f"[robots] skipping (disallowed): {url}")
                continue

            try:
                print(f"[visit] {url}")
                # First fetch HTML to extract links (faster than rendering every page)
                # This will not handle JS-generated links, but is fast and polite.
                headers = {"User-Agent": user_agent} if user_agent else {}
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    print(f"  -> HTTP {resp.status_code}, skipping link extraction")
                    html = resp.text if resp.text else ""
                else:
                    html = resp.text

                # extract links and enqueue same-domain ones
                for link in extract_links(html, url):
                    if same_domain(base_netloc, link) and link not in seen:
                        seen.add(link)
                        q.put(link)

                # Now render with Playwright and screenshot
                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                except Exception as e:
                    # fallback: try load with smaller wait
                    try:
                        page.goto(url, timeout=20000)
                    except Exception as e2:
                        print(f"  -> page.goto failed: {e2}; skipping screenshot")
                        continue

                # Wait briefly so dynamic content can settle (tweak if needed)
                time.sleep(0.5)

                # Create filename-safe path
                safe_name = url.replace("://", "_").replace("/", "_").replace("?", "_").replace("&", "_")
                if len(safe_name) > 200:
                    safe_name = safe_name[:200]
                filename = os.path.join(out_dir, f"{page_count:04d}_{safe_name}.png")

                # fullPage screenshot
                try:
                    page.screenshot(path=filename, full_page=True)
                    print(f"  -> screenshot saved: {filename}")
                except Exception as e:
                    print(f"  -> screenshot failed: {e}")

                page_count += 1
                # delay functionality is commented out for now (GUI will implement later)
                # time.sleep(delay)

            except Exception as e:
                print(f"  -> error visiting {url}: {e}")

        try:
            context.close()
            browser.close()
        except:
            pass

    print(f"Done. {page_count} screenshots saved in {out_dir}")
    return page_count

def screenshot_urls(urls, out_dir, start_index=0, max_pages=None, headless=True, user_agent=None):
    """
    Take screenshots for a list of absolute URLs and save them into out_dir.

    Returns a dict: { 'screenshots': int, 'failed': int, 'failed_urls': list }
    """
    os.makedirs(out_dir, exist_ok=True)
    total = 0
    failed = 0
    failed_urls = []

    if max_pages is None:
        max_pages = len(urls)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(user_agent=user_agent) if user_agent else browser.new_context()
        page = context.new_page()

        for i, url in enumerate(urls[start_index:], start=start_index):
            if total >= max_pages:
                break
            try:
                print(f"[visit] {url}")
                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                except Exception:
                    try:
                        page.goto(url, timeout=20000)
                    except Exception as e:
                        print(f"  -> page.goto failed: {e}; skipping screenshot")
                        failed += 1
                        failed_urls.append(url)
                        continue

                # Wait briefly so dynamic content can settle
                time.sleep(0.5)

                safe_name = url.replace("://", "_").replace("/", "_").replace("?", "_").replace("&", "_")
                if len(safe_name) > 200:
                    safe_name = safe_name[:200]
                filename = os.path.join(out_dir, f"{i:04d}_{safe_name}.png")

                try:
                    page.screenshot(path=filename, full_page=True)
                    print(f"  -> screenshot saved: {filename}")
                    total += 1
                except Exception as e:
                    print(f"  -> screenshot failed: {e}")
                    failed += 1
                    failed_urls.append(url)

                # delay commented out; GUI will implement delay control later
                # time.sleep(delay)

            except Exception as e:
                print(f"  -> error visiting {url}: {e}")
                failed += 1
                failed_urls.append(url)

        try:
            context.close()
            browser.close()
        except:
            pass

    return { 'screenshots': total, 'failed': failed, 'failed_urls': failed_urls, 'out_dir': out_dir }





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
    #result = screenshot_urls(urls, folder, start_index=0, max_pages=max_pages, headless=headless, user_agent=user_agent)
    
    #-------------TODO--------4 STEP: Screenshot mobile URLs-–-------------------–––-

    return "Great"
