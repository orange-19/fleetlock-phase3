"""Worker repository for database operations on workers."""

import logging
from typing import Dict, Any, List, Optional

from sqlalchemy.exc import IntegrityError

from app.db.database import db
from app.db.models import Worker, User

logger = logging.getLogger(__name__)


class WorkerRepository:
    """Repository for Worker database operations."""

    @staticmethod
    def create(user_id: int, platform: str, city: str, zone: str = "zone-central") -> Worker:
        """
        Create a new worker record.

        Args:
            user_id (int): Foreign key to User.
            platform (str): Delivery/gig platform (swiggy, zomato, uber, etc.).
            city (str): Worker's city.
            zone (str): Service zone. Defaults to "zone-central".

        Returns:
            Worker: Created worker instance.

        Raises:
            ValueError: If worker already exists for user_id or database error.
        """
        try:
            worker = Worker(user_id=user_id, platform=platform, city=city, zone=zone)
            db.session.add(worker)
            db.session.flush()  # Flush to get worker.id without committing
            logger.info(f"Worker created: user_id={user_id}, platform={platform}")
            return worker
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error creating worker: {e}")
            raise ValueError(f"Worker already exists for user_id {user_id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating worker: {e}")
            raise

    @staticmethod
    def get_by_user_id(user_id: int) -> Optional[Worker]:
        """
        Get worker by user ID.

        Args:
            user_id (int): User ID.

        Returns:
            Worker | None: Worker if found, None otherwise.
        """
        return Worker.query.filter_by(user_id=user_id).first()

    @staticmethod
    def get_by_id(worker_id: int) -> Optional[Worker]:
        """
        Get worker by worker ID.

        Args:
            worker_id (int): Worker ID.

        Returns:
            Worker | None: Worker if found, None otherwise.
        """
        return Worker.query.get(worker_id)

    @staticmethod
    def get_all() -> List[Worker]:
        """
        Get all workers.

        Returns:
            List[Worker]: List of all workers.
        """
        return Worker.query.all()

    @staticmethod
    def get_by_zone(zone: str) -> List[Worker]:
        """
        Get all active workers in a zone with active plans.

        Args:
            zone (str): Zone to filter by.

        Returns:
            List[Worker]: List of workers in zone with active subscriptions.
        """
        return Worker.query.filter_by(zone=zone, status="active").filter(
            Worker.active_plan.isnot(None)
        ).all()

    @staticmethod
    def get_by_city(city: str) -> List[Worker]:
        """
        Get all workers in a city.

        Args:
            city (str): City to filter by.

        Returns:
            List[Worker]: List of workers in city.
        """
        return Worker.query.filter_by(city=city).all()

    @staticmethod
    def update(worker_id: int, **kwargs) -> Optional[Worker]:
        """
        Update worker record.

        Args:
            worker_id (int): Worker ID.
            **kwargs: Fields to update.

        Returns:
            Worker | None: Updated worker if found.
        """
        try:
            worker = Worker.query.get(worker_id)
            if not worker:
                logger.warning(f"Worker not found: {worker_id}")
                return None

            for key, value in kwargs.items():
                if hasattr(worker, key):
                    setattr(worker, key, value)

            db.session.flush()  # Flush changes without committing
            logger.info(f"Worker updated: {worker_id}")
            return worker
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating worker {worker_id}: {e}")
            raise

    @staticmethod
    def update_after_claim(
        worker_id: int, payout_amount: float, claim_approved: bool
    ) -> Optional[Worker]:
        """
        Update worker stats after a claim is processed.

        Increments total_claims and total_payouts, adjusts claim_accuracy_rate.

        Args:
            worker_id (int): Worker ID.
            payout_amount (float): Payout amount for claim.
            claim_approved (bool): Whether claim was approved.

        Returns:
            Worker | None: Updated worker if found.
        """
        try:
            worker = Worker.query.get(worker_id)
            if not worker:
                logger.warning(f"Worker not found: {worker_id}")
                return None

            # Increment total claims
            worker.total_claims += 1

            # Update accuracy rate (moving average)
            if claim_approved:
                total = worker.total_claims
                current_accurate = worker.claim_accuracy_rate * (total - 1)
                worker.claim_accuracy_rate = (current_accurate + 1) / total
                worker.total_payouts += payout_amount
            else:
                total = worker.total_claims
                current_accurate = worker.claim_accuracy_rate * (total - 1)
                worker.claim_accuracy_rate = current_accurate / total if total > 0 else 0.0

            db.session.flush()  # Flush changes without committing
            logger.info(
                f"Worker updated after claim: {worker_id}, "
                f"total_claims={worker.total_claims}, total_payouts={worker.total_payouts}"
            )
            return worker
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating worker after claim {worker_id}: {e}")
            raise

    @staticmethod
    def increment_renewal_streak(worker_id: int) -> Optional[Worker]:
        """
        Increment worker's renewal streak.

        Args:
            worker_id (int): Worker ID.

        Returns:
            Worker | None: Updated worker if found.
        """
        try:
            worker = Worker.query.get(worker_id)
            if not worker:
                logger.warning(f"Worker not found: {worker_id}")
                return None

            worker.renewal_streak += 1
            db.session.flush()  # Flush changes without committing
            logger.info(f"Worker renewal streak incremented: {worker_id}")
            return worker
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error incrementing renewal streak for {worker_id}: {e}")
            raise

    @staticmethod
    def get_with_user_info(worker_id: int) -> Optional[Dict[str, Any]]:
        """
        Get worker with joined user information.

        Args:
            worker_id (int): Worker ID.

        Returns:
            Dict | None: Worker data merged with user data if found.
        """
        worker = Worker.query.get(worker_id)
        if not worker:
            return None

        worker_dict = worker.to_dict()
        user_dict = worker.user.to_dict()
        return {**worker_dict, "user": user_dict}

    @staticmethod
    def get_all_with_user_info() -> List[Dict[str, Any]]:
        """
        Get all workers with joined user information.

        Returns:
            List[Dict]: List of worker data merged with user data.
        """
        workers = Worker.query.all()
        result = []
        for worker in workers:
            worker_dict = worker.to_dict()
            user_dict = worker.user.to_dict()
            result.append({**worker_dict, "user": user_dict})
        return result
