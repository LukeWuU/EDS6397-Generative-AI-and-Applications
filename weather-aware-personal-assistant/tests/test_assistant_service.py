"""Unit tests for application service orchestration."""

from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path

import pytest
from zoneinfo import ZoneInfo

from assistant.advice_engine import generate_advice
from assistant.assistant_service import AssistantService, create_default_service
from assistant.models import (
    AdviceBundle,
    CalendarError,
    CalendarEvent,
    EventWeatherSummary,
    ForecastStatus,
    WeatherFetchError,
    WeatherHour,
)
from assistant.weather_window import summarize_event_weather

HOUSTON = ZoneInfo("America/Chicago")

FORBIDDEN_IMPORT_ROOTS = {"rich", "assistant.cli", "httpx", "requests"}
FORBIDDEN_CALLS = {"print", "input", "open"}
FORBIDDEN_LOGIC_TOKENS = {
    "rain_travel",
    "rain_gear",
    "severe_weather",
    "extreme_heat",
    "cold_weather",
    "strong_wind",
    "bus",
    "umbrella",
}


def _event(
    *,
    location: str = "Office",
    start: datetime | None = None,
    end: datetime | None = None,
) -> CalendarEvent:
    return CalendarEvent(
        title="Event",
        start=start or datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON),
        end=end or datetime(2026, 6, 10, 10, 0, 0, tzinfo=HOUSTON),
        location=location,
    )


def _hour(
    timestamp: datetime | None = None,
    *,
    precipitation_mm: float | None = 0.0,
    weather_code: int | None = 0,
) -> WeatherHour:
    return WeatherHour(
        timestamp=timestamp or datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON),
        temperature_c=20.0,
        precipitation_mm=precipitation_mm,
        weather_code=weather_code,
        wind_speed_ms=5.0,
    )


def _bundle(event: CalendarEvent) -> AdviceBundle:
    summary = EventWeatherSummary(
        status=ForecastStatus.AVAILABLE,
        overlapping_hours=(),
        min_temperature_c=20.0,
        max_temperature_c=20.0,
        max_precipitation_mm=0.0,
        max_wind_speed_ms=5.0,
        worst_weather_code=0,
    )
    return AdviceBundle(event=event, summary=summary, items=())


def _service_source() -> str:
    import assistant.assistant_service as assistant_service

    return Path(assistant_service.__file__).read_text(encoding="utf-8")


def _service_ast() -> ast.Module:
    return ast.parse(_service_source())


class Spy:
    def __init__(self) -> None:
        self.calls: list[object] = []


def test_construction_performs_no_file_reads() -> None:
    def loader(path: str | Path) -> tuple[CalendarEvent, ...]:
        raise AssertionError("loader should not run during construction")

    def fetcher() -> tuple[WeatherHour, ...]:
        raise AssertionError("fetcher should not run during construction")

    AssistantService(load_calendar_fn=loader, fetch_weather_fn=fetcher)


def test_construction_performs_no_network_calls() -> None:
    service = AssistantService()
    assert service.events == ()
    assert service.weather_hours == ()


def test_initial_events_is_empty_tuple() -> None:
    assert AssistantService().events == ()


def test_initial_weather_hours_is_empty_tuple() -> None:
    assert AssistantService().weather_hours == ()


def test_properties_return_tuples() -> None:
    service = AssistantService()
    assert isinstance(service.events, tuple)
    assert isinstance(service.weather_hours, tuple)


def test_create_default_service_returns_assistant_service() -> None:
    service = create_default_service()
    assert isinstance(service, AssistantService)
    assert service.events == ()
    assert service.weather_hours == ()


