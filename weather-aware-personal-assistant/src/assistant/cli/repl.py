"""Interactive REPL for the weather-aware personal assistant."""

from __future__ import annotations

from collections.abc import Callable

from rich.console import Console

from assistant.assistant_service import AssistantService, create_default_service
from assistant.cli.formatter import (
    render_advice,
    render_error,
    render_events,
    render_help,
    render_info,
    render_success,
    render_weather,
    render_welcome,
)
from assistant.models import CalendarError, WeatherFetchError

_PROMPT = "assistant> "


def run_repl(
    service: AssistantService | None = None,
    *,
    console: Console | None = None,
    input_fn: Callable[[str], str] = input,
) -> None:
    """Run the interactive assistant REPL."""
    active_service = service if service is not None else create_default_service()
    active_console = console if console is not None else Console()

    render_welcome(active_console)
    _attempt_startup_reload(active_service, active_console)

    while True:
        try:
            raw_command = input_fn(_PROMPT)
        except (EOFError, KeyboardInterrupt):
            active_console.print()
            render_info(active_console, "Goodbye.")
            return

        command = raw_command.strip().lower()
        if not command:
            render_info(active_console, "Enter a command or type 'help'.")
            continue

        if command in {"quit", "exit"}:
            render_info(active_console, "Goodbye.")
            return

        if _dispatch_command(command, active_service, active_console):
            continue

        render_error(
            active_console,
            f"Unknown command '{raw_command.strip()}'. Type 'help' for available commands.",
        )


def _attempt_startup_reload(service: AssistantService, console: Console) -> None:
    try:
        service.reload()
    except CalendarError as exc:
        render_error(console, f"Calendar error: {exc}")
        return
    except WeatherFetchError as exc:
        render_error(console, f"Weather error: {exc}")
        return

    render_success(
        console,
        f"Loaded {len(service.events)} event(s) and {len(service.weather_hours)} weather hour(s).",
    )


def _dispatch_command(
    command: str,
    service: AssistantService,
    console: Console,
) -> bool:
    if command == "help":
        render_help(console)
        return True

    if command == "events":
        render_events(console, service.events)
        return True

    if command == "weather":
        render_weather(console, service.weather_hours)
        return True

    if command == "advice":
        render_advice(console, service.advice_for_all_events())
        return True

    if command == "reload":
        _handle_reload(service, console)
        return True

    return False


def _handle_reload(service: AssistantService, console: Console) -> None:
    try:
        service.reload()
    except CalendarError as exc:
        render_error(console, f"Calendar error: {exc}")
        return
    except WeatherFetchError as exc:
        render_error(console, f"Weather error: {exc}")
        return

    render_success(
        console,
        f"Reloaded {len(service.events)} event(s) and {len(service.weather_hours)} weather hour(s).",
    )
