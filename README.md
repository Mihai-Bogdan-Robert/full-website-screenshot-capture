# website-capture v2.0 — Full-Page Website Screenshot Tool

A complete system for discovering and capturing full-page screenshots of websites using Playwright, Docker, and modern web technologies.

## Features

-  **Multiple Discovery Methods**: Sitemap (fast) or web crawler (comprehensive)
-  **Multi-Device Support**: Capture desktop and mobile viewports simultaneously
-  **Automatic Cookie Handling**: Dismisses cookie banners automatically
-  **Real-time Progress**: Live progress updates during capture
-  **Screenshot Gallery**: Interactive preview and download
-  **Two Usage Modes**:
- **Web Interface** — Browser-based UI for visual workflows
- **CLI Tool** — Command-line interface for automation
-  **Docker-Ready**: Backend runs in a containerized environment
-  **REST API**: Extensible backend API for integrations

---

## Quick Start (3 minutes)

### Prerequisites
- Docker & Docker Compose
- Python 3.8+ (for CLI usage)

### Step 1: Start the backend
```bash
cd website-capture
docker-compose up -d
```

The backend will be ready at `http://localhost:5000`

### Step 2: Choose your interface

#### **Option A: Web Interface** (Browser)
1. Open `http://localhost:5000` in your browser
2. Enter a domain (e.g., `example.com`)
3. Select discovery method and devices
4. Click "Start Capture"
5. Watch progress and download screenshots

#### **Option B: CLI Tool** (Terminal)
```bash
# Install the CLI tool (one-time)
cd cli && ./install.sh

# Capture a website
webcapture capture example.com

# Capture with options
webcapture capture example.com --mode crawl --device mobile --max 50 --output ./my-screenshots

# Check job status
webcapture status <job_id>

# Cancel a job
webcapture cancel <job_id>
```

---

## Documentation

### Getting Started
- [QUICKSTART.md](QUICKSTART.md) — Detailed setup guide for both methods
- [WEB_INTERFACE_README.md](frontend/README.md) — Web UI documentation
- [CLI Documentation](docs/CLI.md) — Command-line tool guide

### Architecture & Development
- [Architecture Overview](docs/ARCHITECTURE.md) — How the system works
- [Backend Documentation](docs/BACKEND.md) — Docker, API, and core logic
- [Web Interface Guide](docs/WEB_INTERFACE.md) — Frontend implementation details

---

## Use Cases

### Web Interface (Best for)
 One-off captures
 Visual workflow preference
 Real-time monitoring
 Non-technical users
 Testing individual websites

### CLI Tool (Best for)
 Automation & scripting
 Batch processing
 CI/CD pipelines
 Scheduled captures
 Server environments
 Integration with other tools

---

## Project Structure

```
website-capture/
├── docker-compose.yml        ← Start the backend
├── app.py                    ← Local dev entry point (no Docker)
│
├── backend/
│   ├── Dockerfile           ← Container definition
│   ├── requirements.txt      ← Backend dependencies
│   ├── api.py               ← Flask REST API server
│   └── src/                 ← Core screenshot logic
│       ├── main.py          ├ Main orchestration
│       ├── crawler.py       ├ Web crawler
│       ├── screenshot.py    ├ Screenshot capture
│       ├── sitemap.py       ├ Sitemap parsing
│       ├── cookie.py        ├ Cookie handling
│       ├── utils.py         ├ URL utilities
│       └── config.py        └ Configuration
│
├── frontend/                 ← Browser UI (Option A)
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── cli/                      ← CLI tool (Option B)
│   ├── webcapture.py
│   ├── setup.py
│   └── install.sh
│
└── docs/                     ← Documentation
    ├── ARCHITECTURE.md
    ├── BACKEND.md
    ├── CLI.md
    └── WEB_INTERFACE.md
```

---

## Common Commands

### Docker
```bash
# Start backend (runs in background)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop backend
docker-compose down

# Rebuild container
docker-compose up -d --build
```

### Web Interface
- Open `http://localhost:5000`
- No additional setup needed

### CLI Tool
```bash
# Install (one-time)
cd cli && ./install.sh

# Use
webcapture capture example.com
webcapture capture example.com --help

# Point to custom backend
WEBCAPTURE_API=http://192.168.1.10:5000 webcapture capture example.com
```

