"""Admin routes blueprint."""

from flask import Blueprint, request

from app.db.models import Claim, Disruption, Subscription, Worker, WorkerKYCAuditLog
from app.db.repositories.claim_repo import ClaimRepository
from app.middleware.jwt_auth import role_required
from app.services.claim_service import ClaimService
from app.services.trigger_engine import TriggerEngine
from app.utils.responses import error_response, success_response

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard", methods=["GET"])
@role_required("admin")
def admin_dashboard() -> tuple:
    """Get admin dashboard with platform-wide stats."""
    try:
        claim_stats = ClaimRepository.get_stats()
        data = {
            "summary": {
                "total_workers": Worker.query.count(),
                "active_workers": Worker.query.filter_by(status="active").count(),
                "active_subscriptions": Subscription.query.filter_by(status="active").count(),
                "total_claims": claim_stats["total"],
                "fraud_cases": Claim.query.filter(Claim.fraud_score >= 0.8).count(),
                "total_payouts": claim_stats["total_payout"],
            },
            "recent_claims": [claim.to_dict() for claim in ClaimRepository.get_recent(limit=10)],
            "recent_disruptions": [
                disruption.to_dict()
                for disruption in Disruption.query.order_by(Disruption.created_at.desc()).limit(10).all()
            ],
            "ml_metrics": {
                "avg_fraud_score_30d": ClaimRepository.get_fraud_over_time(days=30),
            },
        }
        return success_response(data, "Admin dashboard retrieved", 200)
    except Exception:
        return error_response("Failed to fetch admin dashboard", status_code=500)