def test_load_events_calls_loader_once_and_caches_tuple() -> None:
    events = (_event(),)
    loader_calls: list[Path] = []
    fetch_calls = 0

    def loader(path: str | Path) -> tuple[CalendarEvent, ...]:
        loader_calls.append(Path(path))
        return events

    def fetcher() -> tuple[WeatherHour, ...]:
        nonlocal fetch_calls
        fetch_calls += 1
        return ()

    service = AssistantService(
        calendar_path="custom.json",
        load_calendar_fn=loader,
        fetch_weather_fn=fetcher,
    )
    returned = service.load_events()
    assert returned is events
    assert service.events is events
    assert len(loader_calls) == 1
    assert loader_calls[0] == Path("custom.json")
    assert fetch_calls == 0


def test_load_events_propagates_calendar_error() -> None:
    def loader(path: str | Path) -> tuple[CalendarEvent, ...]:
        raise CalendarError("bad calendar")

    service = AssistantService(load_calendar_fn=loader)
    with pytest.raises(CalendarError, match="bad calendar"):
        service.load_events()


def test_load_events_preserves_cache_on_failure() -> None:
    existing = (_event(location="Cached"),)

    def loader(path: str | Path) -> tuple[CalendarEvent, ...]:
        raise CalendarError("bad calendar")

    service = AssistantService(load_calendar_fn=loader)
    service._events = existing
    with pytest.raises(CalendarError):
        service.load_events()
    assert service.events is existing


def test_load_events_rejects_non_tuple_return() -> None:
    def loader(path: str | Path) -> tuple[CalendarEvent, ...]:
        return []  # type: ignore[return-value]

    service = AssistantService(load_calendar_fn=loader)
    with pytest.raises(TypeError, match="must return a tuple"):
        service.load_events()


def test_load_events_rejects_non_calendar_event_elements() -> None:
    def loader(path: str | Path) -> tuple[CalendarEvent, ...]:
        return ("bad",)  # type: ignore[return-value]

    service = AssistantService(load_calendar_fn=loader)
    with pytest.raises(TypeError, match="CalendarEvent instances"):
        service.load_events()


def test_fetch_weather_calls_fetcher_once_and_caches_tuple() -> None:
    hours = (_hour(),)
    loader_calls = 0
    fetch_calls = 0

    def loader(path: str | Path) -> tuple[CalendarEvent, ...]:
        nonlocal loader_calls
        loader_calls += 1
        return ()

    def fetcher() -> tuple[WeatherHour, ...]:
        nonlocal fetch_calls
        fetch_calls += 1
        return hours

    service = AssistantService(load_calendar_fn=loader, fetch_weather_fn=fetcher)
    returned = service.fetch_weather()
    assert returned is hours
    assert service.weather_hours is hours
    assert fetch_calls == 1
    assert loader_calls == 0


def test_fetch_weather_propagates_weather_fetch_error() -> None:
    def fetcher() -> tuple[WeatherHour, ...]:
        raise WeatherFetchError("bad weather")

    service = AssistantService(fetch_weather_fn=fetcher)
    with pytest.raises(WeatherFetchError, match="bad weather"):
        service.fetch_weather()


def test_fetch_weather_preserves_cache_on_failure() -> None:
    existing = (_hour(),)

    def fetcher() -> tuple[WeatherHour, ...]:
        raise WeatherFetchError("bad weather")

    service = AssistantService(fetch_weather_fn=fetcher)
    service._weather_hours = existing
    with pytest.raises(WeatherFetchError):
        service.fetch_weather()
    assert service.weather_hours is existing


def test_fetch_weather_rejects_non_tuple_return() -> None:
    def fetcher() -> tuple[WeatherHour, ...]:
        return []  # type: ignore[return-value]

    service = AssistantService(fetch_weather_fn=fetcher)
    with pytest.raises(TypeError, match="must return a tuple"):
        service.fetch_weather()


def test_fetch_weather_rejects_non_weather_hour_elements() -> None:
    def fetcher() -> tuple[WeatherHour, ...]:
        return ("bad",)  # type: ignore[return-value]

    service = AssistantService(fetch_weather_fn=fetcher)
    with pytest.raises(TypeError, match="WeatherHour instances"):
        service.fetch_weather()


