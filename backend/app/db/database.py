"""Database initialization and utilities."""

import logging
from typing import Any

from flask_sqlalchemy import SQLAlchemy

logger = logging.getLogger(__name__)

# SQLAlchemy instance - bind to app in app factory
db = SQLAlchemy()


def init_db(app: Any) -> None:
    """
    Initialize database with Flask app.

    Args:
        app: Flask application instance.
    """
    # NOTE: db.init_app(app) is called in app.create_app(), not here
    # Create all tables
    db.create_all()
    logger.info("Database tables created/verified")

    # Initialize default data
    seed_admin(app)


def seed_admin(app: Any) -> None:
    """
    Seed default admin user if not exists.

    Creates admin@fleetlock.in with password "FleetLock@2026" if admin doesn't exist.

    Args:
        app: Flask application instance.
    """
    try:
        from app.db.models import User
        import bcrypt

        # Check if admin already exists
        admin = User.query.filter_by(email="admin@fleetlock.in").first()
        if admin:
            logger.info("Admin user already exists")
            return

        # Create admin user with bcrypt-hashed password
        default_password = "FleetLock@2026"
        password_hash = bcrypt.hashpw(
            default_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        admin_user = User(
            email="admin@fleetlock.in",
            password_hash=password_hash,
            name="FleetLock Admin",
            role="admin",
            phone="+91-0000000000",
            city="Bangalore",
        )

        db.session.add(admin_user)
        db.session.commit()
        logger.info("Admin user created: admin@fleetlock.in")

    except Exception as e:
        logger.error(f"Error seeding admin user: {e}")
        db.session.rollback()
