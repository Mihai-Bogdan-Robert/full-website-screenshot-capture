"""HTTP endpoints."""

import logging
import threading

from flask import Blueprint, jsonify, render_template, request

from capture.security import UnsafeURL, normalize_user_url, safe_get
from capture.sitemap import sitemap_url_for
from webapp import config
from webapp.delivery import send_job_update
from webapp.jobs import store
from webapp.runner import run_job

logger = logging.getLogger(__name__)

api = Blueprint('api', __name__)

MODES = ('sitemap', 'crawl')
DEVICES = ('desktop', 'mobile')


def _error(message, status=400):
    return jsonify({'error': message}), status


@api.get('/')
def index():
    return render_template('index.html')


@api.post('/api/jobs')
def create_job():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data.get('url'):
        return _error('URL is required')

    try:
        url = normalize_user_url(str(data['url']))
    except UnsafeURL as err:
        return _error(str(err))

    try:
        max_pages = int(data.get('max_pages', config.DEFAULT_MAX_PAGES))
    except (TypeError, ValueError):
        return _error('max_pages must be a number')
    max_pages = max(1, min(max_pages, config.MAX_PAGES_LIMIT))

    mode = data.get('mode', 'sitemap')
    if mode not in MODES:
        return _error("mode must be 'sitemap' or 'crawl'")

    device = data.get('device', 'desktop')
    if device not in DEVICES:
        return _error("device must be 'desktop' or 'mobile'")

    job = store.create(url, max_pages, mode, device)
    threading.Thread(target=run_job, args=(job,), daemon=True).start()
    return jsonify(job.to_dict()), 201


@api.get('/api/jobs/<job_id>')
def get_job(job_id):
    job = store.get(job_id)
    if not job:
        return _error('Job not found', 404)
    return jsonify(job.to_dict())


@api.post('/api/jobs/<job_id>/cancel')
def cancel_job(job_id):
    job = store.get(job_id)
    if not job:
        return _error('Job not found', 404)
    if job.finished:
        return _error('Job already finished')

    store.request_cancel(job_id)
    job.status = 'cancelled'
    job.message = 'Cancelled by user'
    send_job_update(job)
    logger.info('[Job %s] Cancelled by user', job_id)
    return jsonify({'message': 'Job cancelled'})


@api.post('/api/check-sitemap')
def check_sitemap():
    """Tell the form whether the site has a sitemap."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data.get('url'):
        return _error('URL is required')

    try:
        sitemap_url = sitemap_url_for(normalize_user_url(str(data['url'])))
        # GET, not HEAD: many servers reject HEAD. Only the status code is needed.
        response = safe_get(sitemap_url, timeout=3, stream=True)
        response.close()
    except Exception as err:
        logger.debug('Sitemap check failed for %s: %s', data['url'], err)
        return jsonify({'exists': False})

    if response.status_code == 200:
        return jsonify({'exists': True, 'sitemap_url': sitemap_url})
    return jsonify({'exists': False})