def test_reload_calls_loader_before_fetcher() -> None:
    order: list[str] = []
    events = (_event(),)
    hours = (_hour(),)

    def loader(path: str | Path) -> tuple[CalendarEvent, ...]:
        order.append("load")
        return events

    def fetcher() -> tuple[WeatherHour, ...]:
        order.append("fetch")
        return hours

    service = AssistantService(load_calendar_fn=loader, fetch_weather_fn=fetcher)
    service.reload()
    assert order == ["load", "fetch"]


def test_reload_calls_each_dependency_once() -> None:
    load_count = 0
    fetch_count = 0

    def loader(path: str | Path) -> tuple[CalendarEvent, ...]:
        nonlocal load_count
        load_count += 1
        return (_event(),)

    def fetcher() -> tuple[WeatherHour, ...]:
        nonlocal fetch_count
        fetch_count += 1
        return (_hour(),)

    service = AssistantService(load_calendar_fn=loader, fetch_weather_fn=fetcher)
    service.reload()
    assert load_count == 1
    assert fetch_count == 1


def test_reload_updates_both_caches_on_success() -> None:
    events = (_event(location="Loaded"),)
    hours = (_hour(),)

    service = AssistantService(
        load_calendar_fn=lambda path: events,
        fetch_weather_fn=lambda: hours,
    )
    returned = service.reload()
    assert returned is events
    assert service.events is events
    assert service.weather_hours is hours


def test_reload_does_not_generate_advice() -> None:
    advice_calls = 0

    def generate(event: CalendarEvent, summary: EventWeatherSummary) -> AdviceBundle:
        nonlocal advice_calls
        advice_calls += 1
        return _bundle(event)

    service = AssistantService(
        load_calendar_fn=lambda path: (_event(),),
        fetch_weather_fn=lambda: (_hour(),),
        generate_advice_fn=generate,
    )
    service.reload()
    assert advice_calls == 0


def test_reload_calendar_failure_prevents_weather_fetch() -> None:
    fetch_called = False

    def loader(path: str | Path) -> tuple[CalendarEvent, ...]:
        raise CalendarError("load failed")

    def fetcher() -> tuple[WeatherHour, ...]:
        nonlocal fetch_called
        fetch_called = True
        return ()

    service = AssistantService(load_calendar_fn=loader, fetch_weather_fn=fetcher)
    with pytest.raises(CalendarError):
        service.reload()
    assert fetch_called is False


def test_reload_calendar_failure_preserves_prior_caches() -> None:
    old_events = (_event(location="Old Event"),)
    old_hours = (_hour(),)

    service = AssistantService(
        load_calendar_fn=lambda path: (_ for _ in ()).throw(CalendarError("load failed")),
        fetch_weather_fn=lambda: (_hour(),),
    )
    service._events = old_events
    service._weather_hours = old_hours
    with pytest.raises(CalendarError):
        service.reload()
    assert service.events is old_events
    assert service.weather_hours is old_hours


def test_reload_weather_failure_preserves_prior_caches() -> None:
    old_events = (_event(location="Old Event"),)
    old_hours = (_hour(),)

    service = AssistantService(
        load_calendar_fn=lambda path: (_event(location="New Event"),),
        fetch_weather_fn=lambda: (_ for _ in ()).throw(WeatherFetchError("fetch failed")),
    )
    service._events = old_events
    service._weather_hours = old_hours
    with pytest.raises(WeatherFetchError):
        service.reload()
    assert service.events is old_events
    assert service.weather_hours is old_hours


def test_successful_reload_replaces_old_tuple_references() -> None:
    first_events = (_event(location="First"),)
    first_hours = (_hour(),)
    second_events = (_event(location="Second"),)
    second_hours = (_hour(precipitation_mm=1.0),)
    load_count = 0

    def loader(path: str | Path) -> tuple[CalendarEvent, ...]:
        nonlocal load_count
        load_count += 1
        return first_events if load_count == 1 else second_events

    def fetcher() -> tuple[WeatherHour, ...]:
        return first_hours if load_count == 1 else second_hours

    service = AssistantService(load_calendar_fn=loader, fetch_weather_fn=fetcher)
    service.reload()
    service.reload()
    assert service.events is second_events
    assert service.weather_hours is second_hours


