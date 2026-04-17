"""
FleetLock — disruption_model.py
DisruptionSeverityModel: XGBClassifier (low / medium / high) with isotonic
calibration, rule-based fallback, and parametric auto-trigger logic.

The severity_multiplier output (0.50 / 0.75 / 1.00) gates the payout formula.
The trigger_auto_claim flag fires when parametric thresholds are crossed.

Input  : Environmental signals (weather API) + operational platform signals
Output : predicted_severity, severity_multiplier, confidence_map,
         trigger_auto_claim, fallback_used
"""

from __future__ import annotations

import logging
import pickle
import joblib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

MODEL_VERSION = "v2.1.0"

SEVERITY_LABELS  = ["low", "medium", "high"]
SEVERITY_LABEL_MAP = {0: "low", 1: "medium", 2: "high"}

SEVERITY_MULTIPLIER_MAP = {
    "low":    0.50,   # Minor disruption: 50% of max payout
    "medium": 0.75,   # Moderate: 75% of max payout
    "high":   1.00,   # Severe: full payout coverage
}

# Disruption type encoding
DISRUPTION_TYPE_MAP = {
    "weather":         0,
    "platform_outage": 1,
    "civic_event":     2,
}

# Time-of-day encoding
TIME_OF_DAY_MAP = {
    "night":     0,
    "morning":   1,
    "afternoon": 2,
    "evening":   3,
}

DISRUPTION_FEATURES = [
    "rainfall_mm",
    "temperature_celsius",
    "aqi_index",
    "wind_speed_kmh",
    "flood_alert_flag",
    "active_claims_zone",
    "baseline_claims_zone",
    "time_of_day_encoded",
    "api_outage_flag",
    "disruption_type_encoded",
    "claims_surge_ratio",       # derived: active_claims / baseline_claims
]

# ── Parametric Trigger Thresholds (v3.0) ──────────────────────────────────────
# When ANY threshold is breached → auto-initiate claims for all active subscribers
# in the affected zone without admin intervention.
PARAMETRIC_THRESHOLDS = {
    "rainfall_mm":    (">", 75),    # Trigger if rainfall > 75mm (last 3h)
    "wind_speed_kmh": (">", 60),    # Trigger if wind > 60 km/h
    "aqi_index":      (">", 200),   # Trigger if AQI > 200
}


# ── Data Classes ───────────────────────────────────────────────────────────────

@dataclass
class DisruptionFeatures:
    zone_id: str

    # Environmental signals (should come from OpenWeatherMap / Tomorrow.io API)
    rainfall_mm: float              # Precipitation in mm (last 3 hours)
    temperature_celsius: float      # Current temperature °C
    aqi_index: float                # Air Quality Index (0-500)
    wind_speed_kmh: float           # Wind speed in km/h
    flood_alert_flag: int           # 1 = active government flood alert

    # Operational platform signals
    active_claims_zone: int         # Currently active claims in this zone
    baseline_claims_zone: int       # Historical average daily claims (same zone)
    time_of_day_encoded: int        # 0=night, 1=morning, 2=afternoon, 3=evening
    api_outage_flag: int            # 1 = Swiggy/Zomato API reporting outage
    disruption_type: Literal["weather", "platform_outage", "civic_event"] = "weather"

    def to_feature_dict(self) -> dict:
        surge_ratio = self.active_claims_zone / max(self.baseline_claims_zone, 1)
        return {
            "rainfall_mm":             self.rainfall_mm,
            "temperature_celsius":     self.temperature_celsius,
            "aqi_index":               self.aqi_index,
            "wind_speed_kmh":          self.wind_speed_kmh,
            "flood_alert_flag":        self.flood_alert_flag,
            "active_claims_zone":      self.active_claims_zone,
            "baseline_claims_zone":    self.baseline_claims_zone,
            "time_of_day_encoded":     self.time_of_day_encoded,
            "api_outage_flag":         self.api_outage_flag,
            "disruption_type_encoded": DISRUPTION_TYPE_MAP.get(self.disruption_type, 0),
            "claims_surge_ratio":      round(surge_ratio, 4),
        }


@dataclass
class DisruptionResult:
    zone_id: str
    predicted_severity: Literal["low", "medium", "high"]
    severity_multiplier: float          # 0.50 | 0.75 | 1.00
    confidence_map: dict[str, float]    # {"low": 0.08, "medium": 0.19, "high": 0.73}
    trigger_auto_claim: bool            # Should parametric trigger fire?
    fallback_used: bool                 # True if rule-based fallback activated
    model_version: str = MODEL_VERSION


# ── Model Class ────────────────────────────────────────────────────────────────

