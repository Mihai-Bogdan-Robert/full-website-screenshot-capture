#!/usr/bin/env python3
"""
Flask web application for Full Website Captures.
Provides a web interface to capture screenshots of websites from their sitemaps.
"""

import os
import uuid
import shutil
import zipfile
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, url_for
from flask_socketio import SocketIO, emit
import main
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
socketio = SocketIO(app, cors_allowed_origins="*")

# Directory to store screenshots
SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screenshots')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Store active jobs
jobs = {}


class Job:
    def __init__(self, job_id, url, max_pages=200, mode='sitemap', device='desktop'):
        self.id = job_id
        self.url = url
        self.max_pages = max_pages
        self.mode = mode  # 'sitemap' or 'crawl'
        self.device = device  # 'desktop' or 'mobile'
        self.status = 'pending'
        self.progress = 0
        self.message = 'Waiting to start...'
        self.result = None
        self.error = None
        self.output_dir = os.path.join(SCREENSHOTS_DIR, job_id)
        self.created_at = datetime.now()
        
    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'max_pages': self.max_pages,
            'mode': self.mode,
            'device': self.device,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at.isoformat()
        }


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs."""
    return jsonify([job.to_dict() for job in jobs.values()])


@app.route('/api/jobs', methods=['POST'])
def create_job():
    """Create a new screenshot job."""
    data = request.get_json()
    
    if not data or not data.get('url'):
        return jsonify({'error': 'URL is required'}), 400
    
    url = data['url'].strip()
    max_pages = int(data.get('max_pages', 200))
    mode = data.get('mode', 'sitemap')  # 'sitemap' or 'crawl'
    device = data.get('device', 'desktop')  # 'desktop' or 'mobile'
    
    # Validate mode
    if mode not in ('sitemap', 'crawl'):
        mode = 'sitemap'
    
    # Validate device
    if device not in ('desktop', 'mobile'):
        device = 'desktop'
    
    job_id = str(uuid.uuid4())[:8]
    job = Job(job_id, url, max_pages, mode, device)
    jobs[job_id] = job
    
    # Start the job in a background thread
    thread = threading.Thread(target=run_job, args=(job,), daemon=True)
    thread.start()
    
    return jsonify(job.to_dict()), 201


@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get job status."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job.to_dict())


@app.route('/api/jobs/<job_id>/download', methods=['GET'])
def download_job(job_id):
    """Download screenshots as a ZIP file."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if job.status != 'completed':
        return jsonify({'error': 'Job not completed yet'}), 400
    
    if not os.path.exists(job.output_dir):
        return jsonify({'error': 'Screenshots not found'}), 404
    
    # Create ZIP file
    zip_path = os.path.join(SCREENSHOTS_DIR, f'{job_id}.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(job.output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, job.output_dir)
                zipf.write(file_path, arcname)
    
    return send_file(
        zip_path,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'screenshots-{job_id}.zip'
    )


@app.route('/api/jobs/<job_id>/screenshots', methods=['GET'])
def list_screenshots(job_id):
    """List screenshots for a job."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if not os.path.exists(job.output_dir):
        return jsonify([])
    
    screenshots = []
    for filename in sorted(os.listdir(job.output_dir)):
        if filename.endswith('.png'):
            screenshots.append({
                'filename': filename,
                'url': url_for('serve_screenshot', job_id=job_id, filename=filename)
            })
    
    return jsonify(screenshots)


@app.route('/screenshots/<job_id>/<filename>')
def serve_screenshot(job_id, filename):
    """Serve a screenshot file."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    file_path = os.path.join(job.output_dir, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(file_path, mimetype='image/png')


def run_job(job):
    """Run the screenshot job in background."""
    def update_status(status, message, progress=None):
        job.status = status
        job.message = message
        if progress is not None:
            job.progress = progress
        socketio.emit('job_update', job.to_dict())
        logger.info(f"[Job {job.id}] {message}")
    
    try:
        device_label = 'mobile' if job.device == 'mobile' else 'desktop'
        logger.info(f"[Job {job.id}] Starting capture for {job.url}")
        logger.info(f"[Job {job.id}] Mode: {job.mode}, Device: {device_label}, Max pages: {job.max_pages}")
        
        if job.mode == 'crawl':
            update_status('running', f'Crawling website to discover pages ({device_label})...', 15)
        else:
            update_status('running', f'Parsing sitemap ({device_label})...', 15)
        
        # Run the main screenshot function with the selected mode and device
        result = main.main(
            folder=job.output_dir,
            url=job.url,
            max_pages=job.max_pages,
            headless=True,
            mode=job.mode,
            device=job.device,
            progress_callback=lambda msg, pct: update_status('running', msg, pct)
        )
        
        job.result = {
            'screenshots': result.get('screenshots', 0),
            'failed': result.get('failed', 0),
            'urls_found': result.get('urls_found', 0),
            'output_dir': job.output_dir
        }
        
        logger.info(f"[Job {job.id}] Completed: {result.get('screenshots', 0)} screenshots, {result.get('failed', 0)} failed")
        update_status('completed', f"Done! {result.get('screenshots', 0)} screenshots captured.", 100)
        
    except Exception as e:
        logger.error(f"[Job {job.id}] Error: {str(e)}")
        job.error = str(e)
        update_status('failed', f'Error: {str(e)}', 0)


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    emit('connected', {'message': 'Connected to server'})


@socketio.on('subscribe')
def handle_subscribe(data):
    """Subscribe to job updates."""
    job_id = data.get('job_id')
    if job_id and job_id in jobs:
        emit('job_update', jobs[job_id].to_dict())


if __name__ == '__main__':
    print("Starting Full Website Captures Web App...")
    print("Open http://localhost:5001 in your browser")
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