def test_advice_for_event_rejects_non_calendar_event() -> None:
    service = AssistantService()
    with pytest.raises(TypeError, match="CalendarEvent"):
        service.advice_for_event("bad")  # type: ignore[arg-type]


def test_advice_for_event_calls_summarizer_and_generator_once() -> None:
    event = _event()
    weather = (_hour(),)
    summary = EventWeatherSummary(
        status=ForecastStatus.AVAILABLE,
        overlapping_hours=weather,
        min_temperature_c=20.0,
        max_temperature_c=20.0,
        max_precipitation_mm=0.0,
        max_wind_speed_ms=5.0,
        worst_weather_code=0,
    )
    bundle = _bundle(event)
    summarize_calls: list[tuple[CalendarEvent, tuple[WeatherHour, ...]]] = []
    advice_calls: list[tuple[CalendarEvent, EventWeatherSummary]] = []

    def summarize(
        passed_event: CalendarEvent,
        passed_weather: tuple[WeatherHour, ...],
    ) -> EventWeatherSummary:
        summarize_calls.append((passed_event, passed_weather))
        return summary

    def generate(
        passed_event: CalendarEvent,
        passed_summary: EventWeatherSummary,
    ) -> AdviceBundle:
        advice_calls.append((passed_event, passed_summary))
        return bundle

    service = AssistantService(
        summarize_weather_fn=summarize,
        generate_advice_fn=generate,
    )
    service._weather_hours = weather
    returned = service.advice_for_event(event)
    assert returned is bundle
    assert summarize_calls == [(event, weather)]
    assert advice_calls == [(event, summary)]


def test_advice_for_event_does_not_load_or_fetch() -> None:
    load_called = False
    fetch_called = False

    service = AssistantService(
        load_calendar_fn=lambda path: (_ for _ in ()).throw(AssertionError("load")),
        fetch_weather_fn=lambda: (_ for _ in ()).throw(AssertionError("fetch")),
        summarize_weather_fn=lambda event, weather: EventWeatherSummary(
            status=ForecastStatus.FORECAST_UNAVAILABLE,
            overlapping_hours=(),
            min_temperature_c=None,
            max_temperature_c=None,
            max_precipitation_mm=None,
            max_wind_speed_ms=None,
            worst_weather_code=None,
        ),
        generate_advice_fn=lambda event, summary: _bundle(event),
    )
    service.advice_for_event(_event())


def test_advice_for_event_passes_empty_cached_weather() -> None:
    captured: list[tuple[WeatherHour, ...]] = []

    def summarize(event: CalendarEvent, weather: tuple[WeatherHour, ...]) -> EventWeatherSummary:
        captured.append(weather)
        return EventWeatherSummary(
            status=ForecastStatus.FORECAST_UNAVAILABLE,
            overlapping_hours=(),
            min_temperature_c=None,
            max_temperature_c=None,
            max_precipitation_mm=None,
            max_wind_speed_ms=None,
            worst_weather_code=None,
        )

    service = AssistantService(
        summarize_weather_fn=summarize,
        generate_advice_fn=lambda event, summary: _bundle(event),
    )
    service.advice_for_event(_event())
    assert captured == [()]


def test_advice_for_event_rejects_invalid_summarizer_return_type() -> None:
    service = AssistantService(
        summarize_weather_fn=lambda event, weather: "bad",  # type: ignore[return-value]
        generate_advice_fn=lambda event, summary: _bundle(event),
    )
    with pytest.raises(TypeError, match="EventWeatherSummary"):
        service.advice_for_event(_event())


