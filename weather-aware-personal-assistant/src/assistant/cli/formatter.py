"""Rich presentation helpers for the weather-aware assistant CLI."""

from __future__ import annotations

from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from assistant.models import AdviceBundle, CalendarEvent, WeatherHour

_MISSING_VALUE = "-"


def render_welcome(console: Console) -> None:
    """Display the REPL welcome panel."""
    console.print(
        Panel(
            "Weather-Aware Personal Assistant\n"
            "Type 'help' for available commands.",
            title="Welcome",
            border_style="blue",
        )
    )


def render_help(console: Console) -> None:
    """Display supported REPL commands."""
    table = Table(title="Commands", show_header=True, header_style="bold")
    table.add_column("Command")
    table.add_column("Description")
    table.add_row("help", "Show available commands")
    table.add_row("events", "List loaded calendar events")
    table.add_row("weather", "Show loaded hourly forecast")
    table.add_row("advice", "Show weather-aware advice for each event")
    table.add_row("reload", "Reload calendar and weather data")
    table.add_row("quit / exit", "Exit the assistant")
    console.print(table)


def render_events(console: Console, events: tuple[CalendarEvent, ...]) -> None:
    """Render cached calendar events."""
    if not events:
        render_info(
            console,
            "No calendar events are currently loaded. Use 'reload' to try again.",
        )
        return

    table = Table(title="Calendar Events", show_header=True, header_style="bold")
    table.add_column("Title")
    table.add_column("Start")
    table.add_column("End")
    table.add_column("Location")
    for event in events:
        table.add_row(
            event.title,
            _format_datetime(event.start),
            _format_datetime(event.end),
            event.location,
        )
    console.print(table)


def render_weather(console: Console, weather_hours: tuple[WeatherHour, ...]) -> None:
    """Render cached hourly weather."""
    if not weather_hours:
        render_info(
            console,
            "No weather forecast is currently loaded. Use 'reload' to try again.",
        )
        return

    table = Table(title="Hourly Forecast", show_header=True, header_style="bold")
    table.add_column("Timestamp")
    table.add_column("Temp (C)")
    table.add_column("Precip (mm)")
    table.add_column("Weather Code")
    table.add_column("Wind (m/s)")
    for hour in weather_hours:
        table.add_row(
            _format_datetime(hour.timestamp),
            _format_optional_float(hour.temperature_c),
            _format_optional_float(hour.precipitation_mm),
            _format_optional_int(hour.weather_code),
            _format_optional_float(hour.wind_speed_ms),
        )
    console.print(table)


def render_advice(console: Console, bundles: tuple[AdviceBundle, ...]) -> None:
    """Render advice bundles for cached events."""
    if not bundles:
        render_info(
            console,
            "No calendar events are currently loaded. Use 'reload' to try again.",
        )
        return

    for bundle in bundles:
        event = bundle.event
        lines = [
            f"Time: {_format_datetime(event.start)} to {_format_datetime(event.end)}",
            f"Location: {event.location}",
        ]
        if bundle.items:
            lines.append("Advice:")
            for item in bundle.items:
                lines.append(
                    f"- {item.category} / {item.rule_id}: {item.message}"
                )
        else:
            lines.append("Advice: No advice items available.")
        console.print(
            Panel(
                "\n".join(lines),
                title=event.title,
                border_style="green",
            )
        )


def render_success(console: Console, message: str) -> None:
    """Display a success message."""
    console.print(Panel(message, title="Success", border_style="green"))


def render_error(console: Console, message: str) -> None:
    """Display a user-facing error message."""
    console.print(Panel(message, title="Error", border_style="red"))


def render_info(console: Console, message: str) -> None:
    """Display an informational message."""
    console.print(Panel(message, title="Info", border_style="cyan"))


def _format_datetime(value: datetime) -> str:
    return value.isoformat(sep=" ", timespec="seconds")


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return _MISSING_VALUE
    return f"{value:g}"


def _format_optional_int(value: int | None) -> str:
    if value is None:
        return _MISSING_VALUE
    return str(value)
