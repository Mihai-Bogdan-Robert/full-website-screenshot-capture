"""
logik - Website screenshot capture and archival tool.

A modular system for discovering and capturing full-page screenshots of websites
using Playwright, with support for both sitemap-based and crawler-based discovery.

Usage:
    from logik import main
    result = main('https://example.com', folder='output')
"""

from main import main

__version__ = '0.1.0'
__all__ = ['main']
