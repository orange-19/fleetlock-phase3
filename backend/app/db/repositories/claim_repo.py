"""Claim repository for database operations on claims."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from sqlalchemy import desc, func

from app.db.database import db
from app.db.models import Claim

logger = logging.getLogger(__name__)


class ClaimRepository:
    """Repository for Claim database operations."""

    @staticmethod
    def create(
        worker_id: int,
        disruption_type: str,
        status: str = "pending",
        fraud_score: float = 0.0,
        fraud_tier: str = "auto_approve",
        severity: str = "low",
        severity_multiplier: float = 1.0,
        payout_amount: float = 0.0,
    ) -> Claim:
        """
        Create a new claim record.

        Args:
            worker_id (int): Worker ID.
            disruption_type (str): Type of disruption.
            status (str): Claim status. Defaults to "pending".
            fraud_score (float): Fraud detection score. Defaults to 0.0.
            fraud_tier (str): Fraud tier (auto_approve, flag_review, auto_reject).
            severity (str): Severity level. Defaults to "low".
            severity_multiplier (float): Severity multiplier. Defaults to 1.0.
            payout_amount (float): Calculated payout amount. Defaults to 0.0.

        Returns:
            Claim: Created claim instance.
        """
        try:
            claim = Claim(
                worker_id=worker_id,
                disruption_type=disruption_type,
                status=status,
                fraud_score=fraud_score,
                fraud_tier=fraud_tier,
                severity=severity,
                severity_multiplier=severity_multiplier,
                payout_amount=payout_amount,
            )
            db.session.add(claim)
            db.session.flush()  # Flush to get claim.id without committing
            logger.info(
                f"Claim created: id={claim.id}, worker_id={worker_id}, "
                f"status={status}, fraud_tier={fraud_tier}"
            )
            return claim
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating claim: {e}")
            raise

    @staticmethod
    def get_by_id(claim_id: int) -> Optional[Claim]:
        """
        Get claim by ID.

        Args:
            claim_id (int): Claim ID.

        Returns:
            Claim | None: Claim if found.
        """
        return Claim.query.get(claim_id)

    @staticmethod
    def get_by_worker(worker_id: int, limit: int = 20) -> List[Claim]:
        """
        Get claims for a worker, ordered by creation date (descending).

        Args:
            worker_id (int): Worker ID.
            limit (int): Maximum number of results. Defaults to 20.

        Returns:
            List[Claim]: List of claims.
        """
        return (
            Claim.query.filter_by(worker_id=worker_id)
            .order_by(desc(Claim.created_at))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_all(limit: int = 100) -> List[Claim]:
        """
        Get all claims.

        Args:
            limit (int): Maximum number of results. Defaults to 100.

        Returns:
            List[Claim]: List of claims.
        """
        return Claim.query.order_by(desc(Claim.created_at)).limit(limit).all()

    @staticmethod
    def get_by_status(status: str, limit: int = 50) -> List[Claim]:
        """
        Get claims filtered by status.

        Args:
            status (str): Status to filter by.
            limit (int): Maximum number of results. Defaults to 50.

        Returns:
            List[Claim]: List of claims with given status.
        """
        return (
            Claim.query.filter_by(status=status)
            .order_by(desc(Claim.created_at))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_recent(limit: int = 20) -> List[Claim]:
        """
        Get most recent claims.

        Args:
            limit (int): Maximum number of results. Defaults to 20.

        Returns:
            List[Claim]: List of recent claims.
        """
        return Claim.query.order_by(desc(Claim.created_at)).limit(limit).all()

    @staticmethod
    def update_status(
        claim_id: int, status: str, notes: Optional[str] = None
    ) -> Optional[Claim]:
        """
        Update claim status and optionally notes.

        Args:
            claim_id (int): Claim ID.
            status (str): New status.
            notes (str | None): Optional notes. Defaults to None.

        Returns:
            Claim | None: Updated claim if found.
        """
        try:
            claim = Claim.query.get(claim_id)
            if not claim:
                logger.warning(f"Claim not found: {claim_id}")
                return None

            claim.status = status
            if notes:
                claim.notes = notes

            db.session.commit()
            logger.info(f"Claim updated: {claim_id}, new_status={status}")
            return claim
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating claim {claim_id}: {e}")
            raise

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """
        Get overall claim statistics.

        Returns:
            Dict: Statistics including total, approved, rejected, pending, flagged counts
                 and total payout sum.
        """
        total_count = Claim.query.count()
        approved_count = Claim.query.filter_by(status="approved").count()
        rejected_count = Claim.query.filter_by(status="rejected").count()
        pending_count = Claim.query.filter_by(status="pending").count()
        flagged_count = Claim.query.filter_by(status="flagged").count()
        total_payout = db.session.query(func.sum(Claim.payout_amount)).scalar() or 0.0

        return {
            "total": total_count,
            "approved": approved_count,
            "rejected": rejected_count,
            "pending": pending_count,
            "flagged": flagged_count,
            "total_payout": float(total_payout),
        }

    @staticmethod
    def get_worker_stats(worker_id: int) -> Dict[str, Any]:
        """
        Get claim statistics for a specific worker.

        Args:
            worker_id (int): Worker ID.

        Returns:
            Dict: Worker's claim statistics.
        """
        total_count = Claim.query.filter_by(worker_id=worker_id).count()
        approved_count = Claim.query.filter_by(
            worker_id=worker_id, status="approved"
        ).count()
        rejected_count = Claim.query.filter_by(
            worker_id=worker_id, status="rejected"
        ).count()
        total_payout = (
            db.session.query(func.sum(Claim.payout_amount))
            .filter_by(worker_id=worker_id)
            .scalar()
            or 0.0
        )

        return {
            "total": total_count,
            "approved": approved_count,
            "rejected": rejected_count,
            "total_payout": float(total_payout),
        }

    @staticmethod
    def get_fraud_over_time(days: int = 30) -> List[Dict[str, Any]]:
        """
        Get average fraud scores over time (grouped by date).

        Args:
            days (int): Number of days to look back. Defaults to 30.

        Returns:
            List[Dict]: List of dicts with date, avg_fraud_score, and count.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        results = (
            db.session.query(
                func.date(Claim.created_at).label("date"),
                func.avg(Claim.fraud_score).label("avg_fraud_score"),
                func.count(Claim.id).label("count"),
            )
            .filter(Claim.created_at >= cutoff_date)
            .group_by(func.date(Claim.created_at))
            .order_by("date")
            .all()
        )

        return [
            {
                "date": str(r.date),
                "avg_fraud_score": float(r.avg_fraud_score) if r.avg_fraud_score else 0.0,
                "count": r.count,
            }
            for r in results
        ]