def test_advice_for_event_rejects_invalid_generator_return_type() -> None:
    service = AssistantService(
        summarize_weather_fn=lambda event, weather: EventWeatherSummary(
            status=ForecastStatus.FORECAST_UNAVAILABLE,
            overlapping_hours=(),
            min_temperature_c=None,
            max_temperature_c=None,
            max_precipitation_mm=None,
            max_wind_speed_ms=None,
            worst_weather_code=None,
        ),
        generate_advice_fn=lambda event, summary: "bad",  # type: ignore[return-value]
    )
    with pytest.raises(TypeError, match="AdviceBundle"):
        service.advice_for_event(_event())


def test_advice_for_event_propagates_dependency_exceptions() -> None:
    def summarize(event: CalendarEvent, weather: tuple[WeatherHour, ...]) -> EventWeatherSummary:
        raise RuntimeError("summarizer failed")

    service = AssistantService(
        summarize_weather_fn=summarize,
        generate_advice_fn=lambda event, summary: _bundle(event),
    )
    with pytest.raises(RuntimeError, match="summarizer failed"):
        service.advice_for_event(_event())


def test_advice_for_all_events_empty_when_no_cached_events() -> None:
    service = AssistantService()
    assert service.advice_for_all_events() == ()


def test_advice_for_all_events_returns_tuple_preserving_order() -> None:
    first = _event(location="First")
    second = _event(location="Second")
    service = AssistantService(
        summarize_weather_fn=lambda event, weather: EventWeatherSummary(
            status=ForecastStatus.FORECAST_UNAVAILABLE,
            overlapping_hours=(),
            min_temperature_c=None,
            max_temperature_c=None,
            max_precipitation_mm=None,
            max_wind_speed_ms=None,
            worst_weather_code=None,
        ),
        generate_advice_fn=lambda event, summary: _bundle(event),
    )
    service._events = (second, first)
    bundles = service.advice_for_all_events()
    assert isinstance(bundles, tuple)
    assert [bundle.event.location for bundle in bundles] == ["Second", "First"]


def test_advice_for_all_events_one_bundle_per_event_using_cached_weather() -> None:
    events = (_event(location="A"), _event(location="B"))
    weather = (_hour(),)
    summarize_calls = 0

    def summarize(event: CalendarEvent, passed_weather: tuple[WeatherHour, ...]) -> EventWeatherSummary:
        nonlocal summarize_calls
        summarize_calls += 1
        assert passed_weather is weather
        return EventWeatherSummary(
            status=ForecastStatus.AVAILABLE,
            overlapping_hours=(),
            min_temperature_c=20.0,
            max_temperature_c=20.0,
            max_precipitation_mm=0.0,
            max_wind_speed_ms=5.0,
            worst_weather_code=0,
        )

    service = AssistantService(
        summarize_weather_fn=summarize,
        generate_advice_fn=lambda event, summary: _bundle(event),
    )
    service._events = events
    service._weather_hours = weather
    bundles = service.advice_for_all_events()
    assert len(bundles) == 2
    assert summarize_calls == 2


def test_integration_rainy_travel_event_with_real_summarizer_and_advice() -> None:
    travel_event = _event(location="Metro Bus Station")
    rainy_hour = _hour(precipitation_mm=1.0, weather_code=61)

    service = AssistantService(
        load_calendar_fn=lambda path: (travel_event,),
        fetch_weather_fn=lambda: (rainy_hour,),
        summarize_weather_fn=summarize_event_weather,
        generate_advice_fn=generate_advice,
    )
    service._events = (travel_event,)
    service._weather_hours = (rainy_hour,)

    bundle = service.advice_for_event(travel_event)
    rule_ids = tuple(item.rule_id for item in bundle.items)
    assert "rain_travel" in rule_ids
    rain_item = next(item for item in bundle.items if item.rule_id == "rain_travel")
    message = rain_item.message.lower()
    assert "bus" in message
    assert "umbrella" in message


