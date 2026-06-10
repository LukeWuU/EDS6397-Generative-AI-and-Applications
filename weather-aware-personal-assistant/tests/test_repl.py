"""Unit tests for the interactive CLI REPL and formatter."""

from __future__ import annotations

import ast
from datetime import datetime
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
from zoneinfo import ZoneInfo

from assistant.assistant_service import AssistantService
from assistant.cli import formatter, repl
from assistant.cli.formatter import (
    render_advice,
    render_events,
    render_help,
    render_weather,
)
from assistant.cli.repl import run_repl
from assistant.models import (
    AdviceBundle,
    AdviceItem,
    CalendarError,
    CalendarEvent,
    EventWeatherSummary,
    ForecastStatus,
    WeatherFetchError,
    WeatherHour,
)

HOUSTON = ZoneInfo("America/Chicago")

FORBIDDEN_REPL_LOGIC_TOKENS = {
    "rain_travel",
    "rain_gear",
    "severe_weather",
    "RAIN_WMO_CODES",
    "SEVERE_WMO_CODES",
    "RAIN_PRECIP_MM_THRESHOLD",
}


class FakeService:
    def __init__(
        self,
        *,
        events: tuple[CalendarEvent, ...] = (),
        weather_hours: tuple[WeatherHour, ...] = (),
        reload_error: Exception | None = None,
        advice_bundles: tuple[AdviceBundle, ...] | None = None,
    ) -> None:
        self._events = events
        self._weather_hours = weather_hours
        self._reload_error = reload_error
        self._advice_bundles = advice_bundles
        self.reload_calls = 0
        self.advice_calls = 0

    @property
    def events(self) -> tuple[CalendarEvent, ...]:
        return self._events

    @property
    def weather_hours(self) -> tuple[WeatherHour, ...]:
        return self._weather_hours

    def reload(self) -> tuple[CalendarEvent, ...]:
        self.reload_calls += 1
        if self._reload_error is not None:
            raise self._reload_error
        return self._events

    def advice_for_all_events(self) -> tuple[AdviceBundle, ...]:
        self.advice_calls += 1
        if self._advice_bundles is not None:
            return self._advice_bundles
        return ()


def _event(location: str = "Office") -> CalendarEvent:
    return CalendarEvent(
        title="Team Standup",
        start=datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON),
        end=datetime(2026, 6, 10, 9, 30, 0, tzinfo=HOUSTON),
        location=location,
    )


def _hour() -> WeatherHour:
    return WeatherHour(
        timestamp=datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON),
        temperature_c=28.0,
        precipitation_mm=0.0,
        weather_code=0,
        wind_speed_ms=5.0,
    )


def _bundle(event: CalendarEvent | None = None) -> AdviceBundle:
    event = event or _event()
    summary = EventWeatherSummary(
        status=ForecastStatus.AVAILABLE,
        overlapping_hours=(),
        min_temperature_c=20.0,
        max_temperature_c=20.0,
        max_precipitation_mm=0.0,
        max_wind_speed_ms=5.0,
        worst_weather_code=0,
    )
    item = AdviceItem(
        priority=7,
        category="general",
        message="No special weather precautions are indicated.",
        rule_id="normal",
    )
    return AdviceBundle(event=event, summary=summary, items=(item,))


def _console() -> tuple[Console, StringIO]:
    output = StringIO()
    return Console(file=output, width=120, force_terminal=True), output


def _run_with_inputs(
    inputs: list[str],
    *,
    service: FakeService | None = None,
) -> tuple[StringIO, FakeService]:
    console, output = _console()
    active_service = service or FakeService(events=(_event(),), weather_hours=(_hour(),))
    input_iter = iter(inputs)

    def scripted_input(prompt: str) -> str:
        return next(input_iter)

    run_repl(active_service, console=console, input_fn=scripted_input)
    return output, active_service


def test_help_displays_supported_commands() -> None:
    output, _ = _run_with_inputs(["help", "quit"])
    text = output.getvalue().lower()
    assert "help" in text
    assert "events" in text
    assert "weather" in text
    assert "advice" in text
    assert "reload" in text
    assert "quit / exit" in text


def test_events_uses_cached_events_without_reload() -> None:
    service = FakeService(events=(_event(location="Cached Office"),))
    output, active_service = _run_with_inputs(["events", "quit"], service=service)
    assert active_service.reload_calls == 1
    assert "Cached Office" in output.getvalue()


def test_weather_uses_cached_weather_without_fetch() -> None:
    service = FakeService(events=(_event(),), weather_hours=(_hour(),))
    output, active_service = _run_with_inputs(["weather", "quit"], service=service)
    assert active_service.reload_calls == 1
    assert "Hourly Forecast" in output.getvalue()
    assert "28" in output.getvalue()


def test_advice_calls_service_advice_for_all_events() -> None:
    bundle = _bundle()
    service = FakeService(
        events=(_event(),),
        weather_hours=(_hour(),),
        advice_bundles=(bundle,),
    )
    output, active_service = _run_with_inputs(["advice", "quit"], service=service)
    assert active_service.advice_calls == 1
    text = output.getvalue()
    assert "Team Standup" in text
    assert "general / normal" in text
    assert "No special weather precautions are indicated." in text


def test_reload_command_calls_service_reload() -> None:
    service = FakeService(events=(_event(),), weather_hours=(_hour(),))
    output, active_service = _run_with_inputs(["reload", "quit"], service=service)
    assert active_service.reload_calls == 2
    assert "Reloaded" in output.getvalue()


def test_quit_and_exit_exit_gracefully() -> None:
    for command in ("quit", "exit"):
        output, _ = _run_with_inputs([command], service=FakeService())
        assert "Goodbye" in output.getvalue()


