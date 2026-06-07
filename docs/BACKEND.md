# Backend Documentation

The backend is a containerized Flask API server that orchestrates screenshot capture, manages jobs, and serves the web interface.

---

## Quick Start

### Starting the Backend

```bash
# With Docker (recommended)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop
docker-compose down
```

### Local Development (no Docker)

```bash
# Install dependencies
pip install -r backend/requirements.txt
playwright install chromium

# Set environment variables
export PORT=5000
export FLASK_ENV=development

# Run
python app.py

# Output:
# WARNING: This is a development server. Do not use it in production.
#  * Running on http://127.0.0.1:5000
```

---

## API Endpoints

### 1. Start Capture Job

**Endpoint**: `POST /api/capture/start`

**Request**:
```json
{
    "domain": "https://example.com",
    "max_pages": 200,
    "discovery_modes": ["sitemap", "crawl"],
    "devices": ["desktop", "mobile"]
}
```

**Parameters**:
- `domain` (string, required): Website domain or URL
- `max_pages` (int, optional): Maximum pages to capture (1-1000, default: 200)
- `discovery_modes` (array, required): `["sitemap"]`, `["crawl"]`, or `["sitemap", "crawl"]`
- `devices` (array, required): `["desktop"]`, `["mobile"]`, or `["desktop", "mobile"]`

**Response**:
```json
{
    "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "running",
    "message": "Starting capture..."
}
```

**Status codes**:
- `200 OK` - Job created successfully
- `400 Bad Request` - Invalid parameters
- `500 Internal Server Error` - Server error

**Example**:
```bash
curl -X POST http://localhost:5000/api/capture/start \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "max_pages": 50,
    "discovery_modes": ["sitemap"],
    "devices": ["desktop"]
  }'
```

---

### 2. Get Job Progress

**Endpoint**: `GET /api/capture/progress/{job_id}`

**Response**:
```json
{
    "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "running",
    "progress": 45,
    "message": "Capturing screenshot 45/100",
    "screenshots": 45,
    "failed": 2,
    "failed_urls": [
        "https://example.com/page-with-error-1",
        "https://example.com/page-with-error-2"
    ],
    "screenshots_data": [
        {
            "filename": "page-title-1.png",
            "data": "iVBORw0KGgoAAAANSUhEUgAA... (base64 PNG)"
        },
        {
            "filename": "page-title-2.png",
            "data": "iVBORw0KGgoAAAANSUhEUgAA... (base64 PNG)"
        }
    ]
}
```

**Status codes**:
- `200 OK` - Job found, data returned
- `404 Not Found` - Job ID doesn't exist

**Example**:
```bash
curl http://localhost:5000/api/capture/progress/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Status values**:
- `pending` - Job created, not started
- `running` - Currently capturing
- `completed` - Success (may have some failures)
- `cancelled` - User cancelled
- `failed` - Critical error occurred

---

### 3. Cancel Job

**Endpoint**: `POST /api/capture/cancel/{job_id}`

**Response**:
```json
{
    "success": true,
    "message": "Job cancelled"
}
```

**Status codes**:
- `200 OK` - Cancellation accepted
- `404 Not Found` - Job not found
- `400 Bad Request` - Job already completed/cancelled

**Example**:
```bash
curl -X POST http://localhost:5000/api/capture/cancel/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

---

### 4. Download Screenshots

**Endpoint**: `GET /api/capture/download/{job_id}`

**Response**: Binary ZIP file attachment

**Status codes**:
- `200 OK` - ZIP file returned
- `404 Not Found` - Job not found
- `409 Conflict` - Job not completed

**Example**:
```bash
curl -O http://localhost:5000/api/capture/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  -o screenshots.zip
```

---

### 5. Health Check

**Endpoint**: `GET /api/health`

**Response**:
```json
{
    "status": "ok",
    "timestamp": "2024-01-20T15:30:45.123456",
    "uptime": 3600
}
```

**Status codes**:
- `200 OK` - Backend is healthy

**Example**:
```bash
curl http://localhost:5000/api/health
```

---

### 6. Web Interface (Static Files)

**Endpoint**: `GET /` and static files

**Response**: HTML, CSS, JavaScript files from `frontend/` folder

**Status codes**:
- `200 OK` - File returned
- `404 Not Found` - File not found

