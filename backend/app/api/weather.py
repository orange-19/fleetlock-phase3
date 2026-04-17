"""Weather-related routes blueprint."""

import asyncio

from flask import Blueprint, current_app, request

from app.db.models import Disruption
from app.services.trigger_engine import TriggerEngine
from app.utils.responses import error_response, success_response
from integrations.weather_client import WeatherClient

weather_bp = Blueprint("weather", __name__)


def _run_async(coro):
    """Run async weather calls from sync route handlers."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()

    return asyncio.run(coro)


@weather_bp.route("/all", methods=["GET"])
def get_all_weather() -> tuple:
    """List latest disruption events."""
    try:
        limit = min(max(int(request.args.get("limit", 50)), 1), 200)
        disruptions = (
            Disruption.query.order_by(Disruption.created_at.desc())
            .limit(limit)
            .all()
        )
        return success_response(
            [disruption.to_dict() for disruption in disruptions],
            "Weather disruptions retrieved",
            200,
        )
    except Exception:
        return error_response("Failed to fetch disruptions", status_code=500)


@weather_bp.route("/poll", methods=["POST"])
def poll_weather() -> tuple:
    """Poll weather API and run disruption trigger workflow for requested zones."""
    payload = request.get_json(silent=True) or {}
    zones = payload.get("zones")
    if zones is None:
        zones = current_app.config.get("SUPPORTED_CITIES", ["bengaluru"])
    if not isinstance(zones, list) or not zones:
        return error_response("'zones' must be a non-empty list", status_code=400)

    results = []
    weather_client = None
    weather_client_error = None
    try:
        weather_client = WeatherClient()
    except Exception as exc:
        weather_client_error = str(exc)

    for zone in zones:
        zone_id = str(zone).strip()
        if not zone_id:
            continue

        weather_data = {
            "rainfall_mm": payload.get("rainfall_mm", 0.0),
            "temperature_celsius": payload.get("temperature_celsius", 25.0),
            "aqi_index": payload.get("aqi_index", 100.0),
            "wind_speed_kmh": payload.get("wind_speed_kmh", 10.0),
            "flood_alert_flag": int(bool(payload.get("flood_alert", False))),
        }

        if weather_client:
            try:
                weather_data = _run_async(weather_client.get_weather_for_zone(zone_id))
            except Exception:
                pass

        trigger_result = TriggerEngine.simulate_disruption(
            zone=zone_id,
            disruption_type="weather",
            rainfall_mm=weather_data.get("rainfall_mm"),
            temperature_celsius=weather_data.get("temperature_celsius"),
            aqi_index=weather_data.get("aqi_index"),
            wind_speed_kmh=weather_data.get("wind_speed_kmh"),
            flood_alert=bool(weather_data.get("flood_alert_flag", 0)),
            platform_outage=False,
        )
        results.append(
            {
                "zone": zone_id,
                "weather": weather_data,
                "trigger_result": trigger_result,
            }
        )

    response_data = {
        "zones_polled": len(results),
        "zones": results,
    }
    if weather_client_error:
        response_data["weather_warning"] = weather_client_error

    return success_response(response_data, "Weather poll completed", 200)
