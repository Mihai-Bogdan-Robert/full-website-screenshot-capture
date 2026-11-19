# Technical notes

How Full Website Captures works inside. For what it does and how to use it, see the [README](../README.md).

## Stack

| Part | Tool |
|---|---|
| Web server | Flask 3 + Flask-SocketIO in threading mode (with `simple-websocket`), served by gunicorn (1 worker, 100 threads) in Docker |
| Browser automation | Playwright, headless Chromium |
| Page discovery | `requests` + BeautifulSoup (crawl), `xml.etree` (sitemap) |
| Frontend | One HTML page, plain CSS (mobile-first, no framework) and ES modules, no build step; Socket.IO client and JSZip from a CDN |

The three CDN scripts (Socket.IO client, JSZip, FileSaver) are pinned to an exact version with a
Subresource Integrity hash, so the page needs internet access to load. Exact Python dependency versions are pinned in `requirements.txt`
on purpose; bump them deliberately and run the tests.

## Files

```
app.py                      Entry point: creates the app (gunicorn app:app, or python app.py)
requirements.txt            Pinned dependencies
Dockerfile                  Image: Python 3.11, Chromium, runs as a non-root user
docker-compose.yml          Run the app (port 5001 on this computer only, memory limit)
docker-compose.dev.yml      Override for development: source folders mounted, Flask dev server

capture/                    The capture engine. No web code in here.
  pipeline.py                 capture_site(): find the pages, then screenshot them
  sitemap.py                  Page discovery from sitemap.xml
  crawler.py                  Page discovery by following links (robots.txt aware)
  urls.py                     URL normalising and the rules for which links are skipped
  screenshots.py              Visit each URL and take the screenshot, file naming
  browser.py                  Chromium start-up, desktop/mobile profiles, request guard
  cookies.py                  Cookie banner dismissal
  security.py                 Address checks that stop it reaching internal networks (SSRF)

webapp/                     The web application
  __init__.py                 create_app(): Flask and Socket.IO set-up, security headers
  config.py                   Environment settings and limits
  api.py                      HTTP endpoints
  events.py                   Socket.IO events (subscribe to a job)
  jobs.py                     Job and the in-memory job store
  runner.py                   Runs a job: starts the worker process, turns its messages into updates
  worker.py                   What the worker process runs (calls capture_site, reports via a queue)
  delivery.py                 Sends job updates and screenshot chunks to the browsers
  extensions.py               The shared Socket.IO object
  templates/index.html        The page
  static/css/style.css        All styles (mobile-first; wider layouts from 520 px and 640 px)
  static/js/                  main.js wires the page; form, capture, status, screenshots, socket, api, state
```

## How a capture runs

```
Browser                        Flask (webapp/)                      Worker process (webapp/worker.py)
   │  POST /api/jobs               │                                         │
   │──────────────────────────────▶│ create Job, start a thread              │
   │◀──────── 201 {job} ───────────│                                         │
   │  socket: subscribe {job_id}   │ thread spawns a process ───────────────▶│ find URLs
   │──────────────────────────────▶│                                         │ open each page in Chromium
   │◀── job_update (progress) ─────│◀──────── progress messages (queue) ─────│ full-page screenshot
   │◀── screenshot_chunk (binary) ─│◀──────── PNG bytes (queue) ─────────────│
   │  build the ZIP in the browser │                                         │
```

1. The browser creates a job with `POST /api/jobs`.
2. `run_job` (`webapp/runner.py`) runs in a background thread. It starts a **separate process**
   (`multiprocessing`, `spawn` start method) that runs Playwright, so a crashing or hanging
   browser cannot block the web server. Progress and screenshots come back through a
   `multiprocessing.Queue`; cancelling sets a `multiprocessing.Event` that the worker checks.
3. Every screenshot is sent to the browser over Socket.IO as raw PNG bytes (no base64), split into
   500 KB `screenshot_chunk` messages that the browser reassembles into a Blob.
