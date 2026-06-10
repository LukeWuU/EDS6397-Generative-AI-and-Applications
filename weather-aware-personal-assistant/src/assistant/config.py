"""Centralized configuration constants for the weather-aware assistant."""

from __future__ import annotations

from typing import Final

DEFAULT_LATITUDE: Final[float] = 29.76
DEFAULT_LONGITUDE: Final[float] = -95.36
DEFAULT_TIMEZONE: Final[str] = "America/Chicago"

OPEN_METEO_FORECAST_URL: Final[str] = "https://api.open-meteo.com/v1/forecast"
DEFAULT_CALENDAR_PATH: Final[str] = "calendar.json"
FORECAST_DAYS: Final[int] = 7

HOURLY_WEATHER_VARIABLES: Final[tuple[str, ...]] = (
    "temperature_2m",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
)
WIND_SPEED_UNIT: Final[str] = "ms"

RAIN_PRECIP_MM_THRESHOLD: Final[float] = 0.1
RAIN_WMO_CODES: Final[frozenset[int]] = frozenset(
    {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}
)
SEVERE_WMO_CODES: Final[frozenset[int]] = frozenset({65, 82, 95, 96, 99})
HEAT_TEMP_C_THRESHOLD: Final[float] = 35.0
COLD_TEMP_C_THRESHOLD: Final[float] = 5.0
STRONG_WIND_MS_THRESHOLD: Final[float] = 14.0

ONLINE_LOCATION_KEYWORDS: Final[frozenset[str]] = frozenset(
    {"online", "remote", "virtual", "zoom", "teams"}
)
