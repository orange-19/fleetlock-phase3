# app/integrations/telematics_client.py

import random
from datetime import datetime
from typing import Dict, List, Tuple


class TelematicsClient:
    """
    Telematics feature generator specifically designed
    for GPS fraud detection model input.
    """

    def __init__(self):
        pass

    def generate_fraud_detection_features(
        self,
        zone_id: str,
        weather_severity: str = "low",
        fraud_type: str = "genuine"
    ) -> Dict:
        """
        Generate fraud-model-ready telematics features.

        Parameters
        ----------
        zone_id : str
            Delivery zone / service zone
        weather_severity : str
            low / medium / high
        fraud_type : str
            genuine / location_mismatch / route_fraud / device_fraud
        """

        zone_multiplier = {
            "ZONE_CHENNAI_N": 1.0,
            "ZONE_BLR_HSR": 0.9,
            "ZONE_MUM_ANDHERI": 1.15
        }.get(zone_id, 1.0)

        # Genuine behavior
        if fraud_type == "genuine":
            gps_drift = random.uniform(8, 25)
            speed_jump = random.uniform(10, 22)
            route_deviation = random.uniform(4, 15)
            zone_entry_lag = random.randint(5, 20)
            device_swap_count = random.randint(0, 1)
            duplicate_trip_flag = 0

        # Fraud: GPS spoofing / fake location
        elif fraud_type == "location_mismatch":
            gps_drift = random.uniform(80, 200)
            speed_jump = random.uniform(40, 90)
            route_deviation = random.uniform(35, 70)
            zone_entry_lag = random.randint(60, 120)
            device_swap_count = random.randint(1, 3)
            duplicate_trip_flag = 1

        # Fraud: suspicious route behavior
        elif fraud_type == "route_fraud":
            gps_drift = random.uniform(50, 100)
            speed_jump = random.uniform(35, 70)
            route_deviation = random.uniform(40, 85)
            zone_entry_lag = random.randint(30, 90)
            device_swap_count = random.randint(0, 2)
            duplicate_trip_flag = 1

        # Fraud: multiple device switching
        elif fraud_type == "device_fraud":
            gps_drift = random.uniform(20, 60)
            speed_jump = random.uniform(20, 40)
            route_deviation = random.uniform(15, 35)
            zone_entry_lag = random.randint(20, 60)
            device_swap_count = random.randint(2, 5)
            duplicate_trip_flag = 1

        else:
            raise ValueError("Invalid fraud_type")

        # Weather adjustment
        if weather_severity == "medium":
            gps_drift += 5
            speed_jump += 3
        elif weather_severity == "high":
            gps_drift += 12
            speed_jump += 8
            route_deviation += 5

        return {
            "gps_drift_meters": round(gps_drift * zone_multiplier, 2),
            "speed_jump_kmh": round(speed_jump, 2),
            "route_deviation_pct": round(route_deviation, 2),
            "zone_entry_lag_mins": zone_entry_lag,
            "device_swap_count": device_swap_count,
            "duplicate_trip_flag": duplicate_trip_flag,
            "timestamp": datetime.utcnow().isoformat()
        }

    def generate_gps_trace(
        self,
        num_points: int = 15,
        stationary: bool = False
    ) -> List[Tuple[float, float]]:
        """
        Generate GPS trace for fraud model.
        Used for stationary fraud detection.
        """

        base_lat = 13.0827
        base_lon = 80.2707

        trace = []

        for _ in range(num_points):
            if stationary:
                lat = base_lat + random.uniform(-0.0001, 0.0001)
                lon = base_lon + random.uniform(-0.0001, 0.0001)
            else:
                lat = base_lat + random.uniform(-0.01, 0.01)
                lon = base_lon + random.uniform(-0.01, 0.01)

            trace.append((round(lat, 6), round(lon, 6)))

        return trace