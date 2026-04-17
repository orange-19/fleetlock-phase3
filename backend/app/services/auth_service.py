"""Authentication service for user registration, login, and JWT token management."""

import logging
import re
from typing import Dict, Any

from flask_jwt_extended import create_access_token
import bcrypt
from sqlalchemy.exc import IntegrityError

from app.db.database import db
from app.db.models import User
from app.db.repositories.worker_repo import WorkerRepository

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""

    @staticmethod
    def validate_registration_data(
        email: str,
        password: str,
        name: str,
        role: str,
        phone: str | None,
        city: str | None,
        platform: str | None,
    ) -> None:
        """
        Validate registration data.

        Args:
            email (str): Email address.
            password (str): Password.
            name (str): User name.
            role (str): User role (worker or admin).
            phone (str | None): Phone number.
            city (str | None): City.
            platform (str | None): Gig platform (required if role=worker).

        Raises:
            ValueError: If any validation fails.
        """
        # Email validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            raise ValueError("Invalid email format")

        # Password validation (minimum 8 chars, at least one uppercase, one digit)
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one digit")

        # Name validation
        if not name or len(name.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")

        # Role validation
        if role not in ("worker", "admin"):
            raise ValueError("Role must be 'worker' or 'admin'")

        # Platform validation (required for workers)
        if role == "worker" and not platform:
            raise ValueError("Platform is required for worker role")

    @staticmethod
    def register(
        email: str,
        password: str,
        name: str,
        role: str = "worker",
        phone: str | None = None,
        city: str | None = None,
        platform: str | None = None,
    ) -> Dict[str, Any]:
        """
        Register a new user.

        Creates user record in users table. If role==worker, also creates worker profile.

        Args:
            email (str): User email (must be unique).
            password (str): User password (will be bcrypt-hashed).
            name (str): User name.
            role (str): User role. Defaults to "worker".
            phone (str | None): Phone number. Defaults to None.
            city (str | None): City. Defaults to None.
            platform (str | None): Gig platform. Defaults to None.

        Returns:
            Dict: Contains 'user' dict and 'access_token' JWT string.

        Raises:
            ValueError: If validation fails or email already exists.
        """
        # Validate input
        AuthService.validate_registration_data(
            email, password, name, role, phone, city, platform
        )

        # Check email uniqueness
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            logger.warning(f"Registration failed: email already exists: {email}")
            raise ValueError(f"Email {email} is already registered")

        try:
            # Hash password with bcrypt
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            # Create user
            user = User(
                email=email,
                password_hash=password_hash,
                name=name,
                role=role,
                phone=phone,
                city=city,
            )
            db.session.add(user)
            db.session.flush()  # Get user.id without committing

            # If worker role, create worker profile
            if role == "worker":
                WorkerRepository.create(
                    user_id=user.id, platform=platform, city=city or "Unknown"
                )

            db.session.commit()
            logger.info(f"User registered: email={email}, role={role}")

            # Generate JWT token (identity must be string for consistency)
            access_token = create_access_token(
                identity=str(user.id),
                additional_claims={"role": user.role, "email": user.email, "name": user.name},
            )

            return {
                "user": user.to_dict(),
                "access_token": access_token,
            }

        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error during registration: {e}")
            raise ValueError("User already exists")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during registration: {e}")
            raise

    @staticmethod
    def login(email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user and return JWT token.

        Args:
            email (str): User email.
            password (str): User password.

        Returns:
            Dict: Contains 'user' dict and 'access_token' JWT string.

        Raises:
            ValueError: If credentials are invalid.
        """
        try:
            # Find user by email
            user = User.query.filter_by(email=email).first()
            if not user:
                logger.warning(f"Login failed: user not found: {email}")
                raise ValueError("Invalid email or password")

            # Verify password
            if not bcrypt.checkpw(
                password.encode("utf-8"), user.password_hash.encode("utf-8")
            ):
                logger.warning(f"Login failed: invalid password for: {email}")
                raise ValueError("Invalid email or password")

            # Generate JWT token (identity must be string for consistency)
            access_token = create_access_token(
                identity=str(user.id),
                additional_claims={"role": user.role, "email": user.email, "name": user.name},
            )

            logger.info(f"User logged in: email={email}, role={user.role}")

            return {
                "user": user.to_dict(),
                "access_token": access_token,
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error during login: {e}")
            raise ValueError("Authentication failed")

    @staticmethod
    def get_current_user(user_id: int) -> Dict[str, Any]:
        """
        Get current authenticated user's profile.

        Args:
            user_id (int): User ID from JWT token.

        Returns:
            Dict: User information. If worker role, includes worker profile.

        Raises:
            ValueError: If user not found.
        """
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"User not found: {user_id}")
            raise ValueError("User not found")

        result = user.to_dict()

        # If worker, include worker profile
        if user.role == "worker" and user.worker:
            result["worker"] = user.worker.to_dict()

        return result

    @staticmethod
    def logout(jti: str, user_id: int, expires_at: Any) -> None:
        """
        Logout user by adding JWT to blocklist.

        Args:
            jti (str): JWT ID (jti claim).
            user_id (int): User ID.
            expires_at (datetime): Token expiration datetime.
        """
        try:
            from app.db.models import TokenBlocklist

            blocklist_entry = TokenBlocklist(
                jti=jti, token_type="access", user_id=user_id, expires_at=expires_at
            )
            db.session.add(blocklist_entry)
            db.session.commit()
            logger.info(f"User logged out: user_id={user_id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error logging out user {user_id}: {e}")
            raise
