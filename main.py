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

# ---- Crawler + Screenshotter ----
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

def main(folder, url, max_pages=200, delay=1.0, headless=True, user_agent=None):
    """
    Programmatic entrypoint for use by other code.

    Usage:
        import main
        result = main.main(folder, url)

    Returns a dict: { 'screenshots': int, 'out_dir': str }
    """

    #--------------------TODO----------------------
    # Add delay slider between requests in GUI

    page_count = crawl_and_screenshot(url, folder, max_pages=max_pages, delay=delay, headless=headless, user_agent=user_agent)
    return { 'screenshots': page_count, 'out_dir': folder }
