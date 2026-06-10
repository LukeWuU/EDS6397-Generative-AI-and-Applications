"""Fetch and parse hourly weather forecasts from Open-Meteo."""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from assistant.config import (
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    DEFAULT_TIMEZONE,
    FORECAST_DAYS,
    HOURLY_WEATHER_VARIABLES,
    OPEN_METEO_FORECAST_URL,
    WIND_SPEED_UNIT,
)
from assistant.models import WeatherFetchError, WeatherHour

_HOUSTON_TZ = ZoneInfo(DEFAULT_TIMEZONE)
_HOURLY_FIELD_NAMES: tuple[str, ...] = (
    "time",
    "temperature_2m",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
)


def build_forecast_params(
    *,
    latitude: float = DEFAULT_LATITUDE,
    longitude: float = DEFAULT_LONGITUDE,
    timezone: str = DEFAULT_TIMEZONE,
    forecast_days: int = FORECAST_DAYS,
) -> dict[str, object]:
    """Build query parameters for an Open-Meteo hourly forecast request."""
    return {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(HOURLY_WEATHER_VARIABLES),
        "timezone": timezone,
        "forecast_days": forecast_days,
        "wind_speed_unit": WIND_SPEED_UNIT,
    }


def fetch_hourly_forecast(
    *,
    latitude: float = DEFAULT_LATITUDE,
    longitude: float = DEFAULT_LONGITUDE,
    timeout_seconds: float = 10.0,
    transport: httpx.BaseTransport | None = None,
) -> tuple[WeatherHour, ...]:
    """Fetch and parse an hourly forecast from Open-Meteo."""
    params = build_forecast_params(latitude=latitude, longitude=longitude)
    try:
        with httpx.Client(transport=transport, timeout=timeout_seconds) as client:
            response = client.get(OPEN_METEO_FORECAST_URL, params=params)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise WeatherFetchError("Weather request timed out.") from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        raise WeatherFetchError(
            f"Weather request failed with HTTP {status_code}."
        ) from exc
    except httpx.HTTPError as exc:
        raise WeatherFetchError("Weather request failed.") from exc

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise WeatherFetchError("Weather response is not valid JSON.") from exc

    return parse_forecast_response(data)


def parse_forecast_response(data: object) -> tuple[WeatherHour, ...]:
    """Validate and parse an Open-Meteo forecast response."""
    if not isinstance(data, dict):
        raise WeatherFetchError("Weather response root must be an object.")

    hourly = data.get("hourly")
    if hourly is None:
        raise WeatherFetchError("Weather response is missing required field 'hourly'.")
    if not isinstance(hourly, dict):
        raise WeatherFetchError("Weather response field 'hourly' must be an object.")

    arrays: dict[str, list[object]] = {}
    for field_name in _HOURLY_FIELD_NAMES:
        values = hourly.get(field_name)
        if values is None:
            raise WeatherFetchError(
                f"Weather response hourly field '{field_name}' is required."
            )
        if not isinstance(values, list):
            raise WeatherFetchError(
                f"Weather response hourly field '{field_name}' must be a list."
            )
        arrays[field_name] = values

    lengths = {field_name: len(values) for field_name, values in arrays.items()}
    unique_lengths = set(lengths.values())
    if len(unique_lengths) > 1:
        raise WeatherFetchError(
            "Weather response hourly arrays must have identical lengths."
        )

    hour_count = lengths["time"]
    parsed_hours: list[WeatherHour] = []
    for index in range(hour_count):
        timestamp = _parse_hourly_timestamp(arrays["time"][index], index=index)
        temperature_c = _parse_optional_float(
            arrays["temperature_2m"][index],
            field_name="temperature_2m",
            index=index,
        )
        precipitation_mm = _parse_optional_float(
            arrays["precipitation"][index],
            field_name="precipitation",
            index=index,
        )
        weather_code = _parse_optional_weather_code(
            arrays["weather_code"][index],
            index=index,
        )
        wind_speed_ms = _parse_optional_float(
            arrays["wind_speed_10m"][index],
            field_name="wind_speed_10m",
            index=index,
        )
        parsed_hours.append(
            WeatherHour(
                timestamp=timestamp,
                temperature_c=temperature_c,
                precipitation_mm=precipitation_mm,
                weather_code=weather_code,
                wind_speed_ms=wind_speed_ms,
            )
        )

    return tuple(parsed_hours)


def _parse_hourly_timestamp(value: object, *, index: int) -> datetime:
    if not isinstance(value, str):
        raise WeatherFetchError(
            f"Weather response hourly 'time' at index {index} must be a string."
        )

    raw_value = value.strip()
    if not raw_value:
        raise WeatherFetchError(
            f"Weather response hourly 'time' at index {index} must be a valid ISO 8601 timestamp."
        )

    try:
        if raw_value.endswith("Z"):
            parsed = datetime.fromisoformat(raw_value[:-1] + "+00:00")
            return parsed.astimezone(_HOUSTON_TZ)

        parsed = datetime.fromisoformat(raw_value)
    except ValueError as exc:
        raise WeatherFetchError(
            f"Weather response hourly 'time' at index {index} has invalid ISO 8601 timestamp: {value!r}."
        ) from exc

    if parsed.tzinfo is None:
        return _localize_naive_houston_timestamp(parsed, index=index)

    return parsed.astimezone(_HOUSTON_TZ)


def _localize_naive_houston_timestamp(naive: datetime, *, index: int) -> datetime:
    aware_fold0 = naive.replace(tzinfo=_HOUSTON_TZ, fold=0)
    aware_fold1 = naive.replace(tzinfo=_HOUSTON_TZ, fold=1)
    offset_fold0 = aware_fold0.utcoffset()
    offset_fold1 = aware_fold1.utcoffset()

    if offset_fold0 != offset_fold1:
        if offset_fold0 is not None and offset_fold1 is not None and offset_fold0 < offset_fold1:
            raise WeatherFetchError(
                f"Weather response hourly 'time' at index {index} is a nonexistent Houston local datetime: {naive.isoformat()}."
            )
        raise WeatherFetchError(
            f"Weather response hourly 'time' at index {index} is an ambiguous Houston local datetime: {naive.isoformat()}."
        )

    round_trip = aware_fold0.astimezone(_HOUSTON_TZ).replace(tzinfo=None)
    if round_trip != naive:
        raise WeatherFetchError(
            f"Weather response hourly 'time' at index {index} is a nonexistent Houston local datetime: {naive.isoformat()}."
        )

    return aware_fold0


def _parse_optional_float(
    value: object,
    *,
    field_name: str,
    index: int,
) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise WeatherFetchError(
            f"Weather response hourly '{field_name}' at index {index} must be a number or null."
        )
    if isinstance(value, (int, float)):
        return float(value)
    raise WeatherFetchError(
        f"Weather response hourly '{field_name}' at index {index} must be a number or null."
    )


def _parse_optional_weather_code(value: object, *, index: int) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise WeatherFetchError(
            f"Weather response hourly 'weather_code' at index {index} must be an integer or null."
        )
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != int(value):
            raise WeatherFetchError(
                f"Weather response hourly 'weather_code' at index {index} must be an integer or null."
            )
        return int(value)
    raise WeatherFetchError(
        f"Weather response hourly 'weather_code' at index {index} must be an integer or null."
    )
