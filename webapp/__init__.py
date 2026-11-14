"""The web application: HTTP API, Socket.IO events and the page that uses them."""

from flask import Flask

from webapp import config
from webapp.api import api
from webapp.extensions import socketio


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.register_blueprint(api)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        return response

    # Imported for its @socketio.on handlers.
    from webapp import events  # noqa: F401

    socketio.init_app(
        app,
        cors_allowed_origins=config.ALLOWED_ORIGINS,
        async_mode='threading',
        ping_timeout=120,
        ping_interval=25,
    )
    return app
