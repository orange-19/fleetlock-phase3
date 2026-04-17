"""Subscription service for insurance plan management."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.db.database import db
from app.db.models import Subscription
from app.db.repositories.worker_repo import WorkerRepository

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for subscription/insurance plan operations."""

    @staticmethod
    def subscribe(worker_id: int, plan_key: str) -> Dict[str, Any]:
        """
        Subscribe worker to an insurance plan.

        Expires any current active subscription for this worker and creates a new one.

        Args:
            worker_id (int): Worker ID.
            plan_key (str): Plan key (level-1, level-2, level-3).

        Returns:
            Dict: Serialized subscription data.

        Raises:
            ValueError: If plan_key invalid or worker not found.
        """
        try:
            from flask import current_app
            from app.db.repositories.worker_repo import WorkerRepository

            # Validate plan exists
            plans = current_app.config["INSURANCE_PLANS"]
            if plan_key not in plans:
                logger.warning(f"Invalid plan key: {plan_key}")
                raise ValueError(f"Plan {plan_key} not found")

            # Get plan config
            plan_config = plans[plan_key]

            # Get worker
            worker = WorkerRepository.get_by_id(worker_id)
            if not worker:
                logger.warning(f"Worker not found: {worker_id}")
                raise ValueError(f"Worker {worker_id} not found")

            # Expire current active subscription
            current_sub = Subscription.query.filter_by(
                worker_id=worker_id, status="active"
            ).first()
            if current_sub:
                current_sub.status = "expired"
                db.session.commit()
                logger.info(f"Expired current subscription: {current_sub.id}")

            # Create new subscription (15 days validity)
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=15)

            subscription = Subscription(
                worker_id=worker_id,
                plan=plan_key,
                status="active",
                premium_weekly=plan_config["premium_weekly"],
                coverage_rate=plan_config["coverage_rate"],
                max_covered_days=plan_config["max_covered_days"],
                start_date=start_date,
                end_date=end_date,
            )
            db.session.add(subscription)
            db.session.flush()

            # Update worker's active plan and increment renewal streak
            WorkerRepository.update(
                worker_id, active_plan=plan_key
            )
            WorkerRepository.increment_renewal_streak(worker_id)

            db.session.commit()
            logger.info(
                f"Subscription created: id={subscription.id}, worker_id={worker_id}, "
                f"plan={plan_key}"
            )

            return subscription.to_dict()

        except ValueError:
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error subscribing worker {worker_id}: {e}")
            raise

    @staticmethod
    def get_active_subscription(worker_id: int) -> Optional[Subscription]:
        """
        Get active subscription for worker.

        Returns subscription where status="active" and end_date > now.

        Args:
            worker_id (int): Worker ID.

        Returns:
            Subscription | None: Active subscription if found.
        """
        subscription = Subscription.query.filter_by(
            worker_id=worker_id, status="active"
        ).filter(Subscription.end_date > datetime.utcnow()).first()

        return subscription

    @staticmethod
    def get_all_plans() -> Dict[str, Dict[str, Any]]:
        """
        Get all available insurance plans from config.

        Returns:
            Dict: Insurance plans configuration.
        """
        from flask import current_app

        return current_app.config["INSURANCE_PLANS"]

    @staticmethod
    def check_and_expire_subscriptions() -> int:
        """
        Check and expire subscriptions that have reached end_date.

        For scheduler use (e.g., periodic task).

        Returns:
            int: Number of subscriptions expired.
        """
        try:
            now = datetime.utcnow()
            expired_subs = Subscription.query.filter_by(
                status="active"
            ).filter(Subscription.end_date <= now).all()

            count = 0
            for sub in expired_subs:
                sub.status = "expired"
                # Also clear active_plan from worker
                WorkerRepository.update(sub.worker_id, active_plan=None)
                count += 1

            db.session.commit()
            logger.info(f"Expired {count} subscriptions")
            return count

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error expiring subscriptions: {e}")
            return 0
