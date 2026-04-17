"""Authentication routes blueprint."""

from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from app.services.auth_service import AuthService
from app.utils.responses import error_response, success_response

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register() -> tuple:
    """Register a new user and return an access token."""
    payload = request.get_json(silent=True) or {}

    required_fields = ["email", "password", "name"]
    missing = [field for field in required_fields if not payload.get(field)]
    if missing:
        return error_response(
            f"Missing required fields: {', '.join(missing)}",
            status_code=400,
        )

    try:
        result = AuthService.register(
            email=payload["email"],
            password=payload["password"],
            name=payload["name"],
            role=payload.get("role", "worker"),
            phone=payload.get("phone"),
            city=payload.get("city"),
            platform=payload.get("platform"),
        )
        return success_response(result, "User registered successfully", 201)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:
        return error_response("Registration failed", status_code=500)


@auth_bp.route("/login", methods=["POST"])
def login() -> tuple:
    """Authenticate user and return JWT token."""
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    password = payload.get("password")

    if not email or not password:
        return error_response("Email and password are required", status_code=400)

    try:
        result = AuthService.login(email=email, password=password)
        return success_response(result, "Login successful", 200)
    except ValueError as exc:
        return error_response(str(exc), status_code=401)
    except Exception:
        return error_response("Login failed", status_code=500)


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user() -> tuple:
    """Return authenticated user profile."""
    try:
        user_id = int(get_jwt_identity())
        user = AuthService.get_current_user(user_id)
        return success_response(user, "User profile retrieved", 200)
    except ValueError as exc:
        return error_response(str(exc), status_code=404)
    except Exception:
        return error_response("Failed to fetch user profile", status_code=500)


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout() -> tuple:
    """Invalidate JWT by putting it in blocklist."""
    try:
        claims = get_jwt()
        jti = claims.get("jti")
        exp = claims.get("exp")
        if not jti or not exp:
            return error_response("Invalid token payload", status_code=400)

        user_id = int(get_jwt_identity())
        expires_at = datetime.utcfromtimestamp(exp)
        AuthService.logout(jti=jti, user_id=user_id, expires_at=expires_at)
        return success_response(None, "Logout successful", 200)
    except Exception:
        return error_response("Logout failed", status_code=500)
