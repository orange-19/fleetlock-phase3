"""Actuator-style health endpoints for runtime monitoring."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from flask import Blueprint, current_app
from sqlalchemy import text

# Support direct execution (e.g., `python app/api/health.py`) by ensuring the
# project root is importable as a package.
if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from app.db.database import db

health_bp = Blueprint("health", __name__)


def _iso_now() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _uptime_seconds() -> int:
    """Return process uptime in seconds based on app startup timestamp."""
    started_at = current_app.config.get("APP_STARTED_AT")
    if not started_at:
        return 0
    return max(int((datetime.now(timezone.utc) - started_at).total_seconds()), 0)


def _api_groups_health() -> Dict[str, Dict[str, object]]:
    """Build API route availability summary by endpoint group."""
    route_rules: List[str] = [rule.rule for rule in current_app.url_map.iter_rules()]

    groups = {
        "auth": "/api/auth/",
        "worker": "/api/worker/",
        "admin": "/api/admin/",
        "weather": "/api/weather/",
        "plans": "/api/plans",
    }

    result: Dict[str, Dict[str, object]] = {}
    for group, prefix in groups.items():
        matching = [rule for rule in route_rules if rule.startswith(prefix)]
        result[group] = {
            "status": "UP" if matching else "DOWN",
            "route_count": len(matching),
        }
    return result


def _database_health() -> Dict[str, str]:
    """Run a lightweight DB ping and return status details."""
    try:
        db.session.execute(text("SELECT 1"))
        db.session.rollback()
        return {"status": "UP"}
    except Exception as exc:
        db.session.rollback()
        return {"status": "DOWN", "error": str(exc)}


@health_bp.route("/health", methods=["GET"])
def health() -> tuple:
    """Actuator-style aggregate health endpoint."""
    db_health = _database_health()
    apis_health = _api_groups_health()

    apis_up = all(group_info["status"] == "UP" for group_info in apis_health.values())
    overall_up = db_health["status"] == "UP" and apis_up

    payload = {
        "status": "UP" if overall_up else "DOWN",
        "timestamp": _iso_now(),
        "uptime_seconds": _uptime_seconds(),
        "components": {
            "database": db_health,
            "apis": {
                "status": "UP" if apis_up else "DOWN",
                "groups": apis_health,
            },
        },
    }
    return payload, 200 if overall_up else 503


@health_bp.route("/health/liveness", methods=["GET"])
def liveness() -> tuple:
    """Liveness probe: process is running if this route responds."""
    return {
        "status": "UP",
        "timestamp": _iso_now(),
        "uptime_seconds": _uptime_seconds(),
    }, 200


@health_bp.route("/health/readiness", methods=["GET"])
def readiness() -> tuple:
    """Readiness probe: app is ready when DB is reachable and APIs are mounted."""
    db_health = _database_health()
    apis_health = _api_groups_health()

    apis_up = all(group_info["status"] == "UP" for group_info in apis_health.values())
    ready = db_health["status"] == "UP" and apis_up

    return {
        "status": "UP" if ready else "DOWN",
        "timestamp": _iso_now(),
        "components": {
            "database": db_health,
            "apis": {
                "status": "UP" if apis_up else "DOWN",
                "groups": apis_health,
            },
        },
    }, 200 if ready else 503