4. Nothing is written to disk on the server. The browser collects the images and JSZip builds the
   ZIP locally.
5. **Both** viewports is handled by the UI: it runs two jobs one after the other (desktop, then
   mobile) and shows them as one result.

A job has the fields `id, url, max_pages, mode, device, status, progress, message, result, error,
screenshot_count, created_at`. Status goes `pending → running → completed | failed | cancelled`.
A job that runs longer than `JOB_TIMEOUT` (30 minutes by default) is stopped and marked failed.

## HTTP API

| Method and path | Body | Purpose |
|---|---|---|
| `GET /` | | The UI |
| `POST /api/jobs` | `{"url", "max_pages" (default 200, limited to 1–`MAX_PAGES_LIMIT`), "mode": "sitemap"\|"crawl", "device": "desktop"\|"mobile"}` | Start a capture, returns the job (201). Invalid input or a non-public address gives 400 with `{"error": ...}` |
| `GET /api/jobs/<id>` | | Job status. The job id is 32 random hex characters and is the only thing protecting a job's results, so there is deliberately no endpoint that lists jobs |
| `POST /api/jobs/<id>/cancel` | | Cancel a running job |
| `POST /api/check-sitemap` | `{"url"}` | Does `<origin>/sitemap.xml` exist? (used by the form) |

Example:

```bash
curl -X POST http://localhost:5001/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com", "mode": "crawl", "device": "desktop", "max_pages": 5}'
```

Screenshots are only delivered over Socket.IO (there is no download endpoint), so a plain `curl`
client sees the status but not the images.

## Socket.IO events

| Direction | Event | Payload |
|---|---|---|
| client → server | `subscribe` / `unsubscribe` | `{job_id}` – join or leave the job's room |
| server → client | `job_update` | the job object (status, progress, message) |
| server → client | `screenshot_chunk` | `{job_id, filename, chunk, chunk_index, total_chunks, count}` (`chunk` = binary piece of the PNG; a small image is one chunk) |

## Finding the pages

**Sitemap mode** fetches `<origin>/sitemap.xml` (or the `.xml` address you typed) and takes every
`<loc>` value, de-duplicated. A sitemap index is followed one level deep (up to 20 child sitemaps;
a child that cannot be read is skipped); at most 5000 URLs are kept.

**Crawl mode** is a breadth-first crawl from the start URL:

- stays on the same domain (subdomains count as the same domain);
- honours `robots.txt` for the user agent `FullWebsiteCaptures/1.0`;
- normalises URLs (drops fragments, trailing slashes) and skips non-page files (images, PDFs,
  office documents, archives, audio and video) and common non-content paths such as `/wp-admin`,
  `/admin`, `/login`, `/cart`, `/checkout`, `/account`, `/api/` and `/feed/`;
- waits 0.5 s between requests;
- stops once `max_pages` URLs are found.

## Taking the screenshots

For each URL (`screenshot_urls` in `capture/screenshots.py`):

1. Open a page with the chosen device profile:
   - desktop: 1920×1080
   - mobile: 390×844, iPhone user agent, touch enabled, device scale factor 3.
2. `goto` with `wait_until="commit"` (20 s timeout, one retry with 10 s); pages that still fail
   are skipped and counted as failed.
3. Try to dismiss cookie banners: click common "accept" buttons (English and Romanian wording,
   plus well-known consent frameworks), then hide leftover banner containers and re-enable page
   scrolling.
4. Scroll the page in steps (up to 20) so lazy-loaded images load, then wait for images.
5. `page.screenshot(full_page=True)` as PNG.
6. File name: `<index>-<page title>.png`, with `-mobile` added for the mobile profile. Path
   separators in titles are replaced, duplicates get a numeric suffix.

## Security

The app opens whatever address a visitor types, so it protects itself and the network it runs in:

- **Only public addresses (SSRF protection, `capture/security.py`).** `localhost`, private networks,
  link-local and cloud-metadata addresses (`169.254.169.254`), IPv4-mapped IPv6 tricks, other
  schemes than `http(s)` and addresses with a username/password are refused. The check runs on the
  typed address, on **every redirect hop**, on every page found by the crawler or listed in a
  sitemap, and on **every request Chromium makes** while loading a page (so a page cannot redirect
  or embed something internal). A refused request is aborted and logged.
- **Capturing your own local sites.** Start the app with `ALLOW_PRIVATE_URLS=1` (Docker: uncomment
  the line in `docker-compose.yml`) to allow `localhost` and private networks. Only do that on a
  machine you alone can reach.
- **Strict input validation.** Bad JSON, missing or oversized URLs, unknown `mode`/`device` and
  non-numeric `max_pages` give a 400 instead of an error; `max_pages` is limited to 1–`MAX_PAGES_LIMIT` (500 by default).
- **Unguessable job ids**, and no endpoint that lists other visitors' jobs.
- **No HTML built from captured data in the UI**: error messages and file names are inserted as
  text, so a hostile page cannot inject script into the UI.
- **Browser hardening**: downloads and service workers are disabled in the capture context; headers
  `X-Content-Type-Options`, `X-Frame-Options` and `Referrer-Policy` are set.
- **Safer defaults**: `python app.py` listens on `127.0.0.1` with debug off, and the compose files
  publish the port on `127.0.0.1` only. A random `SECRET_KEY` is generated when none is set.

## Configuration

| Setting | Where | Default |
|---|---|---|
| `ALLOW_PRIVATE_URLS` | environment | off. `1` allows `localhost` and private networks |
| `ALLOWED_ORIGINS` | environment, comma-separated | `*`. Set to your domain(s) when the app is on the internet |
| `SECRET_KEY` | environment | random at every start |
| `HOST`, `PORT`, `FLASK_DEBUG` | environment, only for `python app.py` | `127.0.0.1`, `5001`, off |
| `JOB_TIMEOUT` | environment, seconds | 1800. A longer capture is stopped |
| `MAX_PAGES_LIMIT` | environment | 500. The form starts at 50 and the API uses 200 when `max_pages` is omitted, or the limit if it is lower |
| Crawl delay | `delay=` in `capture_site()` | 0.5 s |
| Finished jobs kept in memory | `JOB_RETENTION` in `webapp/config.py` | 2 hours |
| Container memory limit | `docker-compose.yml` | 2 GB |

The Docker image runs `gunicorn --worker-class gthread --workers 1 --threads 100 --no-control-socket app:app`. Use a single worker: jobs and
Socket.IO rooms live in the memory of one process.

## Known limitations

- **No rate limiting or login.** Nothing limits how many captures a visitor can start or how many
  run at once, and anyone who can reach the app can use it. The online version at
  captures.smart-web-tools.com adds limits around this app; they are not part of this repository.
  If you publish your own instance, lower `MAX_PAGES_LIMIT` and `JOB_TIMEOUT` and add limits in
  front of it (a reverse proxy, or Flask-Limiter).
- **DNS rebinding.** Host names are resolved for the check and again by the HTTP client or
  browser; a hostile DNS server could in theory answer differently the second time. Chromium's
  per-request check narrows this, but for a hostile environment also block internal ranges at the
  network level (firewall rules for the container).
- **Chromium runs without its own sandbox** (Playwright's default). The container runs as a
  non-root user; a seccomp profile that allows Chromium's sandbox would harden it further.
- **Jobs live in memory.** A restart loses them (finished jobs are dropped after 2 hours anyway).
- **CORS is open by default** (`ALLOWED_ORIGINS=*`); restrict it on a public instance.
- Pages behind a login cannot be captured. Large sites produce large ZIPs, built in the browser's
  memory.

## Development

Developed with AI assistance; reviewed and tested by the maintainer.
