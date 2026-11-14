"""Settings read from the environment, and the limits the app enforces."""

import os
import secrets


def _flag(name):
    return os.environ.get(name, '').strip().lower() in ('1', 'true', 'yes')


# A random key is generated at start-up unless SECRET_KEY is set (the app has no sessions to persist).
SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

# Browser origins allowed to open a Socket.IO connection, comma separated. "*" accepts any origin;
# set it to your domain when the app is reachable from the internet.
_origins = os.environ.get('ALLOWED_ORIGINS', '*').strip()
ALLOWED_ORIGINS = '*' if _origins == '*' else [o.strip() for o in _origins.split(',') if o.strip()]

# Only used by `python app.py`.
HOST = os.environ.get('HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', '5001'))
DEBUG = _flag('FLASK_DEBUG')

MAX_PAGES_LIMIT = 500
DEFAULT_MAX_PAGES = 200
MAX_JOB_DURATION = 30 * 60        # seconds; a longer capture is stopped
JOB_RETENTION = 2 * 60 * 60       # seconds; finished jobs are forgotten after this

# Screenshots are sent to the browser in pieces of this many bytes.
SCREENSHOT_CHUNK_SIZE = 500 * 1024
