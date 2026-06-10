"""Unit tests for pure rule-based advice generation."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path

import pytest
from zoneinfo import ZoneInfo

from assistant.advice_engine import generate_advice
from assistant.config import (
    COLD_TEMP_C_THRESHOLD,
    HEAT_TEMP_C_THRESHOLD,
    ONLINE_LOCATION_KEYWORDS,
    RAIN_PRECIP_MM_THRESHOLD,
    SEVERE_WMO_CODES,
    STRONG_WIND_MS_THRESHOLD,
)
from assistant.models import (
    AdviceBundle,
    AdviceItem,
    CalendarEvent,
    EventWeatherSummary,
    ForecastStatus,
    WeatherHour,
)

HOUSTON = ZoneInfo("America/Chicago")

FORBIDDEN_IMPORT_ROOTS = {
    "httpx",
    "rich",
    "assistant.cli",
    "assistant.calendar_loader",
    "assistant.weather_client",
    "assistant.weather_window",
    "assistant.assistant_service",
}
FORBIDDEN_CALLS = {"print", "input", "open"}


def _event(location: str = "Office Building A") -> CalendarEvent:
    return CalendarEvent(
        title="Event",
        start=datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON),
        end=datetime(2026, 6, 10, 10, 0, 0, tzinfo=HOUSTON),
        location=location,
    )


def _summary(
    *,
    status: ForecastStatus = ForecastStatus.AVAILABLE,
    max_precipitation_mm: float | None = 0.0,
    worst_weather_code: int | None = 0,
    max_temperature_c: float | None = 20.0,
    min_temperature_c: float | None = 20.0,
    max_wind_speed_ms: float | None = 5.0,
) -> EventWeatherSummary:
    return EventWeatherSummary(
        status=status,
        overlapping_hours=(),
        min_temperature_c=min_temperature_c,
        max_temperature_c=max_temperature_c,
        max_precipitation_mm=max_precipitation_mm,
        max_wind_speed_ms=max_wind_speed_ms,
        worst_weather_code=worst_weather_code,
    )


def _rule_ids(bundle: AdviceBundle) -> tuple[str, ...]:
    return tuple(item.rule_id for item in bundle.items)


def _advice_engine_source() -> str:
    import assistant.advice_engine as advice_engine

    return Path(advice_engine.__file__).read_text(encoding="utf-8")


def _advice_engine_ast() -> ast.Module:
    return ast.parse(_advice_engine_source())


def test_forecast_unavailable_returns_exactly_one_item() -> None:
    bundle = generate_advice(_event(), _summary(status=ForecastStatus.FORECAST_UNAVAILABLE))
    assert len(bundle.items) == 1


def test_forecast_unavailable_priority_zero() -> None:
    bundle = generate_advice(_event(), _summary(status=ForecastStatus.FORECAST_UNAVAILABLE))
    assert bundle.items[0].priority == 0


def test_forecast_unavailable_rule_id_and_category() -> None:
    bundle = generate_advice(_event(), _summary(status=ForecastStatus.FORECAST_UNAVAILABLE))
    assert bundle.items[0].rule_id == "forecast_unavailable"
    assert bundle.items[0].category == "forecast"


def test_forecast_unavailable_blocks_other_rules() -> None:
    bundle = generate_advice(
        _event("Metro Bus Station"),
        _summary(
            status=ForecastStatus.FORECAST_UNAVAILABLE,
            max_precipitation_mm=2.0,
            worst_weather_code=95,
            max_temperature_c=40.0,
            min_temperature_c=0.0,
            max_wind_speed_ms=20.0,
        ),
    )
    assert _rule_ids(bundle) == ("forecast_unavailable",)


def test_forecast_unavailable_message_has_no_action_keywords() -> None:
    bundle = generate_advice(_event(), _summary(status=ForecastStatus.FORECAST_UNAVAILABLE))
    message = bundle.items[0].message.lower()
    assert "bus" not in message
    assert "umbrella" not in message
    assert "hydration" not in message
    assert "warm layers" not in message
    assert "caution" not in message


def test_precipitation_at_threshold_triggers_rain() -> None:
    bundle = generate_advice(_event(), _summary(max_precipitation_mm=RAIN_PRECIP_MM_THRESHOLD))
    assert "rain_gear" in _rule_ids(bundle)


def test_precipitation_below_threshold_does_not_trigger_rain() -> None:
    bundle = generate_advice(
        _event(),
        _summary(max_precipitation_mm=RAIN_PRECIP_MM_THRESHOLD - 0.01, worst_weather_code=0),
    )
    assert "rain_gear" not in _rule_ids(bundle)
    assert "rain_travel" not in _rule_ids(bundle)


def test_rain_wmo_code_triggers_rain_without_precipitation() -> None:
    bundle = generate_advice(
        _event(),
        _summary(max_precipitation_mm=None, worst_weather_code=61),
    )
    assert "rain_gear" in _rule_ids(bundle)


def test_precipitation_triggers_rain_without_weather_code() -> None:
    bundle = generate_advice(
        _event(),
        _summary(max_precipitation_mm=0.5, worst_weather_code=None),
    )
    assert "rain_gear" in _rule_ids(bundle)


def test_zero_precipitation_with_clear_code_does_not_trigger_rain() -> None:
    bundle = generate_advice(
        _event(),
        _summary(max_precipitation_mm=0.0, worst_weather_code=0),
    )
    assert "rain_gear" not in _rule_ids(bundle)


def test_freezing_rain_code_triggers_rain() -> None:
    bundle = generate_advice(_event(), _summary(max_precipitation_mm=None, worst_weather_code=66))
    assert "rain_gear" in _rule_ids(bundle)


def test_shower_code_triggers_rain() -> None:
    bundle = generate_advice(_event(), _summary(max_precipitation_mm=None, worst_weather_code=80))
    assert "rain_gear" in _rule_ids(bundle)


def test_rainy_metro_bus_station_produces_rain_travel() -> None:
    bundle = generate_advice(
        _event("Metro Bus Station"),
        _summary(max_precipitation_mm=1.0, worst_weather_code=61),
    )
    assert "rain_travel" in _rule_ids(bundle)


def test_rain_travel_message_contains_bus_and_umbrella() -> None:
    bundle = generate_advice(
        _event("Metro Bus Station"),
        _summary(max_precipitation_mm=1.0),
    )
    rain_item = next(item for item in bundle.items if item.rule_id == "rain_travel")
    message = rain_item.message.lower()
    assert "bus" in message
    assert "umbrella" in message


def test_rain_travel_category_and_priority() -> None:
    bundle = generate_advice(
        _event("Metro Bus Station"),
        _summary(max_precipitation_mm=1.0),
    )
    rain_item = next(item for item in bundle.items if item.rule_id == "rain_travel")
    assert rain_item.category == "travel"
    assert rain_item.priority == 2


def test_rain_travel_excludes_rain_gear() -> None:
    bundle = generate_advice(
        _event("Metro Bus Station"),
        _summary(max_precipitation_mm=1.0),
    )
    assert "rain_gear" not in _rule_ids(bundle)


def test_rainy_zoom_does_not_recommend_bus() -> None:
    bundle = generate_advice(_event("Zoom"), _summary(max_precipitation_mm=1.0))
    assert "rain_travel" not in _rule_ids(bundle)
    for item in bundle.items:
        assert "bus" not in item.message.lower()


def test_rainy_online_does_not_recommend_public_transit() -> None:
    bundle = generate_advice(_event("Online"), _summary(max_precipitation_mm=1.0))
    for item in bundle.items:
        assert "public transit" not in item.message.lower()


def test_mixed_zoom_and_metro_classified_online() -> None:
    bundle = generate_advice(
        _event("Zoom meeting near Metro Station"),
        _summary(max_precipitation_mm=1.0),
    )
    assert "rain_travel" not in _rule_ids(bundle)
    assert "rain_gear" in _rule_ids(bundle)


def test_online_rainy_event_may_receive_rain_gear_only() -> None:
    bundle = generate_advice(_event("Remote"), _summary(max_precipitation_mm=1.0))
    assert _rule_ids(bundle) == ("rain_gear",)


def test_physical_rainy_office_produces_rain_gear() -> None:
    bundle = generate_advice(_event("Office Building A"), _summary(max_precipitation_mm=1.0))
    assert "rain_gear" in _rule_ids(bundle)


def test_rain_gear_message_recommends_umbrella_or_gear() -> None:
    bundle = generate_advice(_event("Office Building A"), _summary(max_precipitation_mm=1.0))
    message = next(item for item in bundle.items if item.rule_id == "rain_gear").message.lower()
    assert "umbrella" in message or "rain gear" in message


def test_rain_gear_has_no_bus_recommendation() -> None:
    bundle = generate_advice(_event("Office Building A"), _summary(max_precipitation_mm=1.0))
    for item in bundle.items:
        assert "bus" not in item.message.lower()


@pytest.mark.parametrize("location", ["  zoom  ", "ZOOM", "online", "REMOTE", "Virtual", "Teams"])
def test_online_keyword_case_and_whitespace_insensitive(location: str) -> None:
    bundle = generate_advice(_event(location), _summary(max_precipitation_mm=1.0))
    assert "rain_travel" not in _rule_ids(bundle)


@pytest.mark.parametrize("location", ["bus-stop", "Metro, Station", "Airport Terminal"])
def test_travel_keyword_punctuation_separation(location: str) -> None:
    bundle = generate_advice(_event(location), _summary(max_precipitation_mm=1.0))
    assert "rain_travel" in _rule_ids(bundle)


@pytest.mark.parametrize(
    "keyword",
    ["bus", "metro", "transit", "commute", "airport", "station", "train", "downtown"],
)
def test_each_travel_keyword_recognized(keyword: str) -> None:
    bundle = generate_advice(_event(keyword.title()), _summary(max_precipitation_mm=1.0))
    assert "rain_travel" in _rule_ids(bundle)


@pytest.mark.parametrize("keyword", sorted(ONLINE_LOCATION_KEYWORDS))
def test_each_online_keyword_recognized(keyword: str) -> None:
    bundle = generate_advice(_event(keyword), _summary(max_precipitation_mm=1.0))
    assert "rain_travel" not in _rule_ids(bundle)


@pytest.mark.parametrize("code", sorted(SEVERE_WMO_CODES))
def test_each_severe_code_triggers_severe_advice(code: int) -> None:
    bundle = generate_advice(_event(), _summary(worst_weather_code=code, max_precipitation_mm=0.0))
    assert "severe_weather" in _rule_ids(bundle)


def test_ordinary_rain_code_does_not_trigger_severe() -> None:
    bundle = generate_advice(_event(), _summary(worst_weather_code=61, max_precipitation_mm=0.0))
    assert "severe_weather" not in _rule_ids(bundle)


def test_severe_rule_priority_one() -> None:
    bundle = generate_advice(_event(), _summary(worst_weather_code=95, max_precipitation_mm=0.0))
    severe = next(item for item in bundle.items if item.rule_id == "severe_weather")
    assert severe.priority == 1


def test_severe_can_coexist_with_rain_rule() -> None:
    bundle = generate_advice(
        _event("Metro Bus Station"),
        _summary(worst_weather_code=95, max_precipitation_mm=1.0),
    )
    assert "severe_weather" in _rule_ids(bundle)
    assert "rain_travel" in _rule_ids(bundle)


def test_severe_precedes_rain_advice() -> None:
    bundle = generate_advice(
        _event("Metro Bus Station"),
        _summary(worst_weather_code=95, max_precipitation_mm=1.0),
    )
    assert bundle.items[0].rule_id == "severe_weather"
    assert bundle.items[1].rule_id == "rain_travel"


def test_missing_weather_code_does_not_trigger_severe() -> None:
    bundle = generate_advice(_event(), _summary(worst_weather_code=None, max_precipitation_mm=0.0))
    assert "severe_weather" not in _rule_ids(bundle)


def test_heat_exact_threshold_triggers() -> None:
    bundle = generate_advice(
        _event(),
        _summary(max_temperature_c=HEAT_TEMP_C_THRESHOLD, max_precipitation_mm=0.0),
    )
    assert "extreme_heat" in _rule_ids(bundle)


def test_heat_below_threshold_does_not_trigger() -> None:
    bundle = generate_advice(
        _event(),
        _summary(max_temperature_c=HEAT_TEMP_C_THRESHOLD - 0.1, max_precipitation_mm=0.0),
    )
    assert "extreme_heat" not in _rule_ids(bundle)


def test_missing_max_temperature_does_not_trigger_heat() -> None:
    bundle = generate_advice(
        _event(),
        _summary(max_temperature_c=None, max_precipitation_mm=0.0),
    )
    assert "extreme_heat" not in _rule_ids(bundle)


def test_heat_message_category_and_rule_id() -> None:
    bundle = generate_advice(
        _event(),
        _summary(max_temperature_c=HEAT_TEMP_C_THRESHOLD, max_precipitation_mm=0.0),
    )
    item = next(item for item in bundle.items if item.rule_id == "extreme_heat")
    assert item.category == "temperature"
    assert "hydrat" in item.message.lower()


def test_cold_exact_threshold_triggers() -> None:
    bundle = generate_advice(
        _event(),
        _summary(min_temperature_c=COLD_TEMP_C_THRESHOLD, max_precipitation_mm=0.0),
    )
    assert "cold_weather" in _rule_ids(bundle)


def test_cold_above_threshold_does_not_trigger() -> None:
    bundle = generate_advice(
        _event(),
        _summary(min_temperature_c=COLD_TEMP_C_THRESHOLD + 0.1, max_precipitation_mm=0.0),
    )
    assert "cold_weather" not in _rule_ids(bundle)


def test_missing_min_temperature_does_not_trigger_cold() -> None:
    bundle = generate_advice(
        _event(),
        _summary(min_temperature_c=None, max_precipitation_mm=0.0),
    )
    assert "cold_weather" not in _rule_ids(bundle)


def test_cold_message_category_and_rule_id() -> None:
    bundle = generate_advice(
        _event(),
        _summary(min_temperature_c=COLD_TEMP_C_THRESHOLD, max_precipitation_mm=0.0),
    )
    item = next(item for item in bundle.items if item.rule_id == "cold_weather")
    assert item.category == "temperature"
    assert "warm" in item.message.lower()


def test_wind_exact_threshold_triggers() -> None:
    bundle = generate_advice(
        _event(),
        _summary(max_wind_speed_ms=STRONG_WIND_MS_THRESHOLD, max_precipitation_mm=0.0),
    )
    assert "strong_wind" in _rule_ids(bundle)


def test_wind_below_threshold_does_not_trigger() -> None:
    bundle = generate_advice(
        _event(),
        _summary(max_wind_speed_ms=STRONG_WIND_MS_THRESHOLD - 0.1, max_precipitation_mm=0.0),
    )
    assert "strong_wind" not in _rule_ids(bundle)


def test_missing_wind_does_not_trigger_strong_wind() -> None:
    bundle = generate_advice(
        _event(),
        _summary(max_wind_speed_ms=None, max_precipitation_mm=0.0),
    )
    assert "strong_wind" not in _rule_ids(bundle)


def test_wind_message_category_and_rule_id() -> None:
    bundle = generate_advice(
        _event(),
        _summary(max_wind_speed_ms=STRONG_WIND_MS_THRESHOLD, max_precipitation_mm=0.0),
    )
    item = next(item for item in bundle.items if item.rule_id == "strong_wind")
    assert item.category == "wind"
    assert "caution" in item.message.lower()


def test_normal_conditions_return_single_normal_item() -> None:
    bundle = generate_advice(
        _event(),
        _summary(
            max_precipitation_mm=0.0,
            worst_weather_code=0,
            max_temperature_c=20.0,
            min_temperature_c=10.0,
            max_wind_speed_ms=5.0,
        ),
    )
    assert _rule_ids(bundle) == ("normal",)


def test_normal_absent_when_other_rules_fire() -> None:
    bundle = generate_advice(
        _event(),
        _summary(max_wind_speed_ms=STRONG_WIND_MS_THRESHOLD, max_precipitation_mm=0.0),
    )
    assert "normal" not in _rule_ids(bundle)


def test_zero_metrics_remain_valid_normal_data() -> None:
    bundle = generate_advice(
        _event(),
        _summary(
            max_precipitation_mm=0.0,
            worst_weather_code=0,
            max_temperature_c=20.0,
            min_temperature_c=10.0,
            max_wind_speed_ms=0.0,
        ),
    )
    assert _rule_ids(bundle) == ("normal",)


def test_rain_travel_plus_heat() -> None:
    bundle = generate_advice(
        _event("Metro Bus Station"),
        _summary(max_precipitation_mm=1.0, max_temperature_c=HEAT_TEMP_C_THRESHOLD),
    )
    assert _rule_ids(bundle) == ("rain_travel", "extreme_heat")


def test_rain_gear_plus_wind() -> None:
    bundle = generate_advice(
        _event("Office"),
        _summary(max_precipitation_mm=1.0, max_wind_speed_ms=STRONG_WIND_MS_THRESHOLD),
    )
    assert _rule_ids(bundle) == ("rain_gear", "strong_wind")


def test_severe_rain_travel_plus_wind() -> None:
    bundle = generate_advice(
        _event("Metro Bus Station"),
        _summary(
            worst_weather_code=95,
            max_precipitation_mm=1.0,
            max_wind_speed_ms=STRONG_WIND_MS_THRESHOLD,
        ),
    )
    assert _rule_ids(bundle) == ("severe_weather", "rain_travel", "strong_wind")


def test_heat_plus_wind() -> None:
    bundle = generate_advice(
        _event(),
        _summary(
            max_temperature_c=HEAT_TEMP_C_THRESHOLD,
            max_wind_speed_ms=STRONG_WIND_MS_THRESHOLD,
            max_precipitation_mm=0.0,
        ),
    )
    assert _rule_ids(bundle) == ("extreme_heat", "strong_wind")


def test_items_sorted_by_priority() -> None:
    bundle = generate_advice(
        _event("Metro Bus Station"),
        _summary(
            worst_weather_code=95,
            max_precipitation_mm=1.0,
            max_temperature_c=HEAT_TEMP_C_THRESHOLD,
            min_temperature_c=COLD_TEMP_C_THRESHOLD,
            max_wind_speed_ms=STRONG_WIND_MS_THRESHOLD,
        ),
    )
    priorities = [item.priority for item in bundle.items]
    assert priorities == sorted(priorities)


def test_generate_advice_is_deterministic() -> None:
    event = _event("Metro Bus Station")
    summary = _summary(worst_weather_code=95, max_precipitation_mm=1.0)
    first = generate_advice(event, summary)
    second = generate_advice(event, summary)
    assert first == second


def test_non_calendar_event_rejected() -> None:
    with pytest.raises(TypeError, match="CalendarEvent"):
        generate_advice("bad", _summary())  # type: ignore[arg-type]


def test_non_event_weather_summary_rejected() -> None:
    with pytest.raises(TypeError, match="EventWeatherSummary"):
        generate_advice(_event(), "bad")  # type: ignore[arg-type]


def test_input_event_not_mutated() -> None:
    event = _event()
    original = (event.title, event.start, event.end, event.location)
    generate_advice(event, _summary(max_precipitation_mm=1.0))
    assert (event.title, event.start, event.end, event.location) == original


def test_input_summary_not_mutated() -> None:
    summary = _summary(max_precipitation_mm=1.0)
    original = (
        summary.status,
        summary.overlapping_hours,
        summary.min_temperature_c,
        summary.max_temperature_c,
        summary.max_precipitation_mm,
        summary.max_wind_speed_ms,
        summary.worst_weather_code,
    )
    generate_advice(_event(), summary)
    assert (
        summary.status,
        summary.overlapping_hours,
        summary.min_temperature_c,
        summary.max_temperature_c,
        summary.max_precipitation_mm,
        summary.max_wind_speed_ms,
        summary.worst_weather_code,
    ) == original


def test_bundle_reuses_original_event_and_summary() -> None:
    event = _event()
    summary = _summary()
    bundle = generate_advice(event, summary)
    assert bundle.event is event
    assert bundle.summary is summary


def test_returned_items_are_tuple() -> None:
    bundle = generate_advice(_event(), _summary())
    assert isinstance(bundle.items, tuple)


def test_frozen_advice_items_reject_mutation() -> None:
    bundle = generate_advice(_event(), _summary())
    with pytest.raises(FrozenInstanceError):
        bundle.items[0].message = "changed"  # type: ignore[misc]


def test_ast_import_guard_rejects_forbidden_modules() -> None:
    imported_roots = set()
    for node in ast.walk(_advice_engine_ast()):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0])
                imported_roots.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
            imported_roots.add(node.module)

    forbidden_found = sorted(root for root in imported_roots if root in FORBIDDEN_IMPORT_ROOTS)
    assert forbidden_found == []


def test_ast_call_guard_rejects_forbidden_calls() -> None:
    called_names: set[str] = set()
    for node in ast.walk(_advice_engine_ast()):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)
    forbidden_found = sorted(name for name in called_names if name in FORBIDDEN_CALLS)
    assert forbidden_found == []


def test_generate_advice_produces_no_stdout_or_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    generate_advice(
        _event("Metro Bus Station"),
        _summary(worst_weather_code=95, max_precipitation_mm=1.0),
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_source_contains_only_ascii_characters() -> None:
    _advice_engine_source().encode("ascii")


def test_source_has_no_live_network_or_file_patterns() -> None:
    source = _advice_engine_source().lower()
    assert "httpx" not in source
    assert "open(" not in source
    assert "datetime.now" not in source
    assert "date.today" not in source
    assert "random" not in source
    assert "os.environ" not in source


def test_no_live_network_used() -> None:
    import assistant.advice_engine as advice_engine

    source = Path(advice_engine.__file__).read_text(encoding="utf-8")
    assert "httpx" not in source
    assert "urllib" not in source
    assert "socket" not in source
