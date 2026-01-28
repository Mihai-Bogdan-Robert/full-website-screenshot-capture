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
import threading
import multiprocessing
from queue import Queue, Empty

# Set multiprocessing start method to 'spawn' for proper process isolation
# This is required on macOS and prevents issues with forking eventlet-patched processes
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass  # Already set

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

# Track active jobs and client sessions
jobs = {}
active_sessions = {}  # {job_id: [session_ids]}
cancelled_jobs = set()  # Set of job IDs that have been cancelled

# Multiprocessing manager for cross-process communication
mp_manager = None
job_queues = {}  # {job_id: multiprocessing.Queue} for receiving results from workers


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
    # The thread will spawn a separate process for Playwright isolation
    job_thread = threading.Thread(target=run_job, args=(job,), daemon=True)
    job_thread.start()
    
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


@app.route('/api/check-sitemap', methods=['POST'])
def check_sitemap():
    """Check if a sitemap exists for the given URL."""
    data = request.get_json()
    
    if not data or not data.get('url'):
        return jsonify({'error': 'URL is required'}), 400
    
    url = data['url'].strip()
    
    # Normalize URL
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url
    
    try:
        from urllib.parse import urlparse
        import requests
        
        parsed = urlparse(url)
        sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
        
        # Try to fetch the sitemap with a short timeout
        response = requests.head(sitemap_url, timeout=3, allow_redirects=True)
        
        if response.status_code == 200:
            return jsonify({'exists': True, 'sitemap_url': sitemap_url})
        else:
            return jsonify({'exists': False})
            
    except Exception as e:
        logger.debug(f"Sitemap check failed for {url}: {e}")
        return jsonify({'exists': False})


# No longer needed - screenshots are stored client-side and ZIP is generated in browser


def playwright_worker(url, max_pages, mode, device, job_id, result_queue, cancel_event):
    """
    Worker function that runs Playwright in a separate process.
    This completely isolates asyncio event loops between jobs.
    """
    import main
    import logging
    import base64
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    logger = logging.getLogger(__name__)
    
    def progress_callback(msg, pct):
        result_queue.put({'type': 'progress', 'message': msg, 'percent': pct})
    
    def screenshot_callback(filename, image_data_base64):
        result_queue.put({'type': 'screenshot', 'filename': filename, 'data': image_data_base64})
    
    def cancel_check():
        return cancel_event.is_set()
    
    try:
        logger.info(f"[Worker {job_id}] Starting Playwright capture")
        result = main.main(
            url=url,
            max_pages=max_pages,
            headless=True,
            mode=mode,
            device=device,
            progress_callback=progress_callback,
            screenshot_callback=screenshot_callback,
            cancel_check=cancel_check
        )
        result_queue.put({'type': 'complete', 'result': result})
        logger.info(f"[Worker {job_id}] Completed successfully")
    except Exception as e:
        logger.error(f"[Worker {job_id}] Error: {e}")
        result_queue.put({'type': 'error', 'error': str(e)})


def run_job(job):
    """Run the screenshot job in background using a separate process for Playwright isolation."""
    
    # Set maximum job duration (30 minutes)
    MAX_JOB_DURATION = 1800
    start_time = time.time()
    
    def check_timeout():
        if time.time() - start_time > MAX_JOB_DURATION:
            logger.warning(f"[Job {job.id}] Timeout exceeded ({MAX_JOB_DURATION}s)")
            return True
        return False
    
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
        logger.info(f"[Job {job.id}] Timeout: {MAX_JOB_DURATION}s")
        
        if job.mode == 'crawl':
            update_status('running', f'Crawling website to discover pages ({device_label})...', 15)
        else:
            update_status('running', f'Parsing sitemap ({device_label})...', 15)
        
        # Create multiprocessing primitives for communication
        result_queue = multiprocessing.Queue()
        cancel_event = multiprocessing.Event()
        
        # Start Playwright in a separate process to isolate asyncio event loop
        logger.info(f"[Job {job.id}] Spawning Playwright worker process...")
        worker_process = multiprocessing.Process(
            target=playwright_worker,
            args=(job.url, job.max_pages, job.mode, job.device, job.id, result_queue, cancel_event)
        )
        worker_process.start()
        
        job_completed = False
        
        # Monitor the process and handle messages
        while True:
            # Check for cancellation
            if job.id in cancelled_jobs or check_timeout():
                logger.info(f"[Job {job.id}] Signaling worker to stop...")
                cancel_event.set()
                worker_process.join(timeout=10)
                if worker_process.is_alive():
                    logger.warning(f"[Job {job.id}] Force terminating worker...")
                    worker_process.terminate()
                    worker_process.join(timeout=5)
                cancelled_jobs.discard(job.id)
                return
            
            # Process messages from worker with timeout
            try:
                msg = result_queue.get(timeout=0.5)
                
                if msg['type'] == 'progress':
                    update_status('running', msg['message'], msg['percent'])
                
                elif msg['type'] == 'screenshot':
                    send_screenshot(msg['filename'], msg['data'])
                
                elif msg['type'] == 'complete':
                    result = msg['result']
                    job.result = {
                        'screenshots': result.get('screenshots', 0),
                        'failed': result.get('failed', 0),
                        'urls_found': result.get('urls_found', 0)
                    }
                    logger.info(f"[Job {job.id}] Completed: {result.get('screenshots', 0)} screenshots, {result.get('failed', 0)} failed")
                    update_status('completed', f"Done! {result.get('screenshots', 0)} screenshots captured.", 100)
                    job_completed = True
                    break  # Exit loop on completion
                    
                elif msg['type'] == 'error':
                    raise Exception(msg['error'])
                    
            except Empty:
                # Queue timeout - check if process is still alive
                if not worker_process.is_alive():
                    # Process died, drain any remaining messages
                    try:
                        while True:
                            msg = result_queue.get_nowait()
                            if msg['type'] == 'complete':
                                result = msg['result']
                                job.result = {
                                    'screenshots': result.get('screenshots', 0),
                                    'failed': result.get('failed', 0),
                                    'urls_found': result.get('urls_found', 0)
                                }
                                logger.info(f"[Job {job.id}] Completed: {result.get('screenshots', 0)} screenshots, {result.get('failed', 0)} failed")
                                update_status('completed', f"Done! {result.get('screenshots', 0)} screenshots captured.", 100)
                                job_completed = True
                            elif msg['type'] == 'error':
                                raise Exception(msg['error'])
                            elif msg['type'] == 'screenshot':
                                send_screenshot(msg['filename'], msg['data'])
                    except Empty:
                        pass
                    break  # Exit loop when process is dead and queue is empty
                continue
            except Exception as e:
                if not isinstance(e, Empty):
                    raise
        
        # Wait for process to finish
        worker_process.join(timeout=30)
        if worker_process.is_alive():
            logger.warning(f"[Job {job.id}] Worker still alive, terminating...")
            worker_process.terminate()
            worker_process.join(timeout=5)
        
        # If job didn't complete normally, mark as failed
        if not job_completed and job.status != 'completed':
            logger.warning(f"[Job {job.id}] Worker process ended without completion message")
            update_status('failed', 'Worker process ended unexpectedly', 0)
        
        logger.info(f"[Job {job.id}] Worker process completed")
        
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
