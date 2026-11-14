"""Take a full-page screenshot of each URL in a list."""

import logging
import re
import time

from capture.browser import open_page
from capture.cookies import dismiss_cookie_banners

logger = logging.getLogger(__name__)

# Share of the overall progress bar used by this phase (page discovery uses the part before it).
PROGRESS_START = 50
PROGRESS_SPAN = 45

# Scrolls down in steps so lazy-loaded images load, then returns to the top.
SCROLL_THROUGH_PAGE_JS = """
async () => {
    const distance = 400;
    const delay = 300;
    const maxScrolls = 20;
    const el = document.scrollingElement || document.documentElement;
    let scrolls = 0;
    while (el.scrollTop + window.innerHeight < el.scrollHeight && scrolls < maxScrolls) {
        el.scrollBy(0, distance);
        await new Promise(r => setTimeout(r, delay));
        scrolls++;
    }
    el.scrollTop = el.scrollHeight;
    await new Promise(r => setTimeout(r, 1000));
    window.scrollTo(0, 0);
}
"""

ALL_IMAGES_LOADED_JS = """
() => Array.from(document.images).every(i => i.complete && (i.naturalWidth > 0 || !i.src))
"""


def sanitize_filename_part(text):
    """Reduce a page title to ASCII letters, digits and single dashes (at most 120 characters)."""
    text = re.sub(r'[ _/]', '-', (text or '').strip())
    text = re.sub(r'[^A-Za-z0-9-]', '', text)
    return re.sub(r'-{2,}', '-', text).strip('-')[:120]


def build_filename(index, title, device, taken):
    """`<index>-<title>.png`, with `-mobile` for the mobile profile and a number if taken."""
    suffix = '-mobile' if device == 'mobile' else ''
    base = f'{index:03d}-{sanitize_filename_part(title)}{suffix}'
    filename = f'{base}.png'
    n = 1
    while filename in taken:
        filename = f'{base}_{n}.png'
        n += 1
    return filename


def _open_url(page, url):
    """Navigate to the URL, retrying once with a shorter timeout. Raises if both attempts fail."""
    try:
        # 'commit' returns as soon as the response starts; waiting for network idle often never ends.
        page.goto(url, timeout=20000, wait_until='commit')
        time.sleep(1.5)
    except Exception as err:
        logger.warning('Navigation error, retrying: %s', err)
        page.goto(url, timeout=10000, wait_until='commit')


def _prepare_page(page):
    """Let the page render, close consent banners and load lazy images."""
    time.sleep(3.0)

    try:
        dismiss_cookie_banners(page)
    except Exception as err:
        logger.debug('Cookie banner dismissal failed: %s', err)

    try:
        page.evaluate(SCROLL_THROUGH_PAGE_JS)
        page.wait_for_function(ALL_IMAGES_LOADED_JS, timeout=5000)
    except Exception as err:
        logger.debug('Image wait failed, continuing: %s', str(err)[:50])

    page.evaluate('window.scrollTo(0, 0)')
    time.sleep(2.0)


def screenshot_urls(urls, on_screenshot, device='desktop', on_progress=None, should_cancel=None):
    """Capture every URL and pass each PNG to on_screenshot(filename, png_bytes).

    Pages that fail are skipped. Returns {'screenshots': n, 'failed': n}.
    """
    if not urls:
        return {'screenshots': 0, 'failed': 0}

    captured = 0
    failed = 0
    filenames = set()

    with open_page(device) as page:
        for index, url in enumerate(urls):
            if should_cancel and should_cancel():
                logger.info('Cancelled')
                break

            if on_progress:
                progress = PROGRESS_START + int(index / len(urls) * PROGRESS_SPAN)
                on_progress(f'Capturing screenshot {index + 1}/{len(urls)}...', progress)
            logger.info('[%d/%d] Visiting %s', index + 1, len(urls), url)

            try:
                _open_url(page, url)
                _prepare_page(page)
                try:
                    title = page.title()
                except Exception:
                    title = ''
                filename = build_filename(index, title, device, filenames)
                on_screenshot(filename, page.screenshot(full_page=True))
            except Exception as err:
                logger.error('Failed to capture %s: %s', url, err)
                failed += 1
                continue

            filenames.add(filename)
            captured += 1
            logger.info('Captured %s', filename)

    logger.info('Done: %d captured, %d failed', captured, failed)
    return {'screenshots': captured, 'failed': failed}