@admin_bp.route("/workers", methods=["GET"])
@role_required("admin")
def get_all_workers() -> tuple:
    """Get all workers with optional status/zone filters and pagination."""
    try:
        status = request.args.get("status")
        zone = request.args.get("zone")
        page = max(int(request.args.get("page", 1)), 1)
        limit = min(max(int(request.args.get("limit", 10)), 1), 100)

        query = Worker.query
        if status and status != "all":
            query = query.filter(Worker.status == status)
        if zone:
            query = query.filter(Worker.zone == zone)

        total = query.count()
        workers = (
            query.order_by(Worker.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        payload = []
        for worker in workers:
            worker_data = worker.to_dict()
            worker_data["user"] = worker.user.to_dict() if worker.user else None
            audit = worker.kyc_audit_log
            worker_data["kyc"] = {
                "status": audit.kyc_status if audit else "not_started",
                "is_verified": bool(audit and audit.kyc_status == "verified"),
                "verification_timestamp": (
                    audit.verification_timestamp.isoformat()
                    if audit and audit.verification_timestamp
                    else None
                ),
                "aadhaar_masked": audit.aadhaar_masked if audit else None,
                "setu_transaction_id": audit.setu_transaction_id if audit else None,
                "setu_reference_id": audit.setu_reference_id if audit else None,
                "error_code": audit.verification_error_code if audit else None,
                "error_message": audit.verification_error_message if audit else None,
            }
            payload.append(worker_data)

        return success_response(
            {
                "workers": payload,
                "total": total,
                "page": page,
                "limit": limit,
            },
            "Workers retrieved",
            200,
        )
    except Exception:
        return error_response("Failed to fetch workers", status_code=500)


@admin_bp.route("/kyc-status", methods=["GET"])
@role_required("admin")
def get_worker_kyc_status() -> tuple:
    """Get paginated worker KYC status list with optional status filtering."""
    try:
        status_filter = (request.args.get("status") or "all").strip().lower()
        page = max(int(request.args.get("page", 1)), 1)
        limit = min(max(int(request.args.get("limit", 10)), 1), 100)

        query = Worker.query
        if status_filter == "verified":
            query = query.join(WorkerKYCAuditLog).filter(WorkerKYCAuditLog.kyc_status == "verified")
        elif status_filter == "pending":
            query = query.join(WorkerKYCAuditLog).filter(
                WorkerKYCAuditLog.kyc_status.in_(["initiated", "otp_sent", "otp_verified"])
            )
        elif status_filter == "failed":
            query = query.join(WorkerKYCAuditLog).filter(
                WorkerKYCAuditLog.kyc_status.in_(["failed", "rejected"])
            )
        elif status_filter == "not_started":
            query = query.outerjoin(WorkerKYCAuditLog).filter(WorkerKYCAuditLog.id.is_(None))
        elif status_filter != "all":
            query = query.join(WorkerKYCAuditLog).filter(WorkerKYCAuditLog.kyc_status == status_filter)

        total = query.count()
        workers = (
            query.order_by(Worker.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        payload = []
        for worker in workers:
            audit = worker.kyc_audit_log
            worker_data = worker.to_dict()
            worker_data["user"] = worker.user.to_dict() if worker.user else None
            worker_data["kyc"] = {
                "status": audit.kyc_status if audit else "not_started",
                "is_verified": bool(audit and audit.kyc_status == "verified"),
                "verification_timestamp": (
                    audit.verification_timestamp.isoformat()
                    if audit and audit.verification_timestamp
                    else None
                ),
                "aadhaar_masked": audit.aadhaar_masked if audit else None,
                "setu_transaction_id": audit.setu_transaction_id if audit else None,
                "setu_reference_id": audit.setu_reference_id if audit else None,
                "error_code": audit.verification_error_code if audit else None,
                "error_message": audit.verification_error_message if audit else None,
            }
            payload.append(worker_data)

        total_workers = Worker.query.count()
        total_kyc_records = WorkerKYCAuditLog.query.count()
        verified_count = WorkerKYCAuditLog.query.filter_by(kyc_status="verified").count()
        pending_count = WorkerKYCAuditLog.query.filter(
            WorkerKYCAuditLog.kyc_status.in_(["initiated", "otp_sent", "otp_verified"])
        ).count()
        failed_count = WorkerKYCAuditLog.query.filter(
            WorkerKYCAuditLog.kyc_status.in_(["failed", "rejected"])
        ).count()

        return success_response(
            {
                "summary": {
                    "total_workers": total_workers,
                    "verified": verified_count,
                    "pending": pending_count,
                    "failed": failed_count,
                    "not_started": max(total_workers - total_kyc_records, 0),
                    "unverified": max(total_workers - verified_count, 0),
                },
                "status_filter": status_filter,
                "workers": payload,
                "total": total,
                "page": page,
                "limit": limit,
            },
            "Worker KYC status retrieved",
            200,
        )
    except Exception:
        return error_response("Failed to fetch worker KYC status", status_code=500)


@admin_bp.route("/ml-insights", methods=["GET"])
@role_required("admin")
def get_ml_insights() -> tuple:
    """Get ML-related operational insights from claim outcomes."""
    try:
        period = request.args.get("period", "30days")
        days = 30
        if period == "7days":
            days = 7
        elif period == "90days":
            days = 90
        elif period == "all":
            days = 3650

        insights = {
            "model": request.args.get("model", "fraud_detection"),
            "period": period,
            "claim_stats": ClaimRepository.get_stats(),
            "fraud_over_time": ClaimRepository.get_fraud_over_time(days=days),
            "high_risk_claims": [
                claim.to_dict()
                for claim in Claim.query.filter(Claim.fraud_score >= 0.8)
                .order_by(Claim.created_at.desc())
                .limit(20)
                .all()
            ],
        }
        return success_response(insights, "ML insights retrieved", 200)
    except Exception:
        return error_response("Failed to fetch ML insights", status_code=500)


@admin_bp.route("/simulate-disruption", methods=["POST"])
@role_required("admin")
def simulate_disruption() -> tuple:
    """Create a disruption event and auto-process impacted worker claims."""
    payload = request.get_json(silent=True) or {}
    zone = payload.get("zone")
    disruption_type = payload.get("disruption_type", "weather")

    if not zone:
        return error_response("'zone' is required", status_code=400)

    try:
        result = TriggerEngine.simulate_disruption(
            zone=zone,
            disruption_type=disruption_type,
            rainfall_mm=payload.get("rainfall_mm"),
            temperature_celsius=payload.get("temperature_celsius"),
            aqi_index=payload.get("aqi_index"),
            wind_speed_kmh=payload.get("wind_speed_kmh"),
            flood_alert=bool(payload.get("flood_alert", False)),
            platform_outage=bool(payload.get("platform_outage", False)),
        )
        return success_response(result, "Disruption simulated", 201)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:
        return error_response("Failed to simulate disruption", status_code=500)


@admin_bp.route("/claims/<claim_id>/action", methods=["POST"])
@role_required("admin")
def claim_action(claim_id: str) -> tuple:
    """Approve or reject a claim."""
    payload = request.get_json(silent=True) or {}
    action = payload.get("action")
    notes = payload.get("reason") or payload.get("notes")

    if not action:
        return error_response("'action' is required", status_code=400)

    try:
        claim_id_int = int(claim_id)
    except ValueError:
        return error_response("Invalid claim_id", status_code=400)

    try:
        result = ClaimService.admin_claim_action(claim_id=claim_id_int, action=action, notes=notes)
        return success_response(result, "Claim action completed", 200)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:
        return error_response("Failed to process claim action", status_code=500)
