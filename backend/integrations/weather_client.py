"""Weather API client with caching - OpenWeatherMap integration."""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)


class WeatherClient:
    """Client for OpenWeatherMap API with caching and disruption model format."""

    BASE_URL = "https://api.openweathermap.org/data/2.5"

    def __init__(self):
        """Initialize weather client with API key from environment."""
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        if not self.api_key:
            raise ValueError("❌ OPENWEATHER_API_KEY is missing in .env file. Please add it.")
        
        self.cache_ttl = 900  # 15 minutes
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def get_weather_for_zone(self, zone_id: str) -> Dict:
        """
        Get weather data for zone in format expected by XGBoost disruption model.

        Returns dict with fields:
            - zone_id (str): Zone identifier
            - rainfall_mm (float): Precipitation in mm
            - temperature_celsius (float): Temperature in °C
            - wind_speed_kmh (float): Wind speed in km/h
            - aqi_index (float): Air Quality Index (0-500)
            - flood_alert_flag (int): 0 or 1
            - timestamp (str): ISO timestamp

        Args:
            zone_id (str): Zone identifier (e.g., "bangalore", "delhi").

        Returns:
            Dict: Weather data formatted for disruption model inference.

        Raises:
            requests.RequestException: If API call fails.
        """
        from flask import current_app

        # Map zone to city
        zone_city_map = current_app.config.get("ZONE_CITY_MAP", {
            "bengaluru": "Bengaluru",
            "delhi": "Delhi",
            "mumbai": "Mumbai",
        })
        city = zone_city_map.get(zone_id.lower(), zone_id)

        # Check cache
        cache_key = f"{zone_id}_weather"
        if cache_key in self._cache:
            cached_entry = self._cache[cache_key]
            if (datetime.utcnow() - cached_entry["fetched_at"]).total_seconds() < self.cache_ttl:
                logger.debug(f"✓ Returning cached weather for zone {zone_id}")
                return cached_entry["data"]

        try:
            # Call OpenWeatherMap API for current weather
            weather_response = requests.get(
                f"{self.BASE_URL}/weather",
                params={"q": city, "appid": self.api_key, "units": "metric"},
                timeout=10
            )
            weather_response.raise_for_status()
            weather_data = weather_response.json()

            # Call AQI endpoint (separate endpoint in OpenWeatherMap)
            aqi_response = requests.get(
                f"{self.BASE_URL}/air_pollution",
                params={
                    "lat": weather_data["coord"]["lat"],
                    "lon": weather_data["coord"]["lon"],
                    "appid": self.api_key,
                },
                timeout=10
            )
            aqi_response.raise_for_status()
            aqi_data = aqi_response.json()

            # Extract AQI value (OpenWeatherMap uses list/main/aqi where aqi=1-5)
            # Convert to 0-500 scale
            aqi_level = aqi_data["list"][0]["main"]["aqi"]  # 1=Good, 5=Very Poor
            aqi_index = aqi_level * 100  # Scale to 500 max

            # Parse weather data
            parsed_data = {
                "zone_id": zone_id,
                "rainfall_mm": weather_data.get("rain", {}).get("1h", 0.0),  # 1h rainfall
                "temperature_celsius": weather_data["main"]["temp"],
                "wind_speed_kmh": weather_data["wind"]["speed"] * 3.6,  # Convert m/s to km/h
                "aqi_index": aqi_index,
                "flood_alert_flag": 1 if weather_data.get("rain", {}).get("1h", 0) > 50 else 0,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Cache result
            self._cache[cache_key] = {
                "data": parsed_data,
                "fetched_at": datetime.utcnow(),
            }

            logger.info(f"✓ Weather data fetched for {zone_id}: {parsed_data['temperature_celsius']}°C, AQI={aqi_index}")
            return parsed_data

        except requests.RequestException as e:
            logger.error(f"✗ Failed to fetch weather from API for {zone_id}: {e}")
            
            # Return cached data if available, otherwise safe defaults
            if cache_key in self._cache:
                logger.warning(f"Using stale cached weather for {zone_id}")
                return self._cache[cache_key]["data"]
            
            # Fallback defaults
            return {
                "zone_id": zone_id,
                "rainfall_mm": 0.0,
                "temperature_celsius": 25.0,
                "wind_speed_kmh": 10.0,
                "aqi_index": 100.0,
                "flood_alert_flag": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }

    def get_zone_weather(self, zone: str, city: str) -> Dict[str, Any]:
        """
        Get weather for a zone/city with caching (synchronous fallback).

        Args:
            zone (str): Geographic zone (for logging).
            city (str): City name (for API query).

        Returns:
            Dict: Weather data with temperature, humidity, description, wind_speed, rainfall, visibility.
        """
        # Check cache
        cache_key = f"{zone}_weather_legacy"
        if cache_key in self._cache:
            cached_entry = self._cache[cache_key]
            fetched_at = cached_entry.get("fetched_at")
            if fetched_at and (datetime.utcnow() - fetched_at).total_seconds() < self.cache_ttl:
                logger.debug(f"Returning cached weather for {zone}")
                return cached_entry.get("data", {})

        # Fetch from API
        try:
            url = f"{self.BASE_URL}/weather"
            params = {
                "q": city,
                "appid": self.api_key,
                "units": "metric",
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Fetched weather from API for {city}")

            # Parse response
            weather_data = {
                "zone": zone,
                "city": city,
                "temperature": data.get("main", {}).get("temp", 25),
                "humidity": data.get("main", {}).get("humidity", 50),
                "description": data.get("weather", [{}])[0].get("description", "Unknown"),
                "wind_speed": data.get("wind", {}).get("speed", 0),
                "rainfall": data.get("rain", {}).get("1h", 0),  # 1h rainfall in mm
                "visibility": data.get("visibility", 10000),
                "fetched_at": datetime.utcnow().isoformat(),
            }

            # Cache result
            self._cache[cache_key] = {
                "data": weather_data,
                "fetched_at": datetime.utcnow(),
            }

            return weather_data

        except requests.RequestException as e:
            logger.error(f"Error fetching weather from API: {e}")
            # Return cached data if available, otherwise safe defaults
            if cache_key in self._cache:
                return self._cache[cache_key].get("data", {})
            return {
                "zone": zone,
                "city": city,
                "temperature": 25,
                "humidity": 50,
                "description": "Data unavailable",
                "wind_speed": 0,
                "rainfall": 0,
                "visibility": 10000,
            }
        except Exception as e:
            logger.error(f"Unexpected error in WeatherClient: {e}")
            return {
                "zone": zone,
                "city": city,
                "temperature": 25,
                "humidity": 50,
                "description": "Error retrieving data",
                "wind_speed": 0,
                "rainfall": 0,
                "visibility": 10000,
            }

    def get_all_zones_weather(self) -> Dict[str, Dict[str, Any]]:
        """
        Get weather for all supported zones.

        Args:
            (Uses SUPPORTED_ZONES and SUPPORTED_CITIES from config)

        Returns:
            Dict: Dictionary of zone → weather_data.
        """
        from flask import current_app

        zones = current_app.config.get("SUPPORTED_ZONES", [])
        cities = current_app.config.get("SUPPORTED_CITIES", [])

        # Map zones to cities (simple 1:1 mapping for MVP)
        zone_city_map = dict(zip(zones, cities))

        result = {}
        for zone, city in zone_city_map.items():
            try:
                result[zone] = self.get_zone_weather(zone, city)
            except Exception as e:
                logger.warning(f"Error getting weather for {zone}: {e}")
                result[zone] = {
                    "zone": zone,
                    "city": city,
                    "error": "Could not fetch weather",
                }

        return result

    def poll_fresh(self, zone: Optional[str] = None) -> Dict[str, Any]:
        """
        Poll fresh weather data (invalidate cache and re-fetch).

        Args:
            zone (str | None): Specific zone to refresh, or all if None.

        Returns:
            Dict: Fresh weather data.
        """
        if zone:
            # Clear specific zone from cache
            if zone in self._cache:
                del self._cache[zone]
            logger.info(f"Cache invalidated for zone: {zone}")
        else:
            # Clear all cache
            self._cache.clear()
            logger.info("All weather cache invalidated")

        # Re-fetch
        if zone:
            from flask import current_app
            cities = {z: c for z, c in zip(current_app.config.get("SUPPORTED_ZONES", []),
                                           current_app.config.get("SUPPORTED_CITIES", []))}
            city = cities.get(zone, "Unknown")
            return self.get_zone_weather(zone, city)
        else:
            return self.get_all_zones_weather()
