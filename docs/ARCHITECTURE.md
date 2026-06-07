# Architecture Overview

## System Design

The website-capture system is built on a **backend/frontend separation** with a unified REST API:

```
┌─────────────────────────────────────────────────────────────┐
│                   FRONTEND CLIENTS                          │
├─────────────────────────┬─────────────────────────────────┤
│  Web Interface (Browser)│   CLI Tool (Terminal)            │
│  http://localhost:5000 │   $ webcapture capture domain     │
└──────────────┬──────────┴────────────────┬─────────────────┘
               │                           │
               │      HTTP REST API        │
               │   (JSON over HTTP)        │
               │                           │
         ┌─────▼───────────────────────────▼──────┐
         │     Backend (Docker Container)         │
         │      Flask REST API (api.py)           │
         ├──────────────────────────────────────┤
         │  Job Management                      │
         │  • Start capture job                 │
         │  • Track progress                    │
         │  • Cancel jobs                       │
         │  • Download ZIP archive              │
         ├──────────────────────────────────────┤
         │  Core Logic (src/)                   │
         │  • Sitemap parsing                   │
         │  • Web crawler                       │
         │  • Screenshot capture                │
         │  • Cookie handling                   │
         └──────────────────────────────────────┘
```

---

## Two-Interface Design

### Why Two Interfaces?

The system provides **two ways to interact** with the same backend:

#### **Web Interface** (Browser UI)
- **Audience**: Non-technical users, one-off captures, visual workflows
- **Technology**: HTML + CSS + JavaScript (vanilla, no frameworks)
- **Communication**: REST API calls over HTTP
- **Files**: `frontend/index.html`, `style.css`, `script.js`
- **Access**: `http://localhost:5000`

#### **CLI Tool** (Command-line)
- **Audience**: Developers, automation, CI/CD pipelines, batch processing
- **Technology**: Python 3 with requests library
- **Communication**: REST API calls over HTTP (same as web)
- **Files**: `cli/webcapture.py` (runs as a command-line program)
- **Access**: `webcapture capture example.com`

### Unified Backend

Both interfaces communicate with **the same REST API**, so:
-  You can start a job in the web UI and check status from CLI
-  Both use the exact same core logic
-  Jobs are shared across both interfaces
-  Single source of truth

---

## Component Breakdown

### Backend (runs in Docker)

```
backend/
├── Dockerfile                    ← Container definition
├── requirements.txt              ← Python dependencies
├── api.py                       ← Flask REST API server
│                                  - Job management (start, progress, cancel)
│                                  - Web interface static file serving
│                                  - REST API endpoints
│
└── src/                         ← Core screenshot logic
    ├── main.py                  ← Orchestration (main entry point)
    ├── crawler.py               ← BFS web crawler for link discovery
    ├── screenshot.py            ← Playwright-based screenshot capture
    ├── sitemap.py               ← XML sitemap parsing
    ├── cookie.py                ← Cookie banner detection & dismissal
    ├── utils.py                 ← URL utilities (normalize, validate, etc.)
    └── config.py                ← Configuration constants (devices, selectors, etc.)
```

### Frontend (served from backend)

```
frontend/
├── index.html                   ← Form + progress UI + results gallery
├── style.css                    ← Responsive styling
└── script.js                    ← API communication & interactivity
```

### CLI Tool (installed locally)

```
cli/
├── webcapture.py               ← CLI program (installed as command)
├── setup.py                    ← Package setup for pip install
├── requirements.txt            ← Dependencies (requests)
└── install.sh                  ← Installation helper script
```

---

## Data Flow

### Starting a Capture Job

```
User Input (Web or CLI)
         │
         ▼
   POST /api/capture/start
   (domain, max_pages, modes, devices)
         │
         ▼
    Backend API
    └─ Create CaptureJob object
    └─ Start background thread
    └─ Return job_id
         │
         ▼
   User receives job_id
```

### During Capture

```
Background Job Thread
    │
    ├─ For each discovery_mode (sitemap/crawl):
    │  └─ For each device (desktop/mobile):
    │     │
    │     ├─ Discover URLs (sitemap or crawler)
    │     ├─ For each URL:
    │     │  ├─ Load page with Playwright
    │     │  ├─ Dismiss cookie banners
    │     │  ├─ Scroll for lazy-load images
    │     │  ├─ Take full-page screenshot
    │     │  ├─ Encode as base64
    │     │  └─ Store in job memory
    │     │
    │     └─ Call progress_callback()
    │
    └─ Mark job as "completed"
```

### Polling Progress

```
Web/CLI
  │
  └─ GET /api/capture/progress/{job_id}
     (every 1 second from web, with interactive status from CLI)
     │
     ▼
  Backend returns:
    {
        "status": "running|completed|failed|cancelled",
        "progress": 0-100,
        "message": "Capturing screenshot...",
        "screenshots": 45,
        "failed": 2,
        "failed_urls": [...],
        "screenshots_data": [{"filename": "...", "data": "base64..."}]
    }
     │
     ▼
  Display to user
```

---

## Request/Response Flow

### Example: Web Interface Workflow

