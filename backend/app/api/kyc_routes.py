"""KYC routes adapted from FleetLock KYC API for Flask."""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.db.repositories.worker_repo import WorkerRepository
from app.integrations.mock_kyc_client import MockKYCClient, _verify_aadhaar_checksum
from app.middleware.jwt_auth import role_required
from app.services.kyc_service import KYCService
from app.utils.responses import error_response, success_response

kyc_bp = Blueprint("kyc", __name__)

# Keep one in-memory mock client so transaction_id -> OTP state survives requests.
_mock_kyc_client = MockKYCClient()


def _get_worker_from_token():
    """Resolve current worker from JWT identity claim."""
    user_id = int(get_jwt_identity())
    worker = WorkerRepository.get_by_user_id(user_id)
    if not worker:
        raise ValueError("Worker profile not found for current user")
    return worker


def _client_ip() -> str:
    """Best-effort client IP extraction from reverse-proxy aware headers."""
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


@kyc_bp.route("/kyc-initiate", methods=["POST"])
@role_required("worker")
def initiate_kyc() -> tuple:
    """Step 1: initiate Aadhaar KYC and send OTP (mock mode)."""
    payload = request.get_json(silent=True) or {}
    aadhaar_number = str(payload.get("aadhaar_number") or "").strip()
    consent = bool(payload.get("consent", False))

    if not aadhaar_number:
        return error_response("'aadhaar_number' is required", status_code=400)
    if not aadhaar_number.isdigit() or len(aadhaar_number) != 12:
        return error_response("'aadhaar_number' must be a 12-digit number", status_code=400)
    if not _verify_aadhaar_checksum(aadhaar_number):
        return error_response("Invalid Aadhaar number (checksum failed)", status_code=400)
    if not consent:
        return error_response("Consent is mandatory for KYC", status_code=400)

    try:
        worker = _get_worker_from_token()
        success, response = KYCService.initiate_kyc(
            worker_id=worker.id,
            aadhaar_number=aadhaar_number,
            consent=consent,
            client_ip=_client_ip(),
            user_agent=request.headers.get("User-Agent", ""),
            kyc_client=_mock_kyc_client,
        )
        if not success:
            return error_response(
                response.get("error_message", "KYC initiation failed"),
                status_code=400,
                errors=response,
            )
        return success_response(response, "KYC initiated", 200)
    except ValueError as exc:
        return error_response(str(exc), status_code=404)
    except Exception:
        return error_response("Failed to initiate KYC", status_code=500)


@kyc_bp.route("/kyc-verify", methods=["POST"])
@role_required("worker")
def verify_kyc_otp() -> tuple:
    """Step 2: verify OTP and persist verified KYC profile."""
    payload = request.get_json(silent=True) or {}
    transaction_id = str(payload.get("transaction_id") or "").strip()
    otp = str(payload.get("otp") or "").strip()

    if not transaction_id:
        return error_response("'transaction_id' is required", status_code=400)
    if not otp:
        return error_response("'otp' is required", status_code=400)
    if not otp.isdigit() or len(otp) != 6:
        return error_response("'otp' must be a 6-digit number", status_code=400)

    try:
        worker = _get_worker_from_token()
        success, response = KYCService.verify_otp(
            worker_id=worker.id,
            transaction_id=transaction_id,
            otp=otp,
            kyc_client=_mock_kyc_client,
        )
        if not success:
            return error_response(
                response.get("error_message", "OTP verification failed"),
                status_code=400,
                errors=response,
            )
        return success_response(response, "KYC verified", 200)
    except ValueError as exc:
        return error_response(str(exc), status_code=404)
    except Exception:
        return error_response("Failed to verify KYC OTP", status_code=500)


@kyc_bp.route("/kyc-status", methods=["GET"])
@role_required("worker")
def get_kyc_status() -> tuple:
    """Get KYC status and audit details for the authenticated worker."""
    try:
        worker = _get_worker_from_token()
        audit_log = KYCService.get_kyc_audit_log(worker.id)
        if not audit_log:
            return error_response("No KYC record found for current worker", status_code=404)

        return success_response(audit_log.to_dict(include_pii=True), "KYC status retrieved", 200)
    except ValueError as exc:
        return error_response(str(exc), status_code=404)
    except Exception:
        return error_response("Failed to fetch KYC status", status_code=500)
