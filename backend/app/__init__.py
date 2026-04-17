"""Flask application factory module."""

import logging
from time import perf_counter
from datetime import datetime, timezone
from typing import Optional

from flask import Flask, jsonify, g, request
from flask_jwt_extended import JWTManager, get_jwt
from flask_cors import CORS

from app.db.database import db, init_db

logger = logging.getLogger(__name__)


def create_app(config_class: Optional[type] = None) -> Flask:
    """
    Create and configure Flask application.

    Initializes:
    - Flask instance
    - Configuration (development/production/testing)
    - Flask-SQLAlchemy for MySQL ORM
    - Flask-JWT-Extended for JWT authentication
    - Flask-CORS for cross-origin requests

    Registers blueprints:
    - auth_bp (prefix /api/auth): Authentication routes
    - worker_bp (prefix /api/worker): Worker routes
    - admin_bp (prefix /api/admin): Admin routes
    - weather_bp (prefix /api/weather): Weather routes
    - plans_bp (prefix /api): Plans routes

    Registers error handlers and JWT callbacks.

    Args:
        config_class (type | None): Configuration class. If None, uses get_config().

    Returns:
        Flask: Configured Flask application instance.
    """
    app = Flask(__name__)
    app.config["APP_STARTED_AT"] = datetime.now(timezone.utc)

    # Load configuration
    if config_class is None:
        from config import get_config
        config_class = get_config()
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    CORS(app, origins=app.config.get("CORS_ORIGINS", ["http://localhost:3000"]))

    # Import models AFTER db.init_app so they register with SQLAlchemy
    from app.db import models  # noqa: F401

    # Register blueprints
    from app.api.auth import auth_bp
    from app.api.worker import worker_bp
    from app.api.kyc_routes import kyc_bp
    from app.api.admin import admin_bp
    from app.api.weather import weather_bp
    from app.api.plans import plans_bp
    from app.api.health import health_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(worker_bp, url_prefix="/api/worker")
    app.register_blueprint(kyc_bp, url_prefix="/api/worker")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(weather_bp, url_prefix="/api/weather")
    app.register_blueprint(plans_bp, url_prefix="/api")
    app.register_blueprint(health_bp, url_prefix="/actuator")

    # Initialize database (create tables and seed admin)
    with app.app_context():
        init_db(app)

    # --- JWT Callbacks ---

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """Check if JWT token is in blocklist (logged out)."""
        try:
            from app.db.models import TokenBlocklist
            jti = jwt_payload.get("jti")
            token = TokenBlocklist.query.filter_by(jti=jti).first()
            return token is not None
        except Exception as e:
            logger.error(f"Error checking token blocklist: {e}")
            return False

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        """Handle expired JWT token."""
        return jsonify({
            "success": False,
            "message": "Token has expired",
            "data": None,
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        """Handle invalid JWT token."""
        return jsonify({
            "success": False,
            "message": "Invalid token",
            "data": None,
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        """Handle missing JWT token."""
        return jsonify({
            "success": False,
            "message": "Authorization header is missing",
            "data": None,
        }), 401

    # --- Request/Response Hooks ---

    @app.before_request
    def log_request():
        """Log incoming request."""
        g._request_started_at = perf_counter()

        # Always print API/actuator endpoint activity in terminal for monitoring.
        if request.path.startswith("/api") or request.path.startswith("/actuator"):
            logger.info("REQ %s %s", request.method, request.path)

    @app.after_request
    def add_security_headers(response):
        """Add security headers to response."""
        if request.path.startswith("/api") or request.path.startswith("/actuator"):
            started = getattr(g, "_request_started_at", None)
            elapsed_ms = ((perf_counter() - started) * 1000.0) if started else 0.0
            logger.info(
                "RES %s %s -> %s (%.1f ms)",
                request.method,
                request.path,
                response.status_code,
                elapsed_ms,
            )

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    # --- Error Handlers ---

    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request."""
        return jsonify({
            "success": False,
            "message": "Bad request",
            "data": None,
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found."""
        return jsonify({
            "success": False,
            "message": "Resource not found",
            "data": None,
        }), 404

    @app.errorhandler(422)
    def unprocessable_entity(error):
        """Handle 422 Unprocessable Entity."""
        return jsonify({
            "success": False,
            "message": "Unprocessable entity",
            "data": None,
        }), 422

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error."""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "data": None,
        }), 500

    logger.info(f"Flask app created with config: {config_class.__name__}")

    return app
