"""KYC business logic service adapted from FleetLock KYC flow."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from app.db.database import db
from app.db.models import WorkerKYCAuditLog

logger = logging.getLogger(__name__)


class KYCService:
    """Service that orchestrates KYC initiate, verify, and status operations."""

    @staticmethod
    def _mask_aadhaar(aadhaar_number: str) -> str:
        if len(aadhaar_number) < 4:
            return "XXXX-XXXX-XXXX"
        return f"XXXX-XXXX-{aadhaar_number[-4:]}"

    @staticmethod
    def initiate_kyc(
        worker_id: int,
        aadhaar_number: str,
        consent: bool,
        client_ip: str,
        user_agent: str,
        kyc_client: Any,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Start KYC and persist consent + transaction metadata."""
        try:
            audit_log = WorkerKYCAuditLog.query.filter_by(worker_id=worker_id).first()

            # Do not downgrade an already verified worker back to OTP flow.
            if audit_log and audit_log.kyc_status == "verified":
                return True, {
                    "worker_id": worker_id,
                    "status": "verified",
                    "message": "KYC is already verified for this worker",
                    "transaction_id": audit_log.setu_transaction_id,
                    "aadhaar_masked": audit_log.aadhaar_masked,
                    "verification_timestamp": (
                        audit_log.verification_timestamp.isoformat()
                        if audit_log.verification_timestamp
                        else None
                    ),
                }

            setu_response = kyc_client.initiate_kyc(
                aadhaar_number=aadhaar_number,
                consent=consent,
            )

            if not audit_log:
                audit_log = WorkerKYCAuditLog(worker_id=worker_id)
                db.session.add(audit_log)

            audit_log.setu_transaction_id = str(setu_response.get("transaction_id") or "")
            audit_log.aadhaar_masked = KYCService._mask_aadhaar(aadhaar_number)
            audit_log.kyc_status = "otp_sent"
            audit_log.consent_given = consent
            audit_log.consent_timestamp = datetime.utcnow()
            audit_log.consent_ip_address = client_ip
            audit_log.consent_user_agent = user_agent
            audit_log.verification_error_code = None
            audit_log.verification_error_message = None
            audit_log.setu_response_json = json.dumps(setu_response)

            db.session.commit()

            return True, {
                "worker_id": worker_id,
                "transaction_id": setu_response.get("transaction_id", ""),
                "status": setu_response.get("status", "otp_sent"),
                "message": "OTP has been sent to your registered Aadhaar mobile number",
                "expires_in_seconds": setu_response.get("expires_in_seconds", 600),
                "masked_phone": setu_response.get("masked_phone"),
                "mock_otp": setu_response.get("mock_otp"),
            }
        except Exception as exc:
            db.session.rollback()
            logger.error("KYC initiation error for worker %s: %s", worker_id, exc)
            return False, {
                "error_code": "KYC_INITIATION_FAILED",
                "error_message": str(exc),
                "retry_available": True,
            }

    @staticmethod
    def verify_otp(
        worker_id: int,
        transaction_id: str,
        otp: str,
        kyc_client: Any,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Verify OTP and persist verified KYC profile fields."""
        try:
            setu_response = kyc_client.verify_otp(transaction_id=transaction_id, otp=otp)

            audit_log = WorkerKYCAuditLog.query.filter_by(
                worker_id=worker_id,
                setu_transaction_id=transaction_id,
            ).first()

            if not audit_log:
                audit_log = WorkerKYCAuditLog(
                    worker_id=worker_id,
                    setu_transaction_id=transaction_id,
                    aadhaar_masked="XXXX-XXXX-XXXX",
                    consent_given=True,
                )
                db.session.add(audit_log)

            audit_log.kyc_status = "verified"
            audit_log.full_name = str(setu_response.get("full_name") or "")
            audit_log.date_of_birth = str(setu_response.get("date_of_birth") or "")
            audit_log.gender = str(setu_response.get("gender") or "")
            audit_log.address = str(setu_response.get("address") or "")
            audit_log.aadhaar_masked = str(
                setu_response.get("aadhaar_masked") or audit_log.aadhaar_masked or ""
            )
            audit_log.setu_reference_id = str(
                setu_response.get("setu_reference_id")
                or setu_response.get("reference_id")
                or ""
            )
            audit_log.verification_timestamp = datetime.utcnow()
            audit_log.verification_error_code = None
            audit_log.verification_error_message = None
            audit_log.setu_response_json = json.dumps(setu_response.get("raw_response", {}))

            db.session.commit()

            return True, {
                "worker_id": worker_id,
                "kyc_status": "verified",
                "full_name": setu_response.get("full_name"),
                "date_of_birth": setu_response.get("date_of_birth"),
                "gender": setu_response.get("gender"),
                "address": setu_response.get("address"),
                "aadhaar_masked": setu_response.get("aadhaar_masked"),
                "setu_reference_id": (
                    setu_response.get("setu_reference_id")
                    or setu_response.get("reference_id")
                ),
                "verification_timestamp": datetime.utcnow().isoformat(),
                "next_step": "subscription_selection",
            }
        except Exception as exc:
            db.session.rollback()
            logger.error("OTP verification error for worker %s: %s", worker_id, exc)
            return False, {
                "error_code": "OTP_VERIFICATION_FAILED",
                "error_message": str(exc),
                "retry_available": True,
            }

    @staticmethod
    def get_kyc_audit_log(worker_id: int) -> Optional[WorkerKYCAuditLog]:
        """Get persisted KYC audit record for a worker."""
        return WorkerKYCAuditLog.query.filter_by(worker_id=worker_id).first()

    @staticmethod
    def is_worker_kyc_verified(worker_id: int) -> bool:
        """Return whether worker has a persisted verified KYC status."""
        audit_log = WorkerKYCAuditLog.query.filter_by(worker_id=worker_id).first()
        return bool(audit_log and audit_log.kyc_status == "verified")
