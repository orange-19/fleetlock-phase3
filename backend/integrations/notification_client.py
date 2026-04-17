"""Notification client for SMS/email alerts."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class NotificationClient:
    """Client for sending notifications to workers."""

    @staticmethod
    def send_claim_notification(
        worker_id: int, claim_status: str, payout_amount: float = 0.0
    ) -> bool:
        """
        Send claim status notification to worker.

        For MVP: logs the notification. In production, integrate with SMS/email service.

        Args:
            worker_id (int): Worker ID.
            claim_status (str): Claim status (approved, rejected, flagged).
            payout_amount (float): Payout amount (if approved). Defaults to 0.0.

        Returns:
            bool: True if notification sent successfully.
        """
        try:
            logger.info(
                f"Claim notification: worker_id={worker_id}, status={claim_status}, "
                f"payout={payout_amount}"
            )

            # For MVP: just log. In production, send SMS/email
            message = f"Your claim has been {claim_status}."
            if claim_status == "approved":
                message += f" Payout: ₹{payout_amount:.2f}"

            logger.info(f"[NOTIFICATION] Worker {worker_id}: {message}")

            return True

        except Exception as e:
            logger.error(f"Error sending claim notification: {e}")
            return False

    @staticmethod
    def send_subscription_notification(worker_id: int, plan: str) -> bool:
        """
        Send subscription confirmation notification.

        For MVP: logs the notification.

        Args:
            worker_id (int): Worker ID.
            plan (str): Plan name/key.

        Returns:
            bool: True if notification sent successfully.
        """
        try:
            logger.info(f"Subscription notification: worker_id={worker_id}, plan={plan}")

            message = f"You are now subscribed to {plan} protection plan."
            logger.info(f"[NOTIFICATION] Worker {worker_id}: {message}")

            return True

        except Exception as e:
            logger.error(f"Error sending subscription notification: {e}")
            return False
