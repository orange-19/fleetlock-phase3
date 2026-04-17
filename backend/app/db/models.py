"""SQLAlchemy ORM models for disruption-guardian database."""

from datetime import datetime
import json
from typing import Dict, Any, Optional, List

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.mysql import ENUM

from app.db.database import db


class User(db.Model):
    """User model for workers and admins."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    role = db.Column(
        ENUM("worker", "admin"), nullable=False, default="worker"
    )
    phone = db.Column(db.String(20), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    worker = db.relationship("Worker", backref="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email}:{self.role}>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "phone": self.phone,
            "city": self.city,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Worker(db.Model):
    """Worker profile model."""

    __tablename__ = "workers"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True)
    platform = db.Column(db.String(50), nullable=False)
    zone = db.Column(db.String(50), default="zone-central", nullable=False, index=True)
    city = db.Column(db.String(100), nullable=False, index=True)
    daily_income_avg = db.Column(db.Float, default=500.0, nullable=False)
    tenure_days = db.Column(db.Integer, default=0, nullable=False)
    active_plan = db.Column(db.String(20), nullable=True)
    renewal_streak = db.Column(db.Integer, default=0, nullable=False)
    claim_accuracy_rate = db.Column(db.Float, default=1.0, nullable=False)
    platform_rating = db.Column(db.Float, default=4.0, nullable=False)
    total_claims = db.Column(db.Integer, default=0, nullable=False)
    total_payouts = db.Column(db.Float, default=0.0, nullable=False)
    status = db.Column(
        ENUM("active", "inactive", "suspended"), default="active", nullable=False, index=True
    )
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    subscriptions = db.relationship("Subscription", backref="worker", lazy="dynamic", cascade="all, delete-orphan")
    claims = db.relationship("Claim", backref="worker", lazy="dynamic", cascade="all, delete-orphan")
    payouts = db.relationship("Payout", backref="worker", lazy="dynamic", cascade="all, delete-orphan")
    kyc_audit_log = db.relationship(
        "WorkerKYCAuditLog",
        backref="worker",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Worker {self.id}:{self.user.email}>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        kyc_status = None
        is_kyc_verified = False
        if self.kyc_audit_log is not None:
            kyc_status = self.kyc_audit_log.kyc_status
            is_kyc_verified = kyc_status == "verified"

        return {
            "id": self.id,
            "user_id": self.user_id,
            "platform": self.platform,
            "zone": self.zone,
            "city": self.city,
            "daily_income_avg": self.daily_income_avg,
            "tenure_days": self.tenure_days,
            "active_plan": self.active_plan,
            "renewal_streak": self.renewal_streak,
            "claim_accuracy_rate": self.claim_accuracy_rate,
            "platform_rating": self.platform_rating,
            "total_claims": self.total_claims,
            "total_payouts": self.total_payouts,
            "is_kyc_verified": is_kyc_verified,
            "kyc_status": kyc_status,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkerKYCAuditLog(db.Model):
    """KYC audit trail for worker verification attempts and outcomes."""

    __tablename__ = "worker_kyc_audit_logs"
    __table_args__ = (
        db.UniqueConstraint("worker_id", name="uq_kyc_worker_id"),
        db.Index("ix_kyc_setu_txn", "setu_transaction_id"),
        db.Index("ix_kyc_status", "kyc_status"),
        db.Index("ix_kyc_created", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("workers.id"), nullable=False, index=True)

    setu_transaction_id = db.Column(db.String(100), nullable=True)
    setu_reference_id = db.Column(db.String(100), nullable=True)

    aadhaar_masked = db.Column(db.String(14), nullable=True)
    kyc_status = db.Column(
        ENUM("initiated", "otp_sent", "otp_verified", "verified", "failed", "rejected"),
        default="initiated",
        nullable=False,
        index=True,
    )

    consent_given = db.Column(db.Boolean, default=False, nullable=False)
    consent_timestamp = db.Column(DateTime, nullable=True)
    consent_ip_address = db.Column(db.String(45), nullable=True)
    consent_user_agent = db.Column(db.Text, nullable=True)

    full_name = db.Column(db.String(255), nullable=True)
    date_of_birth = db.Column(db.String(10), nullable=True)
    gender = db.Column(db.String(1), nullable=True)
    address = db.Column(db.Text, nullable=True)

    verification_timestamp = db.Column(DateTime, nullable=True)
    verification_error_code = db.Column(db.String(50), nullable=True)
    verification_error_message = db.Column(db.Text, nullable=True)
    setu_response_json = db.Column(db.Text, nullable=True)

    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<WorkerKYCAuditLog worker={self.worker_id}:status={self.kyc_status}>"

    def to_dict(self, include_pii: bool = False) -> Dict[str, Any]:
        """Serialize KYC audit record; include PII only when requested."""
        parsed_setu_response: Optional[Dict[str, Any]] = None
        if include_pii and self.setu_response_json:
            try:
                parsed_setu_response = json.loads(self.setu_response_json)
            except (ValueError, TypeError):
                parsed_setu_response = None

        return {
            "worker_id": self.worker_id,
            "kyc_status": self.kyc_status,
            "is_kyc_verified": self.kyc_status == "verified",
            "aadhaar_masked": self.aadhaar_masked,
            "setu_transaction_id": self.setu_transaction_id,
            "full_name": self.full_name if include_pii else None,
            "date_of_birth": self.date_of_birth if include_pii else None,
            "gender": self.gender if include_pii else None,
            "address": self.address if include_pii else None,
            "setu_reference_id": self.setu_reference_id,
            "consent_given": self.consent_given,
            "consent_timestamp": self.consent_timestamp.isoformat() if self.consent_timestamp else None,
            "consent_ip_address": self.consent_ip_address,
            "verification_timestamp": (
                self.verification_timestamp.isoformat() if self.verification_timestamp else None
            ),
            "verification_error_code": self.verification_error_code,
            "verification_error_message": self.verification_error_message,
            "setu_response": parsed_setu_response,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Subscription(db.Model):
    """Subscription/Insurance plan model."""

    __tablename__ = "subscriptions"
    __table_args__ = (db.Index("idx_worker_status", "worker_id", "status"),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("workers.id"), nullable=False, index=True)
    plan = db.Column(db.String(20), nullable=False)
    status = db.Column(
        ENUM("active", "expired", "cancelled"), default="active", nullable=False
    )
    premium_weekly = db.Column(db.Float, nullable=False)
    coverage_rate = db.Column(db.Float, nullable=False)
    max_covered_days = db.Column(db.Integer, nullable=False)
    start_date = db.Column(DateTime, nullable=False)
    end_date = db.Column(DateTime, nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Subscription {self.id}:worker={self.worker_id}:plan={self.plan}>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        return {
            "id": self.id,
            "worker_id": self.worker_id,
            "plan": self.plan,
            "status": self.status,
            "premium_weekly": self.premium_weekly,
            "coverage_rate": self.coverage_rate,
            "max_covered_days": self.max_covered_days,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Claim(db.Model):
    """Insurance claim model."""

    __tablename__ = "claims"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("workers.id"), nullable=False, index=True)
    disruption_type = db.Column(
        ENUM("weather", "platform_outage", "civic_event", "flood", "heat", "aqi"),
        nullable=False,
    )
    status = db.Column(
        ENUM("pending", "approved", "rejected", "flagged"),
        default="pending",
        nullable=False,
        index=True,
    )
    fraud_score = db.Column(db.Float, default=0.0, nullable=False)
    fraud_tier = db.Column(db.String(20), default="auto_approve", nullable=False)
    severity = db.Column(db.String(20), default="low", nullable=False)
    severity_multiplier = db.Column(db.Float, default=1.0, nullable=False)
    payout_amount = db.Column(db.Float, default=0.0, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    updated_at = db.Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    payouts = db.relationship("Payout", backref="claim", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Claim {self.id}:worker={self.worker_id}:status={self.status}>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        return {
            "id": self.id,
            "worker_id": self.worker_id,
            "disruption_type": self.disruption_type,
            "status": self.status,
            "fraud_score": self.fraud_score,
            "fraud_tier": self.fraud_tier,
            "severity": self.severity,
            "severity_multiplier": self.severity_multiplier,
            "payout_amount": self.payout_amount,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Payout(db.Model):
    """Payout transaction model."""

    __tablename__ = "payouts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("workers.id"), nullable=False, index=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.id"), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50), default="upi", nullable=False)
    status = db.Column(
        ENUM("pending", "completed", "failed"),
        default="pending",
        nullable=False,
    )
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Payout {self.id}:worker={self.worker_id}:claim={self.claim_id}>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        return {
            "id": self.id,
            "worker_id": self.worker_id,
            "claim_id": self.claim_id,
            "amount": self.amount,
            "method": self.method,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Disruption(db.Model):
    """Disruption event model (weather, outages, civic events, etc.)."""

    __tablename__ = "disruptions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    zone = db.Column(db.String(50), nullable=False, index=True)
    disruption_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    severity_multiplier = db.Column(db.Float, default=1.0, nullable=False)
    rainfall_mm = db.Column(db.Float, nullable=True)
    temperature_celsius = db.Column(db.Float, nullable=True)
    aqi_index = db.Column(db.Float, nullable=True)
    wind_speed_kmh = db.Column(db.Float, nullable=True)
    flood_alert = db.Column(db.Boolean, default=False, nullable=False)
    platform_outage = db.Column(db.Boolean, default=False, nullable=False)
    affected_workers_count = db.Column(db.Integer, default=0, nullable=False)
    auto_claims_created = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<Disruption {self.id}:zone={self.zone}:type={self.disruption_type}>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        return {
            "id": self.id,
            "zone": self.zone,
            "disruption_type": self.disruption_type,
            "severity": self.severity,
            "severity_multiplier": self.severity_multiplier,
            "rainfall_mm": self.rainfall_mm,
            "temperature_celsius": self.temperature_celsius,
            "aqi_index": self.aqi_index,
            "wind_speed_kmh": self.wind_speed_kmh,
            "flood_alert": self.flood_alert,
            "platform_outage": self.platform_outage,
            "affected_workers_count": self.affected_workers_count,
            "auto_claims_created": self.auto_claims_created,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TokenBlocklist(db.Model):
    """Token blocklist for JWT logout functionality."""

    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    jti = db.Column(db.String(255), unique=True, nullable=False, index=True)
    token_type = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    expires_at = db.Column(DateTime, nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<TokenBlocklist jti={self.jti[:20]}...>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        return {
            "id": self.id,
            "jti": self.jti,
            "token_type": self.token_type,
            "user_id": self.user_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
