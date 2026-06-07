# Web Interface Guide

The web interface provides a browser-based UI for capturing website screenshots with visual progress tracking and screenshot gallery.

---

## Quick Start

### 1. Start Backend
```bash
docker-compose up -d
```

### 2. Open Browser
```
http://localhost:5000
```

### 3. Capture a Website
1. Enter domain
2. Choose discovery method and device
3. Click " Start Capture"
4. Watch progress updates
5. Download results

---

## Using the Web Interface

### Form Fields

#### Domain Input
- **Field**: Text input at top of form
- **Accepts**: Domain or full URL
- **Examples**:
- `example.com`
- `https://example.com`
- `www.example.com`
- `example.com/subpath`
- **Required**: Yes
- **Validation**: Must be valid domain

#### Discovery Method (Checkboxes)
Choose how URLs are discovered:

**Sitemap** ()
- Fast (5-10x faster)
- Parses XML sitemap
- Good for: Known structure, single crawl
- Best for: First captures, testing

**Crawl** ()
- Thorough, finds all internal links
- Uses BFS web crawling
- Respects robots.txt
- Good for: Complete coverage
- Best for: Comprehensive captures

**Both** ( + )
- Uses both methods
- Captures union of both
- Finds most links (good coverage)
- Best for: Maximum completeness

#### Device Type (Checkboxes)
Choose viewport(s) to capture:

**Desktop** ()
- Resolution: 1920×1080
- Standard laptop/monitor size
- Most common
- Fastest

**Mobile** ()
- Resolution: 390×844
- Modern smartphone size
- Shows mobile responsiveness
- Slower (needs additional renders)

**Both** ( + )
- Captures both viewports
- Each page captured twice
- 2x capture time
- Shows responsive design

#### Max Pages Input
- **Field**: Number input (1-1000)
- **Default**: 200
- **Purpose**: Limit maximum pages to capture
- **Tips**:
- Small number (10-25) for testing
- Medium number (50-100) for typical sites
- Large number (500+) for comprehensive capture
- 1000 is the hard limit
- **Time impact**: Linear (50 pages ≈ 5-10 minutes)

### Submission

**" Start Capture" Button**
- Validates all inputs
- Creates capture job on backend
- Starts background capture thread
- Redirects to progress view

---

## Progress View

### Progress Display

Shows real-time updates while capture is running:

```
Capturing example.com...

████████░░░░░░░░░░░ 40% (40/100)

Capturing screenshot...

Screenshots: 40
Failed: 2
Elapsed: 2 minutes
```

### Information Shown
- **Progress bar**: Visual representation of completion
- **Percentage**: 0-100%
- **Counter**: Current/Total pages
- **Status message**: What's currently happening
- **Screenshot count**: Successful captures
- **Failed count**: Pages that failed
- **Elapsed time**: How long it's been running

### Auto-Update
- Updates every 1 second
- Continues until completion
- Can cancel anytime

### Cancel Button

**" Cancel Capture" Button**
- Stops the running job
- Saves screenshots captured so far
- Shows cancellation confirmation

---

## Results View

After capture completes, shows results screen with:

### Summary Statistics

```
 Capture Complete!

 Results
├─ Screenshots: 95
├─ Failed: 5
├─ Saved to: /screenshots
└─ Duration: 8 minutes
```

### Screenshot Gallery

#### Display
- Shows all captured screenshots
- One preview per page
- Scrollable grid layout
- Responsive (adjusts to screen size)

#### Each Screenshot Shows
- Thumbnail of captured page
- Filename (usually page title)
- Device type badge (Desktop/Mobile)
- Individual download button

#### Actions
- **View full size**: Click screenshot to expand
- **Download one**: Click download icon
- **Download all**: " Download All" button at top

### Failed URLs Section

Shows pages that failed to capture:

```
 Failed URLs (5)

├─ https://example.com/broken-page-1
├─ https://example.com/broken-page-2
├─ https://example.com/broken-page-3
├─ https://example.com/broken-page-4
└─ https://example.com/broken-page-5
```

#### Why Pages Fail
- Network timeout
- Server error (5xx)
- Page too complex
- Resource blocked
- Browser crash

---

## Download Options

### Download Individual Screenshot
```
[ Download] button next to each screenshot
```
- Downloads PNG file
- Named with page title (sanitized)
- Same name format as batch download

### Download All Screenshots

```
[ Download All Screenshots] button at top
```
- Creates ZIP archive
- Contains all screenshots
- Contains `manifest.json` with metadata
- Sequential download to local directory

#### ZIP Contents
```
screenshots-example-com.zip
├── screenshot-001.png
├── screenshot-002.png
├── screenshot-003.png
├── ...
├── screenshot-095.png
└── manifest.json
```

#### manifest.json
```json
{
  "domain": "example.com",
  "total": 95,
  "failed": 5,
  "captured_at": "2024-01-20T15:35:20",
  "settings": {
    "discovery_modes": ["sitemap"],
    "devices": ["desktop"],
    "max_pages": 100
  },
  "files": [
    {
      "filename": "screenshot-001.png",
      "url": "https://example.com/",
      "device": "desktop",
      "discovery": "sitemap"
    },
  ...
  ],
  "failed_urls": [...]
}
```

---

## Features

### Cookie Banner Handling
- Automatically detects common cookie dialogs
- Attempts to dismiss them
- Falls back to JavaScript disabling cookies
- Result: Cleaner screenshots without overlays

