"""Application configuration module for multi-environment setup."""

import os
from datetime import timedelta
from typing import Dict, Any
from pathlib import Path

from dotenv import load_dotenv


# Load environment variables from project root .env once during config import.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)


def _as_bool(value: str | None, default: bool = False) -> bool:
    """Parse boolean-like environment values safely."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Base configuration class with defaults."""

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret-key-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_EXPIRY_HOURS", 24)))

    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "mysql+pymysql://root:password@localhost:3306/disruption_guardian",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = _as_bool(os.getenv("SQLALCHEMY_ECHO"), default=False)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 20,
        "max_overflow": 30,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }

    # CORS
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Weather API
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
    WEATHER_API_BASE_URL = os.getenv(
        "WEATHER_API_BASE_URL", "https://api.openweathermap.org/data/2.5"
    )
    WEATHER_CACHE_TTL_SECONDS = int(os.getenv("WEATHER_CACHE_TTL_SECONDS", "900"))

    # Insurance Plans Configuration
    INSURANCE_PLANS: Dict[str, Dict[str, Any]] = {
        "level-1": {
            "name": "Level 1 Basic",
            "premium_weekly": 49,
            "coverage_rate": 0.50,
            "max_covered_days": 3,
        },
        "level-2": {
            "name": "Level 2 Standard",
            "premium_weekly": 99,
            "coverage_rate": 0.70,
            "max_covered_days": 5,
        },
        "level-3": {
            "name": "Level 3 Premium",
            "premium_weekly": 149,
            "coverage_rate": 0.90,
            "max_covered_days": 7,
        },
    }

    # Fraud Detection Thresholds
    FRAUD_AUTO_APPROVE_THRESHOLD = 0.3
    FRAUD_AUTO_REJECT_THRESHOLD = 0.8

    # Severity Thresholds (for weather and environmental disruptions)
    SEVERITY_THRESHOLDS = {
        "rainfall_mm": {"low": 20, "medium": 50, "high": 100},
        "temperature_celsius": {"low": 38, "medium": 42, "high": 45},
        "aqi_index": {"low": 150, "medium": 300, "high": 400},
        "wind_speed_kmh": {"low": 40, "medium": 60, "high": 80},
    }

    # Supported Platforms, Zones, Cities
    SUPPORTED_PLATFORMS = ["swiggy", "zomato", "uber", "ola", "dunzo", "zepto", "blinkit"]
    SUPPORTED_ZONES = [
        "zone-central",
        "zone-north",
        "zone-south",
        "zone-east",
        "zone-west",
    ]
    SUPPORTED_CITIES = ["bangalore", "mumbai", "delhi", "pune", "hyderabad"]


class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG = True


class ProductionConfig(Config):
    """Production environment configuration."""

    DEBUG = False
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Testing environment configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:password@localhost:3306/disruption_guardian_test"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


def get_config(env: str | None = None) -> type:
    """
    Get configuration class based on environment.

    Args:
        env (str | None): Environment name (development, production, testing).
                         If None, reads from FLASK_ENV environment variable.

    Returns:
        type: Configuration class.

    Raises:
        ValueError: If environment is not recognized.
    """
    if env is None:
        env = os.getenv("FLASK_ENV", "development").lower()

    config_map = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }

    if env not in config_map:
        raise ValueError(
            f"Unknown environment: {env}. Supported: {', '.join(config_map.keys())}"
        )

    return config_map[env]
