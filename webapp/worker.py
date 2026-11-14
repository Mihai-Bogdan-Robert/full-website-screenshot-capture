"""The capture itself runs in a separate process, so a crashing or hanging browser cannot take
the web server down. It reports back through a multiprocessing queue with these messages:

    {'type': 'progress',   'message': str, 'percent': int}
    {'type': 'screenshot', 'filename': str, 'data': bytes}
    {'type': 'complete',   'result': dict}
    {'type': 'error',      'error': str}
"""

import logging

from capture.pipeline import capture_site

logger = logging.getLogger(__name__)


def run_capture(job_id, url, max_pages, mode, device, messages, cancel_event):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%H:%M:%S')
    try:
        logger.info('[Worker %s] Starting capture', job_id)
        result = capture_site(
            url,
            on_screenshot=lambda filename, png: messages.put(
                {'type': 'screenshot', 'filename': filename, 'data': png}),
            max_pages=max_pages,
            mode=mode,
            device=device,
            on_progress=lambda message, percent: messages.put(
                {'type': 'progress', 'message': message, 'percent': percent}),
            should_cancel=cancel_event.is_set,
        )
        messages.put({'type': 'complete', 'result': result})
    except Exception as err:
        logger.error('[Worker %s] %s', job_id, err)
        messages.put({'type': 'error', 'error': str(err)[:300]})
