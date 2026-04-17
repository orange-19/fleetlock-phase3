# app/ml/disruption_model.py

import os
import joblib
import numpy as np
from typing import Dict, Optional
from xgboost import XGBClassifier

SEVERITY_LABELS = {0: "LOW", 1: "MEDIUM", 2: "HIGH", 3: "CRITICAL"}

# Must match exactly what WeatherClient returns
FEATURE_COLUMNS = [
    "rainfall_mm",
    "temperature_celsius",
    "wind_speed_kmh",
    "aqi_index",
    "flood_alert_flag",
]


class DisruptionModel:

    def __init__(self):
        self.model: Optional[XGBClassifier] = None

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        self.model = XGBClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            eval_metric="mlogloss",
            random_state=42,
        )
        self.model.fit(X, y)

    def predict(self, weather_data: Dict) -> Dict:
        """Pass in the dict from WeatherClient.get_weather_for_zone()"""
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        features = np.array(
            [[weather_data[col] for col in FEATURE_COLUMNS]],
            dtype=np.float32
        )
        severity_code = int(self.model.predict(features)[0])
        confidence = float(np.max(self.model.predict_proba(features)[0]))

        return {
            "zone_id":        weather_data["zone_id"],
            "severity_code":  severity_code,
            "severity_label": SEVERITY_LABELS[severity_code],
            "confidence":     round(confidence, 4),
            "timestamp":      weather_data["timestamp"],
        }

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        joblib.dump(self.model, path)

    @classmethod
    def load(cls, path: str) -> "DisruptionModel":
        instance = cls()
        instance.model = joblib.load(path)
        return instance