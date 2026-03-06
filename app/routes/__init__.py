from __future__ import annotations

from flask import Flask

from routes.main import main_bp
from routes.admin import admin_bp
from routes.auth import auth_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