### Lazy-Load Image Support
- Scrolls page to trigger lazy-loaded images
- Waits for images to load
- Result: Complete page screenshots with all content

### Full-Page Capture
- Captures entire page (not just viewport)
- Vertical scroll height is unlimited
- Result: See whole page in one screenshot

### Mobile Responsiveness
- Multiple device sizes: desktop and mobile
- Shows how sites look on different devices
- Mobile size: 390×844 (modern smartphone)

### Real-Time Progress
- Updates every 1 second
- Shows which page is being captured
- Shows progress percentage and counter
- Shows error count in real-time

### Job History (Optional)
- Can bookmark progress URLs
- Share capture jobs with others
- Return to previous captures

---

## Technical Details

### Browser Compatibility
- Chrome/Chromium (required)
- Safari (supported)
- Firefox (supported)
- Edge (supported)
- Mobile browsers (supported, responsive design)

### Responsive Design
- Mobile-friendly layout
- Adapts to screen size
- Touch-friendly buttons
- Scrollable content

### Performance
- Single-page app (SPA)
- Only reloads when necessary
- Efficient polling (1 second interval)
- Lazy-load screenshot thumbnails

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` in form | Submit capture |
| `Esc` on results | Go back to form |
| `Space` on screenshot | Expand full-size |
| `Ctrl+S` | Download currently viewed screenshot |

---

## Troubleshooting

### Form Won't Submit

**"Invalid domain" error**
- Check domain format
- Remove extra spaces
- Use format: `example.com` or `https://example.com`

**"Connection error"**
```bash
# Check backend is running
curl http://localhost:5000/api/health

# Restart backend
docker-compose restart backend
```

### No Progress Updates

**Check network connection**
- Open browser console (F12)
- Check Network tab for API calls
- Verify calls are reaching backend

**Check backend logs**
```bash
docker-compose logs backend
```

### Screenshots Not Appearing

**Wait for capture to complete**
- Progress may be slow
- Lazy-load images take time
- Check progress percentage

**Check for failures**
- Scroll to "Failed URLs" section
- May indicate website issues

**Try with smaller max_pages**
- `max_pages: 10` for testing

### Download Not Starting

**Check browser downloads**
- May be blocked by browser
- Check browser settings
- Try incognito/private window

**Large downloads**
- ZIP may take time to create
- Show download progress
- Be patient

---

## Advanced Features

### Multiple Simultaneous Captures

- Start one capture via web UI
- While running, open new tab
- Start another capture
- Both run in parallel on same backend
- Track with different job IDs

### Check Status from CLI

While capture is running in web UI:
```bash
# Get job ID from URL (browser shows in progress bar)
# http://localhost:5000/progress/a1b2c3d4-...

webcapture status a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### Share Progress Link

During capture, the URL in address bar is:
```
http://localhost:5000/progress/{job_id}
```

Can be shared with others to view progress.

---

## Common Workflows

### Quick Test
1. Enter domain
2. Set Max Pages: 10
3. Select Sitemap + Desktop
4. Click Start
5. Waits ~2-5 minutes
6. Download results

### Complete Capture
1. Enter domain
2. Set Max Pages: 100-200
3. Select Both (sitemap + crawl) + Both (desktop + mobile)
4. Click Start
5. Wait 20-40 minutes
6. Download results

### Mobile-Only Capture
1. Enter domain
2. Keep Max Pages: 200
3. Select Sitemap or Crawl
4. **Uncheck Desktop**
5. **Check Mobile**
6. Click Start
7. Download when done

### Responsive Design Review
1. Enter domain
2. Set Max Pages: 25-50
3. Select Sitemap (fast)
4. **Check Both (desktop + mobile)**
5. Click Start
6. View both viewport versions in gallery

---

## Accessibility

- Form labels clearly marked
- Color contrast WCAG AA compliant
- Keyboard navigation supported
- Screen reader friendly
- Touch-friendly buttons and inputs

---

## Performance Characteristics

| Scenario | Time |
|----------|------|
| 10 pages, sitemap, desktop | 1-2 minutes |
| 50 pages, sitemap, desktop | 5-10 minutes |
| 100 pages, sitemap, desktop | 10-20 minutes |
| 50 pages, sitemap, both devices | 10-20 minutes |
| 50 pages, both modes, both devices | 20-30 minutes |

---

## Tips & Best Practices

 **Use Sitemap mode** for faster results (5-10x faster)
 **Start with Desktop only** to test, then add Mobile
 **Use moderate Max Pages** (50-100) for quick feedback
 **Check console (F12)** for JavaScript errors
 **Run large captures overnight** (1000+ pages)

 **Don't use Crawl on large sites** (will take hours)
 **Mobile screenshots are slower** (2x capture time)
 **Some sites block automated access** (try different site)

---

## Comparison with CLI Tool

| Feature | Web UI | CLI |
|---------|--------|-----|
| **Ease** |  |  |
| **Visual** |  Progress bar |  Text progress |
| **Automation** | Manual only |  Scriptable |
| **Batch** | One at a time |  Multiple in parallel |
| **Best for** | One-off, testing | Automation, CI/CD |

---

See also: [QUICKSTART.md](../QUICKSTART.md), [ARCHITECTURE.md](ARCHITECTURE.md), [CLI.md](CLI.md)