class DisruptionSeverityModel:
    """
    Multi-class classifier: predicts disruption severity (low / medium / high).
    Uses XGBClassifier + isotonic calibration.
    Falls back to deterministic rule-based logic if model is unavailable.
    Includes parametric auto-trigger check for v3.0 claim automation.
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self._is_trained = False

        self._xgb_base = XGBClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            num_class=3,
            objective="multi:softprob",
            eval_metric="mlogloss",
            use_label_encoder=False,
            random_state=random_state,
            verbosity=0,
        )
        self.model: CalibratedClassifierCV | None = None

    # ── Training ──────────────────────────────────────────────────────────────

    def train(self, X: pd.DataFrame | None = None, y: pd.Series | None = None) -> dict:
        """
        Train the classifier. X and y must be provided (uses actual data, not synthetic).
        y values should be 0=low, 1=medium, 2=high.
        Returns evaluation metrics dict.
        """
        if X is None or y is None:
            raise ValueError("X and y are required. Please provide training data (e.g., from Excel file).")

        X_train, X_test, y_train, y_test = train_test_split(
            X[DISRUPTION_FEATURES], y,
            test_size=0.20, random_state=self.random_state, stratify=y
        )

        # Calibrate with isotonic regression for reliable confidence_map output
        self.model = CalibratedClassifierCV(self._xgb_base, method="isotonic", cv=3)
        self.model.fit(X_train, y_train)
        self._is_trained = True

        y_pred = self.model.predict(X_test)
        report = classification_report(
            y_test, y_pred,
            target_names=SEVERITY_LABELS,
            output_dict=True
        )
        acc = report["accuracy"]
        logger.info(f"DisruptionSeverityModel trained | Accuracy={acc:.4f}")
        return {"accuracy": round(acc, 4), "classification_report": report}

    # ── Model Persistence ─────────────────────────────────────────────────────

    def save(self, filepath: str | Path, format: str = "joblib") -> None:
        """
        Save the trained model to disk.
        
        Args:
            filepath: Path to save the model
            format: "joblib" (default, fastest), "pickle", or "model_only"
        """
        if not self._is_trained:
            raise ValueError("Model must be trained before saving.")
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "joblib":
            joblib.dump(self.model, filepath)
            logger.info(f"Model saved to {filepath} (joblib format)")
        elif format == "pickle":
            with open(filepath, "wb") as f:
                pickle.dump(self.model, f)
            logger.info(f"Model saved to {filepath} (pickle format)")
        elif format == "model_only":
            # Save XGBoost model in native format + metadata
            xgb_path = filepath.with_suffix(".xgb")
            self._xgb_base.get_booster().save_model(xgb_path)
            logger.info(f"XGBoost model saved to {xgb_path}")
        else:
            raise ValueError(f"Unknown format: {format}")

    def load(self, filepath: str | Path, format: str = "joblib") -> None:
        """
        Load a previously trained model from disk.
        
        Args:
            filepath: Path to load the model from
            format: "joblib" (default) or "pickle"
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Model file not found: {filepath}")
        
        try:
            if format == "joblib":
                self.model = joblib.load(filepath)
            elif format == "pickle":
                with open(filepath, "rb") as f:
                    self.model = pickle.load(f)
            else:
                raise ValueError(f"Unknown format: {format}")
            
            self._is_trained = True
            logger.info(f"Model loaded from {filepath} ({format} format)")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict(self, features: DisruptionFeatures) -> DisruptionResult:
        """Run inference on a single DisruptionFeatures instance."""
        fallback_used = False
        trigger_auto_claim = self._check_parametric_trigger(features)

        if not self._is_trained:
            # Graceful degradation: use rule-based fallback
            logger.warning("Model not trained — activating rule-based fallback.")
            severity = self._rule_based_fallback(features)
            fallback_used = True
            confidence_map = self._fallback_confidence(severity)
        else:
            feat_df = pd.DataFrame([features.to_feature_dict()])[DISRUPTION_FEATURES]
            proba = self.model.predict_proba(feat_df)[0]   # shape: [3]

            # Map probabilities to labels
            confidence_map = {
                "low":    round(float(proba[0]), 4),
                "medium": round(float(proba[1]), 4),
                "high":   round(float(proba[2]), 4),
            }
            severity = SEVERITY_LABEL_MAP[int(np.argmax(proba))]

        return DisruptionResult(
            zone_id=features.zone_id,
            predicted_severity=severity,
            severity_multiplier=SEVERITY_MULTIPLIER_MAP[severity],
            confidence_map=confidence_map,
            trigger_auto_claim=trigger_auto_claim,
            fallback_used=fallback_used,
        )

    def predict_batch(self, features_list: list[DisruptionFeatures]) -> list[DisruptionResult]:
        """Batch inference across a list of DisruptionFeatures."""
        return [self.predict(f) for f in features_list]

    # ── Rule-Based Fallback ───────────────────────────────────────────────────

    @staticmethod
    def _rule_based_fallback(features: DisruptionFeatures) -> Literal["low", "medium", "high"]:
        """
        Deterministic fallback when ML model is unavailable.
        Triggered automatically — no admin action required.
        """
        if features.rainfall_mm > 100:   return "high"
        if features.rainfall_mm > 50:    return "medium"
        if features.wind_speed_kmh > 80: return "high"
        if features.aqi_index > 300:     return "high"
        if features.flood_alert_flag:    return "high"
        return "low"

    @staticmethod
    def _fallback_confidence(severity: str) -> dict[str, float]:
        """Produce a dummy confidence map for fallback mode."""
        base = {"low": 0.0, "medium": 0.0, "high": 0.0}
        base[severity] = 1.0
        return base

    # ── Parametric Trigger (v3.0) ─────────────────────────────────────────────

    @staticmethod
    def _check_parametric_trigger(features: DisruptionFeatures) -> bool:
        """
        Evaluate PARAMETRIC_THRESHOLDS.
        Returns True if ANY threshold is breached → auto-initiate claims
        for all active subscribers in the zone. No admin required.
        """
        feat_dict = {
            "rainfall_mm":    features.rainfall_mm,
            "wind_speed_kmh": features.wind_speed_kmh,
            "aqi_index":      features.aqi_index,
        }
        for field_name, (operator, threshold) in PARAMETRIC_THRESHOLDS.items():
            value = feat_dict.get(field_name, 0)
            if operator == ">" and value > threshold:
                logger.info(
                    f"Parametric trigger FIRED: {field_name}={value} {operator} {threshold}"
                )
                return True
        return False