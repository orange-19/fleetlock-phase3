"""Trigger engine for disruption event simulation and processing."""

import logging
from typing import Dict, Any, List, Optional

from app.db.database import db
from app.db.models import Disruption
from app.db.repositories.worker_repo import WorkerRepository
from app.services.claim_service import ClaimService

logger = logging.getLogger(__name__)


class TriggerEngine:
    """Engine for simulating disruption events and triggering automated claims."""

    @staticmethod
    def simulate_disruption(
        zone: str,
        disruption_type: str,
        rainfall_mm: Optional[float] = None,
        temperature_celsius: Optional[float] = None,
        aqi_index: Optional[float] = None,
        wind_speed_kmh: Optional[float] = None,
        flood_alert: bool = False,
        platform_outage: bool = False,
    ) -> Dict[str, Any]:
        """
        Simulate a disruption event and trigger automated claim evaluation.

        Pipeline:
        1. Build features from disruption parameters
        2. Compute severity
        3. Find all workers in zone with active plans
        4. For each worker: run claim pipeline
        5. Store disruption record
        6. Return summary

        Args:
            zone (str): Service zone.
            disruption_type (str): Type of disruption.
            rainfall_mm (float | None): Rainfall in mm. Defaults to None.
            temperature_celsius (float | None): Temperature. Defaults to None.
            aqi_index (float | None): AQI index. Defaults to None.
            wind_speed_kmh (float | None): Wind speed. Defaults to None.
            flood_alert (bool): Flood alert flag. Defaults to False.
            platform_outage (bool): Platform outage flag. Defaults to False.

        Returns:
            Dict: Disruption summary with affected workers and created claims.
        """
        try:
            # 1. Build features from disruption parameters
            features = {
                "rainfall_mm": rainfall_mm or 0,
                "temperature_celsius": temperature_celsius or 25,
                "aqi_index": aqi_index or 100,
                "wind_speed_kmh": wind_speed_kmh or 0,
                "flood_alert_flag": 1 if flood_alert else 0,
                "platform_outage": platform_outage,
            }

            # 2. Compute severity (Simple rule-based fallback for MVP)
            # In production, use app.ml_models.disruption_model.DisruptionModel
            if rainfall_mm and rainfall_mm > 100:
                severity = "high"
                severity_multiplier = 1.0
            elif rainfall_mm and rainfall_mm > 50:
                severity = "medium"
                severity_multiplier = 0.75
            elif aqi_index and aqi_index > 300:
                severity = "high"
                severity_multiplier = 1.0
            elif flood_alert or platform_outage:
                severity = "medium"
                severity_multiplier = 0.75
            else:
                severity = "low"
                severity_multiplier = 0.5

            logger.info(
                f"Simulating disruption: zone={zone}, type={disruption_type}, "
                f"severity={severity}"
            )

            # 3. Find all workers in zone with active plans
            workers_in_zone = WorkerRepository.get_by_zone(zone)
            affected_count = len(workers_in_zone)

            logger.info(f"Found {affected_count} affected workers in {zone}")

            # 4. For each worker: run claim pipeline
            claims_created = 0
            claims_summary = []

            for worker in workers_in_zone:
                try:
                    # Run claim pipeline
                    claim_result = ClaimService.file_claim(worker.id, disruption_type)
                    claims_created += 1
                    claims_summary.append({
                        "worker_id": worker.id,
                        "claim_id": claim_result["claim"]["id"],
                        "status": claim_result["claim"]["status"],
                        "payout_amount": claim_result.get("payout_amount", 0),
                    })
                except Exception as e:
                    logger.warning(f"Could not auto-create claim for worker {worker.id}: {e}")
                    # Skip this worker and continue

            # 5. Store disruption record
            disruption = Disruption(
                zone=zone,
                disruption_type=disruption_type,
                severity=severity,
                severity_multiplier=severity_multiplier,
                rainfall_mm=rainfall_mm,
                temperature_celsius=temperature_celsius,
                aqi_index=aqi_index,
                wind_speed_kmh=wind_speed_kmh,
                flood_alert=flood_alert,
                platform_outage=platform_outage,
                affected_workers_count=affected_count,
                auto_claims_created=claims_created,
            )
            db.session.add(disruption)
            db.session.commit()

            logger.info(
                f"Disruption stored: id={disruption.id}, affected={affected_count}, "
                f"claims_created={claims_created}"
            )

            # 6. Return summary
            return {
                "disruption": disruption.to_dict(),
                "affected_workers": affected_count,
                "auto_claims_created": claims_created,
                "claims_summary": claims_summary,
            }

        except Exception as e:
            logger.error(f"Error simulating disruption: {e}")
            raise ValueError(f"Error simulating disruption: {e}")
