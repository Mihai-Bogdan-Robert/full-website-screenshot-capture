"""Runs one capture job: starts the worker process and turns its messages into job updates."""

import logging
import multiprocessing
import time
from queue import Empty

from webapp import config
from webapp.delivery import send_job_update, send_screenshot
from webapp.jobs import store
from webapp.worker import run_capture

logger = logging.getLogger(__name__)

# Not fork: forking a process that already has threads is unsafe.
_mp = multiprocessing.get_context('spawn')


class WorkerError(Exception):
    pass


def _set_status(job, status, message, progress=None):
    if job.status == 'cancelled':
        return  # a late message from the worker must not revive a cancelled job
    job.status = status
    job.message = message
    if progress is not None:
        job.progress = progress
    send_job_update(job)
    logger.info('[Job %s] %s', job.id, message)


def _handle_message(job, message):
    """Apply one worker message to the job. Returns True when the capture is complete."""
    kind = message['type']
    if kind == 'progress':
        _set_status(job, 'running', message['message'], message['percent'])
    elif kind == 'screenshot':
        send_screenshot(job, message['filename'], message['data'])
    elif kind == 'complete':
        result = message['result']
        job.result = {key: result.get(key, 0) for key in ('screenshots', 'failed', 'urls_found')}
        _set_status(job, 'completed', f"Done! {job.result['screenshots']} screenshots captured.", 100)
        return True
    elif kind == 'error':
        raise WorkerError(message['error'])
    return False


def _stop_worker(job, process, cancel_event):
    cancel_event.set()
    process.join(timeout=10)
    if process.is_alive():
        logger.warning('[Job %s] Worker did not stop, terminating it', job.id)
        process.terminate()
        process.join(timeout=5)


def _drain(job, messages):
    """Handle whatever the worker left in the queue before it exited."""
    completed = False
    while True:
        try:
            completed = _handle_message(job, messages.get_nowait()) or completed
        except Empty:
            return completed


def run_job(job):
    """Run a capture to the end. Meant to be the target of a background thread."""
    deadline = time.monotonic() + config.MAX_JOB_DURATION
    messages = _mp.Queue()
    cancel_event = _mp.Event()
    process = _mp.Process(
        target=run_capture,
        args=(job.id, job.url, job.max_pages, job.mode, job.device, messages, cancel_event),
    )

    try:
        label = 'Crawling website to discover pages' if job.mode == 'crawl' else 'Parsing sitemap'
        logger.info('[Job %s] %s, %s, %s, max %d pages', job.id, job.url, job.mode, job.device, job.max_pages)
        _set_status(job, 'running', f'{label} ({job.device})...', 15)
        process.start()

        completed = False
        while not completed:
            if store.cancel_requested(job.id):
                logger.info('[Job %s] Stopping the worker (cancelled)', job.id)
                _stop_worker(job, process, cancel_event)
                store.clear_cancel(job.id)
                return
            if time.monotonic() > deadline:
                logger.warning('[Job %s] Time limit of %ds exceeded', job.id, config.MAX_JOB_DURATION)
                _stop_worker(job, process, cancel_event)
                job.error = 'The capture took too long and was stopped'
                _set_status(job, 'failed', job.error, 0)
                return

            try:
                completed = _handle_message(job, messages.get(timeout=0.5))
            except Empty:
                if not process.is_alive():
                    completed = _drain(job, messages)
                    break

        process.join(timeout=30)
        if process.is_alive():
            logger.warning('[Job %s] Worker still running, terminating it', job.id)
            process.terminate()
            process.join(timeout=5)

        if not completed:
            _set_status(job, 'failed', 'Worker process ended unexpectedly', 0)

    except Exception as err:
        logger.error('[Job %s] %s', job.id, err, exc_info=True)
        job.error = str(err)[:300]
        _set_status(job, 'failed', f'Error: {err}', 0)
        if process.is_alive():
            process.terminate()
