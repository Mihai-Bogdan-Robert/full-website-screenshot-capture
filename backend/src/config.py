"""
Configuration constants and settings for logik.
"""

import logging

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
