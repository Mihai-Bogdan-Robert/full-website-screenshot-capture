"""Socket.IO events: a browser subscribes to a job to receive its updates and screenshots."""

import logging

from flask import request
from flask_socketio import emit, join_room, leave_room

from webapp.extensions import socketio
from webapp.jobs import store

logger = logging.getLogger(__name__)


@socketio.on('connect')
def on_connect():
    logger.info('Client connected: %s', request.sid)


@socketio.on('disconnect')
def on_disconnect():
    logger.info('Client disconnected: %s', request.sid)
    store.unsubscribe_everywhere(request.sid)


@socketio.on('subscribe')
def on_subscribe(data):
    job = store.get(data.get('job_id'))
    if job:
        join_room(job.id)
        store.subscribe(job.id, request.sid)
        emit('job_update', job.to_dict())


@socketio.on('unsubscribe')
def on_unsubscribe(data):
    job_id = data.get('job_id')
    if job_id:
        leave_room(job_id)
        store.unsubscribe(job_id, request.sid)
