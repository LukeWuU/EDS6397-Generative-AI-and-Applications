"""Select and aggregate hourly weather overlapping calendar events."""

from __future__ import annotations

from datetime import datetime

from assistant.models import (
    CalendarEvent,
    EventWeatherSummary,
    ForecastStatus,
    WeatherHour,
)

_SNOW_PRECIPITATION_CODES: frozenset[int] = frozenset({71, 73, 75, 77, 85, 86})
_SEVERITY_TIERS: tuple[frozenset[int], ...] = (
    frozenset({96, 99}),
    frozenset({95}),
    frozenset({67}),
    frozenset({82}),
    frozenset({65}),
    frozenset({66}),
    frozenset({56, 57}),
    frozenset({81}),
    frozenset({80}),
    frozenset({63}),
    frozenset({61}),
    frozenset({55}),
    frozenset({53}),
    frozenset({51}),
    _SNOW_PRECIPITATION_CODES,
    frozenset(),
    frozenset({0}),
)


def select_overlapping_hours(
    event: CalendarEvent,
    weather_hours: tuple[WeatherHour, ...],
) -> tuple[WeatherHour, ...]:
    """Return weather hours whose bucket start falls in [event.start, event.end)."""
    _validate_weather_hours_tuple(weather_hours)
    _ensure_timezone_aware(event.start, "event.start")
    _ensure_timezone_aware(event.end, "event.end")

    selected: list[WeatherHour] = []
    for hour in weather_hours:
        _ensure_timezone_aware(hour.timestamp, "weather_hour.timestamp")
        if event.start <= hour.timestamp < event.end:
            selected.append(hour)
    return tuple(sorted(selected, key=lambda hour: hour.timestamp))


def summarize_event_weather(
    event: CalendarEvent,
    weather_hours: tuple[WeatherHour, ...],
) -> EventWeatherSummary:
    """Aggregate overlapping hourly weather into an event summary."""
    overlapping_hours = select_overlapping_hours(event, weather_hours)
    if not overlapping_hours:
        return EventWeatherSummary(
            status=ForecastStatus.FORECAST_UNAVAILABLE,
            overlapping_hours=(),
            min_temperature_c=None,
            max_temperature_c=None,
            max_precipitation_mm=None,
            max_wind_speed_ms=None,
            worst_weather_code=None,
        )

    temperatures = [hour.temperature_c for hour in overlapping_hours]
    precipitation_values = [hour.precipitation_mm for hour in overlapping_hours]
    wind_values = [hour.wind_speed_ms for hour in overlapping_hours]
    weather_codes = [hour.weather_code for hour in overlapping_hours]

    return EventWeatherSummary(
        status=ForecastStatus.AVAILABLE,
        overlapping_hours=overlapping_hours,
        min_temperature_c=_min_non_none(temperatures),
        max_temperature_c=_max_non_none(temperatures),
        max_precipitation_mm=_max_non_none(precipitation_values),
        max_wind_speed_ms=_max_non_none(wind_values),
        worst_weather_code=_select_worst_weather_code(weather_codes),
    )


def _validate_weather_hours_tuple(weather_hours: object) -> None:
    if not isinstance(weather_hours, tuple):
        raise TypeError("weather_hours must be a tuple.")
    for hour in weather_hours:
        if not isinstance(hour, WeatherHour):
            raise TypeError("weather_hours must contain WeatherHour instances.")


def _ensure_timezone_aware(value: datetime, label: str) -> bool:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(f"{label} must be timezone-aware.")
    return True


def _min_non_none(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return min(present)


def _max_non_none(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return max(present)


def _severity_tier_index(code: int) -> int:
    for tier_index, tier_codes in enumerate(_SEVERITY_TIERS):
        if not tier_codes:
            continue
        if code in tier_codes:
            return tier_index
    if code == 0:
        return 16
    return 15


def _weather_code_severity_key(code: int) -> tuple[int, int]:
    """Lower tier index is more severe; larger code breaks ties."""
    return (_severity_tier_index(code), -code)


def _select_worst_weather_code(codes: list[int | None]) -> int | None:
    present = [code for code in codes if code is not None]
    if not present:
        return None
    return min(present, key=_weather_code_severity_key)
