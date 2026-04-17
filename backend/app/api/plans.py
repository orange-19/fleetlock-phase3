"""Plans-related routes blueprint."""

from flask import Blueprint, request

from app.services.payout_service import PayoutService
from app.services.subscription_service import SubscriptionService
from app.utils.responses import error_response, success_response

plans_bp = Blueprint("plans", __name__)


@plans_bp.route("/plans", methods=["GET"])
def get_all_plans() -> tuple:
    """Return all configured insurance plans."""
    try:
        plans = SubscriptionService.get_all_plans()
        data = [{"id": plan_id, **plan_config} for plan_id, plan_config in plans.items()]
        return success_response(data, "Plans retrieved", 200)
    except Exception:
        return error_response("Failed to fetch plans", status_code=500)


@plans_bp.route("/payout-calculator", methods=["GET"])
def payout_calculator() -> tuple:
    """Estimate payout for a hypothetical claim."""
    plan = request.args.get("plan")
    severity = request.args.get("severity", "medium").lower()
    daily_income_raw = request.args.get("daily_income")

    if not plan or daily_income_raw is None:
        return error_response("'plan' and 'daily_income' query params are required", status_code=400)

    try:
        daily_income = float(daily_income_raw)
    except ValueError:
        return error_response("daily_income must be numeric", status_code=400)

    try:
        estimate = PayoutService.calculate_estimated_payout(
            plan_key=plan,
            daily_income=daily_income,
            severity=severity,
        )
        return success_response(estimate, "Payout calculated", 200)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:
        return error_response("Failed to calculate payout", status_code=500)
