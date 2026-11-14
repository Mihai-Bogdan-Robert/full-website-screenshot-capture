"""Send job updates and screenshots to the browsers watching a job."""

import logging
import time

from webapp import config
from webapp.extensions import socketio
from webapp.jobs import store

logger = logging.getLogger(__name__)

PAUSE_BETWEEN_CHUNKS = 0.05
PAUSE_BETWEEN_SCREENSHOTS = 0.1


def send_job_update(job):
    try:
        socketio.emit('job_update', job.to_dict(), to=job.id)
    except Exception as err:
        logger.error('[Job %s] Failed to send update: %s', job.id, err)


def send_screenshot(job, filename, png):
    """Send one PNG as binary chunks (`screenshot_chunk` events) to the job's subscribers.

    The pauses keep a large image from flooding the connection.
    """
    job.screenshot_count += 1
    if not store.has_subscribers(job.id):
        logger.warning('[Job %s] Nobody is listening, dropping %s', job.id, filename)
        return

    size = config.SCREENSHOT_CHUNK_SIZE
    total_chunks = (len(png) + size - 1) // size
    try:
        for index in range(total_chunks):
            socketio.emit('screenshot_chunk', {
                'job_id': job.id,
                'filename': filename,
                'chunk': png[index * size:(index + 1) * size],
                'chunk_index': index,
                'total_chunks': total_chunks,
                'count': job.screenshot_count,
            }, to=job.id)
            time.sleep(PAUSE_BETWEEN_CHUNKS)
        logger.info('[Job %s] Sent %s (%.1f KB)', job.id, filename, len(png) / 1024)
        time.sleep(PAUSE_BETWEEN_SCREENSHOTS)
    except Exception as err:
        logger.error('[Job %s] Failed to send %s: %s', job.id, filename, err)
