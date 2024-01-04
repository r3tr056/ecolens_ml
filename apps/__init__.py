import os
from flask import Flask

def create_app():
    app = Flask(__name__)
    environ_config = os.environ['CONFIG_SETUP']
    app.config.from_object(environ_config)

    with app.app_context():
        # Register all blueprints
        return app