"""Helpers for deciding which links the crawler follows."""

from urllib.parse import urldefrag, urljoin, urlparse

SKIPPED_EXTENSIONS = (
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico', '.bmp',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.zip', '.rar', '.tar', '.gz', '.7z',
    '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
    '.css', '.js', '.json', '.xml', '.rss', '.atom',
    '.woff', '.woff2', '.ttf', '.eot', '.otf',
    '.exe', '.dmg', '.apk', '.msi',
)

SKIPPED_PATHS = (
    '/wp-admin', '/wp-includes', '/wp-content/plugins',
    '/admin', '/login', '/logout', '/register', '/signup',
    '/cart', '/checkout', '/account',
    '/api/', '/feed/', '/rss',
    '/.well-known/', '/cdn-cgi/',
)


def normalize_url(url, base_url=None):
    """Make a link absolute and comparable: no fragment, no trailing slash (except the root).

    Returns None for anything that is not an http(s) address.
    """
    if url.startswith('//'):
        url = 'https:' + url
    elif base_url and not url.startswith(('http://', 'https://')):
        url = urljoin(base_url, url)

    url, _ = urldefrag(url)
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return None

    path = parsed.path.rstrip('/') or '/'
    normalized = f'{parsed.scheme}://{parsed.netloc}{path}'
    if parsed.query:
        normalized += f'?{parsed.query}'
    return normalized


def is_same_domain(url, base_domain):
    """True for the domain itself and any of its subdomains."""
    host = urlparse(url).netloc.lower()
    base_domain = base_domain.lower()
    return host == base_domain or host.endswith('.' + base_domain)


def should_skip_url(url):
    """True for files and paths that are not pages worth capturing."""
    path = urlparse(url).path.lower()
    return path.endswith(SKIPPED_EXTENSIONS) or any(skip in path for skip in SKIPPED_PATHS)
