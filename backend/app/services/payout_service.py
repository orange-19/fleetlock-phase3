"""Payout service for earnings and payout retrieval."""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.db.repositories.payout_repo import PayoutRepository
from app.db.repositories.worker_repo import WorkerRepository

logger = logging.getLogger(__name__)


class PayoutService:
    """Service for payout-related queries and calculations."""

    @staticmethod
    def get_worker_payouts(worker_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get payouts for a worker.

        Args:
            worker_id (int): Worker ID.
            limit (int): Maximum payouts to return. Defaults to 10.

        Returns:
            List[Dict]: List of serialized payout dicts.
        """
        payouts = PayoutRepository.get_by_worker(worker_id, limit=limit)
        return [payout.to_dict() for payout in payouts]

    @staticmethod
    def get_worker_earnings(worker_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get worker earnings over a period.

        Args:
            worker_id (int): Worker ID.
            days (int): Number of days to look back. Defaults to 30.

        Returns:
            Dict: Earnings summary with daily breakdown, total, average.
        """
        from app.db.models import Payout
        from sqlalchemy import func

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Get all payouts in the period
            query_result = (
                Payout.query.filter(
                    Payout.worker_id == worker_id,
                    Payout.created_at >= cutoff_date,
                    Payout.status == "completed",
                )
                .all()
            )

            total = sum(payout.amount for payout in query_result)
            count = len(query_result)
            average = total / count if count > 0 else 0.0

            # Group by date
            daily_earnings = {}
            for payout in query_result:
                date_key = payout.created_at.date().isoformat()
                if date_key not in daily_earnings:
                    daily_earnings[date_key] = 0.0
                daily_earnings[date_key] += payout.amount

            return {
                "worker_id": worker_id,
                "period_days": days,
                "total_earnings": round(total, 2),
                "average_daily_earnings": round(average, 2),
                "payout_count": count,
                "daily_earnings": daily_earnings,
            }

        except Exception as e:
            logger.error(f"Error getting worker earnings: {e}")
            return {
                "worker_id": worker_id,
                "period_days": days,
                "total_earnings": 0.0,
                "average_daily_earnings": 0.0,
                "payout_count": 0,
                "daily_earnings": {},
            }

    @staticmethod
    def calculate_estimated_payout(
        plan_key: str, daily_income: float, severity: str
    ) -> Dict[str, Any]:
        """
        Calculate estimated payout for a hypothetical claim.

        For payout calculator endpoint frontend.

        Args:
            plan_key (str): Insurance plan key (level-1, level-2, level-3).
            daily_income (float): Daily income amount.
            severity (str): Severity level (low, medium, high).

        Returns:
            Dict: Estimated payout breakdown.

        Raises:
            ValueError: If plan_key invalid or severity invalid.
        """
        try:
            from flask import current_app

            # Get plan from config
            plans = current_app.config.get("INSURANCE_PLANS", {})
            if plan_key not in plans:
                raise ValueError(f"Plan {plan_key} not found")

            plan = plans[plan_key]

            # Get severity multiplier
            multipliers = {"low": 1.0, "medium": 1.5, "high": 2.0}
            if severity not in multipliers:
                raise ValueError(f"Invalid severity: {severity}")

            severity_multiplier = multipliers[severity]

            # Calculate estimated payout
            base = daily_income
            coverage_rate = plan["coverage_rate"]
            loyalty_bonus = 1.0  # No loyalty for estimate

            estimated_payout = (
                base * coverage_rate * severity_multiplier * loyalty_bonus
            )
            estimated_payout = round(estimated_payout, 2)

            return {
                "plan": plan_key,
                "plan_name": plan.get("name", plan_key),
                "daily_income": daily_income,
                "coverage_rate": coverage_rate,
                "coverage_percentage": int(coverage_rate * 100),
                "severity": severity,
                "severity_multiplier": severity_multiplier,
                "base_payout": round(base * coverage_rate, 2),
                "estimated_payout": estimated_payout,
                "breakdown": {
                    "daily_income": daily_income,
                    "coverage_applied": round(daily_income * coverage_rate, 2),
                    "severity_multiplier": severity_multiplier,
                    "loyalty_bonus": 1.0,
                    "final_payout": estimated_payout,
                },
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error calculating estimated payout: {e}")
            raise ValueError("Error calculating payout")
