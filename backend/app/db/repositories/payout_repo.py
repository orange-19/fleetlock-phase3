"""Payout repository for database operations on payouts."""

import logging
from typing import Dict, Any, List, Optional

from sqlalchemy import func

from app.db.database import db
from app.db.models import Payout

logger = logging.getLogger(__name__)


class PayoutRepository:
    """Repository for Payout database operations."""

    @staticmethod
    def create(
        worker_id: int, claim_id: int, amount: float, method: str = "upi"
    ) -> Payout:
        """
        Create a new payout record.

        Args:
            worker_id (int): Worker ID.
            claim_id (int): Claim ID.
            amount (float): Payout amount.
            method (str): Payment method. Defaults to "upi".

        Returns:
            Payout: Created payout instance.
        """
        try:
            payout = Payout(
                worker_id=worker_id, claim_id=claim_id, amount=amount, method=method
            )
            db.session.add(payout)
            db.session.flush()  # Flush to get payout.id without committing
            logger.info(
                f"Payout created: id={payout.id}, worker_id={worker_id}, "
                f"claim_id={claim_id}, amount={amount}"
            )
            return payout
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating payout: {e}")
            raise

    @staticmethod
    def get_by_worker(worker_id: int, limit: int = 10) -> List[Payout]:
        """
        Get payouts for a worker.

        Args:
            worker_id (int): Worker ID.
            limit (int): Maximum number of results. Defaults to 10.

        Returns:
            List[Payout]: List of payouts for worker.
        """
        return Payout.query.filter_by(worker_id=worker_id).limit(limit).all()

    @staticmethod
    def get_by_claim(claim_id: int) -> Optional[Payout]:
        """
        Get payout for a claim.

        Args:
            claim_id (int): Claim ID.

        Returns:
            Payout | None: Payout if found.
        """
        return Payout.query.filter_by(claim_id=claim_id).first()

    @staticmethod
    def get_total_by_worker(worker_id: int) -> float:
        """
        Get total payout amount for a worker.

        Args:
            worker_id (int): Worker ID.

        Returns:
            float: Total payout amount.
        """
        total = (
            db.session.query(func.sum(Payout.amount))
            .filter_by(worker_id=worker_id)
            .scalar()
            or 0.0
        )
        return float(total)

    @staticmethod
    def get_all(limit: int = 50) -> List[Payout]:
        """
        Get all payouts.

        Args:
            limit (int): Maximum number of results. Defaults to 50.

        Returns:
            List[Payout]: List of all payouts.
        """
        return Payout.query.limit(limit).all()
