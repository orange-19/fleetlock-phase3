"""Payment gateway client."""

import logging
from typing import Dict, Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class PaymentClient:
    """Client for payment gateway operations."""

    @staticmethod
    def process_payout(worker_id: int, amount: float, method: str = "upi") -> Dict[str, Any]:
        """
        Process payout transaction.

        For MVP: simulates successful payout. In production, integrate with actual payment gateway.

        Args:
            worker_id (int): Worker ID.
            amount (float): Payout amount.
            method (str): Payment method (upi, bank_transfer, etc.). Defaults to "upi".

        Returns:
            Dict: Transaction result with status and transaction ID.
        """
        try:
            # For MVP: simulate successful payout
            transaction_id = str(uuid4())

            logger.info(
                f"Payout processed: worker_id={worker_id}, amount={amount}, "
                f"method={method}, transaction_id={transaction_id}"
            )

            return {
                "status": "completed",
                "transaction_id": transaction_id,
                "worker_id": worker_id,
                "amount": amount,
                "method": method,
            }

        except Exception as e:
            logger.error(f"Error processing payout: {e}")
            return {
                "status": "failed",
                "worker_id": worker_id,
                "amount": amount,
                "method": method,
                "error": str(e),
            }
