"""Main Flask application entry point."""

import sys
import os
import logging

# Ensure project root is in Python path for root-level package imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """
    Create and run Flask application.

    Initializes the Flask app factory and starts the development server.
    For production deployment, use gunicorn or another WSGI server.

    Environment Variables:
        - FLASK_ENV: application environment (development/production/testing)
        - PORT: server port (default: 5000)
        - DEBUG: enable debug mode (default: False for production)
        - SQLALCHEMY_DATABASE_URI: MySQL database connection string
    """
    app = create_app()

    # Get port from environment or default to 5000
    port = int(os.getenv("PORT", 5000))
    debug = app.config.get("DEBUG", False)

    logger.info(f"Starting Flask server on 0.0.0.0:{port} (debug={debug})")

    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
