"""Headless Chromium: device profiles, and a page whose every request is checked for safety."""

import logging
import threading
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

from capture.security import UnsafeURL, check_url

logger = logging.getLogger(__name__)

DEVICES = {
    'desktop': {
        'viewport': {'width': 1920, 'height': 1080},
        'is_mobile': False,
        'has_touch': False,
    },
    'mobile': {
        'viewport': {'width': 390, 'height': 844},
        'user_agent': ('Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 '
                       '(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'),
        'is_mobile': True,
        'has_touch': True,
        'device_scale_factor': 3,
    },
}

PLAYWRIGHT_STOP_TIMEOUT = 5


def _block_non_public_requests(route):
    """Abort any request the page makes (redirects and sub-resources included) to a
    non-public address."""
    url = route.request.url
    if url.startswith(('http://', 'https://')):
        try:
            check_url(url, cache=True)
        except UnsafeURL:
            logger.warning('Blocked request to a non-public address: %s', url[:120])
            route.abort('blockedbyclient')
            return
    route.continue_()


def _stop_playwright(playwright):
    """Stop Playwright, giving up after a few seconds: its shutdown can hang."""
    stopper = threading.Thread(target=lambda: _ignore_errors(playwright.stop), daemon=True)
    stopper.start()
    stopper.join(timeout=PLAYWRIGHT_STOP_TIMEOUT)
    if stopper.is_alive():
        logger.warning('Playwright did not stop in time, continuing')


def _ignore_errors(func):
    try:
        func()
    except Exception:
        pass


@contextmanager
def open_page(device='desktop'):
    """Yield a Playwright page set up for the given device ('desktop' or 'mobile')."""
    profile = DEVICES.get(device, DEVICES['desktop'])
    logger.info('Using the %s viewport: %dx%d', device, profile['viewport']['width'],
                profile['viewport']['height'])

    # Started by hand instead of `with sync_playwright()` so that a hanging shutdown can be abandoned.
    playwright = sync_playwright().start()
    try:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=False, service_workers='block', **profile)
        context.route('**/*', _block_non_public_requests)
        try:
            yield context.new_page()
        finally:
            try:
                context.close()
                browser.close()
            except Exception as err:
                logger.warning('Browser cleanup error: %s', err)
    finally:
        _stop_playwright(playwright)
