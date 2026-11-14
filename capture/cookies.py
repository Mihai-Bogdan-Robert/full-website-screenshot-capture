"""Dismiss cookie-consent banners before a page is captured."""

import logging
import time

logger = logging.getLogger(__name__)

# Playwright's :has-text() is a case-insensitive substring match, so "Accept" also covers
# "Accept all", "I accept", "Acceptă", "Tout accepter" and so on.
ACCEPT_BUTTON_TEXTS = [
    'Accept', 'Agree', 'OK', 'Got it', 'Allow', 'Continue', 'Consent',
    'De acord', 'Înțeleg', 'Inteleg',
    'Akzeptieren', 'Zustimmen',
    "J'accepte",
    'Aceptar',
]
ACCEPT_LINK_TEXTS = ['Accept', 'I agree']

ACCEPT_SELECTORS = (
    [f'button:has-text("{text}")' for text in ACCEPT_BUTTON_TEXTS]
    + [f'a:has-text("{text}")' for text in ACCEPT_LINK_TEXTS]
    + [
        '#onetrust-accept-btn-handler',
        '#accept-cookies', '#accept-all-cookies', '#cookie-accept', '#cookies-accept',
        '#cookieAccept', '#acceptCookies', '#gdpr-accept', '#consent-accept',
        '.cookie-accept', '.accept-cookies', '.cookie-consent-accept',
        "[data-action='accept']", "[data-consent='accept']", '[data-cookie-accept]',
        '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
        '#CybotCookiebotDialogBodyButtonAccept',
        '.qc-cmp2-summary-buttons button:first-child',
        '.cookie-close', '.cookie-dismiss',
        "[aria-label='Close cookie banner']", "[aria-label='Accept cookies']",
    ]
)

# Fallback when no button was found: hide the banner containers and any fixed overlay, and
# give the page its scrolling back.
HIDE_BANNERS_JS = """
() => {
    const bannerSelectors = [
        '#onetrust-consent-sdk', '#cookie-banner', '#cookie-notice', '#gdpr-banner',
        '.cookie-banner', '.cookie-notice', '.gdpr-banner', '.consent-banner',
        '[class*="cookie-consent"]', '[class*="cookie-banner"]',
        '[id*="cookie-consent"]', '[id*="cookie-banner"]',
    ];
    document.querySelectorAll(bannerSelectors.join(',')).forEach(el => { el.style.display = 'none'; });

    document.querySelectorAll('[class*="overlay"], [class*="backdrop"]').forEach(el => {
        const style = window.getComputedStyle(el);
        if (style.position === 'fixed' && parseFloat(style.opacity) > 0.3) {
            el.style.display = 'none';
        }
    });

    document.body.style.overflow = 'auto';
    document.documentElement.style.overflow = 'auto';
}
"""


def dismiss_cookie_banners(page):
    """Click the first visible "accept" button. If there is none, hide banners with JavaScript.

    Returns True when a button was clicked.
    """
    for selector in ACCEPT_SELECTORS:
        try:
            element = page.locator(selector).first
            if element.is_visible(timeout=200):
                element.click(timeout=1000)
                logger.info('Dismissed cookie banner with %s', selector)
                time.sleep(0.5)  # let the banner animate away
                return True
        except Exception:
            continue

    try:
        page.evaluate(HIDE_BANNERS_JS)
    except Exception:
        pass
    return False
