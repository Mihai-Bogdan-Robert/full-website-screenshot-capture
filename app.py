"""
Local development entry point — delegates to backend/api.py.

For production use Docker instead:
    docker-compose up

For local development (without Docker):
    python app.py
"""

import os
import sys

# Ensure backend/api.py can find its sibling modules in backend/src/
_backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
_src_dir = os.path.join(_backend_dir, 'src')
for _p in (_backend_dir, _src_dir):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Set the frontend path for local runs (backend/api.py reads this env var)
os.environ.setdefault(
    'WEB_INTERFACE_DIR',
    os.path.join(os.path.dirname(__file__), 'frontend')
)

from api import app  # noqa: E402 — backend/api.py is now on sys.path

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
