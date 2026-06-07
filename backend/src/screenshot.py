"""
Screenshot capture functionality using Playwright.
"""

import os
import time
import base64
import asyncio
import logging
import threading
from config import DEVICE_CONFIGS
from cookie import dismiss_cookie_banners
from utils import sanitize_filename

logger = logging.getLogger(__name__)


def screenshot_urls(urls, folder=None, start_index=0, max_pages=None, headless=True, user_agent=None, device='desktop', progress_callback=None, screenshot_callback=None, cancel_check=None):
    """
    Takes screenshots of the given URLs using Playwright.

    Filenames are created from the page <title>, sanitized for filesystem safety.
    Mobile screenshots are suffixed with '-mobile'.
    
    Args:
        urls: List of URLs to capture
        folder: Output folder for screenshots (optional if screenshot_callback is provided)
        start_index: Starting index
        max_pages: Maximum number of pages to capture
        headless: Run browser headless
        user_agent: Custom user agent
        device: 'desktop' or 'mobile'
        progress_callback: Callback for progress updates
        screenshot_callback: If provided, sends (filename, base64_data) instead of saving to disk
        cancel_check: Optional callback() that returns True if job should be cancelled
    
    Returns a dict with counts, failed URLs and saved file paths.
    """
    from playwright.sync_api import sync_playwright
    
    # Determine if this is mobile mode for filename suffix
    is_mobile = device == 'mobile'
    # Only create folder if we're saving to disk
    if folder and not screenshot_callback:
        os.makedirs(folder, exist_ok=True)
    
    # total: number of successful screenshots
    total = 0
    failed = 0
    failed_urls = []
    saved_files = []

    if max_pages is None:
        max_pages = len(urls)
    
    # Get device configuration
    device_config = DEVICE_CONFIGS.get(device, DEVICE_CONFIGS['desktop'])

    used = set()

    # 'used' keeps track of generated filenames during this run so we can avoid collisions when two pages produce the same title.

    # Clean up any existing event loop to prevent "inside asyncio loop" error
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create a new event loop if current one is running
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        elif loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        # No event loop exists, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Manually manage playwright to avoid blocking on context manager exit
    playwright_instance = sync_playwright().start()
    
    try:
        browser = playwright_instance.chromium.launch(headless=headless)
        
        # Create context with device-specific settings
        context_options = {
            'viewport': device_config['viewport'],
            'is_mobile': device_config.get('is_mobile', False),
            'has_touch': device_config.get('has_touch', False),
        }
        
        # Add device scale factor for mobile (retina display)
        if 'device_scale_factor' in device_config:
            context_options['device_scale_factor'] = device_config['device_scale_factor']
        
        # Use custom user agent if provided, otherwise use device default
        if user_agent:
            context_options['user_agent'] = user_agent
        elif device_config.get('user_agent'):
            context_options['user_agent'] = device_config['user_agent']
        
        context = browser.new_context(**context_options)
        page = context.new_page()
        
        logger.info(f"📐 Using {device} viewport: {device_config['viewport']['width']}x{device_config['viewport']['height']}")
        
        total_urls = min(len(urls[start_index:]), max_pages)

        for idx, url in enumerate(urls[start_index:], start=start_index):
            # Check for cancellation
            if cancel_check and cancel_check():
                logger.info("⚠️ Job cancelled by user")
                break
            
            if total >= max_pages:
                break
            try:
                # Calculate progress: 50% to 95% for screenshots
                if progress_callback and total_urls > 0:
                    screenshot_progress = 50 + int((total / total_urls) * 45)
                    progress_callback(f'📸 Capturing screenshot {total+1}/{total_urls}...', screenshot_progress)
                
                logger.info(f"🌐 [{total+1}/{max_pages}] Visiting: {url}")
                
                # Navigate with aggressive timeout - use 'commit' which is fastest
                # This waits only for navigation to commit, not for page to fully load
                try:
                    page.goto(url, timeout=20000, wait_until='commit')
                    # Give more time for initial page elements to load
                    time.sleep(1.5)
                except Exception as nav_error:
                    logger.warning(f"   ⚠️  Navigation error, trying fallback: {nav_error}")
                    # Try one more time with even more aggressive settings
                    try:
                        page.goto(url, timeout=10000, wait_until='commit')
                    except Exception:
                        logger.error(f"   ❌ Failed to load page, skipping")
                        failed += 1
                        failed_urls.append(url)
                        continue
                
                # Don't wait for network idle - it often never happens
                # Wait longer for the page to render and images to load
                time.sleep(3.0)
                
                # Try to dismiss cookie banners and popups
                try:
                    dismiss_cookie_banners(page)
                except Exception as cookie_error:
                    logger.debug(f"   Cookie banner dismissal: {cookie_error}")

                # Try to trigger lazy-loaded images by scrolling the page slowly
                # and then wait until all <img> elements report they are complete
                # (naturalWidth > 0) to reduce partially-loaded images in screenshots.
                try:
                    # Scroll the page in small steps so that lazy-load handlers trigger.
                    page.evaluate("""
                    async () => {
                        const distance = 400;
                        const delay = 300; // ms - increased for slower animations
                        const el = document.scrollingElement || document.documentElement;
                        const maxScrolls = 20; // limit scrolling to prevent hanging
                        let scrollCount = 0;
                        while (el.scrollTop + window.innerHeight < el.scrollHeight && scrollCount < maxScrolls) {
                            el.scrollBy(0, distance);
                            await new Promise(r => setTimeout(r, delay));
                            scrollCount++;
                        }
                        // one final scroll to bottom
                        el.scrollTop = el.scrollHeight;
                        // longer pause at bottom for animations
                        await new Promise(r => setTimeout(r, 1000));
                        // return to top
                        window.scrollTo(0, 0);
                        return true;
                    }
                    """)

                    # Wait for images to fully load
                    page.wait_for_function(
                        "() => { const imgs = Array.from(document.images); if (!imgs.length) return true; return imgs.every(i => i.complete && (i.naturalWidth > 0 || !i.src)); }",
                        timeout=5000,  # Increased to 5s for better image loading
                    )
                except Exception as e:
                    # Non-fatal: if scrolling or the wait fails, proceed to screenshot anyway.
                    logger.debug(f"   ⚠️  Image-ready wait failed (continuing): {str(e)[:50]}")

                # Ensure we're at the top of the page before screenshot
                page.evaluate("window.scrollTo(0, 0)")
                # Wait longer for scroll and animations to complete
                time.sleep(2.0)

                # read <title> from the page, if Playwright fails to get it fall back to empty string
                try:
                    title = page.title() or ''
                except Exception:
                    title = ''

                name = sanitize_filename(title)
                # Build filename: index-PageTitle.png or index-PageTitle-mobile.png
                suffix = "-mobile" if is_mobile else ""
                base = f"{idx:03d}-{name}{suffix}"
                filename = base + ".png"
                n = 1

                # Filename conflicts
                while filename in used:
                    filename = f"{base}_{n}.png"
                    n += 1

                # capture the screenshot with full_page=True
                try:
                    if screenshot_callback:
                        # Stream screenshot as base64 to browser
                        screenshot_bytes = page.screenshot(full_page=True)
                        screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                        screenshot_callback(filename, screenshot_base64)
                        logger.info(f"   📸 Screenshot streamed: {filename}")
                    else:
                        # Save to disk
                        fullpath = os.path.join(folder, filename)
                        page.screenshot(path=fullpath, full_page=True)
                        logger.info(f"   📸 Screenshot saved: {filename}")
                        saved_files.append(fullpath)
                    
                    total += 1
                    used.add(filename)
                except Exception as e:
                    logger.error(f"   ❌ Screenshot failed: {e}")
                    failed += 1
                    failed_urls.append(url)

            except Exception as e:
                logger.error(f"   ❌ Error visiting page: {e}")
                failed += 1
                failed_urls.append(url)

        try:
            logger.info(f"🧹 Cleaning up browser resources...")
            context.close()
            browser.close()
            logger.info(f"✅ Browser closed successfully")
        except Exception as e:
            logger.warning(f"⚠️  Browser cleanup error (non-fatal): {e}")
    
    finally:
        # Properly stop Playwright to clean up asyncio event loop
        # Use a thread with timeout to prevent hanging
        def stop_playwright():
            try:
                playwright_instance.stop()
            except Exception:
                pass
        
        stop_thread = threading.Thread(target=stop_playwright, daemon=True)
        stop_thread.start()
        stop_thread.join(timeout=5)  # Wait max 5 seconds
        
        if stop_thread.is_alive():
            logger.warning(f"⚠️  Playwright stop timed out (continuing anyway)")
        else:
            logger.info(f"✅ Playwright instance stopped")
        
        logger.info(f"✅ Job completed: {total} screenshots, {failed} failed")
    
    return { 'screenshots': total, 'failed': failed, 'failed_urls': failed_urls, 'saved': saved_files, 'out_dir': folder }
