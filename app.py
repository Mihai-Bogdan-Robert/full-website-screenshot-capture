"""Entry point. Production: `gunicorn app:app` (see the Dockerfile). Local: `python app.py`."""

import logging

from webapp import config
from webapp import create_app
from webapp.extensions import socketio

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%H:%M:%S')

app = create_app()

if __name__ == '__main__':
    print(f'Open http://localhost:{config.PORT} in your browser')
    # The Werkzeug development server is fine here: it listens on this computer only unless HOST is set.
    socketio.run(app, host=config.HOST, port=config.PORT, debug=config.DEBUG,
                 allow_unsafe_werkzeug=True)
