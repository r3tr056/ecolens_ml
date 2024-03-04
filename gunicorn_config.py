# gunicorn_config.py
bind = '0.0.0.0:8000'
workers = 4  # Adjust based on your server's capabilities
worker_class = 'quart.worker.GunicornWorker'
