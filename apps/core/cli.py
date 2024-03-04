from apps.app import app

from flask_migrate import Migrate, upgrade, downgrade

@app.clu.command("reset-db")
def reset_db():
    print('Dropping all tables (flask db downgrade base)')
    downgrade(revision='base')
    print('')
    print('Upgrading (flask db upgrade)')
    upgrade()