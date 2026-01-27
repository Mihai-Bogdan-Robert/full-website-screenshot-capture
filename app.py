#!/usr/bin/env python3
"""
Flask web application for Full Website Captures.
Provides a web interface to capture screenshots of websites from their sitemaps.
Screenshots are streamed to the browser and stored client-side.
"""

# Eventlet monkey-patching must happen FIRST before any other imports
import eventlet
eventlet.monkey_patch(thread=False)  # Don't patch threading - needed for Playwright

import os
import uuid
import base64
import logging
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import main
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configure SocketIO with optimized settings
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    max_http_buffer_size=10 * 1024 * 1024,  # 10MB buffer
    ping_timeout=120,
    ping_interval=25,
    async_mode='eventlet',
    logger=False,
    engineio_logger=False
)

# Thread pool for running Playwright in separate threads
executor = ThreadPoolExecutor(max_workers=2)

# Store active jobs and client sessions
jobs = {}
active_sessions = {}  # {job_id: [session_ids]}
cancelled_jobs = set()  # Set of job IDs that have been cancelled


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
        self.screenshot_count = 0
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
            'screenshot_count': self.screenshot_count,
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
    
    # Start the job in a native thread (NOT eventlet greenlet)
    # This allows Playwright to work properly with its own threading
    executor.submit(run_job, job)
    
    return jsonify(job.to_dict()), 201


@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get job status."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job.to_dict())


