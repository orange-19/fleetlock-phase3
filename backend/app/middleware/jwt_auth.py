"""JWT authentication and role-based authorization middleware."""

import logging
from functools import wraps
from typing import Callable

from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt, verify_jwt_in_request

logger = logging.getLogger(__name__)


def role_required(required_role: str) -> Callable:
    """
    Decorator to enforce role-based access control on routes.

    Wraps flask-jwt-extended's jwt_required and adds role verification.
    Checks that the JWT token's 'role' claim matches the required role.

    Args:
        required_role (str): The required role (e.g., 'worker', 'admin').

    Returns:
        Callable: Decorator function that enforces role-based access.

    Example:
        @app.route("/admin/dashboard")
        @role_required("admin")
        def admin_dashboard():
            return jsonify({"message": "Admin only"})

    Raises:
        401 Unauthorized: If JWT is missing or invalid.
        403 Forbidden: If user's role does not match required_role.
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Verify JWT is present and valid
            verify_jwt_in_request()

            # Get JWT claims
            claims = get_jwt()
            user_role = claims.get("role")

            # Check role matches
            if user_role != required_role:
                logger.warning(
                    f"Access denied: user role={user_role}, required={required_role}"
                )
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"{required_role.capitalize()} access required",
                            "data": None,
                        }
                    ),
                    403,
                )

            return fn(*args, **kwargs)

        return wrapper

    return decorator