---

## Job Structure

### CaptureJob Class

```python
class CaptureJob:
    def __init__(self):
        self.job_id = uuid.uuid4()
        self.status = "running"  # or "completed", "cancelled", "failed"
        self.progress = 0  # 0-100
        self.message = ""
        self.screenshots = []  # List of {"filename": ..., "data": ...}
        self.failed_urls = []
        self.start_time = time.time()
        self.cancelled = False
```

---

## How Capture Works

### Flow

```
1. POST /api/capture/start
   └─ Validate input
   └─ Create CaptureJob
   └─ Start background thread
   └─ Return job_id to client

2. Background thread runs _run_capture_job()
   For each discovery_mode in ["sitemap", "crawl"]:
      For each device in ["desktop", "mobile"]:
         a. Discover URLs (sitemap or crawler)
            │
            ├─ Sitemap: Parse XML
            └─ Crawl: BFS web crawler
       
         b. For each discovered URL:
            ├─ Load page with Playwright
            ├─ Dismiss cookie banners
            ├─ Scroll for lazy-load images
            ├─ Take full-page screenshot
            ├─ Convert to base64 PNG
            ├─ Store in job.screenshots[]
            └─ Call progress_callback()
       
         c. Update job.progress (0-100)

3. Client polls GET /api/capture/progress/{job_id}
   └─ Receive live updates every 1 second

4. When complete:
   └─ GET /api/capture/download/{job_id}
   └─ Receive ZIP of all screenshots
```

### Core Modules

#### main.py
```python
main(
    url: str,
    folder: str = None,
    max_pages: int = 200,
    mode: str = 'sitemap',
    device: str = 'desktop',
    progress_callback: callable = None,
    screenshot_callback: callable = None,
    cancel_check: callable = None
) -> dict
```

Orchestrates the capture process. Called for each (mode, device) combination.

#### sitemap.py
```python
parse_sitemap(domain: str) -> list
```

Fetches and parses XML sitemap, returns list of URLs.

#### crawler.py
```python
crawl_website(
    url: str,
    max_pages: int = 200,
    delay: float = 1.0
) -> list
```

Uses BFS to discover internal links. Respects robots.txt and implements crawl delay.

#### screenshot.py
```python
screenshot_urls(
    urls: list,
    device: str = 'desktop',
    max_pages: int = 200,
    progress_callback: callable = None,
    screenshot_callback: callable = None,
    cancel_check: callable = None
) -> dict
```

Captures screenshots for each URL. Handles lazy-loading and cookie dismissal.

#### cookie.py
```python
dismiss_cookie_banners(page: Page) -> None
```

Attempts to dismiss common cookie consent banners using Playwright selectors and JavaScript.

#### utils.py
Utility functions:
- `normalize_url(url)` - Standardize URL format
- `is_same_domain(url1, url2)` - Check if URLs share domain
- `should_skip_url(url)` - Filter non-page resources
- `get_robots_parser(domain)` - Fetch robots.txt
- `sanitize_filename(title)` - Create filesystem-safe names
- `build_url(domain)` - Construct URLs

#### config.py
Configuration constants:
- `DEFAULT_USER_AGENT` - User agent string
- `DEVICE_CONFIGS` - Desktop (1920x1080) and mobile (390x844) configs
- `COOKIE_SELECTORS` - CSS selectors for cookie buttons

---

## Callbacks

The backend uses callbacks to communicate with the API layer:

### progress_callback
```python
def progress_callback(message: str, percent: int):
    """Called regularly to report progress"""
    job.message = message
    job.progress = percent
```

### screenshot_callback
```python
def screenshot_callback(filename: str, base64_data: str):
    """Called when a screenshot is taken"""
    job.screenshots.append({
        'filename': filename,
        'data': base64_data
    })
```

### cancel_check
```python
def cancel_check() -> bool:
    """Returns True if job should be cancelled"""
    return job.cancelled
```

---

## Environment Variables

### Backend (api.py)

```bash
PORT=5000                        # API server port (default: 5000)
FLASK_ENV=development            # "development" or "production"
WEB_INTERFACE_DIR=./frontend     # Path to frontend files
```

### Docker (docker-compose.yml)

```yaml
environment:
- PORT=5000
- FLASK_ENV=production
- WEB_INTERFACE_DIR=/app/frontend
```

