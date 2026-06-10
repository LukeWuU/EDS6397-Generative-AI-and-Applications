"""Unit tests for event weather-window selection and aggregation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from zoneinfo import ZoneInfo

from assistant.models import CalendarEvent, EventWeatherSummary, ForecastStatus, WeatherHour
from assistant.weather_window import select_overlapping_hours, summarize_event_weather

HOUSTON = ZoneInfo("America/Chicago")


def _event(
    *,
    start: datetime,
    end: datetime,
    title: str = "Event",
    location: str = "Office",
) -> CalendarEvent:
    return CalendarEvent(title=title, start=start, end=end, location=location)


def _hour(
    timestamp: datetime,
    *,
    temperature_c: float | None = 20.0,
    precipitation_mm: float | None = 0.0,
    weather_code: int | None = 0,
    wind_speed_ms: float | None = 5.0,
) -> WeatherHour:
    return WeatherHour(
        timestamp=timestamp,
        temperature_c=temperature_c,
        precipitation_mm=precipitation_mm,
        weather_code=weather_code,
        wind_speed_ms=wind_speed_ms,
    )


def _dt(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=HOUSTON)


def test_hour_exactly_at_event_start_is_included() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hours = (_hour(_dt(2026, 6, 10, 9)),)
    selected = select_overlapping_hours(event, hours)
    assert selected == hours


def test_hour_exactly_at_event_end_is_excluded() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hours = (_hour(_dt(2026, 6, 10, 11)),)
    selected = select_overlapping_hours(event, hours)
    assert selected == ()


def test_hour_before_event_start_is_excluded() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hours = (_hour(_dt(2026, 6, 10, 8)),)
    selected = select_overlapping_hours(event, hours)
    assert selected == ()


def test_hour_after_event_end_is_excluded() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hours = (_hour(_dt(2026, 6, 10, 12)),)
    selected = select_overlapping_hours(event, hours)
    assert selected == ()


def test_event_shorter_than_one_hour() -> None:
    event = _event(start=_dt(2026, 6, 10, 9, 0), end=_dt(2026, 6, 10, 9, 30))
    hours = (
        _hour(_dt(2026, 6, 10, 9)),
        _hour(_dt(2026, 6, 10, 10)),
    )
    selected = select_overlapping_hours(event, hours)
    assert selected == (hours[0],)


def test_multi_hour_event() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours = (
        _hour(_dt(2026, 6, 10, 9)),
        _hour(_dt(2026, 6, 10, 10)),
        _hour(_dt(2026, 6, 10, 11)),
        _hour(_dt(2026, 6, 10, 12)),
    )
    selected = select_overlapping_hours(event, hours)
    assert selected == hours[:3]


def test_no_overlap_returns_empty_tuple() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 10))
    hours = (_hour(_dt(2026, 6, 10, 12)),)
    selected = select_overlapping_hours(event, hours)
    assert selected == ()


def test_selected_output_sorted_when_input_unsorted() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hour_11 = _hour(_dt(2026, 6, 10, 11))
    hour_9 = _hour(_dt(2026, 6, 10, 9))
    hour_10 = _hour(_dt(2026, 6, 10, 10))
    selected = select_overlapping_hours(event, (hour_11, hour_9, hour_10))
    assert selected == (hour_9, hour_10, hour_11)


def test_input_tuple_is_not_mutated() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hours = [_hour(_dt(2026, 6, 10, 10)), _hour(_dt(2026, 6, 10, 9))]
    original = tuple(hours)
    select_overlapping_hours(event, original)
    assert tuple(hours) == original


def test_selected_collection_is_tuple() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    selected = select_overlapping_hours(event, (_hour(_dt(2026, 6, 10, 9)),))
    assert isinstance(selected, tuple)


def test_list_weather_hours_rejected() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    with pytest.raises(TypeError, match="weather_hours must be a tuple"):
        select_overlapping_hours(event, [_hour(_dt(2026, 6, 10, 9))])  # type: ignore[arg-type]


def test_non_weather_hour_in_tuple_rejected() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    with pytest.raises(TypeError, match="WeatherHour instances"):
        select_overlapping_hours(event, ("bad",))  # type: ignore[arg-type]


def test_no_overlap_produces_forecast_unavailable() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 10))
    summary = summarize_event_weather(event, (_hour(_dt(2026, 6, 10, 12)),))
    assert summary.status == ForecastStatus.FORECAST_UNAVAILABLE


def test_unavailable_summary_has_empty_overlapping_hours() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 10))
    summary = summarize_event_weather(event, ())
    assert summary.overlapping_hours == ()


def test_unavailable_summary_aggregate_fields_are_none() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 10))
    summary = summarize_event_weather(event, (_hour(_dt(2026, 6, 10, 12)),))
    assert summary.min_temperature_c is None
    assert summary.max_temperature_c is None
    assert summary.max_precipitation_mm is None
    assert summary.max_wind_speed_ms is None
    assert summary.worst_weather_code is None


def test_unavailable_summary_does_not_substitute_nearest_hour() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 10))
    nearest = _hour(_dt(2026, 6, 10, 8), temperature_c=99.0)
    summary = summarize_event_weather(event, (nearest,))
    assert summary.status == ForecastStatus.FORECAST_UNAVAILABLE
    assert summary.max_temperature_c is None


def test_minimum_temperature_selected() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours = (
        _hour(_dt(2026, 6, 10, 9), temperature_c=25.0),
        _hour(_dt(2026, 6, 10, 10), temperature_c=18.0),
    )
    summary = summarize_event_weather(event, hours)
    assert summary.min_temperature_c == 18.0


def test_maximum_temperature_selected() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours = (
        _hour(_dt(2026, 6, 10, 9), temperature_c=25.0),
        _hour(_dt(2026, 6, 10, 10), temperature_c=18.0),
    )
    summary = summarize_event_weather(event, hours)
    assert summary.max_temperature_c == 25.0


def test_negative_temperature_retained() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hours = (_hour(_dt(2026, 6, 10, 9), temperature_c=-3.0),)
    summary = summarize_event_weather(event, hours)
    assert summary.min_temperature_c == -3.0
    assert summary.max_temperature_c == -3.0


def test_zero_temperature_retained() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hours = (_hour(_dt(2026, 6, 10, 9), temperature_c=0.0),)
    summary = summarize_event_weather(event, hours)
    assert summary.min_temperature_c == 0.0


def test_none_temperatures_ignored() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours = (
        _hour(_dt(2026, 6, 10, 9), temperature_c=None),
        _hour(_dt(2026, 6, 10, 10), temperature_c=20.0),
    )
    summary = summarize_event_weather(event, hours)
    assert summary.min_temperature_c == 20.0
    assert summary.max_temperature_c == 20.0


def test_all_none_temperatures_produce_none() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hours = (_hour(_dt(2026, 6, 10, 9), temperature_c=None),)
    summary = summarize_event_weather(event, hours)
    assert summary.min_temperature_c is None
    assert summary.max_temperature_c is None


def test_maximum_precipitation_selected() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours = (
        _hour(_dt(2026, 6, 10, 9), precipitation_mm=0.2),
        _hour(_dt(2026, 6, 10, 10), precipitation_mm=1.5),
    )
    summary = summarize_event_weather(event, hours)
    assert summary.max_precipitation_mm == 1.5


def test_zero_precipitation_retained() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hours = (_hour(_dt(2026, 6, 10, 9), precipitation_mm=0.0),)
    summary = summarize_event_weather(event, hours)
    assert summary.max_precipitation_mm == 0.0


def test_none_precipitation_ignored() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours = (
        _hour(_dt(2026, 6, 10, 9), precipitation_mm=None),
        _hour(_dt(2026, 6, 10, 10), precipitation_mm=0.4),
    )
    summary = summarize_event_weather(event, hours)
    assert summary.max_precipitation_mm == 0.4


def test_all_none_precipitation_produces_none() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hours = (_hour(_dt(2026, 6, 10, 9), precipitation_mm=None),)
    summary = summarize_event_weather(event, hours)
    assert summary.max_precipitation_mm is None


def test_maximum_wind_speed_selected() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours = (
        _hour(_dt(2026, 6, 10, 9), wind_speed_ms=4.0),
        _hour(_dt(2026, 6, 10, 10), wind_speed_ms=12.0),
    )
    summary = summarize_event_weather(event, hours)
    assert summary.max_wind_speed_ms == 12.0


def test_zero_wind_speed_retained() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hours = (_hour(_dt(2026, 6, 10, 9), wind_speed_ms=0.0),)
    summary = summarize_event_weather(event, hours)
    assert summary.max_wind_speed_ms == 0.0


def test_none_wind_values_ignored() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours = (
        _hour(_dt(2026, 6, 10, 9), wind_speed_ms=None),
        _hour(_dt(2026, 6, 10, 10), wind_speed_ms=7.0),
    )
    summary = summarize_event_weather(event, hours)
    assert summary.max_wind_speed_ms == 7.0


def test_all_none_wind_values_produce_none() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hours = (_hour(_dt(2026, 6, 10, 9), wind_speed_ms=None),)
    summary = summarize_event_weather(event, hours)
    assert summary.max_wind_speed_ms is None


def test_wind_speed_remains_meters_per_second() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hours = (_hour(_dt(2026, 6, 10, 9), wind_speed_ms=14.0),)
    summary = summarize_event_weather(event, hours)
    assert summary.max_wind_speed_ms == 14.0


def test_weather_code_zero_retained() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hours = (_hour(_dt(2026, 6, 10, 9), weather_code=0),)
    summary = summarize_event_weather(event, hours)
    assert summary.worst_weather_code == 0


def test_all_none_weather_codes_produce_none() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hours = (_hour(_dt(2026, 6, 10, 9), weather_code=None),)
    summary = summarize_event_weather(event, hours)
    assert summary.worst_weather_code is None


def test_severe_code_outranks_ordinary_rain() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours = (
        _hour(_dt(2026, 6, 10, 9), weather_code=61),
        _hour(_dt(2026, 6, 10, 10), weather_code=95),
    )
    summary = summarize_event_weather(event, hours)
    assert summary.worst_weather_code == 95


def test_code_99_outranks_95() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours = (
        _hour(_dt(2026, 6, 10, 9), weather_code=95),
        _hour(_dt(2026, 6, 10, 10), weather_code=99),
    )
    summary = summarize_event_weather(event, hours)
    assert summary.worst_weather_code == 99


def test_code_67_outranks_65() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours = (
        _hour(_dt(2026, 6, 10, 9), weather_code=65),
        _hour(_dt(2026, 6, 10, 10), weather_code=67),
    )
    summary = summarize_event_weather(event, hours)
    assert summary.worst_weather_code == 67


def test_code_82_outranks_63() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours = (
        _hour(_dt(2026, 6, 10, 9), weather_code=63),
        _hour(_dt(2026, 6, 10, 10), weather_code=82),
    )
    summary = summarize_event_weather(event, hours)
    assert summary.worst_weather_code == 82


def test_worst_weather_code_independent_of_input_order() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours_a = (
        _hour(_dt(2026, 6, 10, 9), weather_code=61),
        _hour(_dt(2026, 6, 10, 10), weather_code=95),
    )
    hours_b = (
        _hour(_dt(2026, 6, 10, 10), weather_code=95),
        _hour(_dt(2026, 6, 10, 9), weather_code=61),
    )
    assert summarize_event_weather(event, hours_a).worst_weather_code == 95
    assert summarize_event_weather(event, hours_b).worst_weather_code == 95


def test_deterministic_tie_break_prefers_larger_code() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours = (
        _hour(_dt(2026, 6, 10, 9), weather_code=96),
        _hour(_dt(2026, 6, 10, 10), weather_code=99),
    )
    summary = summarize_event_weather(event, hours)
    assert summary.worst_weather_code == 99


def test_unknown_weather_code_handled_deterministically() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours = (
        _hour(_dt(2026, 6, 10, 9), weather_code=0),
        _hour(_dt(2026, 6, 10, 10), weather_code=42),
    )
    summary = summarize_event_weather(event, hours)
    assert summary.worst_weather_code == 42


def test_available_overlap_produces_available_status() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    summary = summarize_event_weather(event, (_hour(_dt(2026, 6, 10, 9)),))
    assert summary.status == ForecastStatus.AVAILABLE


def test_overlapping_hours_are_immutable_tuple() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 11))
    hour = _hour(_dt(2026, 6, 10, 9))
    summary = summarize_event_weather(event, (hour,))
    assert isinstance(summary.overlapping_hours, tuple)
    assert summary.overlapping_hours[0] is hour


def test_summary_data_availability_properties() -> None:
    event = _event(start=_dt(2026, 6, 10, 9), end=_dt(2026, 6, 10, 12))
    hours = (
        _hour(
            _dt(2026, 6, 10, 9),
            temperature_c=20.0,
            precipitation_mm=0.1,
            weather_code=61,
            wind_speed_ms=3.0,
        ),
    )
    summary = summarize_event_weather(event, hours)
    assert summary.has_temperature_data is True
    assert summary.has_precipitation_data is True
    assert summary.has_wind_data is True
    assert summary.has_weather_code_data is True


def test_source_has_no_forbidden_patterns() -> None:
    import assistant.weather_window as weather_window

    source = Path(weather_window.__file__).read_text(encoding="utf-8")
    forbidden = [
        "print(",
        "input(",
        "open(",
        "httpx",
        "rich",
        "assistant.cli",
        "calendar_loader",
        "weather_client",
        "advice_engine",
        "assistant_service",
    ]
    lowered = source.lower()
    for pattern in forbidden:
        assert pattern.lower() not in lowered


def test_source_contains_only_ascii_characters() -> None:
    import assistant.weather_window as weather_window

    source = Path(weather_window.__file__).read_text(encoding="utf-8")
    source.encode("ascii")
