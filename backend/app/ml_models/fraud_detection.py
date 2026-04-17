# app/ml/gps_fraud_model.py

import os
import math
import joblib
import pickle
import logging
from pathlib import Path
import numpy as np
from typing import Dict, List, Tuple, Optional
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)

# ── Haversine (from document formula) ─────────────────────────────────────────

EARTH_RADIUS_KM = 6371.0
FRAUD_DISTANCE_THRESHOLD_KM = 5.0    # > 5 km → location mismatch fraud
STATIONARY_THRESHOLD_KM = 0.05       # < 50 m movement across trace = stationary
STATIONARY_HOURS_THRESHOLD = 2.0     # > 2 hrs stationary = suspicious


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute great-circle distance in km between two GPS coordinates
    using the Haversine formula:

        hav(θ) = sin²(Δφ/2) + cos(φ1)·cos(φ2)·sin²(Δλ/2)
        d = 2R · arcsin(√hav(θ))
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)

    hav_theta = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    )
    hav_theta = min(1.0, hav_theta)   # guard against float overflow
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(hav_theta))


# ── Feature columns (must stay consistent train ↔ predict) ────────────────────

FEATURE_COLUMNS = [
    "gps_drift_meters",         # from TelematicsClient
    "speed_jump_kmh",           # from TelematicsClient
    "route_deviation_pct",      # from TelematicsClient
    "zone_entry_lag_mins",      # from TelematicsClient
    "device_swap_count",        # from TelematicsClient
    "duplicate_trip_flag",      # from TelematicsClient
    "claimed_vs_actual_km",     # haversine(claimed_location, actual_gps)
    "max_trace_span_km",        # max haversine distance across GPS trace
    "is_location_mismatch",     # 1 if claimed_vs_actual_km > 5 km
    "is_stationary",            # 1 if trace spread < 50 m
]

FRAUD_LABELS = {0: "GENUINE", 1: "FRAUD"}


