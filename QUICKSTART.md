#  Quick Start Guide

Get website-capture up and running in 5 minutes with one of two approaches.

---

## Choose Your Interface

### **Option A: Web Interface** (Easiest for first-time users)
Visual, browser-based capture with progress tracking and screenshot gallery.

### **Option B: CLI Tool** (Best for automation & scripting)
Command-line interface for automation, CI/CD, and batch processing.

**Both use the same backend** — choose based on your workflow preference.

---

## Installation

### Prerequisites
- **Docker & Docker Compose** (recommended)
- **Python 3.8+** (for CLI usage)

### Step 1: Start the backend
```bash
cd website-capture
docker-compose up -d
```

This command:
- Builds the Docker container (first run)
- Starts the backend API server
- Makes it accessible at `http://localhost:5000`

The backend will be ready in ~1-2 minutes (first build takes longer).

### Step 2: Choose your interface

---

## Option A: Web Interface 

### Usage

1. **Open in browser**:
   ```
   http://localhost:5000
   ```

2. **Fill in the form**:
   - Domain: `example.com` (or `https://example.com`)
   - Discovery: Choose ` Sitemap`, ` Crawl`, or both
   - Device: Choose ` Desktop`, ` Mobile`, or both
   - Max Pages: Set limit (1-1000)

3. **Click " Start Capture"**

4. **Monitor progress**:
   - Real-time progress bar
   - Screenshot count updates
   - Failure tracking

5. **Download results**:
   - View screenshots in gallery
   - Download individual images
   - Download all as ZIP

### Example
- Domain: `example.com`
- Discovery: Sitemap (faster)
- Device: Desktop
- Max Pages: 50
- Result: 50 desktop screenshots in ~5-10 minutes

---

## Option B: CLI Tool 

### Installation

```bash
cd cli
./install.sh
```

This installs the `webcapture` command globally on your system.

### Basic Usage

```bash
# Simplest form
webcapture capture example.com

# With options
webcapture capture example.com \
  --mode sitemap \
  --device desktop \
  --max 50 \
  --output ./my-screenshots

# Check job status
webcapture status <job_id>

# Cancel a running job
webcapture cancel <job_id>
```

### Examples

**Capture with sitemap (default, fast)**
```bash
webcapture capture wikipedia.org
```

**Capture with crawler (thorough, slower)**
```bash
webcapture capture wikipedia.org --mode crawl
```

**Capture both desktop and mobile**
```bash
webcapture capture wikipedia.org --device both --max 20
```

**Capture with custom output directory**
```bash
webcapture capture example.com --output ~/captures/example
```

**Use custom backend URL**
```bash
WEBCAPTURE_API=http://192.168.1.10:5000 webcapture capture example.com
```

### Full Options Reference

```bash
webcapture capture <domain> [options]

Options:
  --mode {sitemap,crawl,both}   URL discovery method (default: sitemap)
  --device {desktop,mobile,both} Viewport type (default: desktop)
  --max N                        Max pages to capture (default: 200)
  --output DIR                   Save screenshots to DIR (default: ./screenshots)
  --help                         Show this help message
```

### Status & Management

```bash
# Get progress of a running job
webcapture status 3f2a1b9d-4c5e-...

# Cancel a job
webcapture cancel 3f2a1b9d-4c5e-...

# View help
webcapture --help
webcapture capture --help
```

---

## Comparison

| Feature | Web UI | CLI |
|---------|--------|-----|
| **Ease of use** |  Easiest |  |
| **Visual progress** |  Live |  Progress bar |
| **Automation** |  Manual |  Scriptable |
| **Batch processing** | Manual (one at a time) |  Loop/batch |
| **CI/CD integration** |  No |  Yes |
| **Technical skill** | Beginner | Intermediate |

---

## Troubleshooting

### Backend won't start
```bash
# Check if Docker is running
docker ps

# Rebuild container
docker-compose up -d --build

# View logs
docker-compose logs backend
```

### Web interface won't load
```bash
# Check backend health
curl http://localhost:5000/api/health

# Should return: {"status": "ok", ...}
```

### CLI can't connect
```bash
# Verify backend is running
curl http://localhost:5000/api/health

# Check API is listening on correct port
netstat -an | grep 5000

# Point to custom backend
WEBCAPTURE_API=http://localhost:5001 webcapture capture example.com
```

### Capture is very slow
- Use `--mode sitemap` instead of `crawl` (much faster)
- Reduce `--max` pages
- Some websites block automated access
- Try a different website to verify

### No screenshots captured
1. Check browser console (F12) for JavaScript errors
2. View backend logs: `docker-compose logs backend`
3. Try a simpler website first (e.g., `example.com`)
4. Verify the domain is accessible: `curl https://example.com`

---

## Common Workflows

### Web UI: Single website
1. Go to http://localhost:5000
2. Enter domain → Click Start → Download when done

### CLI: Batch processing
```bash
#!/bin/bash
for site in example.com google.com wikipedia.org; do
    echo "Capturing $site..."
    webcapture capture $site --output ./captures/$site
done
echo "Done!"
```

### CLI: Automated daily capture
```bash
# Add to crontab for daily 2 AM capture
0 2 * * * webcapture capture mysite.com --output ~/daily-captures/$(date +%Y-%m-%d)
```

### CLI: CI/CD integration
```yaml
# GitHub Actions example
- name: Capture website
  run: |
    webcapture capture ${{ github.event.inputs.domain }} \
      --mode both \
      --device both \
      --max 100
```

---

## Next Steps

- **[Full README](README.md)** — Complete feature list and configuration
- **[Web UI Guide](frontend/README.md)** — Frontend details
- **[CLI Reference](docs/CLI.md)** — Full CLI documentation
- **[Architecture](docs/ARCHITECTURE.md)** — How it works under the hood
- **[API Docs](docs/BACKEND.md)** — REST API reference

---

## System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 2 GB | 4+ GB |
| Disk | 500 MB | 2+ GB |
| CPU | 2 cores | 4+ cores |
| Network | 1 Mbps | 5+ Mbps |

---

## Performance Tips

 Use `sitemap` mode (5-10x faster than crawl)
 Capture `desktop` only unless you need mobile
 Set `--max` to what you actually need
 Run large captures overnight
 Increase delay if getting rate-limited (429 errors)

---

## Stopping the Backend

```bash
# Stop without removing container
docker-compose stop

# Stop and remove container
docker-compose down

# Stop and remove container + volumes
docker-compose down -v
```

---

## Local Development (without Docker)

```bash
# Install dependencies
pip install -r backend/requirements.txt
playwright install chromium

# Run Flask server
FLASK_ENV=development python app.py

# In another terminal, install + use CLI
cd cli && ./install.sh
webcapture capture example.com
```

---

**Questions?** See [README.md](README.md) or the [docs/](docs/) folder.