def test_unknown_command_shows_help_hint_and_continues() -> None:
    output, _ = _run_with_inputs(["forecast", "quit"], service=FakeService())
    text = output.getvalue()
    assert "Unknown command" in text
    assert "help" in text.lower()
    assert "Goodbye" in text


def test_empty_input_does_not_crash() -> None:
    output, _ = _run_with_inputs(["", "quit"], service=FakeService())
    assert "Enter a command" in output.getvalue()


def test_command_matching_is_case_insensitive_and_whitespace_tolerant() -> None:
    service = FakeService(events=(_event(),), weather_hours=(_hour(),))
    output, active_service = _run_with_inputs(["  HELP  ", "quit"], service=service)
    assert "Commands" in output.getvalue()


def test_startup_reload_success_shows_success_message() -> None:
    service = FakeService(events=(_event(),), weather_hours=(_hour(),))
    output, active_service = _run_with_inputs(["quit"], service=service)
    assert active_service.reload_calls == 1
    assert "Loaded 1 event(s) and 1 weather hour(s)" in output.getvalue()


def test_startup_calendar_error_keeps_repl_available() -> None:
    service = FakeService(reload_error=CalendarError("bad calendar"))
    output, _ = _run_with_inputs(["help", "quit"], service=service)
    text = output.getvalue()
    assert "Calendar error" in text
    assert "Commands" in text
    assert "Traceback" not in text


def test_startup_weather_error_keeps_repl_available() -> None:
    service = FakeService(reload_error=WeatherFetchError("bad weather"))
    output, _ = _run_with_inputs(["events", "quit"], service=service)
    text = output.getvalue()
    assert "Weather error" in text
    assert "No calendar events are currently loaded" in text
    assert "Traceback" not in text


def test_reload_calendar_error_in_loop_is_user_facing() -> None:
    service = FakeService(events=(_event(),), weather_hours=(_hour(),))

    def failing_reload() -> tuple[CalendarEvent, ...]:
        service.reload_calls += 1
        if service.reload_calls >= 2:
            raise CalendarError("reload failed")
        return service._events

    service.reload = failing_reload  # type: ignore[method-assign]
    output, _ = _run_with_inputs(["reload", "quit"], service=service)
    assert "Calendar error: reload failed" in output.getvalue()
    assert "Traceback" not in output.getvalue()


def test_reload_weather_error_in_loop_is_user_facing() -> None:
    service = FakeService(events=(_event(),), weather_hours=(_hour(),))

    def failing_reload() -> tuple[CalendarEvent, ...]:
        service.reload_calls += 1
        if service.reload_calls >= 2:
            raise WeatherFetchError("reload failed")
        return service._events

    service.reload = failing_reload  # type: ignore[method-assign]
    output, _ = _run_with_inputs(["reload", "quit"], service=service)
    assert "Weather error: reload failed" in output.getvalue()
    assert "Traceback" not in output.getvalue()


def test_eof_exits_gracefully() -> None:
    console, output = _console()
    service = FakeService()

    def raise_eof(prompt: str) -> str:
        raise EOFError

    run_repl(service, console=console, input_fn=raise_eof)
    assert "Goodbye" in output.getvalue()


def test_keyboard_interrupt_exits_gracefully() -> None:
    console, output = _console()
    service = FakeService()

    def raise_interrupt(prompt: str) -> str:
        raise KeyboardInterrupt

    run_repl(service, console=console, input_fn=raise_interrupt)
    assert "Goodbye" in output.getvalue()


def test_events_empty_message() -> None:
    console, output = _console()
    render_events(console, ())
    assert "No calendar events are currently loaded" in output.getvalue()


def test_weather_empty_message() -> None:
    console, output = _console()
    render_weather(console, ())
    assert "No weather forecast is currently loaded" in output.getvalue()


def test_advice_empty_message() -> None:
    console, output = _console()
    render_advice(console, ())
    assert "No calendar events are currently loaded" in output.getvalue()


def test_formatter_shows_missing_weather_values_as_dash() -> None:
    hour = WeatherHour(
        timestamp=datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON),
        temperature_c=None,
        precipitation_mm=None,
        weather_code=None,
        wind_speed_ms=None,
    )
    console, output = _console()
    render_weather(console, (hour,))
    assert output.getvalue().count("-") >= 4


def test_main_entry_point_calls_run_repl(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def fake_run_repl() -> None:
        called["value"] = True

    monkeypatch.setattr("assistant.__main__.run_repl", fake_run_repl)
    from assistant.__main__ import main

    main()
    assert called["value"] is True


def test_repl_source_has_no_duplicated_advice_logic_tokens() -> None:
    source = Path(repl.__file__).read_text(encoding="utf-8").lower()
    found = sorted(token.lower() for token in FORBIDDEN_REPL_LOGIC_TOKENS if token.lower() in source)
    assert found == []


def test_formatter_source_has_no_duplicated_advice_logic_tokens() -> None:
    source = Path(formatter.__file__).read_text(encoding="utf-8").lower()
    found = sorted(token.lower() for token in FORBIDDEN_REPL_LOGIC_TOKENS if token.lower() in source)
    assert found == []


def test_repl_ast_has_no_direct_builtin_input_calls() -> None:
    tree = ast.parse(Path(repl.__file__).read_text(encoding="utf-8"))
    direct_input_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "input":
            direct_input_calls.append(node)
    assert direct_input_calls == []


def test_repl_does_not_call_run_repl_recursively() -> None:
    source = Path(repl.__file__).read_text(encoding="utf-8")
    assert source.count("run_repl(") == 1
