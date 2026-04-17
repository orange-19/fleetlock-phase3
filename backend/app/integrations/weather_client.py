# app/integrations/weather_client.py
import httpx
import os
from typing import Dict
from datetime import datetime

# Zone coordinates (add more zones as needed)
ZONE_COORDINATES = {
    "ZONE_CHENNAI_N": (13.0827, 80.2707),
    "ZONE_CHENNAI_S": (13.0500, 80.2500),
    "ZONE_BLR_HSR":   (12.9081, 77.6476),
    "ZONE_MUM_ANDHERI": (19.1197, 72.8468),
}

class WeatherClient:
    BASE_URL = "https://api.openweathermap.org/data/2.5"

    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        if not self.api_key:
            raise ValueError("❌ OPENWEATHER_API_KEY is missing in .env file. Please add it.")

    async def get_weather_for_zone(self, zone_id: str) -> Dict:
        """
        Fetch live weather data for a zone.
        Returns exactly the format your DisruptionModel will need.
        """
        if zone_id not in ZONE_COORDINATES:
            raise ValueError(f"Unknown zone_id: {zone_id}")

        lat, lon = ZONE_COORDINATES[zone_id]

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Current Weather
            weather_url = f"{self.BASE_URL}/weather"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric"
            }
            resp = await client.get(weather_url, params=params)
            resp.raise_for_status()
            w = resp.json()

            # 2. Air Pollution (AQI)
            pollution_url = f"{self.BASE_URL}/air_pollution"
            pollution_resp = await client.get(pollution_url, params=params)
            pollution_resp.raise_for_status()
            p = pollution_resp.json()

            # Prepare data for Disruption Model
            weather_data = {
                "zone_id": zone_id,
                "rainfall_mm": w.get("rain", {}).get("1h") or w.get("rain", {}).get("3h") or 0.0,
                "temperature_celsius": round(w["main"]["temp"], 1),
                "wind_speed_kmh": round(w.get("wind", {}).get("speed", 0) * 3.6, 1),
                "aqi_index": p["list"][0]["main"]["aqi"] * 50,   # 1-5 → 50-250
                "flood_alert_flag": 1 if any("flood" in item.get("description", "").lower() 
                                           for item in w.get("weather", [])) else 0,
                "disruption_type": "weather",
                "timestamp": datetime.utcnow().isoformat()
            }
            return weather_data