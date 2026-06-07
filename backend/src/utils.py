"""
Utility functions for URL processing and validation.
"""

import urllib.robotparser
from urllib.parse import urlparse, urljoin, urldefrag
import logging

logger = logging.getLogger(__name__)


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


def build_url(unparsed_url):
    """
    Build a sitemap URL from a given URL.
    If the URL already ends with .xml, use as-is.
    Otherwise, append /sitemap.xml to the origin.
    """
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


def sanitize_filename(s):
    """
    Sanitize a string for use as a filename.
    - Convert None to empty string and trim whitespace
    - Replace forward slashes with dashes
    - Replace spaces and underscores with dashes
    - Keep only ASCII letters, digits and dash
    - Collapse multiple dashes into single dash
    - Strip leading/trailing dashes
    - Limit to 120 characters
    """
    s = (s or '').strip()
    s = s.replace('/', '-')
    s = s.replace(' ', '-').replace('_', '-')
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
    out = ''.join(ch for ch in s if ch in allowed)
    while '--' in out:
        out = out.replace('--', '-')
    out = out.strip('-')
    return out[:120]
