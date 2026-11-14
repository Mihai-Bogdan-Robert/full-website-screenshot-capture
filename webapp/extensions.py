"""Objects shared between modules; they are attached to the app in create_app()."""

from flask_socketio import SocketIO

socketio = SocketIO()