1. **User submits form**
   ```javascript
   fetch('/api/capture/start', {
       method: 'POST',
       body: JSON.stringify({
           domain: 'example.com',
           max_pages: 200,
           discovery_modes: ['sitemap'],
           devices: ['desktop']
       })
   })
   ```

2. **Backend creates job**
   ```python
   @app.route('/api/capture/start', methods=['POST'])
   def start_capture():
       job_id = uuid.uuid4()
       job = CaptureJob(...)
       thread = Thread(target=_run_capture_job, args=(job_id,))
       thread.start()
       return {'job_id': job_id}
   ```

3. **Browser polls progress** (every 1 second)
   ```javascript
   fetch(`/api/capture/progress/${job_id}`)
   ```

4. **Backend returns live updates**
   ```python
   @app.route('/api/capture/progress/<job_id>')
   def get_progress(job_id):
       return job.to_dict()
   ```

5. **User downloads results**
   ```
   GET /api/capture/download/{job_id}
   → Returns ZIP with all screenshots
   ```

---

## Docker Architecture

### Container Structure

```
Docker Container (website-capture-backend)
├── OS: Python 3.12 on Debian Slim
├── Installed: Playwright + Chromium browser
├── Working Dir: /app
├── Mounted Volumes:
│   └─ ./frontend → /app/frontend (read-only)
├── Exposed Ports:
│   └─ 5000 (Flask API)
└── Process:
    └─ python api.py
```

### Volume Mounting

The `frontend/` folder is mounted as a **read-only volume** so:
- You can edit HTML/CSS/JS without rebuilding
- Changes are immediately visible
- Backend always serves latest version

```yaml
# docker-compose.yml
volumes:
- ./frontend:/app/frontend:ro
```

---

## Job Lifecycle

```
┌─────────────┐
│   PENDING   │  Job created, waiting to start
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   RUNNING   │  Actively capturing screenshots
└──────┬──────┘
       │
       ├─ On success
       │
       ▼
┌─────────────┐
│ COMPLETED   │  Success, screenshots ready
└─────────────┘
     
       OR ──────────────────────
       │
       ├─ On user cancel
       │
       ▼
┌─────────────┐
│  CANCELLED  │  User stopped the job
└─────────────┘

       OR ──────────────────────
       │
       ├─ On error
       │
       ▼
┌─────────────┐
│   FAILED    │  Error occurred
└─────────────┘
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend (Web)** | HTML5 + CSS3 + JavaScript | Visual interface |
| **Frontend (CLI)** | Python 3.8+ | Command-line interface |
| **API Server** | Flask 3.0+ | REST API & static serving |
| **Screenshot Engine** | Playwright 1.40+ | Browser automation |
| **Container** | Docker | Isolated environment |
| **Discovery** | BeautifulSoup 4.12 | HTML parsing |
| **HTTP** | requests 2.31+ | API communication |

---

## Concurrency & Threading

### Single-threaded API
The Flask API runs in the main thread and handles incoming requests.

### Multi-threaded Jobs
Each capture job runs in a **separate background thread** to avoid blocking the API:

```python
# api.py
thread = threading.Thread(
    target=_run_capture_job,
    args=(job_id,),
    daemon=True  # Dies if main thread exits
)
thread.start()
```

### Thread Safety
Job data is protected with a lock to prevent race conditions:

```python
jobs_lock = threading.Lock()

with jobs_lock:
    jobs[job_id] = job  # Safe access to shared dictionary
```

---

## Error Handling Strategy

### Graceful Degradation
- If a page fails to load: skip it, continue with next
- If screenshot fails: count as failure, continue
- If cookie dismiss fails: non-fatal, continue anyway

### User Feedback
- Real-time progress updates
- Failed URLs listed at the end
- Detailed error messages in logs

### Cancellation Support
- User can cancel anytime via API
- Background thread checks `job.cancelled` flag regularly
- Cleanup happens gracefully

---

## Future Enhancements

Possible architectural improvements:

- **Database Backend**: Replace in-memory job storage
- **Job Persistence**: Resume interrupted captures
- **Queue System**: Use Celery/RabbitMQ for job queuing
- **Load Balancing**: Distribute jobs across multiple workers
- **Results Storage**: S3 or cloud storage integration
- **Authentication**: User accounts and API keys
- **Webhooks**: Notify user when job completes
- **Caching**: Cache screenshots and avoid re-capturing

---

## Security Considerations

- **Input Validation**: All user inputs validated
- **XSS Protection**: HTML escaping in web UI
- **Rate Limiting**: Can be added to API
- **CORS**: Enabled for local access
- **Robots.txt**: Respected during crawling
- **User Agent**: Identifies tool appropriately

---

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Sitemap parse | 1-5s | Depends on sitemap size |
| Per-page load | 3-5s | With loading + scrolling |
| Per-page screenshot | 1-2s | Full-page render + encode |
| Total (50 pages) | 5-10m | Desktop sitemap mode |
| Total (50 pages) | 10-20m | Desktop + mobile both |

---

See also: [BACKEND.md](BACKEND.md), [CLI.md](CLI.md), [WEB_INTERFACE.md](WEB_INTERFACE.md)
