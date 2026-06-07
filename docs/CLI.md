# CLI Tool Documentation

The CLI tool (`webcapture` command) enables command-line control of the website screenshot capture system.

---

## Installation

### One-Time Setup

```bash
cd cli
./install.sh
```

This installs the `webcapture` command globally on your system using pip.

### Verification

```bash
# Check installation
which webcapture

# Test it works
webcapture --help
```

### Manual Installation (Alternative)

```bash
cd cli
pip install -e .
```

---

## Basic Usage

### Simplest Form

```bash
webcapture capture example.com
```

This captures the website using default options:
- Discovery: Sitemap (fast)
- Device: Desktop
- Max pages: 200
- Output: `./screenshots/`

### With Options

```bash
webcapture capture example.com \
  --mode crawl \
  --device both \
  --max 50 \
  --output ./my-captures
```

---

## Commands

### 1. Capture

Start a new screenshot capture job.

```bash
webcapture capture <domain> [options]
```

**Arguments**:
- `domain` (required): Website domain or URL
- Examples: `example.com`, `https://example.com`, `google.com`

**Options**:
```
--mode {sitemap,crawl,both}
    URL discovery method (default: sitemap)
    - sitemap: Fast, uses XML sitemap if available
    - crawl: Thorough, uses web crawler
    - both: Uses both methods, captures union

--device {desktop,mobile,both}
    Device viewport (default: desktop)
    - desktop: 1920x1080 resolution
    - mobile: 390x844 resolution
    - both: Captures both viewports

--max N
    Maximum pages to capture (default: 200)
    - Range: 1-1000
    - Useful for testing or limiting time

--output DIR
    Save screenshots to DIR (default: ./screenshots)
    - Created if it doesn't exist
    - Previous screenshots preserved

--help
    Show help message
```

**Examples**:

```bash
# Quick test (10 pages)
webcapture capture example.com --max 10

# Thorough crawl
webcapture capture example.com --mode crawl --max 100

# Mobile only
webcapture capture example.com --device mobile

# Both desktop and mobile
webcapture capture example.com --device both --max 50

# Custom output directory
webcapture capture example.com --output ~/website-captures/example

# Full custom setup
webcapture capture wikipedia.org \
  --mode both \
  --device both \
  --max 100 \
  --output ./wiki-capture
```

**Output**:
```
Starting capture of example.com...
Job ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890

Progress: ████████░░░░░░░░░░░ 40% (40/100) - Capturing screenshot...

 Capture complete!
  Screenshots: 95
  Failed: 5
  Saved to: /Users/username/website-captures/example
```

---

### 2. Status

Check the status of a running or completed job.

```bash
webcapture status <job_id>
```

**Arguments**:
- `job_id` (required): Job ID from capture command output

**Example**:
```bash
webcapture status a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Output**:
```
Job ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Status: running
Progress: 60% (60/100)
Message: Capturing screenshot...

Screenshots: 60
Failed: 0

Started: 2024-01-20 15:30:45
Elapsed: 5 minutes 23 seconds
```

---

### 3. Cancel

Stop a running capture job.

```bash
webcapture cancel <job_id>
```

**Arguments**:
- `job_id` (required): Job ID from capture command output

**Example**:
```bash
webcapture cancel a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Output**:
```
Cancelled job a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

---

### 4. Help

```bash
# General help
webcapture --help

# Specific command help
webcapture capture --help
webcapture status --help
```

---

## Environment Variables

### WEBCAPTURE_API

Points to the backend API server.

```bash
# Default (local backend)
WEBCAPTURE_API=http://localhost:5000

# Custom backend
WEBCAPTURE_API=http://192.168.1.10:5000 webcapture capture example.com

# Remote backend
WEBCAPTURE_API=https://api.example.com webcapture capture example.com
```

**Usage**:
```bash
# One-time
WEBCAPTURE_API=http://other-server:5000 webcapture capture example.com

# Persistent (add to ~/.bashrc or ~/.zshrc)
export WEBCAPTURE_API=http://other-server:5000
```

---

## Common Workflows

### Single Website Capture

```bash
webcapture capture example.com
# Downloads and shows results when complete
```

### Batch Capture (Multiple Sites)

```bash
#!/bin/bash
sites=(
    example.com
    google.com
    wikipedia.org
    github.com
)

for site in "${sites[@]}"; do
    echo "Capturing $site..."
    webcapture capture $site --output ./captures/$site --max 25
    echo "Done: $site"
done

echo "All captures complete!"
```

### Capture with Monitoring

```bash
# Start capture
JOB_ID=$(webcapture capture example.com | grep "Job ID:" | awk '{print $NF}')

# Monitor progress
watch -n 1 "webcapture status $JOB_ID"

# (Press Ctrl+C to exit watch, then download)
```

### Parallel Captures

```bash
#!/bin/bash
# Start multiple captures simultaneously

JOB1=$(webcapture capture example.com --max 50 | grep "Job ID:" | awk '{print $NF}')
JOB2=$(webcapture capture google.com --max 50 | grep "Job ID:" | awk '{print $NF}')

# Wait for both to complete
echo "Waiting for jobs to complete..."
sleep 2
while true; do
    STATUS1=$(webcapture status $JOB1 | grep "Status:")
    STATUS2=$(webcapture status $JOB2 | grep "Status:")
  
    if [[ $STATUS1 == *"completed"* ]] && [[ $STATUS2 == *"completed"* ]]; then
        echo "All jobs complete!"
        break
    fi
    sleep 5
