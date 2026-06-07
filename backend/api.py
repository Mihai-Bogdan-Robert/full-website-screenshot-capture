"""Flask REST API server for website-capture backend v2.0.

Imports core logic from src/ (added to PYTHONPATH in Dockerfile).
Serves the web interface from WEB_INTERFACE_DIR (mounted volume).

Run locally:
    cd backend
    WEB_INTERFACE_DIR=../frontend PYTHONPATH=src python api.py
Run via Docker:
    docker-compose up
"""

import os
import sys
import uuid
import io
import base64
import logging
import threading
import zipfile
from datetime import datetime

# Version info
APP_VERSION = '2.0.0'

from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from werkzeug.exceptions import BadRequest

# --- Logging (must be set up before any logger.* calls) -------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# --- Import core logic (src/ is on PYTHONPATH in Docker; add it locally) --
_src_dir = os.path.join(os.path.dirname(__file__), 'src')
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

try:
    from main import main as logik_main
    logger.info("✅ Core logik modules loaded from src/")
except ImportError as exc:
    logger.error("❌ Could not import logik modules: %s", exc)
    logik_main = None

# --- Flask app setup -------------------------------------------------------
# Web interface static files are mounted at WEB_INTERFACE_DIR inside Docker
WEB_INTERFACE_DIR = os.environ.get(
    'WEB_INTERFACE_DIR',
    os.path.join(os.path.dirname(__file__), '..', 'frontend')
)

app = Flask(__name__)
CORS(app)
app.config['JSON_SORT_KEYS'] = False
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

# --- In-memory job store ---------------------------------------------------
jobs: dict = {}
jobs_lock = threading.Lock()


# ==========================================================================
# Job model
# ==========================================================================

class CaptureJob:
    def __init__(self, job_id, domain, max_pages, discovery_modes, devices):
        self.job_id = job_id
        self.domain = domain
        self.max_pages = max_pages
        self.discovery_modes = discovery_modes
        self.devices = devices
        self.status = 'pending'      # pending | running | completed | failed | cancelled
        self.progress = 0
        self.message = 'Initializing...'
        self.urls_found = 0
        self.screenshots = 0
        self.failed = 0
        self.failed_urls = []
        self.screenshots_data = []   # list of {filename, data (base64)}
        self.error = None
        self.created_at = datetime.utcnow()
        self.completed_at = None
        self.cancelled = False

    def to_dict(self, include_screenshots=True):
        d = {
            'job_id': self.job_id,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'urls_found': self.urls_found,
            'screenshots': self.screenshots,
            'failed': self.failed,
            'failed_urls': self.failed_urls,
            'error': self.error,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
        if include_screenshots:
            d['screenshots_data'] = self.screenshots_data
        return d


# ==========================================================================
# Web interface routes
# ==========================================================================

@app.route('/')
def index():
    return send_from_directory(WEB_INTERFACE_DIR, 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    # Only serve known static extensions to avoid leaking unintended files
    allowed = {'.html', '.css', '.js', '.ico', '.png', '.svg', '.woff', '.woff2'}
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed:
        return jsonify({'error': 'Not found'}), 404
    return send_from_directory(WEB_INTERFACE_DIR, filename)


# ==========================================================================
# API: health
# ==========================================================================

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'version': APP_VERSION,
        'logik_loaded': logik_main is not None,
        'web_interface_dir': WEB_INTERFACE_DIR,
    })


# ==========================================================================
# API: capture
# ==========================================================================

@app.route('/api/capture/start', methods=['POST'])
def start_capture():
    try:
        data = request.get_json(force=True)
        if not data:
            raise BadRequest('Request body must be JSON')

        domain = data.get('domain', '').strip()
        if not domain:
            raise BadRequest('domain is required')

        max_pages = data.get('max_pages', 200)
        if not isinstance(max_pages, int) or not (1 <= max_pages <= 1000):
            raise BadRequest('max_pages must be an integer between 1 and 1000')

        discovery_modes = data.get('discovery_modes', [])
        if not discovery_modes or not isinstance(discovery_modes, list):
            raise BadRequest('discovery_modes must be a non-empty list')
        invalid = set(discovery_modes) - {'sitemap', 'crawl'}
        if invalid:
            raise BadRequest(f'Invalid discovery modes: {invalid}')

        devices = data.get('devices', [])
        if not devices or not isinstance(devices, list):
            raise BadRequest('devices must be a non-empty list')
        invalid = set(devices) - {'desktop', 'mobile'}
        if invalid:
            raise BadRequest(f'Invalid devices: {invalid}')

        job_id = str(uuid.uuid4())
        job = CaptureJob(job_id, domain, max_pages, discovery_modes, devices)

        with jobs_lock:
            jobs[job_id] = job

        thread = threading.Thread(target=_run_capture_job, args=(job_id,), daemon=True)
        thread.start()

        logger.info("Started job %s for %s", job_id, domain)
        return jsonify({'job_id': job_id, 'status': 'started'}), 202

    except BadRequest as exc:
        return jsonify({'error': str(exc.description)}), 400
    except Exception as exc:
        logger.exception("Error starting capture")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/capture/progress/<job_id>', methods=['GET'])
