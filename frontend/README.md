# Web Interface - Browser-Based Screenshot Capture

Browser-based UI for capturing website screenshots. Part of the website-capture system that offers **two ways to capture**: Web Interface (here) or [CLI Tool](../docs/CLI.md).

---

## Quick Start

```bash
# 1. Start backend
docker-compose up -d

# 2. Open browser
http://localhost:5000

# 3. Enter domain and click "Start Capture"
```

---

## What This Does

This directory contains the **frontend interface** for the website-capture system. It provides:

- 🌐 Browser-based capture control
- 📊 Real-time progress tracking
- 📸 Screenshot gallery preview
- ⬇️ Download individual or all screenshots

**Alternative**: Use the [CLI tool](../docs/CLI.md) for automation/scripting instead.



---

## Files

| File | Purpose | Size |
|------|---------|------|
| `index.html` | Form + progress + gallery | ~8 KB |
| `style.css` | Responsive styling | ~12 KB |
| `script.js` | API communication + UX | ~10 KB |

Total: ~30 KB (uncompressed)

---

## Features

### 🎯 Capture Configuration
- **Domain input**: Supports `example.com` or `https://example.com`
- **Discovery method**: Choose Sitemap (fast) or Crawl (thorough) or both
- **Device type**: Choose Desktop (1920×1080) or Mobile (390×844) or both
- **Max pages**: Limit 1-1000 pages (default: 200)
- **Form validation**: Helpful error messages

### 📊 Real-Time Progress
- Live progress bar (0-100%)
- Current status message
- Page counter (40/100)
- Failure count
- Elapsed time

### 📸 Screenshot Gallery
- Responsive grid layout
- Thumbnail previews
- Full-size image viewer
- Individual download buttons
- Mobile-friendly cards

### ⬇️ Download Options
- **Individual**: Download single screenshot as PNG
- **Batch**: Download all as ZIP archive
- **Metadata**: Includes manifest.json with details

### 🎨 Design
- Modern, clean aesthetic
- Gradient header
- Dark/light mode compatible
- Fully responsive (mobile, tablet, desktop)
- Smooth animations

---

## How It Works

### 1. User Submits Form
```javascript
// User clicks "Start Capture"
// JavaScript validates form
// POST to /api/capture/start
```

### 2. Backend Creates Job
```
Backend starts background thread
Returns job_id to browser
Starts discovering and capturing URLs
```

### 3. Browser Polls Progress
```javascript
// Poll GET /api/capture/progress/{job_id}
// Every 1 second
// Update progress bar and stats
```

### 4. Results Display
```
When status = "completed"
Show screenshot gallery
Show failed URLs (if any)
Enable download buttons
```

---

## API Communication

### Endpoints Used

**Start Capture**
```javascript
POST /api/capture/start
{
    domain: "example.com",
    max_pages: 200,
    discovery_modes: ["sitemap"],
    devices: ["desktop"]
}
```

**Poll Progress**
```javascript
GET /api/capture/progress/{job_id}
```

Response includes:
- `status`: "running" | "completed" | "cancelled" | "failed"
- `progress`: 0-100
- `message`: Current operation
- `screenshots`: Count of successful captures
- `failed`: Count of failures
- `screenshots_data`: Base64 images
- `failed_urls`: List of URLs that failed

**Cancel Job**
```javascript
POST /api/capture/cancel/{job_id}
```

See [BACKEND.md](../docs/BACKEND.md) for full API details.

---

## JavaScript Architecture

### State
```javascript
let currentJobId = null;        // Active job ID
let pollInterval = null;         // Progress poll timer
let captureJob = {              // Current job data
    status: "pending",
    progress: 0,
    screenshots: [],
    failed_urls: []
};
```

### Key Functions

**Form & Submission**
- `handleFormSubmit()` - Validate and start capture
- `resetForm()` - Clear form fields
- `validateForm()` - Check all inputs

**Progress Tracking**
- `pollJobProgress()` - Get updates from backend (every 1s)
- `updateProgressBar()` - Render progress visually
- `updateStats()` - Show screenshot counts

**Results Display**
- `displayResults()` - Show final gallery and stats
- `renderScreenshots()` - Create thumbnail grid
- `displayFailedUrls()` - Show failed URLs list

**Downloads**
- `downloadScreenshot(filename)` - Save single PNG
- `downloadAll()` - Download ZIP of all
- `downloadAsZip()` - Create ZIP archive

**Utilities**
- `escapeHtml(text)` - XSS prevention
- `formatTime(ms)` - Format elapsed time
- `createFilename(title)` - Sanitize filenames

---

## Styling

### CSS Variables (Customizable Theme)

```css
:root {
    /* Colors */
    --primary: #6366f1;
    --secondary: #8b5cf6;
    --success: #10b981;
    --error: #ef4444;
    --warning: #f59e0b;
  
    /* Backgrounds */
    --bg-primary: #f9fafb;
    --bg-secondary: #ffffff;
    --bg-tertiary: #f3f4f6;
  
    /* Text */
    --text-primary: #111827;
    --text-secondary: #6b7280;
    --text-tertiary: #9ca3af;
  
    /* Borders */
    --border: #e5e7eb;
    --border-light: #f3f4f6;
  
    /* Shadows */
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
    --shadow-lg: 0 10px 15px rgba(0,0,0,0.15);
}
```

**To change colors**, edit these variables in `style.css`.

### Responsive Breakpoints

