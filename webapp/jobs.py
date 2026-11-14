"""Capture jobs and who is listening to them. Everything lives in memory."""

import uuid
from datetime import datetime

from webapp import config

FINISHED = ('completed', 'failed', 'cancelled')


class Job:
    def __init__(self, url, max_pages, mode, device):
        # A long random id: it is the only secret protecting a job's results.
        self.id = uuid.uuid4().hex
        self.url = url
        self.max_pages = max_pages
        self.mode = mode          # 'sitemap' or 'crawl'
        self.device = device      # 'desktop' or 'mobile'
        self.status = 'pending'   # pending -> running -> completed | failed | cancelled
        self.progress = 0
        self.message = 'Waiting to start...'
        self.result = None
        self.error = None
        self.screenshot_count = 0
        self.created_at = datetime.now()

    @property
    def finished(self):
        return self.status in FINISHED

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
            'created_at': self.created_at.isoformat(),
        }


class JobStore:
    def __init__(self):
        self._jobs = {}
        self._subscribers = {}      # job id -> set of Socket.IO session ids
        self._cancel_requested = set()

    def create(self, url, max_pages, mode, device):
        self.prune()
        job = Job(url, max_pages, mode, device)
        self._jobs[job.id] = job
        return job

    def get(self, job_id):
        return self._jobs.get(job_id)

    def prune(self):
        """Forget old finished jobs so memory does not grow forever."""
        now = datetime.now()
        for job_id, job in list(self._jobs.items()):
            if job.finished and (now - job.created_at).total_seconds() > config.JOB_RETENTION:
                del self._jobs[job_id]
                self._cancel_requested.discard(job_id)
                self._subscribers.pop(job_id, None)

    def request_cancel(self, job_id):
        self._cancel_requested.add(job_id)

    def cancel_requested(self, job_id):
        return job_id in self._cancel_requested

    def clear_cancel(self, job_id):
        self._cancel_requested.discard(job_id)

    def subscribe(self, job_id, sid):
        self._subscribers.setdefault(job_id, set()).add(sid)

    def unsubscribe(self, job_id, sid):
        sids = self._subscribers.get(job_id)
        if sids:
            sids.discard(sid)
            if not sids:
                del self._subscribers[job_id]

    def unsubscribe_everywhere(self, sid):
        for job_id in list(self._subscribers):
            self.unsubscribe(job_id, sid)

    def has_subscribers(self, job_id):
        return bool(self._subscribers.get(job_id))


store = JobStore()
