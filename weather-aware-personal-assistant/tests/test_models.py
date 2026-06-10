"""Unit tests for configuration constants and domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest
from zoneinfo import ZoneInfo

from assistant import config
from assistant.models import (
    AdviceBundle,
    AdviceItem,
    AssistantError,
    CalendarError,
    CalendarEvent,
    EventWeatherSummary,
    ForecastStatus,
    WeatherFetchError,
    WeatherHour,
)

HOUSTON = ZoneInfo("America/Chicago")


def _event(
    *,
    title: str = "Team Standup",
    start: datetime | None = None,
    end: datetime | None = None,
    location: str = "Office Building A, Houston",
) -> CalendarEvent:
    start = start or datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON)
    end = end or datetime(2026, 6, 10, 9, 30, 0, tzinfo=HOUSTON)
    return CalendarEvent(title=title, start=start, end=end, location=location)


def _weather_hour() -> WeatherHour:
    return WeatherHour(
        timestamp=datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON),
        temperature_c=30.0,
        precipitation_mm=0.0,
        weather_code=0,
        wind_speed_ms=5.0,
    )


def _summary(
    *,
    overlapping_hours: tuple[WeatherHour, ...] = (),
) -> EventWeatherSummary:
    return EventWeatherSummary(
        status=ForecastStatus.AVAILABLE,
        overlapping_hours=overlapping_hours,
        min_temperature_c=30.0,
        max_temperature_c=30.0,
        max_precipitation_mm=0.0,
        max_wind_speed_ms=5.0,
        worst_weather_code=0,
    )


def test_calendar_event_valid_creation() -> None:
    event = _event()
    assert event.title == "Team Standup"
    assert event.location == "Office Building A, Houston"


@pytest.mark.parametrize("title", ["", "   "])
def test_calendar_event_rejects_blank_title(title: str) -> None:
    with pytest.raises(CalendarError, match="title"):
        _event(title=title)


def test_calendar_event_rejects_naive_start() -> None:
    naive_start = datetime(2026, 6, 10, 9, 0, 0)
    aware_end = datetime(2026, 6, 10, 9, 30, 0, tzinfo=HOUSTON)
    with pytest.raises(CalendarError, match="start"):
        CalendarEvent(
            title="Standup",
            start=naive_start,
            end=aware_end,
            location="Office",
        )


def test_calendar_event_rejects_naive_end() -> None:
    aware_start = datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON)
    naive_end = datetime(2026, 6, 10, 9, 30, 0)
    with pytest.raises(CalendarError, match="end"):
        CalendarEvent(
            title="Standup",
            start=aware_start,
            end=naive_end,
            location="Office",
        )


def test_calendar_event_rejects_end_equal_to_start() -> None:
    moment = datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON)
    with pytest.raises(CalendarError, match="strictly after"):
        _event(start=moment, end=moment)


def test_calendar_event_rejects_end_before_start() -> None:
    start = datetime(2026, 6, 10, 10, 0, 0, tzinfo=HOUSTON)
    end = datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON)
    with pytest.raises(CalendarError, match="strictly after"):
        _event(start=start, end=end)


def test_calendar_event_rejects_non_string_location() -> None:
    start = datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON)
    end = datetime(2026, 6, 10, 9, 30, 0, tzinfo=HOUSTON)
    with pytest.raises(CalendarError, match="location"):
        CalendarEvent(title="Standup", start=start, end=end, location=123)  # type: ignore[arg-type]


def test_calendar_event_rejects_non_datetime_start() -> None:
    end = datetime(2026, 6, 10, 9, 30, 0, tzinfo=HOUSTON)
    with pytest.raises(CalendarError, match="start must be a datetime"):
        CalendarEvent(
            title="Standup",
            start="2026-06-10T09:00:00",  # type: ignore[arg-type]
            end=end,
            location="Office",
        )


def test_calendar_event_rejects_non_datetime_end() -> None:
    start = datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON)
    with pytest.raises(CalendarError, match="end must be a datetime"):
        CalendarEvent(
            title="Standup",
            start=start,
            end="2026-06-10T09:30:00",  # type: ignore[arg-type]
            location="Office",
        )


def test_weather_hour_accepts_missing_optional_fields() -> None:
    hour = WeatherHour(
        timestamp=datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON),
        temperature_c=None,
        precipitation_mm=None,
        weather_code=None,
        wind_speed_ms=None,
    )
    assert hour.temperature_c is None
    assert hour.precipitation_mm is None
    assert hour.weather_code is None
    assert hour.wind_speed_ms is None


def test_weather_hour_retains_injected_wind_speed_ms() -> None:
    hour = WeatherHour(
        timestamp=datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON),
        temperature_c=28.0,
        precipitation_mm=0.0,
        weather_code=0,
        wind_speed_ms=12.5,
    )
    assert hour.wind_speed_ms == 12.5


def test_weather_hour_rejects_non_datetime_timestamp() -> None:
    with pytest.raises(TypeError, match="timestamp must be a datetime"):
        WeatherHour(
            timestamp="2026-06-10T09:00:00",  # type: ignore[arg-type]
            temperature_c=None,
            precipitation_mm=None,
            weather_code=None,
            wind_speed_ms=None,
        )


def test_event_weather_summary_uses_immutable_tuple() -> None:
    hour = _weather_hour()
    summary = _summary(overlapping_hours=(hour,))
    assert isinstance(summary.overlapping_hours, tuple)
    assert summary.has_temperature_data is True
    assert summary.has_precipitation_data is True
    assert summary.has_wind_data is True
    assert summary.has_weather_code_data is True


def test_event_weather_summary_rejects_list_for_overlapping_hours() -> None:
    hour = _weather_hour()
    with pytest.raises(TypeError, match="overlapping_hours must be a tuple"):
        EventWeatherSummary(
            status=ForecastStatus.AVAILABLE,
            overlapping_hours=[hour],  # type: ignore[arg-type]
            min_temperature_c=30.0,
            max_temperature_c=30.0,
            max_precipitation_mm=0.0,
            max_wind_speed_ms=5.0,
            worst_weather_code=0,
        )


def test_event_weather_summary_rejects_non_weather_hour_in_tuple() -> None:
    with pytest.raises(TypeError, match="WeatherHour instances"):
        EventWeatherSummary(
            status=ForecastStatus.AVAILABLE,
            overlapping_hours=("not-a-weather-hour",),  # type: ignore[arg-type]
            min_temperature_c=30.0,
            max_temperature_c=30.0,
            max_precipitation_mm=0.0,
            max_wind_speed_ms=5.0,
            worst_weather_code=0,
        )


def test_advice_bundle_uses_immutable_tuple() -> None:
    event = _event()
    summary = EventWeatherSummary(
        status=ForecastStatus.FORECAST_UNAVAILABLE,
        overlapping_hours=(),
        min_temperature_c=None,
        max_temperature_c=None,
        max_precipitation_mm=None,
        max_wind_speed_ms=None,
        worst_weather_code=None,
    )
    item = AdviceItem(
        priority=0,
        category="forecast",
        message="No forecast available.",
        rule_id="forecast_unavailable",
    )
    bundle = AdviceBundle(event=event, summary=summary, items=(item,))
    assert isinstance(bundle.items, tuple)
    assert bundle.items[0].rule_id == "forecast_unavailable"


def test_advice_bundle_rejects_list_for_items() -> None:
    event = _event()
    summary = _summary()
    item = AdviceItem(
        priority=0,
        category="forecast",
        message="No forecast available.",
        rule_id="forecast_unavailable",
    )
    with pytest.raises(TypeError, match="items must be a tuple"):
        AdviceBundle(event=event, summary=summary, items=[item])  # type: ignore[arg-type]


def test_advice_bundle_rejects_non_advice_item_in_tuple() -> None:
    event = _event()
    summary = _summary()
    with pytest.raises(TypeError, match="AdviceItem instances"):
        AdviceBundle(
            event=event,
            summary=summary,
            items=("not-an-advice-item",),  # type: ignore[arg-type]
        )


def test_frozen_dataclasses_reject_attribute_mutation() -> None:
    event = _event()
    with pytest.raises(FrozenInstanceError):
        event.title = "Changed"  # type: ignore[misc]


def test_typed_exceptions_inherit_from_assistant_error() -> None:
    assert issubclass(CalendarError, AssistantError)
    assert issubclass(WeatherFetchError, AssistantError)


def test_configuration_constants_match_approved_values() -> None:
    assert config.DEFAULT_LATITUDE == 29.76
    assert config.DEFAULT_LONGITUDE == -95.36
    assert config.DEFAULT_TIMEZONE == "America/Chicago"
    assert config.RAIN_PRECIP_MM_THRESHOLD == 0.1
    assert config.HEAT_TEMP_C_THRESHOLD == 35.0
    assert config.COLD_TEMP_C_THRESHOLD == 5.0
    assert config.STRONG_WIND_MS_THRESHOLD == 14.0
    assert config.WIND_SPEED_UNIT == "ms"
    assert config.RAIN_WMO_CODES == frozenset(
        {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}
    )
    assert config.SEVERE_WMO_CODES == frozenset({65, 82, 95, 96, 99})