class GPSFraudModel:
    """
    XGBoost-based GPS fraud detector.

    Two primary fraud signals it captures
    ──────────────────────────────────────
    1. Location mismatch  — claimed GPS is > 5 km from actual device location
                            (person claims to be somewhere they are not)
    2. Stationary fraud   — device barely moves across the trace for a long
                            duration (parked/stationary while filing active
                            delivery/field claim)

    Input pipeline
    ──────────────
    TelematicsClient.generate_realistic_gps_features()   → telematics dict
    TelematicsClient.generate_fake_gps_trace()           → GPS trace list
    + claimed_location (lat, lon)
    + actual_location  (lat, lon)
    ↓
    GPSFraudModel.build_features()
    ↓
    GPSFraudModel.predict()
    """

    def __init__(self):
        self.model: Optional[XGBClassifier] = None

    # ── Feature engineering ───────────────────────────────────────────────────

    def build_features(
        self,
        telematics: Dict,
        gps_trace: List[Tuple[float, float]],
        claimed_location: Tuple[float, float],
        actual_location: Tuple[float, float],
    ) -> Dict:
        """
        Combine TelematicsClient output + GPS trace + location pair
        into the flat feature dict expected by predict().

        Parameters
        ----------
        telematics        : output of TelematicsClient.generate_realistic_gps_features()
        gps_trace         : output of TelematicsClient.generate_fake_gps_trace()
        claimed_location  : (lat, lon) the person CLAIMS to be at
        actual_location   : (lat, lon) where the device GPS actually is

        Returns
        -------
        dict with all FEATURE_COLUMNS keys populated
        """
        # 1. Distance between claimed and actual device location
        claimed_vs_actual_km = haversine_km(
            claimed_location[0], claimed_location[1],
            actual_location[0],  actual_location[1],
        )

        # 2. Max spread across the GPS trace (stationary detection)
        max_trace_span_km = self._trace_span_km(gps_trace)

        # 3. Derived fraud flags
        is_location_mismatch = 1 if claimed_vs_actual_km > FRAUD_DISTANCE_THRESHOLD_KM else 0
        is_stationary        = 1 if max_trace_span_km < STATIONARY_THRESHOLD_KM else 0

        return {
            # raw telematics signals
            "gps_drift_meters":    telematics["gps_drift_meters"],
            "speed_jump_kmh":      telematics["speed_jump_kmh"],
            "route_deviation_pct": telematics["route_deviation_pct"],
            "zone_entry_lag_mins": telematics["zone_entry_lag_mins"],
            "device_swap_count":   telematics["device_swap_count"],
            "duplicate_trip_flag": telematics["duplicate_trip_flag"],
            # haversine-derived signals
            "claimed_vs_actual_km":  round(claimed_vs_actual_km, 4),
            "max_trace_span_km":     round(max_trace_span_km, 4),
            "is_location_mismatch":  is_location_mismatch,
            "is_stationary":         is_stationary,
        }

    # ── Training ──────────────────────────────────────────────────────────────

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Fit on pre-built feature matrix.

        Parameters
        ----------
        X : np.ndarray  shape (n_samples, len(FEATURE_COLUMNS))
            Built via build_features() for each sample.
        y : np.ndarray  shape (n_samples,)
            0 = GENUINE, 1 = FRAUD
        """
        self.model = XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            scale_pos_weight=3,    # fraud is minority class — up-weight it
            eval_metric="logloss",
            random_state=42,
        )
        self.model.fit(X, y)

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict(self, features: Dict) -> Dict:
        """
        Predict fraud from a feature dict produced by build_features().

        Returns
        -------
        dict
            {
                "label":         "FRAUD" | "GENUINE",
                "fraud_code":    1 | 0,
                "confidence":    float,
                "fraud_reasons": list[str]   ← human-readable explanation
            }
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        row = np.array(
            [[features[col] for col in FEATURE_COLUMNS]],
            dtype=np.float32
        )
        fraud_code  = int(self.model.predict(row)[0])
        proba       = self.model.predict_proba(row)[0]
        confidence  = float(proba[fraud_code])

        return {
            "label":         FRAUD_LABELS[fraud_code],
            "fraud_code":    fraud_code,
            "confidence":    round(confidence, 4),
            "fraud_reasons": self._explain(features),
        }

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self, path: str, format: str = "joblib", save_metadata: bool = True) -> Dict:
        """
        Save the trained fraud detection model to disk.
        
        Args:
            path (str): File path where model will be saved.
            format (str): Serialization format - "joblib" (default) or "pickle".
            save_metadata (bool): Whether to save model metadata alongside the model.
        
        Returns:
            dict: Information about the saved model (path, format, size, timestamp).
        
        Raises:
            ValueError: If model is not trained.
            IOError: If file cannot be written.
        
        Examples:
            >>> model = GPSFraudModel()
            >>> model.train(X, y)
            >>> info = model.save("saved_models/fraud_model.joblib")
            >>> print(f"Model saved: {info['file_size_mb']:.2f} MB")
        """
        if self.model is None:
            raise ValueError("Model must be trained before saving. Call train() first.")
        
        try:
            # Create directory if needed
            directory = os.path.dirname(path) or "."
            Path(directory).mkdir(parents=True, exist_ok=True)
            
            # Save model
            if format.lower() == "joblib":
                joblib.dump(self.model, path)
            elif format.lower() == "pickle":
                with open(path, "wb") as f:
                    pickle.dump(self.model, f)
            else:
                raise ValueError(f"Unsupported format: {format}. Use 'joblib' or 'pickle'.")
            
            # Get file info
            file_size = os.path.getsize(path)
            file_size_mb = file_size / (1024 * 1024)
            
            logger.info(f"✓ Model saved to {path} ({file_size_mb:.2f} MB)")
            
            # Optionally save metadata
            metadata = {
                "path": path,
                "format": format,
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size_mb, 2),
                "model_type": "GPSFraudModel",
                "n_estimators": self.model.n_estimators if hasattr(self.model, 'n_estimators') else None,
            }
            
            if save_metadata:
                metadata_path = path.replace(".joblib", "_metadata.txt").replace(".pickle", "_metadata.txt")
                with open(metadata_path, "w") as f:
                    f.write(f"Model Metadata\n")
                    f.write(f"==============\n")
                    for key, value in metadata.items():
                        f.write(f"{key}: {value}\n")
                logger.info(f"✓ Metadata saved to {metadata_path}")
            
            return metadata
        
        except IOError as e:
            logger.error(f"✗ Failed to save model: {e}")
            raise
        except Exception as e:
            logger.error(f"✗ Unexpected error while saving model: {e}")
            raise

    @classmethod
    def load(cls, path: str, format: str = "joblib") -> "GPSFraudModel":
        """
        Load a trained fraud detection model from disk.
        
        Args:
            path (str): File path where model is saved.
            format (str): Serialization format - "joblib" (default) or "pickle".
        
        Returns:
            GPSFraudModel: Loaded model instance ready for predictions.
        
        Raises:
            FileNotFoundError: If model file doesn't exist.
            ValueError: If format is not supported.
            EOFError: If model file is corrupted.
        
        Examples:
            >>> model = GPSFraudModel.load("saved_models/fraud_model.joblib")
            >>> prediction = model.predict(features)
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found: {path}")
        
        try:
            instance = cls()
            
            if format.lower() == "joblib":
                instance.model = joblib.load(path)
            elif format.lower() == "pickle":
                with open(path, "rb") as f:
                    instance.model = pickle.load(f)
            else:
                raise ValueError(f"Unsupported format: {format}. Use 'joblib' or 'pickle'.")
            
            file_size_mb = os.path.getsize(path) / (1024 * 1024)
            logger.info(f"✓ Model loaded from {path} ({file_size_mb:.2f} MB)")
            
            return instance
        
        except FileNotFoundError:
            raise
        except EOFError as e:
            logger.error(f"✗ Model file corrupted: {path}")
            raise
        except Exception as e:
            logger.error(f"✗ Failed to load model: {e}")
            raise

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _trace_span_km(self, trace: List[Tuple[float, float]]) -> float:
        """Max haversine distance between any two points in the GPS trace."""
        if len(trace) < 2:
            return 0.0
        max_dist = 0.0
        for i in range(len(trace)):
            for j in range(i + 1, len(trace)):
                d = haversine_km(trace[i][0], trace[i][1],
                                 trace[j][0], trace[j][1])
                if d > max_dist:
                    max_dist = d
        return max_dist

    def _explain(self, features: Dict) -> List[str]:
        """Return a list of human-readable fraud signals triggered."""
        reasons = []
        if features["is_location_mismatch"]:
            reasons.append(
                f"Claimed location is {features['claimed_vs_actual_km']:.2f} km "
                f"from actual device GPS (threshold: {FRAUD_DISTANCE_THRESHOLD_KM} km)"
            )
        if features["is_stationary"]:
            reasons.append(
                f"Device trace span is only {features['max_trace_span_km']*1000:.1f} m "
                f"— device appears stationary"
            )
        if features["device_swap_count"] >= 2:
            reasons.append(f"Device swapped {features['device_swap_count']} times during trip")
        if features["duplicate_trip_flag"]:
            reasons.append("Duplicate trip ID detected")
        if features["gps_drift_meters"] > 50:
            reasons.append(f"GPS drift {features['gps_drift_meters']} m exceeds normal range")
        if features["route_deviation_pct"] > 30:
            reasons.append(f"Route deviation {features['route_deviation_pct']}% is abnormally high")
        return reasons or ["No individual rule triggered — model flagged pattern holistically"]