```css
/* Mobile first approach */
Mobile:   < 480px  (small phones)
Tablet:   480px - 768px
Desktop:  768px - 1200px
Large:    > 1200px (wide screens)
```

Grid adjusts from 1 column (mobile) to 4+ columns (desktop).

### Key Components

| Component | Class | Purpose |
|-----------|-------|---------|
| Header | `.header` | Gradient banner |
| Form | `.form-container` | Input fields & buttons |
| Progress | `.progress-bar` | Visual progress indicator |
| Gallery | `.screenshots-grid` | Screenshot thumbnails |
| Stats | `.stats-container` | Summary numbers |

---

## Browser Support

| Browser | Version | Support |
|---------|---------|---------|
| Chrome | 90+ | ✅ Full |
| Firefox | 88+ | ✅ Full |
| Safari | 14+ | ✅ Full |
| Edge | 90+ | ✅ Full |
| Mobile Chrome | Latest | ✅ Full |
| Mobile Safari | Latest | ✅ Full |

**Required features**:
- Fetch API
- Promise support
- ES6+ JavaScript
- FormData API

---

## Customization

### Change Theme Colors

Edit `style.css` at the top:
```css
:root {
    --primary: #your-color;  /* Change main color */
    --success: #your-color;  /* Change success color */
    /* ... change others ... */
}
```

### Change Screenshot Grid Size

Edit `style.css`:
```css
.screenshots-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 20px;
}
```

### Change Progress Poll Interval

Edit `script.js`:
```javascript
const POLL_INTERVAL = 1000;  // Change from 1000ms to desired interval
```

Lower = more frequent updates but more server requests
Higher = fewer requests but less responsive

### Change Maximum Pages Default

Edit `index.html`:
```html
<input type="number" id="maxPages" value="200" min="1" max="1000">
<!-- Change value="200" to desired default -->
```

---

## Performance

### Optimizations

1. **Polling interval**: 1 second (balanced trade-off)
2. **Base64 images**: Stored in memory, sent via API
3. **Sequential downloads**: 200ms delay between files
4. **Lazy rendering**: Screenshots rendered as they arrive

### For Large Captures (100+ screenshots)

Browser may slow down due to:
- Many DOM elements in gallery
- Large base64 image strings
- Memory usage

Solutions:
- Enable pagination (show 20 at a time)
- Lazy-load images (load on scroll)
- Implement virtual scrolling

### Typical Performance

| Scenario | Time | Notes |
|----------|------|-------|
| 10 pages | 1-2m | Quick test |
| 50 pages | 5-10m | Typical capture |
| 100 pages | 10-20m | Larger crawl |
| 500+ pages | 1-2h | Comprehensive |

---

## Security

### XSS Prevention
- All user input is escaped with `escapeHtml()`
- No innerHTML use with user data
- textContent used instead

### CORS
- Handled by Flask backend (`flask-cors`)
- Allows requests from same origin

### Input Validation
- Domain format checked
- Max pages limited to 1-1000
- Discovery mode validated
- Device type validated

### Server-Side Protection
- Rate limiting (can be added)
- Input sanitization
- Error message filtering

---

## Accessibility (a11y)

- Semantic HTML structure
- Form labels linked to inputs
- ARIA labels for buttons
- Color contrast: WCAG AA compliant
- Keyboard navigation: Full support
- Focus indicators: Clear and visible
- Error messages: Descriptive text

---

## Troubleshooting

### Form won't submit
```
✓ Check domain format (example.com or https://example.com)
✓ Ensure at least one discovery mode selected
✓ Ensure at least one device selected
✓ Check browser console (F12) for errors
```

### No progress updates
```
✓ Verify backend is running: curl http://localhost:5000/api/health
✓ Check browser Network tab (F12) for API requests
✓ Check backend logs: docker-compose logs backend
```

### Screenshots not showing
```
✓ Wait for capture to complete (check progress %)
✓ Try with fewer pages (--max 10) to test
✓ Check for failed URLs
✓ Review browser console for errors
```

### Download not working
```
✓ Try incognito/private window
✓ Check browser download settings
✓ Verify file is created (check System Downloads)
✓ Try single screenshot first
```

---

## Comparison: Web UI vs CLI

| Feature | Web UI | CLI |
|---------|--------|-----|
| **Ease** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Visual progress** | Real-time bar | Text progress |
| **Gallery** | Interactive | File-based |
| **Automation** | Manual | ✅ Scriptable |
| **Batch processing** | One at a time | ✅ Multiple |
| **Best for** | Testing, one-off | Automation, CI/CD |

**Use Web UI for:**
- Visual workflows
- One-off captures
- Testing websites
- No technical skill needed

**Use CLI Tool for:**
- Automation
- Batch processing
- CI/CD pipelines
- Scheduled captures

---

## File Structure

```
frontend/
├── index.html      ← Form, progress, gallery
├── style.css       ← All styling
├── script.js       ← All JavaScript logic
└── README.md       ← This file
```

---

## Related Documentation

- **[QUICKSTART.md](../QUICKSTART.md)** — Get started in 5 minutes
- **[README.md](../README.md)** — Main project documentation
- **[ARCHITECTURE.md](../docs/ARCHITECTURE.md)** — How system works
- **[BACKEND.md](../docs/BACKEND.md)** — API reference
- **[CLI.md](../docs/CLI.md)** — Command-line tool

---

## License

See [LICENSE](../LICENSE) file.

---

**Need help?** Check [QUICKSTART.md](../QUICKSTART.md) or the [docs/](../docs/) folder.