@app.route('/api/jobs/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancel a running job."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if job.status in ('completed', 'failed', 'cancelled'):
        return jsonify({'error': 'Job already finished'}), 400
    
    # Mark job as cancelled
    cancelled_jobs.add(job_id)
    job.status = 'cancelled'
    job.message = 'Cancelled by user'
    
    # Emit update to clients
    try:
        socketio.emit('job_update', job.to_dict(), room=job_id)
    except Exception as e:
        logger.error(f"[Job {job_id}] Failed to emit cancel status: {e}")
    
    logger.info(f"[Job {job_id}] Cancelled by user")
    return jsonify({'message': 'Job cancelled'})


# No longer needed - screenshots are stored client-side and ZIP is generated in browser


def run_job(job):
    """Run the screenshot job in background. Screenshots are streamed to browser via Socket.IO."""
    
    # Thread-safe wrapper for socketio.emit
    def emit_safe(event, data, room=None):
        """Emit Socket.IO event from any thread safely."""
        try:
            if room:
                socketio.emit(event, data, room=room)
            else:
                socketio.emit(event, data)
        except Exception as e:
            logger.error(f"[Job {job.id}] Failed to emit {event}: {e}")
    
    def update_status(status, message, progress=None):
        job.status = status
        job.message = message
        if progress is not None:
            job.progress = progress
        try:
            emit_safe('job_update', job.to_dict(), room=job.id)
            logger.info(f"[Job {job.id}] {message}")
        except Exception as e:
            logger.error(f"[Job {job.id}] Failed to emit status: {e}")
    
    def send_screenshot(filename, image_data_base64):
        """Send screenshot data to browser via Socket.IO with chunking for large images."""
        job.screenshot_count += 1
        
        try:
            # Check if we have active sessions
            if job.id not in active_sessions or not active_sessions[job.id]:
                logger.warning(f"[Job {job.id}] No active sessions, skipping screenshot: {filename}")
                return
            
            # Calculate image size
            image_size = len(image_data_base64)
            chunk_size = 500 * 1024  # 500KB chunks
            
            if image_size > chunk_size:
                # Send large images in chunks
                num_chunks = (image_size + chunk_size - 1) // chunk_size
                logger.info(f"[Job {job.id}] Sending {filename} in {num_chunks} chunks ({image_size / 1024:.1f} KB)")
                
                for i in range(num_chunks):
                    start = i * chunk_size
                    end = min(start + chunk_size, image_size)
                    chunk = image_data_base64[start:end]
                    
                    emit_safe('screenshot_chunk', {
                        'job_id': job.id,
                        'filename': filename,
                        'chunk': chunk,
                        'chunk_index': i,
                        'total_chunks': num_chunks,
                        'count': job.screenshot_count
                    }, room=job.id)
                    
                    # Small delay between chunks to prevent overwhelming the connection
                    eventlet.sleep(0.05)
                
                logger.info(f"[Job {job.id}] Sent screenshot: {filename} (chunked)")
            else:
                # Send small images directly
                emit_safe('screenshot_data', {
                    'job_id': job.id,
                    'filename': filename,
                    'data': image_data_base64,
                    'count': job.screenshot_count
                }, room=job.id)
                
                logger.info(f"[Job {job.id}] Sent screenshot: {filename} ({image_size / 1024:.1f} KB)")
            
            # Small delay after each screenshot to prevent socket overflow
            eventlet.sleep(0.1)
            
        except Exception as e:
            logger.error(f"[Job {job.id}] Failed to send screenshot {filename}: {e}")
    
    try:
        device_label = 'mobile' if job.device == 'mobile' else 'desktop'
        logger.info(f"[Job {job.id}] Starting capture for {job.url}")
        logger.info(f"[Job {job.id}] Mode: {job.mode}, Device: {device_label}, Max pages: {job.max_pages}")
        
        if job.mode == 'crawl':
            update_status('running', f'Crawling website to discover pages ({device_label})...', 15)
        else:
            update_status('running', f'Parsing sitemap ({device_label})...', 15)
        
        # Create thread-safe progress/screenshot callbacks
        class ThreadSafeCallback:
            def __init__(self, job_id):
                self.job_id = job_id
                
            def progress(self, msg, pct):
                update_status('running', msg, pct)
            
            def screenshot(self, filename, image_data_base64):
                send_screenshot(filename, image_data_base64)
            
            def is_cancelled(self):
                return self.job_id in cancelled_jobs
        
        callback = ThreadSafeCallback(job.id)
        
        # Run the main screenshot function directly (not in ThreadPoolExecutor)
        # The callbacks handle Socket.IO emissions which are thread-safe in Flask-SocketIO
        logger.info(f"[Job {job.id}] Running screenshot capture...")
        result = main.main(
            url=job.url,
            max_pages=job.max_pages,
            headless=True,
            mode=job.mode,
            device=job.device,
            progress_callback=callback.progress,
            screenshot_callback=callback.screenshot,
            cancel_check=callback.is_cancelled
        )
        
        logger.info(f"[Job {job.id}] main.main() returned successfully")
        logger.info(f"[Job {job.id}] Result type: {type(result)}, value: {result}")
        
        # Check if job was cancelled
        if job.id in cancelled_jobs:
            logger.info(f"[Job {job.id}] Job was cancelled")
            cancelled_jobs.discard(job.id)  # Clean up
            return
        
        logger.info(f"[Job {job.id}] Got result: {result}")
        
        job.result = {
            'screenshots': result.get('screenshots', 0),
            'failed': result.get('failed', 0),
            'urls_found': result.get('urls_found', 0)
        }
        
        logger.info(f"[Job {job.id}] Completed: {result.get('screenshots', 0)} screenshots, {result.get('failed', 0)} failed")
        update_status('completed', f"Done! {result.get('screenshots', 0)} screenshots captured.", 100)
        logger.info(f"[Job {job.id}] Completion status emitted")
        
    except Exception as e:
        logger.error(f"[Job {job.id}] Error: {str(e)}", exc_info=True)
        job.error = str(e)
        update_status('failed', f'Error: {str(e)}', 0)


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {request.sid}")
    # Remove from all job rooms
    for job_id, sessions in list(active_sessions.items()):
        if request.sid in sessions:
            sessions.remove(request.sid)
            if not sessions:
                del active_sessions[job_id]


@socketio.on('subscribe')
def handle_subscribe(data):
    """Subscribe to job updates."""
    job_id = data.get('job_id')
    if job_id and job_id in jobs:
        # Join the job's room
        join_room(job_id)
        
        # Track active session
        if job_id not in active_sessions:
            active_sessions[job_id] = []
        if request.sid not in active_sessions[job_id]:
            active_sessions[job_id].append(request.sid)
        
        logger.info(f"Client {request.sid} subscribed to job {job_id}")
        emit('job_update', jobs[job_id].to_dict())


@socketio.on('unsubscribe')
def handle_unsubscribe(data):
    """Unsubscribe from job updates."""
    job_id = data.get('job_id')
    if job_id:
        leave_room(job_id)
        if job_id in active_sessions and request.sid in active_sessions[job_id]:
            active_sessions[job_id].remove(request.sid)
            if not active_sessions[job_id]:
                del active_sessions[job_id]
        logger.info(f"Client {request.sid} unsubscribed from job {job_id}")


if __name__ == '__main__':
    print("Starting Full Website Captures Web App...")
    print("Open http://localhost:5001 in your browser")
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
