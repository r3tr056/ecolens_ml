from dotenv import load_dotenv
from apps.app import create_app

load_dotenv()
flask_app = create_app()
celery_app = flask_app.extensions['celery']