def get_progress(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job.to_dict()), 200


@app.route('/api/capture/cancel/<job_id>', methods=['POST'])
def cancel_capture(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    if job.status in ('completed', 'failed', 'cancelled'):
        return jsonify({'error': f'Cannot cancel a {job.status} job'}), 400

    job.cancelled = True
    job.status = 'cancelled'
    job.message = 'Cancelled by user'
    logger.info("Cancelled job %s", job_id)
    return jsonify({'job_id': job_id, 'status': 'cancelled'})


@app.route('/api/capture/download/<job_id>', methods=['GET'])
def download_screenshots(job_id):
    """Download all screenshots for a completed job as a ZIP archive."""
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    if job.status != 'completed':
        return jsonify({'error': f'Job is {job.status}, not completed'}), 400
    if not job.screenshots_data:
        return jsonify({'error': 'No screenshots available'}), 404

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for shot in job.screenshots_data:
            zf.writestr(shot['filename'], base64.b64decode(shot['data']))
    buf.seek(0)

    return send_file(
        buf,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'screenshots-{job_id[:8]}.zip',
    )


# ==========================================================================
# Background job runner
# ==========================================================================

def _run_capture_job(job_id: str):
    with jobs_lock:
        job = jobs[job_id]

    try:
        if logik_main is None:
            raise RuntimeError("Core logik modules are not loaded. Check server logs.")

        job.status = 'running'
        job.message = 'Starting...'

        def progress_cb(message, percent):
            if job.cancelled:
                return
            job.message = message
            job.progress = percent

        def screenshot_cb(filename, b64_data):
            if job.cancelled:
                return
            job.screenshots_data.append({'filename': filename, 'data': b64_data})
            job.screenshots = len(job.screenshots_data)  # live count

        def cancel_check():
            return job.cancelled

        all_urls_found = 0
        all_failed = 0
        all_failed_urls: list = []
        first_combination = True

        for mode in job.discovery_modes:
            for device in job.devices:
                if job.cancelled:
                    break

                try:
                    result = logik_main(
                        url=job.domain,
                        folder=None,
                        max_pages=job.max_pages,
                        delay=1.0,
                        headless=True,
                        user_agent=None,
                        mode=mode,
                        device=device,
                        progress_callback=progress_cb,
                        screenshot_callback=screenshot_cb,
                        cancel_check=cancel_check,
                    )
                    if result:
                        all_failed += result.get('failed', 0)
                        all_failed_urls.extend(result.get('failed_urls', []))
                        if first_combination:
                            all_urls_found = result.get('urls_found', 0)
                            first_combination = False

                except Exception as exc:
                    logger.error("Capture error (mode=%s device=%s): %s", mode, device, exc)
                    all_failed += job.max_pages

        if job.cancelled:
            job.status = 'cancelled'
            job.message = 'Cancelled by user'
        else:
            job.status = 'completed'
            job.urls_found = all_urls_found
            job.failed = all_failed
            job.failed_urls = all_failed_urls
            job.message = f'Done — {job.screenshots} screenshots captured'
            job.completed_at = datetime.utcnow()

        logger.info("Job %s finished: %d screenshots, %d failed", job_id, job.screenshots, all_failed)

    except Exception as exc:
        logger.exception("Unexpected error in job %s", job_id)
        job.status = 'failed'
        job.error = str(exc)
        job.message = f'Failed: {str(exc)[:100]}'
        job.completed_at = datetime.utcnow()


# ==========================================================================
# Error handlers
# ==========================================================================

@app.errorhandler(404)
def not_found(_):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(_):
    return jsonify({'error': 'Internal server error'}), 500


# ==========================================================================
# Entry point
# ==========================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    logger.info("Starting backend on port %d (debug=%s)", port, debug)
    logger.info("Serving web interface from: %s", WEB_INTERFACE_DIR)
    app.run(host='0.0.0.0', port=port, debug=debug)
