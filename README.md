# Full Website Captures

![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0-green.svg)
![Playwright](https://img.shields.io/badge/playwright-1.45-orange.svg)
![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg)

A powerful web application that automatically captures full-page screenshots of entire websites. Simply enter a URL and let the app discover and screenshot all pages—perfect for archiving, design reviews, competitive analysis, documentation, or portfolio showcases.

---

## ✨ Features

### Core Functionality
- 📸 **Full-Page Screenshots** — Captures complete page content including below-the-fold content
- 🖥️ **Multi-Viewport Support** — Desktop (1920×1080), Mobile (390×844), or capture **both simultaneously**
- 🗺️ **Sitemap Mode** — Fast page discovery using sitemap.xml (recommended)
- 🕷️ **Crawl Mode** — Discover pages by following internal links (no sitemap required)
- 🍪 **Smart Cookie Handling** — Automatically dismisses cookie banners in multiple languages
- 🖼️ **Lazy-Load Support** — Waits for images and animations to fully load before capturing

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [How to Use](#-how-to-use)
- [Deployment](#-deployment)
- [How It Works (Technical)](#-how-it-works-technical)
- [Configuration](#%EF%B8%8F-configuration)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/Mihai-Bogdan-Robert/Full-Website-Captures.git
cd Full-Website-Captures

# Start with Docker Compose
docker-compose up -d

# View logs
docker logs -f full-website-captures
```

Open **http://localhost:5001** in your browser.

### Option 2: Local Python Installation

**Prerequisites:** Python 3.11+, pip

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
python -m playwright install chromium
python -m playwright install-deps chromium

# Start the server
python app.py
```

Open **http://localhost:5001** in your browser.

---

## 📖 How to Use

### Basic Workflow

1. **Enter Website URL**
   - Type or paste any website URL (e.g., `example.com`)
   - Protocol (`https://`) is optional—it's added automatically

2. **Configure Capture Settings**
   - **Mode:** Choose between Sitemap or Crawl
     - 🗺️ **Sitemap** (Recommended): Fast, uses sitemap.xml
     - 🕷️ **Crawl**: Discovers pages by following links
   - **Viewport:** Select capture resolution
     - 🖥️ **Desktop**: 1920×1080 resolution
     - 📱 **Mobile**: 390×844 (iPhone 13 Pro size)
     - 🔄 **Both**: Captures desktop first, then mobile (all in one ZIP)
   - **Max Pages:** Limit number of pages to capture (1-500)

3. **Check Sitemap Availability** (Optional)
   - Click "Check Sitemap" to see if the site has a sitemap
   - If available, use Sitemap mode for faster captures

4. **Start Capture**
   - Click "Start Capture" button
   - The interface will show:
     - Pages crawled/discovered
     - Screenshots captured vs total
     - Real-time progress percentage
     - Live screenshot previews in grid

5. **Monitor Progress**
   - Watch the progress bar and status messages
   - View screenshots appearing in real-time below
   - Cancel anytime with "Cancel Capture" button

6. **Download Results**
   - When complete, click "Download ZIP"
   - File is auto-named: `example.com-screenshots.zip`
   - For "Both" mode, ZIP contains both desktop and mobile screenshots

### Tips for Best Results

- ✅ Use **Sitemap mode** when available—it's much faster
- ✅ Start with a **low page limit** (10-20) to test first
- ✅ Use **Mobile viewport** to capture responsive designs
- ✅ Check **sitemap availability** before starting large captures
- ⚠️ Large sites (100+ pages) can take 10-30 minutes
- ⚠️ Some sites may block automated access—respect robots.txt

---

## 🐳 Deployment

### Production Deployment (Docker Compose)

**For deploying on a local server or VPS:**

1. **Clone and Configure**
   ```bash
   git clone https://github.com/Mihai-Bogdan-Robert/Full-Website-Captures.git
   cd Full-Website-Captures
   ```

2. **Set Environment Variables** (Optional)
   ```bash
   # Create .env file
   echo "SECRET_KEY=$(openssl rand -hex 32)" > .env
   ```

3. **Deploy**
   ```bash
   # Production deployment
   docker-compose up -d

   # Or for development with hot-reload
   docker-compose -f docker-compose.dev.yml up -d
   ```

4. **Verify Health**
   ```bash
   # Check container status
   docker ps

   # View logs
   docker logs full-website-captures

   # Check health
   curl http://localhost:5001/
   ```

### Reverse Proxy Setup (Nginx)

If deploying on a server with a domain:

```nginx
server {
    listen 80;
    server_name screenshots.yourdomain.com;

    location / {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
```

### Container Management

```bash
# Stop container
docker-compose down

# Restart container
docker-compose restart

# View logs (live)
docker logs -f full-website-captures

# Rebuild after code changes
docker-compose up -d --build

# Check resource usage
docker stats full-website-captures
```

---

## 🔧 How It Works (Technical)

### Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   Web Browser                        │
│  (React-like UI with Socket.IO client)              │
└─────────────────┬───────────────────────────────────┘
                  │ WebSocket + HTTP
                  │
┌─────────────────▼───────────────────────────────────┐
│              Flask + SocketIO Server                 │
│  • Job Management                                    │
│  • WebSocket Real-time Updates                      │
│  • Process Orchestration                            │
└─────────────────┬───────────────────────────────────┘
                  │ Spawns Process
                  │
┌─────────────────▼───────────────────────────────────┐
│           Playwright Worker Process                  │
│  • Isolated asyncio event loop                      │
│  • Chromium browser automation                      │
│  • Screenshot capture & streaming                   │
└──────────────────────────────────────────────────────┘
```

### Component Breakdown

#### 1. **Frontend (templates/index.html)**
- Single-page application with vanilla JavaScript
- Socket.IO client for real-time bidirectional communication
- JSZip library for client-side ZIP generation
- Screenshot storage in memory during capture
- Responsive grid gallery with lightbox modal

#### 2. **Flask Application (app.py)**
- **Job Management**: Creates and tracks capture jobs with unique IDs
- **API Endpoints**:
  - `POST /api/jobs` — Create new capture job
  - `GET /api/jobs/<id>` — Get job status
  - `POST /api/jobs/<id>/cancel` — Cancel running job
  - `POST /api/check-sitemap` — Check sitemap availability
- **WebSocket Events**:
  - `connect/disconnect` — Client connection management
  - `subscribe/unsubscribe` — Join job-specific rooms
  - `job_update` — Status and progress updates
  - `screenshot_data` — Stream screenshot to browser
  - `screenshot_chunk` — Large screenshot chunking (500KB chunks)

#### 3. **Worker Process (Playwright Isolation)**
- **Why Process Isolation?** Playwright uses asyncio internally. Running it in the same process as eventlet (Flask-SocketIO's async mode) causes event loop conflicts
- **Solution**: Each job spawns a separate Python process with its own event loop
- **Communication**: Uses `multiprocessing.Queue` for sending results back to main process
- **Cancellation**: `multiprocessing.Event` signals worker to stop gracefully

#### 4. **Screenshot Engine (main.py)**

**Page Discovery:**
- **Sitemap Mode**: Parses sitemap.xml to extract all `<loc>` URLs
- **Crawl Mode**: BFS traversal of internal links, respects robots.txt

**Screenshot Process:**
1. **Browser Launch**: Headless Chromium with device-specific viewport
2. **Navigation**: Navigate to URL with timeout (`wait_until='commit'`)
3. **Cookie Dismissal**: Tries 50+ selectors in multiple languages
4. **Lazy Loading**: Scrolls page to trigger lazy-loaded images
5. **Image Wait**: Waits for all `<img>` elements to report complete
6. **Capture**: Full-page screenshot with Playwright
7. **Streaming**: Base64-encodes and sends to browser via queue

**Optimizations:**
- 1.5-3 second waits for animations to complete
- JavaScript scroll simulation to trigger lazy-load
- Cookie banner auto-dismissal (supports 50+ patterns)
- Network-aware navigation (doesn't wait for full page idle)

#### 5. **Memory Management**
- Screenshots never saved to disk on server
- Base64 data streamed directly to browser
- Browser stores in-memory until ZIP download
- Large images (>500KB) sent in chunks to prevent WebSocket overflow
- Worker process terminates after job, releasing all memory

#### 6. **Error Handling**
- Job timeout: 30 minutes maximum per job
- Browser cleanup with 5-second timeout to prevent hanging
- Process termination if worker becomes unresponsive
- Cancellation support at any stage

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Flask secret key for sessions |
| `PYTHONUNBUFFERED` | `1` | Disable Python output buffering (for logs) |

### Docker Resource Limits

Defined in `docker-compose.yml`:
- **Memory Limit**: 2GB maximum
- **Memory Reservation**: 512MB guaranteed
- **CPU**: No limit (uses available cores)

Adjust in `docker-compose.yml` if needed:
```yaml
deploy:
  resources:
    limits:
      memory: 4G  # Increase for larger sites
    reservations:
      memory: 1G
```

### Application Limits

Hard-coded in `app.py`:
- **Max Job Duration**: 30 minutes (1800 seconds)
- **Max Pages**: 500 per capture
- **WebSocket Buffer**: 10MB
- **Screenshot Chunk Size**: 500KB

---

## 🐛 Troubleshooting

### Screenshots Stuck at "Processing..."
- **Cause**: Worker process hung during cleanup
- **Fixed**: Latest version includes 5-second timeout on Playwright cleanup
- **Solution**: Refresh page and try again

### "Job already finished" Error
- **Cause**: Attempting to cancel completed job
- **Solution**: Start a new capture

### Container Won't Start
```bash
# Check logs for errors
docker logs full-website-captures

# Common fixes:
docker-compose down
docker-compose up -d --build
```

### High Memory Usage
- **Normal**: Chromium uses 200-500MB per job
- **If excessive**: Restart container
```bash
docker-compose restart
```

### Captures Timing Out
- Increase timeout in `app.py`:
```python
MAX_JOB_DURATION = 3600  # 1 hour
```

---

## 📁 Project Structure

```
Full-Website-Captures/
├── app.py                  # Flask app + SocketIO server
├── main.py                 # Playwright screenshot engine
├── templates/
│   └── index.html          # Single-page web interface
├── static/
│   ├── style.css           # Custom styles + gradients
│   └── favicon.svg         # Camera icon
├── Dockerfile              # Multi-stage production build
├── docker-compose.yml      # Production deployment
├── docker-compose.dev.yml  # Development with hot-reload
├── requirements.txt        # Python dependencies
├── .dockerignore           # Docker build exclusions
├── .gitignore              # Git exclusions
└── README.md               # This file
```

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | Flask 3.0 | Web framework |
| **Real-time** | Flask-SocketIO + eventlet | WebSocket communication |
| **Browser** | Playwright | Headless browser automation |
| **Parsing** | BeautifulSoup4 | HTML parsing for crawl mode |
| **Sitemap** | xml.etree.ElementTree | XML parsing |
| **Frontend** | Vanilla JS + Tailwind CSS | UI and styling |
| **Download** | JSZip + FileSaver.js | Client-side ZIP generation |
| **Container** | Docker + Gunicorn | Production deployment |

---

## 📄 License

This project is licensed under **CC BY-NC-ND 4.0** (Creative Commons Attribution-NonCommercial-NoDerivatives).

### You MAY:
- ✅ Use this software for personal, non-commercial purposes
- ✅ Share the software with proper attribution to the author
- ✅ Deploy on your own servers for personal use

### You MAY NOT:
- ❌ Sell this software or use it commercially
- ❌ Use it in any commercial product or service
- ❌ Offer it as a paid service (SaaS)
- ❌ Distribute modified versions
- ❌ Remove or alter attribution

See [LICENSE](LICENSE) for full legal details.

---

## 👤 Author

**Mihai-Bogdan-Robert**

For **commercial licensing inquiries**, please contact the author.

---

## 🙏 Acknowledgments

- Built with [Playwright](https://playwright.dev/) for reliable browser automation
- UI inspired by modern dark-mode design trends
- Cookie banner selectors support 10+ languages

---

**⭐ If you find this useful, please star the repository!**
