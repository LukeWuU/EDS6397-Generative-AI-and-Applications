"""Pure rule-based weather advice generation."""

from __future__ import annotations

import re

from assistant.config import (
    COLD_TEMP_C_THRESHOLD,
    HEAT_TEMP_C_THRESHOLD,
    ONLINE_LOCATION_KEYWORDS,
    RAIN_PRECIP_MM_THRESHOLD,
    RAIN_WMO_CODES,
    SEVERE_WMO_CODES,
    STRONG_WIND_MS_THRESHOLD,
)
from assistant.models import (
    AdviceBundle,
    AdviceItem,
    CalendarEvent,
    EventWeatherSummary,
    ForecastStatus,
)

_TRAVEL_LOCATION_KEYWORDS: frozenset[str] = frozenset(
    {"bus", "metro", "transit", "commute", "airport", "station", "train", "downtown"}
)

_FORECAST_UNAVAILABLE_ITEM = AdviceItem(
    priority=0,
    category="forecast",
    message="No forecast is available for this event window.",
    rule_id="forecast_unavailable",
)

_SEVERE_WEATHER_ITEM = AdviceItem(
    priority=1,
    category="safety",
    message="Reconsider or delay travel and monitor official weather alerts.",
    rule_id="severe_weather",
)

_RAIN_TRAVEL_ITEM = AdviceItem(
    priority=2,
    category="travel",
    message="Use or consider the bus or public transit and bring an umbrella.",
    rule_id="rain_travel",
)

_RAIN_GEAR_ITEM = AdviceItem(
    priority=3,
    category="weather",
    message="Bring an umbrella or rain gear.",
    rule_id="rain_gear",
)

_EXTREME_HEAT_ITEM = AdviceItem(
    priority=4,
    category="temperature",
    message="Stay hydrated and limit prolonged outdoor exposure.",
    rule_id="extreme_heat",
)

_COLD_WEATHER_ITEM = AdviceItem(
    priority=5,
    category="temperature",
    message="Wear warm layers for cold conditions.",
    rule_id="cold_weather",
)

_STRONG_WIND_ITEM = AdviceItem(
    priority=6,
    category="wind",
    message="Use caution with loose items and exposed travel.",
    rule_id="strong_wind",
)

_NORMAL_ITEM = AdviceItem(
    priority=7,
    category="general",
    message="No special weather precautions are indicated.",
    rule_id="normal",
)


def generate_advice(
    event: CalendarEvent,
    summary: EventWeatherSummary,
) -> AdviceBundle:
    """Return deterministic advice for one event and weather summary."""
    if not isinstance(event, CalendarEvent):
        raise TypeError("event must be a CalendarEvent instance.")
    if not isinstance(summary, EventWeatherSummary):
        raise TypeError("summary must be an EventWeatherSummary instance.")

    if summary.status == ForecastStatus.FORECAST_UNAVAILABLE:
        return AdviceBundle(
            event=event,
            summary=summary,
            items=(_FORECAST_UNAVAILABLE_ITEM,),
        )

    items: list[AdviceItem] = []

    if _is_severe_weather(summary):
        items.append(_SEVERE_WEATHER_ITEM)

    if _is_rainy(summary):
        if _is_travel_location(event.location):
            items.append(_RAIN_TRAVEL_ITEM)
        else:
            items.append(_RAIN_GEAR_ITEM)

    if _is_extreme_heat(summary):
        items.append(_EXTREME_HEAT_ITEM)

    if _is_cold_weather(summary):
        items.append(_COLD_WEATHER_ITEM)

    if _is_strong_wind(summary):
        items.append(_STRONG_WIND_ITEM)

    if not items:
        items.append(_NORMAL_ITEM)

    sorted_items = tuple(sorted(items, key=lambda item: (item.priority, item.rule_id)))
    return AdviceBundle(event=event, summary=summary, items=sorted_items)


def _is_severe_weather(summary: EventWeatherSummary) -> bool:
    return (
        summary.worst_weather_code is not None
        and summary.worst_weather_code in SEVERE_WMO_CODES
    )


def _is_rainy(summary: EventWeatherSummary) -> bool:
    if (
        summary.max_precipitation_mm is not None
        and summary.max_precipitation_mm >= RAIN_PRECIP_MM_THRESHOLD
    ):
        return True
    return (
        summary.worst_weather_code is not None
        and summary.worst_weather_code in RAIN_WMO_CODES
    )


def _is_extreme_heat(summary: EventWeatherSummary) -> bool:
    return (
        summary.max_temperature_c is not None
        and summary.max_temperature_c >= HEAT_TEMP_C_THRESHOLD
    )


def _is_cold_weather(summary: EventWeatherSummary) -> bool:
    return (
        summary.min_temperature_c is not None
        and summary.min_temperature_c <= COLD_TEMP_C_THRESHOLD
    )


def _is_strong_wind(summary: EventWeatherSummary) -> bool:
    return (
        summary.max_wind_speed_ms is not None
        and summary.max_wind_speed_ms >= STRONG_WIND_MS_THRESHOLD
    )


def _is_online_location(location: str) -> bool:
    return _location_matches_keywords(location, ONLINE_LOCATION_KEYWORDS)


def _is_travel_location(location: str) -> bool:
    if _is_online_location(location):
        return False
    return _location_matches_keywords(location, _TRAVEL_LOCATION_KEYWORDS)


def _location_matches_keywords(location: str, keywords: frozenset[str]) -> bool:
    tokens = _location_tokens(location)
    return any(keyword in tokens for keyword in keywords)


def _location_tokens(location: str) -> frozenset[str]:
    return frozenset(
        token for token in re.split(r"[^a-z0-9]+", location.lower()) if token
    )