### Local Development (no Docker)
```bash
# Install dependencies
pip install -r backend/requirements.txt
playwright install chromium

# Run with Flask debug mode
FLASK_ENV=development python app.py
```

---

## API Endpoints

The backend provides REST endpoints:

### Start Capture
```
POST /api/capture/start
Content-Type: application/json

{
    "domain": "https://example.com",
    "max_pages": 200,
    "discovery_modes": ["sitemap"],
    "devices": ["desktop"]
}
```

### Get Progress
```
GET /api/capture/progress/{job_id}
```

### Cancel Job
```
POST /api/capture/cancel/{job_id}
```

### Download Screenshots
```
GET /api/capture/download/{job_id}
```

See [Backend Documentation](docs/BACKEND.md) for full API details.

---

## ⚙️ Configuration

### Capture Options

| Option | Values | Default | Notes |
|--------|--------|---------|-------|
| **mode** | `sitemap`, `crawl`, `both` | `sitemap` | URL discovery method |
| **device** | `desktop`, `mobile`, `both` | `desktop` | Viewport to capture |
| **max_pages** | 1-1000 | 200 | Maximum pages to capture |
| **delay** | seconds | 1.0 | Delay between requests |

### Environment Variables

```bash
# Backend
PORT=5000                    # API server port
FLASK_ENV=development        # Debug mode
WEB_INTERFACE_DIR=./frontend

# CLI
WEBCAPTURE_API=http://localhost:5000    # Backend URL
```

---

## Troubleshooting

### Backend won't start
```bash
# Rebuild the container
docker-compose up -d --build

# Check logs
docker-compose logs backend
```

### CLI can't connect to backend
```bash
# Verify backend is running
curl http://localhost:5000/api/health

# Point to correct backend
WEBCAPTURE_API=http://localhost:5000 webcapture capture example.com
```

### Slow captures
- Use `sitemap` mode instead of `crawl`
- Reduce `max_pages`
- Increase `delay` if getting 429 errors

### Missing screenshots
- Check browser console (F12) for errors
- Verify backend logs: `docker-compose logs backend`
- Try with a different website first

---

## Learn More

- **[QUICKSTART.md](QUICKSTART.md)** — Step-by-step setup
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — System design
- **[docs/BACKEND.md](docs/BACKEND.md)** — API & Docker details
- **[docs/CLI.md](docs/CLI.md)** — CLI reference
- **[docs/WEB_INTERFACE.md](docs/WEB_INTERFACE.md)** — UI guide

---

## Examples

### Capture a site via web UI
1. Go to http://localhost:5000
2. Enter: `theatlantic.com`
3. Select: Sitemap + Desktop
4. Click "Start"
5. Download screenshots when complete

### Capture a site via CLI
```bash
webcapture capture theatlantic.com --mode sitemap --device desktop
```

### Batch capture multiple sites
```bash
for site in example.com google.com wikipedia.org; do
    webcapture capture $site --output ./captures/$site
done
```

### Integration example (Python)
```python
import requests

# Start a capture job via the API
response = requests.post('http://localhost:5000/api/capture/start', json={
    'domain': 'example.com',
    'max_pages': 50,
    'discovery_modes': ['sitemap'],
    'devices': ['desktop']
})
job_id = response.json()['job_id']

# Poll for completion
import time
while True:
    status = requests.get(f'http://localhost:5000/api/capture/progress/{job_id}').json()
    if status['status'] == 'completed':
        print(f"Captured {status['screenshots']} screenshots!")
        break
    time.sleep(1)
```

---

## 🤝 Contributing

Found a bug or have a feature request? Feel free to open an issue or submit a pull request.

---

## License

See LICENSE file for details.

---

## FAQ

**Q: Do I need Docker?**
A: No, you can run locally with `python app.py`, but Docker is recommended for production.

**Q: Can I use both web UI and CLI at the same time?**
A: Yes! They both use the same backend. Start a capture in the web UI and check its status from CLI.

**Q: What's the maximum number of pages I can capture?**
A: 1000 pages max per job, but capture time depends on website speed.

**Q: Can I download screenshots as a ZIP?**
A: Yes, both interfaces offer ZIP downloads of all captured screenshots.

**Q: Is it safe to capture someone else's website?**
A: Ensure you have permission. The tool respects robots.txt and includes appropriate delays.

---

**Questions?** Check the [documentation folder](docs/) or [QUICKSTART.md](QUICKSTART.md).
