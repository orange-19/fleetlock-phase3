"""Claim filing and processing service."""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.db.database import db
from app.db.repositories.claim_repo import ClaimRepository
from app.db.repositories.payout_repo import PayoutRepository
from app.db.repositories.worker_repo import WorkerRepository
from app.services.kyc_service import KYCService
from app.ml_models.disruption_model import DisruptionModel
from app.ml_models.fraud_detection import GPSFraudModel
from app.services.subscription_service import SubscriptionService
from integrations.weather_client import WeatherClient

logger = logging.getLogger(__name__)


class ClaimService:
    """Service for claim filing and processing."""

    _fraud_model: Optional[GPSFraudModel] = None
    _disruption_model: Optional[DisruptionModel] = None
    _fraud_model_checked = False
    _disruption_model_checked = False

    @staticmethod
    def _saved_models_dir() -> Path:
        return Path(__file__).resolve().parents[1] / "ml_models" / "saved_models"

    @classmethod
    def _get_fraud_model(cls) -> Optional[GPSFraudModel]:
        if cls._fraud_model is not None:
            return cls._fraud_model
        if cls._fraud_model_checked:
            return None
        cls._fraud_model_checked = True

        candidate_paths = [
            cls._saved_models_dir() / "fraud_model.joblib",
            cls._saved_models_dir() / "fraud_model.pkl",
        ]
        for path in candidate_paths:
            if not path.exists():
                continue
            try:
                loaded_model = GPSFraudModel.load(str(path))
                feature_count = getattr(loaded_model.model, "n_features_in_", None)
                if feature_count is not None and int(feature_count) != 10:
                    logger.warning(
                        "Skipping fraud model %s due to feature mismatch (%s)",
                        path,
                        feature_count,
                    )
                    continue
                cls._fraud_model = loaded_model
                logger.info("Loaded fraud model from %s", path)
                return cls._fraud_model
            except Exception as exc:
                logger.warning("Could not load fraud model from %s: %s", path, exc)
        return None

    @classmethod
    def _get_disruption_model(cls) -> Optional[DisruptionModel]:
        if cls._disruption_model is not None:
            return cls._disruption_model
        if cls._disruption_model_checked:
            return None
        cls._disruption_model_checked = True

        candidate_paths = [
            cls._saved_models_dir() / "disruption_model_joblib.pkl",
            cls._saved_models_dir() / "disruption_model.pkl",
            cls._saved_models_dir() / "disruption_model_pickle.pkl",
            cls._saved_models_dir() / "model_from_excel.pkl",
        ]
        for path in candidate_paths:
            if not path.exists():
                continue
            try:
                loaded_model = DisruptionModel.load(str(path))
                feature_count = getattr(loaded_model.model, "n_features_in_", None)
                if feature_count is not None and int(feature_count) != 5:
                    logger.warning(
                        "Skipping disruption model %s due to feature mismatch (%s)",
                        path,
                        feature_count,
                    )
                    continue
                cls._disruption_model = loaded_model
                logger.info("Loaded disruption model from %s", path)
                return cls._disruption_model
            except Exception as exc:
                logger.warning("Could not load disruption model from %s: %s", path, exc)
        return None

    @staticmethod
    def _run_async(coro: Any) -> Any:
        """Run async coroutine from sync service code safely."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()

        return asyncio.run(coro)

    @staticmethod
    def file_claim(
        worker_id: int,
        disruption_type: str,
        zone_id: str = "bengaluru",
        telematics: Optional[Dict[str, Any]] = None,
        gps_trace: Optional[list] = None,
        claimed_location: Optional[tuple] = None,
        actual_location: Optional[tuple] = None,
    ) -> Dict[str, Any]:
        """File a new insurance claim and run the ML scoring pipeline."""
        try:
            subscription = SubscriptionService.get_active_subscription(worker_id)
            if not subscription:
                raise ValueError("No active subscription found. Please subscribe to a plan.")

            worker = WorkerRepository.get_by_id(worker_id)
            if not worker:
                raise ValueError("Worker not found")

            if not KYCService.is_worker_kyc_verified(worker_id):
                raise ValueError("KYC verification is required before filing a claim.")

            try:
                weather_client = WeatherClient()
                weather_data = ClaimService._run_async(
                    weather_client.get_weather_for_zone(zone_id)
                )
            except Exception as exc:
                logger.warning("Weather fetch failed for zone %s: %s", zone_id, exc)
                weather_data = {
                    "zone_id": zone_id,
                    "rainfall_mm": 0.0,
                    "temperature_celsius": 25.0,
                    "wind_speed_kmh": 10.0,
                    "aqi_index": 100.0,
                    "flood_alert_flag": 0,
                    "timestamp": "",
                }

            fraud_model = ClaimService._get_fraud_model()
            claimed_loc = claimed_location or (12.9716, 77.5946)
            actual_loc = actual_location or (12.9719, 77.5949)
            gps_trace_list = gps_trace or [
                (12.9716, 77.5946),
                (12.9717, 77.5947),
                (12.9718, 77.5948),
            ]
            telematics_dict = telematics or {
                "gps_drift_meters": 50.0,
                "speed_jump_kmh": 5.0,
                "route_deviation_pct": 2.0,
                "zone_entry_lag_mins": 3,
                "device_swap_count": 0,
                "duplicate_trip_flag": 0,
            }

            try:
                if fraud_model is None:
                    fraud_score = 0.3
                    fraud_tier = "auto_approve"
                else:
                    fraud_features = fraud_model.build_features(
                        telematics_dict, gps_trace_list, claimed_loc, actual_loc
                    )
                    fraud_result = fraud_model.predict(fraud_features)
                    fraud_score = float(fraud_result.get("confidence", 0.5))
                    fraud_code = int(fraud_result.get("fraud_code", 0))
                    fraud_tier = "auto_reject" if fraud_code == 1 else "auto_approve"
            except Exception as exc:
                logger.warning("Fraud model error: %s", exc)
                fraud_score = 0.3
                fraud_tier = "auto_approve"

            try:
                disruption_model = ClaimService._get_disruption_model()
                severity_map = {
                    "low": 0.5,
                    "medium": 0.75,
                    "high": 1.0,
                    "critical": 1.25,
                }
                if disruption_model is None:
                    severity = "low"
                    severity_multiplier = 1.0
                else:
                    severity_result = disruption_model.predict(weather_data)
                    severity = severity_result.get("severity_label", "LOW").lower()
                    severity_multiplier = severity_map.get(severity, 1.0)
            except Exception as exc:
                logger.warning("Disruption model error: %s", exc)
                severity = "low"
                severity_multiplier = 1.0

            if fraud_tier == "auto_reject":
                payout_amount = 0.0
            else:
                loyalty_bonus = 1.0
                if worker.tenure_days > 30:
                    loyalty_bonus += 0.1
                if worker.tenure_days > 90:
                    loyalty_bonus += 0.1
                if worker.renewal_streak > 2:
                    loyalty_bonus += 0.05
                if worker.claim_accuracy_rate > 0.95:
                    loyalty_bonus += 0.05

                payout_amount = round(
                    worker.daily_income_avg
                    * subscription.coverage_rate
                    * severity_multiplier
                    * loyalty_bonus,
                    2,
                )

            claim_status = {
                "auto_approve": "approved",
                "flag_review": "flagged",
                "auto_reject": "rejected",
            }.get(fraud_tier, "flagged")

            claim = ClaimRepository.create(
                worker_id=worker_id,
                disruption_type=disruption_type,
                status=claim_status,
                fraud_score=fraud_score,
                fraud_tier=fraud_tier,
                severity=severity,
                severity_multiplier=severity_multiplier,
                payout_amount=payout_amount,
            )

            payout = None
            if claim_status == "approved":
                payout = PayoutRepository.create(
                    worker_id=worker_id,
                    claim_id=claim.id,
                    amount=payout_amount,
                )
                WorkerRepository.update_after_claim(
                    worker_id, payout_amount, claim_approved=True
                )
            else:
                WorkerRepository.update_after_claim(worker_id, 0.0, claim_approved=False)

            db.session.commit()

            return {
                "claim": claim.to_dict(),
                "payout": payout.to_dict() if payout else None,
                "payout_amount": payout_amount,
                "fraud_score": fraud_score,
                "fraud_tier": fraud_tier,
                "severity": severity,
                "severity_multiplier": severity_multiplier,
                "weather_data": weather_data,
                "message": f"Claim {claim_status} by fraud system",
            }

        except ValueError:
            db.session.rollback()
            raise
        except Exception as exc:
            db.session.rollback()
            logger.error("Error filing claim for worker %s: %s", worker_id, exc)
            raise ValueError("Error processing claim. Please try again.") from exc

    @staticmethod
    def get_worker_claims(worker_id: int, limit: int = 20) -> list:
        """Get claims for a worker."""
        claims = ClaimRepository.get_by_worker(worker_id, limit=limit)
        return [claim.to_dict() for claim in claims]

    @staticmethod
    def admin_claim_action(
        claim_id: int, action: str, notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve or reject a claim as admin."""
        try:
            claim = ClaimRepository.get_by_id(claim_id)
            if not claim:
                raise ValueError("Claim not found")

            action = action.lower().strip()
            if action == "approve":
                claim = ClaimRepository.update_status(claim_id, "approved", notes=notes)
                payout = PayoutRepository.get_by_claim(claim_id)
                if not payout:
                    payout = PayoutRepository.create(
                        worker_id=claim.worker_id,
                        claim_id=claim_id,
                        amount=claim.payout_amount,
                    )

                WorkerRepository.update_after_claim(
                    claim.worker_id, claim.payout_amount, claim_approved=True
                )
                db.session.commit()
                return {
                    "claim": claim.to_dict(),
                    "payout": payout.to_dict(),
                    "message": "Claim approved",
                }

            if action == "reject":
                claim = ClaimRepository.update_status(claim_id, "rejected", notes=notes)
                WorkerRepository.update_after_claim(claim.worker_id, 0.0, claim_approved=False)
                db.session.commit()
                return {
                    "claim": claim.to_dict(),
                    "message": "Claim rejected",
                }

            raise ValueError("Invalid action: must be 'approve' or 'reject'.")

        except ValueError:
            db.session.rollback()
            raise
        except Exception as exc:
            db.session.rollback()
            logger.error("Error processing admin action on claim %s: %s", claim_id, exc)
            raise ValueError("Error processing claim action") from exc