done
```

### Scheduled Daily Capture

```bash
# Add to crontab
0 2 * * * /usr/local/bin/webcapture capture mysite.com --output ~/daily-captures/$(date +\%Y-\%m-\%d)
```

### CI/CD Integration (GitHub Actions)

```yaml
name: Screenshot Capture

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  capture:
    runs-on: ubuntu-latest
  
    services:
      backend:
        image: website-capture:latest
        ports:
          - 5000:5000
  
    steps:
      - name: Wait for backend
        run: sleep 10
    
      - name: Capture website
        run: |
          pip install requests
          webcapture capture example.com \
            --mode both \
            --device both \
            --max 100
    
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: screenshots
          path: screenshots/
```

---

## Output Format

### Progress Display

```
Starting capture of example.com...
Job ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890

Progress: ████████░░░░░░░░░░░ 40% (40/100) - Capturing screenshot...
```

### Completion

```
 Capture complete!
  Screenshots: 95
  Failed: 5
  Saved to: /home/user/screenshots

Failed URLs:
- https://example.com/error-page-1
- https://example.com/error-page-2
- https://example.com/error-page-3
- https://example.com/error-page-4
- https://example.com/error-page-5
```

### Files Created

In the output directory (`./screenshots/` by default):
- `screenshot-001.png` - First captured page
- `screenshot-002.png` - Second page
- ... (numbered sequentially)
- `manifest.json` - Metadata about capture

---

## Exit Codes

```
0   - Success
1   - General error (bad arguments, connection failed, etc.)
2   - Job failed (capture errors)
130 - User cancelled (Ctrl+C)
```

**Usage in scripts**:
```bash
webcapture capture example.com
if [ $? -eq 0 ]; then
    echo "Capture successful"
else
    echo "Capture failed"
    exit 1
fi
```

---

## Error Messages

### Common Errors

**"Connection refused"**
```
ERROR: Could not connect to backend at http://localhost:5000
Make sure backend is running: docker-compose up -d
```

**"Invalid domain"**
```
ERROR: Invalid domain: "not a real site"
```

**"Job not found"**
```
ERROR: Job a1b2c3d4-e5f6 not found
Check Job ID and try again
```

**"Capture failed"**
```
ERROR: Capture job failed
Check backend logs: docker-compose logs backend
```

---

## Troubleshooting

### Backend Connection Issues

```bash
# Check backend is running
curl http://localhost:5000/api/health

# Try custom endpoint
WEBCAPTURE_API=http://0.0.0.0:5000 webcapture status <job_id>

# Check firewall
nc -zv localhost 5000
```

### Installation Issues

```bash
# Verify installation
pip list | grep webcapture

# Reinstall
pip uninstall webcapture -y
cd cli && pip install -e .

# Check path
which webcapture
```

### Slow Captures

```bash
# Use sitemap (faster)
webcapture capture example.com --mode sitemap

# Reduce page count
webcapture capture example.com --max 25

# Check network
ping example.com
```

### Missing Screenshots

```bash
# Check backend logs
docker-compose logs backend

# Increase timeout (edit webcapture.py)
# Reduce max_pages
webcapture capture example.com --max 5

# Try different website
webcapture capture example.com
```

---

## Advanced Usage

### Python Integration

The CLI tool communicates with the REST API, so you can also use the API directly from Python:

```python
import requests
import json

# Start a job
response = requests.post('http://localhost:5000/api/capture/start', json={
    'domain': 'example.com',
    'max_pages': 50,
    'discovery_modes': ['sitemap'],
    'devices': ['desktop']
})
job_id = response.json()['job_id']

# Check progress
import time
while True:
    progress = requests.get(f'http://localhost:5000/api/capture/progress/{job_id}').json()
    print(f"{progress['progress']}% - {progress['message']}")
  
    if progress['status'] == 'completed':
        break
  
    time.sleep(1)

# Download results
zip_data = requests.get(f'http://localhost:5000/api/capture/download/{job_id}')
with open('screenshots.zip', 'wb') as f:
    f.write(zip_data.content)
```

### Custom Output Processing

```bash
#!/bin/bash
# Capture and process

OUTPUT_DIR="./my-captures"
webcapture capture example.com --output "$OUTPUT_DIR"

# Convert to WebP (requires imagemagick)
for png in "$OUTPUT_DIR"/*.png; do
    convert "$png" "${png%.png}.webp"
done

# Create HTML index
cat > "$OUTPUT_DIR/index.html" <<EOF
<html>
<head><title>Screenshots</title></head>
<body>
EOF

for img in "$OUTPUT_DIR"/*.webp; do
    echo "<img src='$(basename $img)' width='50%'>" >> "$OUTPUT_DIR/index.html"
done

echo "</body></html>" >> "$OUTPUT_DIR/index.html"

echo "Done! Open $OUTPUT_DIR/index.html in browser"
```

---

## Performance Tips

 **Use sitemap mode** — 5-10x faster than crawl
 **Capture desktop only** — 2x faster than desktop + mobile
 **Reduce max_pages** — Linear time savings
 **Run overnight** — Large captures (1000+ pages) take hours
 **Use fast network** — Internet speed is a bottleneck

 **Avoid crawl mode** on large sites (10000+ pages)
 **Don't interrupt often** — Restarting costs time
 **High max_pages** — 1000+ pages can take hours

---

## Uninstallation

```bash
pip uninstall webcapture -y
```

---

See also: [QUICKSTART.md](../QUICKSTART.md), [ARCHITECTURE.md](ARCHITECTURE.md), [BACKEND.md](BACKEND.md)