---

## Docker Configuration

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (one-time)
RUN playwright install --with-deps chromium

# Copy application code
COPY backend/ .
COPY backend/src /app/src

# Set Python path for imports
ENV PYTHONPATH=/app/src

# Expose API port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Run Flask app
CMD ["python", "api.py"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "5000:5000"
    environment:
      - PORT=5000
      - FLASK_ENV=production
      - WEB_INTERFACE_DIR=/app/frontend
    volumes:
      - ./frontend:/app/frontend:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## Performance Optimization

### Capture Speed

| Metric | Time | Notes |
|--------|------|-------|
| Parse sitemap | 1-5s | Depends on file size |
| Load page | 3-5s | Network + rendering |
| Screenshot | 1-2s | Full-page render + encode |
| Total (50 pages, sitemap, desktop) | 5-10m | Linear with page count |
| Total (50 pages, both modes, both devices) | 20-30m | 4 combinations |

### Bottlenecks

1. **Network latency** - Page load time dominates
2. **Playwright overhead** - Browser launch is expensive
3. **Screenshot rendering** - Full-page screenshots take time
4. **Lazy-loading** - Scrolling adds time but is necessary

### Improvements

- Reuse browser instances across multiple pages
- Parallel capture on multiple cores (future)
- Connection pooling for HTTP requests
- Aggressive timeout settings

---

## Error Handling

### Try/Catch Strategy

```python
try:
    screenshot = page.screenshot(full_page=True)
except TimeoutError:
    # Page took too long
    failed_urls.append(url)
    continue
except Exception as e:
    # Other error
    failed_urls.append(url)
    continue
```

### User Feedback

- **Failed URLs** tracked and returned to user
- **Progress messages** explain what's happening
- **Error logs** available via `docker-compose logs`

---

## Debugging

### View Logs

```bash
# Tail logs in real-time
docker-compose logs -f backend

# View last 100 lines
docker-compose logs --tail=100 backend

# Local development
# Logs output to terminal automatically
```

### Common Issues

#### Backend won't start
```bash
# Check if port is in use
lsof -i :5000

# Try different port
PORT=5001 python app.py
```

#### High memory usage
- Kill unused job threads
- Reduce max_pages
- Restart backend

#### Slow captures
- Switch from `crawl` to `sitemap` mode
- Reduce `max_pages`
- Increase `delay` to avoid rate limiting

---

## Security

### Input Validation

```python
# Validate domain
if not is_valid_url(domain):
    return error_response("Invalid domain")

# Validate max_pages
if max_pages < 1 or max_pages > 1000:
    return error_response("max_pages must be 1-1000")
```

### CORS

```python
# Allow local requests
CORS(app, origins=["http://localhost:*"])
```

### Rate Limiting

Can be added using Flask-Limiter:

```python
from flask_limiter import Limiter
limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route('/api/capture/start', methods=['POST'])
@limiter.limit("10 per hour")
def start_capture():
  ...
```

---

## Testing

### Health check
```bash
curl http://localhost:5000/api/health
```

### Start a job
```bash
curl -X POST http://localhost:5000/api/capture/start \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "max_pages": 10,
    "discovery_modes": ["sitemap"],
    "devices": ["desktop"]
  }'
```

### Check progress
```bash
curl http://localhost:5000/api/capture/progress/<job_id>
```

### Download results
```bash
curl http://localhost:5000/api/capture/download/<job_id> \
  -o results.zip
```

---

## Deployment Considerations

### Production Setup

1. **Use WSGI server** instead of Flask dev server
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 api:app
   ```

2. **Enable HTTPS** with reverse proxy
   ```nginx
   server {
       listen 443 ssl;
       server_name example.com;
     
       location / {
           proxy_pass http://localhost:5000;
       }
   }
   ```

3. **Add database** for job persistence
   ```python
   # Use PostgreSQL instead of in-memory dict
   ```

4. **Implement rate limiting** and authentication
5. **Monitor resources** (CPU, memory, disk)
6. **Set up log aggregation** (ELK, Datadog, etc.)

---

See also: [ARCHITECTURE.md](ARCHITECTURE.md), [CLI.md](CLI.md), [WEB_INTERFACE.md](WEB_INTERFACE.md)