def test_atomic_reload_preserves_old_identities_after_weather_failure() -> None:
    old_events = (_event(location="Old"),)
    old_hours = (_hour(),)
    load_count = 0

    def loader(path: str | Path) -> tuple[CalendarEvent, ...]:
        nonlocal load_count
        load_count += 1
        return (_event(location=f"Loaded {load_count}"),)

    def fetcher() -> tuple[WeatherHour, ...]:
        if load_count == 1:
            return (_hour(),)
        raise WeatherFetchError("second fetch failed")

    service = AssistantService(load_calendar_fn=loader, fetch_weather_fn=fetcher)
    service.reload()
    first_events = service.events
    first_hours = service.weather_hours

    with pytest.raises(WeatherFetchError):
        service.reload()

    assert service.events is first_events
    assert service.weather_hours is first_hours


def test_cached_tuples_and_domain_objects_remain_unchanged_after_service_use() -> None:
    event = _event(location="Immutable Office")
    hour = _hour(precipitation_mm=0.5)
    events_tuple = (event,)
    hours_tuple = (hour,)
    original_event_state = (event.title, event.start, event.end, event.location)
    original_hour_state = (
        hour.timestamp,
        hour.temperature_c,
        hour.precipitation_mm,
        hour.weather_code,
        hour.wind_speed_ms,
    )

    service = AssistantService(
        load_calendar_fn=lambda path: events_tuple,
        fetch_weather_fn=lambda: hours_tuple,
        summarize_weather_fn=lambda passed_event, weather: EventWeatherSummary(
            status=ForecastStatus.AVAILABLE,
            overlapping_hours=weather,
            min_temperature_c=20.0,
            max_temperature_c=20.0,
            max_precipitation_mm=0.5,
            max_wind_speed_ms=5.0,
            worst_weather_code=0,
        ),
        generate_advice_fn=lambda passed_event, summary: AdviceBundle(
            event=passed_event,
            summary=summary,
            items=(),
        ),
    )

    service.reload()
    assert service.events is events_tuple
    assert service.weather_hours is hours_tuple
    assert isinstance(service.events, tuple)
    assert isinstance(service.weather_hours, tuple)

    bundles = service.advice_for_all_events()
    assert isinstance(bundles, tuple)
    assert len(bundles) == 1
    assert bundles[0].event is event

    assert (event.title, event.start, event.end, event.location) == original_event_state
    assert (
        hour.timestamp,
        hour.temperature_c,
        hour.precipitation_mm,
        hour.weather_code,
        hour.wind_speed_ms,
    ) == original_hour_state
    assert service.events is events_tuple
    assert service.weather_hours is hours_tuple


def test_ast_import_guard_rejects_forbidden_modules() -> None:
    imported: set[str] = set()
    for node in ast.walk(_service_ast()):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden_found = sorted(name for name in imported if name in FORBIDDEN_IMPORT_ROOTS)
    assert forbidden_found == []


def test_ast_call_guard_rejects_forbidden_calls() -> None:
    called: set[str] = set()
    for node in ast.walk(_service_ast()):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called.add(func.id)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)
    forbidden_calls_found = sorted(called & FORBIDDEN_CALLS)
    assert forbidden_calls_found == []


def test_logic_separation_guard_rejects_duplicated_rule_tokens() -> None:
    source = _service_source().lower()
    found = sorted(token for token in FORBIDDEN_LOGIC_TOKENS if token in source)
    assert found == []


def test_runtime_operations_produce_no_stdout_or_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    event = _event(location="Metro Bus Station")
    hour = _hour(precipitation_mm=1.0)
    service = AssistantService(
        load_calendar_fn=lambda path: (event,),
        fetch_weather_fn=lambda: (hour,),
        summarize_weather_fn=summarize_event_weather,
        generate_advice_fn=generate_advice,
    )
    service.load_events()
    service.fetch_weather()
    service.reload()
    service.advice_for_event(event)
    service.advice_for_all_events()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_source_contains_only_ascii_characters() -> None:
    _service_source().encode("ascii")


def test_no_live_network_or_real_file_access_patterns() -> None:
    source = _service_source().lower()
    assert "httpx" not in source
    assert "urllib" not in source
    assert "open(" not in source
    assert "datetime.now" not in source
    assert "date.today" not in source
    assert "random" not in source
    assert "os.environ" not in source
