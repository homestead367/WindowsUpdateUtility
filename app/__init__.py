import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from .config import Config
from .database import init_db

_csrf = CSRFProtect()

def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    os.makedirs(app.config['UPLOAD_FOLDER'], mode=0o700, exist_ok=True)
    init_db(app)
    _csrf.init_app(app)

    from .routes.dashboard import bp as dashboard_bp
    from .routes.jobs import bp as jobs_bp
    from .routes.api import bp as api_bp
    from .routes.settings import bp as settings_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(settings_bp)

    _csrf.exempt(api_bp)  # API uses JSON; protected by SameSite=Lax + no CORS

    return app
