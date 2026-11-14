"""
URL safety checks (protection against SSRF).

The app fetches and opens whatever address a visitor gives it, so by default it refuses
anything that is not a public http(s) address: localhost, private networks (10.x, 192.168.x,
172.16-31.x), link-local / cloud-metadata addresses (169.254.x), and so on.

Every request is checked: the address typed in the form, every redirect hop, every page found
by the crawler or listed in a sitemap, and every request the browser makes while loading a page.

To capture sites on your own machine or network (for example http://localhost:3000 while
developing), start the app with  ALLOW_PRIVATE_URLS=1.
"""

import ipaddress
import os
import socket
from functools import lru_cache
from urllib.parse import urljoin, urlparse

import requests

MAX_URL_LENGTH = 2048


class UnsafeURL(ValueError):
    """Raised when a URL is not allowed."""


def private_urls_allowed():
    return os.environ.get('ALLOW_PRIVATE_URLS', '').strip().lower() in ('1', 'true', 'yes')


def _is_public_ip(ip):
    ip = ipaddress.ip_address(ip)
    mapped = getattr(ip, 'ipv4_mapped', None)  # ::ffff:127.0.0.1 and similar
    if mapped is not None:
        ip = mapped
    return ip.is_global and not ip.is_multicast


def _resolve(host):
    """Return every IP address a host name points to."""
    try:
        return {info[4][0].split('%')[0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise UnsafeURL(f'Cannot resolve host "{host}"') from exc


def _looks_like_ip(host):
    try:
        ipaddress.ip_address(host.split('%')[0])
        return True
    except ValueError:
        return False


@lru_cache(maxsize=2048)
def _host_is_public_cached(host):
    return all(_is_public_ip(ip) for ip in _resolve(host))


def _host_is_public(host, cache):
    if _looks_like_ip(host):
        return _is_public_ip(host.split('%')[0])
    if cache:
        return _host_is_public_cached(host)
    return all(_is_public_ip(ip) for ip in _resolve(host))


def check_url(url, cache=False):
    """Return the URL if it is allowed, otherwise raise UnsafeURL.

    cache=True remembers the result per host name; use it inside a short-lived worker
    (one capture job), not in the long-running web process.
    """
    if not isinstance(url, str) or not url or len(url) > MAX_URL_LENGTH:
        raise UnsafeURL('Invalid URL')
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise UnsafeURL('Only http and https addresses are allowed')
    try:
        host = parsed.hostname
    except ValueError as exc:
        raise UnsafeURL('Invalid URL') from exc
    if not host:
        raise UnsafeURL('Invalid URL')
    if parsed.username or parsed.password:
        raise UnsafeURL('Addresses with a username or password are not allowed')
    if private_urls_allowed():
        return url
    try:
        public = _host_is_public(host, cache)
    except ValueError as exc:
        raise UnsafeURL('Invalid URL') from exc
    if not public:
        raise UnsafeURL('Only public websites can be captured')
    return url


def normalize_user_url(raw):
    """Add https:// when the scheme is missing, then check the URL."""
    raw = (raw or '').strip()
    if raw and '://' not in raw:
        raw = 'https://' + raw.lstrip('/')
    return check_url(raw)


def safe_get(url, max_redirects=5, **kwargs):
    """requests.get that checks every redirect hop against check_url."""
    kwargs.pop('allow_redirects', None)
    for _ in range(max_redirects + 1):
        check_url(url, cache=True)
        resp = requests.get(url, allow_redirects=False, **kwargs)
        location = resp.headers.get('Location')
        if resp.is_redirect and location:
            resp.close()
            url = urljoin(url, location)
            continue
        return resp
    raise requests.exceptions.TooManyRedirects('Too many redirects')
