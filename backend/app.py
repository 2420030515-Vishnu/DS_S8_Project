"""Application factory for the India COVID-19 analytics API."""
import hmac
import os
from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify, request, session
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv

try:
    from .database import close_db, init_db
    from .routes.auth_routes import auth_bp
    from .routes.data_routes import data_bp
except ImportError:  # Optional direct invocation: `python backend/app.py`
    from database import close_db, init_db
    from routes.auth_routes import auth_bp
    from routes.data_routes import data_bp


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _cors_origins():
    raw = os.environ.get("FRONTEND_ORIGINS") or os.environ.get("FRONTEND_ORIGIN") or "http://localhost:5173"
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app(test_config=None):
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    app = Flask(__name__)
    backend_dir = Path(__file__).resolve().parent
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY"),
        DATABASE=os.environ.get("DATABASE_PATH", str(backend_dir / "covid_dashboard.sqlite3")),
        DATA_DIR=os.environ.get("COVID_DATA_DIR", str(backend_dir / "data")),
        FRONTEND_ORIGINS=_cors_origins(),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=_env_bool("SESSION_COOKIE_SECURE", os.environ.get("APP_ENV", "development").casefold() == "production"),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=1024 * 1024,
        CSRF_ENABLED=True,
        JSON_SORT_KEYS=False,
        TESTING=False,
    )
    if test_config:
        app.config.update(test_config)
    configured_secret = app.config.get("SECRET_KEY")
    if not isinstance(configured_secret, str) or len(configured_secret) < 32 or configured_secret.startswith("replace-with-"):
        raise RuntimeError("Set FLASK_SECRET_KEY to a private random value of at least 32 characters before starting the backend.")

    CORS(app, resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGINS"]}},
         supports_credentials=True, allow_headers=["Content-Type", "X-CSRF-Token"],
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    app.register_blueprint(auth_bp)
    app.register_blueprint(data_bp)
    app.teardown_appcontext(close_db)
    init_db(app.config["DATABASE"])

    @app.cli.command("init-db")
    def init_db_command():
        """Create the SQLite account and preference tables (safe to re-run)."""
        init_db(app.config["DATABASE"])
        print("Database initialized.")

    @app.before_request
    def protect_mutating_requests():
        if not app.config["CSRF_ENABLED"] or not request.path.startswith("/api/"):
            return None
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None
        expected = session.get("csrf_token", "")
        supplied = request.headers.get("X-CSRF-Token", "")
        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            return jsonify({"error": "A valid CSRF token is required.", "code": "csrf_failed"}), 403
        return None

    @app.before_request
    def log_request_start():
        app.logger.info("Request %s %s", request.method, request.path)

    @app.after_request
    def log_response(response):
        app.logger.info("Response %s %s status=%s", request.method, request.path, response.status_code)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if request.path.startswith("/api/auth/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({"error": error.description, "code": error.name.lower().replace(" ", "_")}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Unhandled request error")
        return jsonify({"error": "The request could not be completed.", "code": "internal_error"}), 500

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "india-covid-analytics-api", "historical_data": True})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")),
            debug=_env_bool("FLASK_DEBUG", False))
