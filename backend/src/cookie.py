"""
Cookie banner detection and dismissal functionality.
"""

import time
import logging
from config import COOKIE_SELECTORS

logger = logging.getLogger(__name__)


def dismiss_cookie_banners(page, timeout=3000):
    """
    Attempts to dismiss cookie consent banners by clicking accept buttons.
    
    Args:
        page: Playwright page object
        timeout: Timeout in milliseconds for locating elements
    
    Returns:
        True if a banner was dismissed, False otherwise
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
