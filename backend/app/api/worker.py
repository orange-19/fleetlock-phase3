"""Worker routes blueprint."""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.db.repositories.claim_repo import ClaimRepository
from app.db.repositories.worker_repo import WorkerRepository
from app.middleware.jwt_auth import role_required
from app.services.claim_service import ClaimService
from app.services.payout_service import PayoutService
from app.services.subscription_service import SubscriptionService
from app.utils.responses import error_response, success_response

worker_bp = Blueprint("worker", __name__)


def _get_worker_from_token():
    """Resolve worker profile from authenticated user token."""
    user_id = int(get_jwt_identity())
    worker = WorkerRepository.get_by_user_id(user_id)
    if not worker:
        raise ValueError("Worker profile not found for current user")
    return worker


@worker_bp.route("/dashboard", methods=["GET"])
@role_required("worker")
def get_dashboard() -> tuple:
    """Get worker dashboard summary."""
    try:
        worker = _get_worker_from_token()
        subscription = SubscriptionService.get_active_subscription(worker.id)
        recent_claims = ClaimService.get_worker_claims(worker.id, limit=10)
        claim_stats = ClaimRepository.get_worker_stats(worker.id)
        earnings = PayoutService.get_worker_earnings(worker.id, days=30)

        data = {
            "worker": WorkerRepository.get_with_user_info(worker.id),
            "subscription": subscription.to_dict() if subscription else None,
            "stats": {
                **claim_stats,
                "claim_accuracy_rate": worker.claim_accuracy_rate,
                "renewal_streak": worker.renewal_streak,
                "total_payouts": worker.total_payouts,
            },
            "earnings": earnings,
            "recent_claims": recent_claims,
        }
        return success_response(data, "Dashboard data retrieved", 200)
    except ValueError as exc:
        return error_response(str(exc), status_code=404)
    except Exception:
        return error_response("Failed to fetch dashboard", status_code=500)


@worker_bp.route("/subscribe", methods=["POST"])
@role_required("worker")
def subscribe_plan() -> tuple:
    """Subscribe current worker to a plan."""
    payload = request.get_json(silent=True) or {}
    plan_key = payload.get("plan")
    if not plan_key:
        return error_response("'plan' is required", status_code=400)

    try:
        worker = _get_worker_from_token()
        subscription = SubscriptionService.subscribe(worker.id, plan_key)
        return success_response(subscription, "Subscription created", 201)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:
        return error_response("Failed to create subscription", status_code=500)


@worker_bp.route("/claim", methods=["POST"])
@role_required("worker")
def file_claim() -> tuple:
    """File a claim for the authenticated worker."""
    payload = request.get_json(silent=True) or {}
    disruption_type = payload.get("disruption_type", "weather")
    allowed_types = {"weather", "platform_outage", "civic_event", "flood", "heat", "aqi"}
    if disruption_type not in allowed_types:
        return error_response("Invalid disruption_type", status_code=400)

    try:
        worker = _get_worker_from_token()
        result = ClaimService.file_claim(
            worker_id=worker.id,
            disruption_type=disruption_type,
            zone_id=payload.get("zone_id", "bengaluru"),
            telematics=payload.get("telematics"),
            gps_trace=payload.get("gps_trace"),
            claimed_location=tuple(payload["claimed_location"]) if payload.get("claimed_location") else None,
            actual_location=tuple(payload["actual_location"]) if payload.get("actual_location") else None,
        )
        return success_response(result, "Claim filed successfully", 201)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:
        return error_response("Failed to file claim", status_code=500)
