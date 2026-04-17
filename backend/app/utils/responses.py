"""Standardized response formatting utilities."""

from typing import Any, Dict, Optional, List

from flask import jsonify


def success_response(
    data: Any = None, message: str = "Success", status_code: int = 200
) -> tuple:
    """
    Create a standardized success response.

    Args:
        data (Any, optional): Response data payload. Defaults to None.
        message (str, optional): Success message. Defaults to "Success".
        status_code (int, optional): HTTP status code. Defaults to 200.

    Returns:
        tuple: (Flask JSON response, HTTP status code).

    Example:
        return success_response(
            data={"user_id": "123", "email": "user@example.com"},
            message="User created",
            status_code=201
        )
    """
    response: Dict[str, Any] = {
        "success": True,
        "message": message,
        "data": data,
    }
    return jsonify(response), status_code


def error_response(
    message: str, status_code: int = 400, errors: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    Create a standardized error response.

    Args:
        message (str): Error message describing what went wrong.
        status_code (int, optional): HTTP status code. Defaults to 400.
        errors (Dict | None): Optional error details dict. Defaults to None.

    Returns:
        tuple: (Flask JSON response, HTTP status code).

    Example:
        return error_response("Invalid email format", status_code=400)
        return error_response("User not found", status_code=404)
        return error_response("Validation failed", errors={"email": "Invalid format"})
    """
    response: Dict[str, Any] = {
        "success": False,
        "message": message,
        "data": None,
    }
    if errors:
        response["errors"] = errors
    return jsonify(response), status_code


def paginated_response(
    data: List[Dict[str, Any]],
    total: int,
    page: int,
    per_page: int,
    message: str = "Success",
) -> tuple:
    """
    Create a paginated response with metadata.

    Args:
        data (List[Dict]): List of items for this page.
        total (int): Total number of items across all pages.
        page (int): Current page number (1-indexed).
        per_page (int): Items per page.
        message (str, optional): Success message. Defaults to "Success".

    Returns:
        tuple: (Flask JSON response, HTTP status code).

    Example:
        return paginated_response(
            data=[{"id": 1, "name": "Worker 1"}],
            total=100,
            page=1,
            per_page=10,
            message="Workers retrieved"
        )
    """
    total_pages = (total + per_page - 1) // per_page  # Ceiling division

    response: Dict[str, Any] = {
        "success": True,
        "message": message,
        "data": data,
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        },
    }
    return jsonify(response), 200
