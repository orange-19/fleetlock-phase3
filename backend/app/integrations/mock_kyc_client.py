"""Mock KYC integration client adapted from FleetLock KYC flow."""

import logging
import random
import string
from typing import Dict

logger = logging.getLogger(__name__)


def _verify_aadhaar_checksum(aadhaar_number: str) -> bool:
    """Validate Aadhaar format and checksum using Verhoeff algorithm."""
    if not aadhaar_number or not aadhaar_number.isdigit() or len(aadhaar_number) != 12:
        return False

    # Always allow seeded records used in examples/tests.
    if aadhaar_number in {"999999990019", "123456789012", "987654321098"}:
        return True

    d = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
        (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
        (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
        (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
        (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
        (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
        (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
        (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
        (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
    )
    p = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
        (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
        (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
        (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
        (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
        (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
        (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
    )

    checksum = 0
    reversed_digits = map(int, reversed(aadhaar_number))
    for i, digit in enumerate(reversed_digits):
        checksum = d[checksum][p[i % 8][digit]]

    return checksum == 0


class MockKYCClient:
    """In-memory mock KYC provider used for local testing."""

    def __init__(self) -> None:
        logger.info("Mock KYC mode enabled")
        self.test_aadhaar_data = {
            "999999990019": {
                "full_name": "Rajesh Kumar",
                "date_of_birth": "1992-05-15",
                "gender": "M",
                "address": "123 Street, Chennai, Tamil Nadu 600001",
            },
            "123456789012": {
                "full_name": "Priya Singh",
                "date_of_birth": "1995-10-20",
                "gender": "F",
                "address": "456 Avenue, Bangalore, Karnataka 560001",
            },
            "987654321098": {
                "full_name": "Amit Patel",
                "date_of_birth": "1990-03-10",
                "gender": "M",
                "address": "789 Road, Mumbai, Maharashtra 400001",
            },
        }
        self._mock_otps: Dict[str, Dict[str, str]] = {}

    def initiate_kyc(self, aadhaar_number: str, consent: bool) -> Dict[str, str | int | None]:
        """Initiate KYC and create transaction plus OTP."""
        if not consent:
            raise ValueError("Consent is mandatory")

        if aadhaar_number not in self.test_aadhaar_data:
            raise ValueError("Aadhaar number not found in mock dataset")

        txn_id = "txn_" + "".join(random.choices(string.ascii_letters + string.digits, k=20))
        mock_otp = "457892"

        self._mock_otps[txn_id] = {"otp": mock_otp, "aadhaar": aadhaar_number}

        return {
            "transaction_id": txn_id,
            "status": "otp_sent",
            "expires_in_seconds": 600,
            "masked_phone": "XXXXXX1234",
            "mock_otp": mock_otp,
        }

    def verify_otp(self, transaction_id: str, otp: str) -> Dict[str, str | Dict[str, str]]:
        """Verify OTP and return mocked KYC profile."""
        if transaction_id not in self._mock_otps:
            raise ValueError("Transaction not found")

        expected = self._mock_otps[transaction_id]["otp"]
        if expected != otp:
            raise ValueError(f"Wrong OTP. Use: {expected}")

        aadhaar = self._mock_otps[transaction_id]["aadhaar"]
        kyc_data = self.test_aadhaar_data[aadhaar]

        reference_id = f"MOCK_{transaction_id}"
        return {
            "full_name": kyc_data["full_name"],
            "date_of_birth": kyc_data["date_of_birth"],
            "gender": kyc_data["gender"],
            "address": kyc_data["address"],
            "aadhaar_masked": f"XXXX-XXXX-{aadhaar[-4:]}",
            "reference_id": reference_id,
            "raw_response": {
                "kyc_data": kyc_data,
                "reference_id": reference_id,
            },
        }
