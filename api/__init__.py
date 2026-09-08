"""
Flask application factory.
"""

from flask import Flask
from flask_cors import CORS

import state
from core.manager import FloodManager
from api.routes import bp


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    state.manager = FloodManager()
    app.register_blueprint(bp)

    return app
