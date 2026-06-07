# website-capture - Website Screenshot Capture System

A complete web-based system for discovering and capturing full-page screenshots of websites using Playwright.

## Overview

This project consists of three main components:

1. **logik** - Core Python package for website screenshot capture
2. **Backend API** - Flask-based REST API for job management
3. **Web Interface** - Modern, responsive web UI for user interaction

## Features

-  **Multiple Discovery Methods**: Sitemap-based (fast) or web crawler-based (comprehensive)
-  **Device Simulation**: Capture screenshots for desktop and mobile viewports simultaneously
-  **Cookie Banner Handling**: Automatically dismisses common cookie consent banners
- 🖼️ **Lazy-Loading Support**: Scrolls pages to trigger lazy-loaded images
-  **Real-time Progress**: Live progress updates during capture
-  **Screenshot Gallery**: Interactive preview and download of captured screenshots
-  **Robots.txt Compliance**: Respects robots.txt during crawling
-  **Job Management**: Background job processing with cancellation support

## Project Structure

```
website-capture/
├── app.py                    # Flask web server
├── requirements.txt          # Python dependencies
├── README.md                # This file
├── backend/
│   └── src/
│       ├── __init__.py       # Package initialization
│       ├── main.py           # Main orchestration function
│       ├── screenshot.py     # Playwright screenshot capture
│       ├── crawler.py        # Web crawler for link discovery
│       ├── sitemap.py        # Sitemap XML parsing
│       ├── cookie.py         # Cookie banner detection
│       ├── utils.py          # URL utilities
│       └── config.py         # Configuration constants
└── frontend/
    ├── index.html            # Web interface HTML
    ├── style.css             # Styling
    ├── script.js             # Frontend JavaScript
    └── README.md             # Web interface documentation
```

## Quick Start

### Installation

1. **Clone or navigate to the project**:
```bash
cd website-capture
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Install Playwright browsers** (required for screenshot capture):
```bash
playwright install chromium
```

### Running the Web Interface

1. **Start the Flask server**:
```bash
python app.py
```

The server will start on `http://localhost:5000`

2. **Open in browser**:
Navigate to `http://localhost:5000` and use the web interface to:
   - Enter a domain to capture
   - Select discovery methods (Sitemap, Crawl, or both)
   - Choose device types (Desktop, Mobile, or both)
   - Set maximum pages to capture
   - Monitor progress in real-time
   - Download captured screenshots

## Using as a Python Module

You can also use the logik package directly in your Python code:

```python
from backend.src.main import main

# Capture screenshots from sitemap
result = main('https://example.com', folder='output')

# Capture using web crawler
result = main('https://example.com', mode='crawl', folder='output')

# Capture mobile screenshots
result = main('https://example.com', device='mobile', folder='output')

# Capture both desktop and mobile
result = main('https://example.com', device='desktop')  # First call
result = main('https://example.com', device='mobile')   # Second call

# With progress callback
def progress(message, percent):
    print(f"[{percent}%] {message}")

result = main('https://example.com', folder='output', progress_callback=progress)
```

## Web Interface API

The Flask backend provides REST API endpoints:

### Start Capture Job
```
POST /api/capture/start
Content-Type: application/json

{
    "domain": "https://example.com",
    "max_pages": 200,
    "discovery_modes": ["sitemap"],
    "devices": ["desktop"]
}

Response: {"job_id": "uuid", "status": "started"}
```

### Get Job Progress
```
GET /api/capture/progress/{job_id}

Response: {
    "job_id": "uuid",
    "status": "running|completed|failed|cancelled",
    "progress": 50,
    "message": "Capturing screenshot...",
    "urls_found": 100,
    "screenshots": 45,
    "failed": 2,
    "failed_urls": [...],
    "screenshots_data": [...]
}
```

### Cancel Job
```
POST /api/capture/cancel/{job_id}

Response: {"job_id": "uuid", "status": "cancelled"}
```

## Configuration

### Main Function Parameters

The `main()` function accepts:

- **url** (required): Website URL or sitemap URL
- **folder**: Output folder for screenshots (optional)
- **max_pages**: Maximum pages to capture (default: 200, range: 1-1000)
- **delay**: Delay between requests in seconds (default: 1.0)
- **headless**: Run browser in headless mode (default: True)
- **user_agent**: Custom user agent string
- **mode**: 'sitemap' (default) or 'crawl'
- **device**: 'desktop' (default) or 'mobile'
- **progress_callback**: Function(message, percent) for progress updates
- **screenshot_callback**: Function(filename, base64_data) for streaming output
- **cancel_check**: Function() returning True to cancel job

### Device Configurations

The system supports two device profiles:

**Desktop** (1920×1080):
- Standard desktop browser viewport
- Mouse support
- No touch events

**Mobile** (390×844):
- iPhone-like viewport
- Touch support
- Mobile user agent
- 3x device scale factor (retina display)

## Examples

### Example 1: Capture Desktop Screenshots
```python
from backend.src.main import main

result = main(
    'https://example.com',
    folder='screenshots',
    max_pages=50,
    device='desktop'
)

print(f"Captured {result['screenshots']} screenshots")
print(f"Failed: {result['failed']}")
```

### Example 2: Crawl and Capture Both Viewports
```python
from backend.src.main import main

# Desktop
result_desktop = main('https://example.com', mode='crawl', device='desktop', max_pages=100)

# Mobile
result_mobile = main('https://example.com', mode='crawl', device='mobile', max_pages=100)

print(f"Total captured: {result_desktop['screenshots'] + result_mobile['screenshots']}")
```

### Example 3: With Progress Tracking
```python
from backend.src.main import main

def show_progress(message, percent):
    print(f"\r[{'='*int(percent/5)}{'':50-int(percent/5)}] {percent}% - {message}", end='')

result = main(
    'https://example.com',
    folder='output',
    progress_callback=show_progress
)

print(f"\n\nDone! {result['screenshots']} screenshots saved.")
```

## Return Value

All capture operations return a dictionary with:

```python
{
    'screenshots': int,        # Number of successful captures
    'failed': int,            # Number of failed captures
    'failed_urls': list,      # URLs that failed to capture
    'saved': list,            # Paths of saved files (if folder specified)
    'out_dir': str,           # Output directory
    'urls_found': int         # Total URLs discovered
}
```

## Troubleshooting

### Issue: "Playwright not found"
**Solution**: Install Playwright browsers:
```bash
playwright install chromium
```

### Issue: "Address already in use" when starting app.py
**Solution**: Change the port:
```bash
PORT=5001 python app.py
```

### Issue: Slow screenshot capture
**Solution**: 
- Reduce `max_pages` parameter
- Use 'sitemap' mode instead of 'crawl'
- Increase `delay` parameter gradually if getting 429 errors

### Issue: Not capturing all images
**Solution**: Increase page load wait time by modifying `screenshot.py`'s `time.sleep()` calls

## Performance Tips

1. **Use sitemap mode** when available - it's 5-10x faster than crawling
2. **Limit max_pages** to what you actually need
3. **Run in headless mode** (default) - much faster than headed mode
4. **Use desktop only** unless you specifically need mobile captures
5. **Set appropriate delay** to respect server rate limits (default: 1.0s)

## Limitations & Known Issues

- Large websites (1000+ pages) may take significant time
- Very slow/unresponsive websites may timeout
- Some websites block automated browser access
- JavaScript-heavy SPAs may not capture correctly
- Memory usage grows with number of screenshots in a single job

## Future Improvements

- [ ] Database backend for job persistence
- [ ] Screenshot comparison/diff functionality
- [ ] OCR text extraction from screenshots
- [ ] Automated accessibility testing
- [ ] Bulk URL import/export
- [ ] Email notifications on job completion
- [ ] AWS S3 integration for storage
- [ ] Scheduled/recurring captures

## License

See LICENSE file in the parent directory.

## Support

For issues, questions, or contributions, please refer to the parent project repository.

## Environment Variables

The Flask app accepts the following environment variables:

- **PORT**: Server port (default: 5000)
- **FLASK_ENV**: Environment mode (default: production, set to 'development' for debug mode)
- **WORKERS**: Number of worker threads for job processing

Example:
```bash
PORT=5001 FLASK_ENV=development python app.py
```
